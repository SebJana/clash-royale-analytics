from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from rapidfuzz import fuzz
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

from core.deps import RedConn
from redis_service import get_redis_json, set_redis_json, build_redis_key
from helpers.auth import get_captcha_text_from_cache, get_wordle_challenge_from_cache
from models.schema import (
    SecurityQuestionsRequest,
    CaptchaAnswerRequest,
    NYTWordleAnswerRequest,
    WordleAnswerRequest,
)
from core.jwt import create_access_token, validate_access_token, AvailableTokenTypes
from core.wordle import (
    get_todays_nyt_wordle,
    pick_random_wordle_solution,
    is_valid_guess,
    evaluate_guess,
    is_guess_solution,
)
from core.validate import valid_timezone
from core.generate_captcha import generate_captcha_string, generate_captcha_image

from core.settings import settings

router = APIRouter(prefix="/auth", tags=["Authorization"])

# Authentication Flow:
# 1) Captcha:
#    1.1) Client requests a captcha_id
#    1.2) Client fetches the captcha image using that id
#    1.3) Client submits the solution → receives a captcha_token
#
# 2) Wordle:
#    Requires captcha_token; correct Wordle answer → wordle_token
#
# 3) Security Questions:
#    Requires wordle_token; correct answers → security_token

# 4) Auth Token:
#    Client exchanges wordle_token for final auth token (grants access)


@router.get("/captcha_id")
async def get_captcha_id(redis_conn: RedConn):
    """Generate a new captcha ID and store the associated text in Redis cache.

    Creates a unique captcha ID and generates random text for the challenge.
    The captcha text is stored using version_ahead=True to ensure the captcha
    remains valid for its full TTL even if a cache version refresh occurs.

    Args:
        redis_conn (RedConn): Redis connection instance.

    Returns:
        dict: Dictionary containing the generated captcha_id.
    """
    text = generate_captcha_string(settings.CAPTCHA_CHAR_LENGTH)
    captcha_id = str(uuid.uuid4())

    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="captchaText",
        version_ahead=True,
        params={"captcha_id": captcha_id},
    )

    await set_redis_json(
        redis_conn, key, value=text, ttl=settings.CACHE_TTL_CAPTCHA_CHALLENGE
    )

    return {"captcha_id": captcha_id}


@router.get("/captcha_image/{captcha_id}")
async def get_captcha_image(redis_conn: RedConn, captcha_id: str):

    # Check the redis cache for both the current and ahead version
    text = await get_captcha_text_from_cache(redis_conn, captcha_id=captcha_id)

    if not text:
        raise HTTPException(
            status_code=404,
            detail="No captcha image generated, no valid captcha id given or expired.",
        )

    image = generate_captcha_image(text)

    # Return the image with the session ID in headers
    return Response(
        content=image,
        media_type="image/png",
    )


@router.post("/verify_captcha")
async def get_captcha_token(redis_conn: RedConn, req: CaptchaAnswerRequest):

    # Check the redis cache for both the current and ahead version
    text = await get_captcha_text_from_cache(redis_conn, captcha_id=req.captcha_id)

    if not text:
        raise HTTPException(
            status_code=404,
            detail="No captcha generated, no valid captcha id given or expired.",
        )

    # Check if stored and given answer match
    if req.answer == text:
        return {
            "captcha_token": create_access_token(type=AvailableTokenTypes.CAPTCHA.value)
        }

    raise HTTPException(
        status_code=401, detail="No captcha token generated, incorrect answer given."
    )


@router.get("/wordle_id")
async def get_wordle_id(redis_conn: RedConn):

    wordle = pick_random_wordle_solution()
    wordle_id = str(uuid.uuid4())

    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="wordleSolution",
        version_ahead=True,
        params={"wordle_id": wordle_id},
    )

    await set_redis_json(
        redis_conn,
        key,
        value={"solution": wordle, "guesses": 0},
        ttl=settings.CACHE_TTL_CAPTCHA_CHALLENGE,
    )

    return {"wordle_id": wordle_id}


@router.post("/verify_wordle")
async def get_wordle_token(redis_conn: RedConn, req: WordleAnswerRequest):

    if not validate_access_token(req.captcha_token, AvailableTokenTypes.CAPTCHA.value):
        raise HTTPException(
            status_code=403,
            detail="No authorization token generated, invalid captcha token given",
        )

    # Extract the wordle session to the given wordle_id
    wordle_session, key = await get_wordle_challenge_from_cache(
        redis_conn, req.wordle_id
    )

    # Session not found (either expired or non existent id given)
    if not wordle_session:
        raise HTTPException(
            status_code=404,
            detail="No valid wordle id given or the wordle challenge expired.",
        )

    # The session JSON is corrupted, abort session to not give up token on empty solution or similar problems
    if "guesses" not in wordle_session or "solution" not in wordle_session:
        raise HTTPException(
            status_code=500,
            detail="Something went wrong, try again with a new wordle challenge.",
        )

    # Extract all needed fields
    solution = wordle_session.get("solution")
    guesses = wordle_session.get("guesses")
    guess = req.wordle_guess.lower()

    # Check if all guesses have been used up
    if guesses >= settings.MAX_WORDLE_GUESSES:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum amount of guesses reached, the word was {solution}, try again with a new wordle challenge.",
        )

    # Upon a non valid guess, reject guess and don't charge a guess
    if not is_valid_guess(guess):
        raise HTTPException(
            status_code=422,
            detail=f"{guess} is not a valid guess, try again with a different word",
        )

    # Check the guess and if it is the solution
    evaluation = evaluate_guess(solution, guess)
    is_solution = is_guess_solution(solution, guess)
    wordle_token = ""

    # If it is, generate a wordle token
    if is_solution:
        wordle_token = create_access_token(type=AvailableTokenTypes.WORDLE.value)

    # Update the 'guesses' count
    updated_challenge = {"solution": solution, "guesses": guesses + 1}
    # Calculate the remaining ones, always 0 or bigger upon any issue
    remaining_guesses = max(settings.MAX_WORDLE_GUESSES - (guesses + 1), 0)

    # Save the updated session again
    # NOTE: resets the previous TTL
    await set_redis_json(
        redis_conn, key, updated_challenge, settings.CACHE_TTL_WORDLE_CHALLENGE
    )

    result = {
        "evaluation": evaluation,
        "remaining_guesses": remaining_guesses,
        "is_solution": is_solution,
        "wordle_token": wordle_token,
    }

    # Reveal the answer upon no more guesses left
    if remaining_guesses == 0:
        result["solution"] = solution

    return result


