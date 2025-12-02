from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from rapidfuzz import fuzz
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

from core.deps import RedConn
from redis_service import get_redis_json, set_redis_json, build_redis_key
from models.schema import (
    SecurityQuestionsRequest,
    CaptchaAnswerRequest,
    WordleAnswerRequest,
)
from core.jwt import create_access_token, validate_access_token, AvailableTokenTypes
from core.wordle import get_todays_wordle
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
# 2) Security Questions:
#    Requires captcha_token; correct answers → security_token
#
# 3) Wordle:
#    Requires security_token; correct Wordle answer → wordle_token
#
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


async def get_captcha_text_from_cache(redis_conn, captcha_id: str):
    """Retrieve captcha text from Redis cache using the captcha ID.

    Checks both current and ahead versions of the cache key to find
    the stored captcha text associated with the given captcha ID.

    Args:
        redis_conn: Redis connection instance.
        captcha_id (str): Unique identifier for the captcha challenge.

    Returns:
        str or None: The stored captcha text if found, None otherwise.
    """
    # Check the redis cache for both the current and ahead version
    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="captchaText",
        params={"captcha_id": captcha_id},
    )

    key_ahead = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="captchaText",
        version_ahead=True,
        params={"captcha_id": captcha_id},
    )

    text = await get_redis_json(redis_conn, key_ahead) or await get_redis_json(
        redis_conn, key
    )

    return text


@router.get("/captcha_image/{captcha_id}")
async def get_captcha_image(redis_conn: RedConn, captcha_id: str):

    # Check the redis cache for both the current and ahead version
    text = await get_captcha_text_from_cache(redis_conn, captcha_id=captcha_id)

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

    # Check if stored and given answer match
    if req.answer == text:
        return {
            "captcha_token": create_access_token(type=AvailableTokenTypes.CAPTCHA.value)
        }

    raise HTTPException(
        status_code=403, detail="No captcha token generated, incorrect answer given."
    )


# NOTE: this is in no way, shape or form a secure protection for the authentication access
# mostly implemented as a fun way to have SOME sort of access denial
# For a more secure protection one of the answers could be an actual password instead of a card, in that
# case fuzzy matching and the .lower() comparison should be adjusted (set settings.SECURITY_FUZZY_THRESHOLD to 100)
@router.post("/verify_security_questions")
async def get_security_token(req: SecurityQuestionsRequest):

    if not validate_access_token(req.captcha_token, AvailableTokenTypes.CAPTCHA.value):
        raise HTTPException(
            status_code=403,
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
        status_code=403, detail="No security token generated, incorrect answers given."
    )


@router.post("/verify_wordle")
async def get_wordle_token(redis_conn: RedConn, req: WordleAnswerRequest):

    if not valid_timezone(req.timezone):
        raise HTTPException(
            status_code=403,
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
            response = await get_todays_wordle(req.timezone)
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
                redis_conn, key, response, ttl=settings.CACHE_TTL_WORDLE_ANSWER
            )

    # If the guess and answer are the matching, generate the wordle token
    if todays_wordle.lower() == req.wordle_guess.lower():
        return {
            "wordle_token": create_access_token(type=AvailableTokenTypes.WORDLE.value)
        }

    raise HTTPException(
        status_code=403,
        detail="No wordle token generated, incorrect answer given.",
    )


@router.post("/token")
async def get_auth_token(wordle_token: str):

    if not validate_access_token(wordle_token, AvailableTokenTypes.WORDLE.value):
        raise HTTPException(
            status_code=403,
            detail="No authorization token generated, invalid token given",
        )

    return {"auth_token": create_access_token(type=AvailableTokenTypes.AUTH.value)}