# NOTE: DEPRECATED Wordle token endpoint
# This route requires users to solve the actual New York Times daily Wordle.
# While simpler to implement, it is much easier to bypass (the answer can be looked up
# or brute-retrieved after the 6 allowed attempts). The custom Wordle challenge endpoint
# is preferred, as it is more secure and more engaging for human users [and definitely more frustrating too ;)].
"""
@router.post("/verify_wordle_nyt")
async def get_nyt_wordle_token(redis_conn: RedConn, req: NYTWordleAnswerRequest):

    if not validate_access_token(req.captcha_token, AvailableTokenTypes.CAPTCHA.value):
        raise HTTPException(
            status_code=403,
            detail="No authorization token generated, invalid captcha token given",
        )

    if not valid_timezone(req.timezone):
        raise HTTPException(
            status_code=422,
            detail=f"No wordle token generated, timezone {req.timezone} doesn't exist.",
        )

    todays_wordle = ""
    # Convert current time to user's timezone to get correct date for their location
    today_str = datetime.now(ZoneInfo(req.timezone)).date().isoformat()

    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="wordleAnswer",
        params={"timezone": req.timezone},
    )
    cached_wordle_answer = await get_redis_json(redis_conn, key)

    # Verify cached answer is from today's date to prevent using yesterday's answer
    if cached_wordle_answer and cached_wordle_answer.get("print_date", "") == today_str:
        todays_wordle = cached_wordle_answer.get("solution", "").lower()
    # If not get todays answer from the Wordle-API
    else:
        try:
            response = await get_todays_nyt_wordle(req.timezone)
        # Prevent authentication if we can't verify the correct answer
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Today's wordle answer can't be checked, the Wordle API seems to be having issues.",
            )
        if response:
            todays_wordle = response.get("solution", "").lower()
            # Store in cache to avoid repeated API calls throughout the day
            await set_redis_json(
                redis_conn, key, response, ttl=settings.CACHE_TTL_NYT_WORDLE_ANSWER
            )

    # If the guess and answer are the matching, generate the wordle token
    if todays_wordle.lower() == req.wordle_guess.lower():
        return {
            "wordle_token": create_access_token(type=AvailableTokenTypes.WORDLE.value)
        }

    raise HTTPException(
        status_code=401,
        detail="No wordle token generated, incorrect answer given.",
    )
"""


# NOTE: this is in no way, shape or form a secure protection for the authentication access
# mostly implemented as a fun way to have SOME sort of access denial
# For a more secure protection one of the answers could be an actual password instead of a card, in that
# case fuzzy matching and the .lower() comparison should be adjusted (set settings.SECURITY_FUZZY_THRESHOLD to 100)
@router.post("/verify_security_questions")
async def get_security_token(req: SecurityQuestionsRequest):

    if not validate_access_token(req.wordle_token, AvailableTokenTypes.WORDLE.value):
        raise HTTPException(
            status_code=401,
            detail="No access granted to answer security questions",
        )

    # Calculate similarity ratios for all three security questions using fuzzy matching
    q1 = fuzz.ratio(settings.MOST_ANNOYING_CARD.lower(), req.most_annoying_card.lower())
    q2 = fuzz.ratio(settings.MOST_SKILLFUL_CARD.lower(), req.most_skillful_card.lower())
    q3 = fuzz.ratio(settings.MOST_MOUSEY_CARD.lower(), req.most_mousey_card.lower())

    # Allow slight typos by using fuzzy matching
    if min(q1, q2, q3) >= settings.SECURITY_FUZZY_THRESHOLD:
        # Generate and return a valid token upon matching answers
        return {
            "security_token": create_access_token(
                type=AvailableTokenTypes.SECURITY.value
            )
        }

    raise HTTPException(
        status_code=401, detail="No security token generated, incorrect answers given."
    )


@router.post("/token")
async def get_auth_token(security_token: str):

    if not validate_access_token(security_token, AvailableTokenTypes.SECURITY.value):
        raise HTTPException(
            status_code=401,
            detail="No authorization token generated, invalid token given",
        )

    return {"auth_token": create_access_token(type=AvailableTokenTypes.AUTH.value)}
