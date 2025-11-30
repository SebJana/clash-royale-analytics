from fastapi import APIRouter, HTTPException, Depends
from rapidfuzz import fuzz
from datetime import date, datetime
from zoneinfo import ZoneInfo


from core.deps import (
    DbConn,
    CrApi,
    RedConn,
    require_tracked_player,
    extract_security_token,
    extract_wordle_token,
)
from redis_service import get_redis_json, set_redis_json, build_redis_key
from core.jwt import create_access_token, validate_access_token
from core.wordle import get_todays_wordle
from core.validate import valid_timezone
from clash_royale_api import ClashRoyaleMaintenanceError
from mongo import (
    get_tracked_players,
    insert_tracked_player,
    deactivate_tracked_player,
    get_players_count,
)
from core.settings import settings

router = APIRouter(prefix="/players", tags=["Tracked Players"])


@router.get("")
async def list_tracked_players(mongo_conn: DbConn):
    try:
        players = await get_tracked_players(mongo_conn)
        return {"activePlayers": players}
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to fetch all tracked players"
        )


@router.get("/count")
async def fetch_tracked_player_count(mongo_conn: DbConn):
    try:
        players_count = await get_players_count(mongo_conn)
        return {"activePlayerCount": players_count}
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to fetch the count of all tracked players"
        )


# NOTE: this is in no way, shape or form a secure protection for the admin access
# mostly implemented as a fun way to have SOME sort of access denial
# For a more secure protection one of the answers could be an actual password tho, instead of a card
@router.get("/security_token")
async def get_security_token(
    most_annoying_card: str, most_skillful_card: str, most_mousey_card: str
):
    # Calculate similarity ratios for all three security questions using fuzzy matching
    q1 = fuzz.ratio(settings.MOST_ANNOYING_CARD.lower(), most_annoying_card.lower())
    q2 = fuzz.ratio(settings.MOST_SKILLFUL_CARD.lower(), most_skillful_card.lower())
    q3 = fuzz.ratio(settings.MOST_MOUSEY_CARD.lower(), most_mousey_card.lower())

    # Allow slight typos by using fuzzy matching
    if min(q1, q2, q3) >= settings.SECURITY_FUZZY_THRESHOLD:
        # Generate and return a valid token upon matching answers
        return {"security_token": create_access_token(type="security")}

    raise HTTPException(
        status_code=403, detail="No security token generated, incorrect answers given."
    )


@router.get("/wordle_token")
async def get_wordle_token(wordle_guess: str, timezone: str, redis_conn: RedConn):

    if not valid_timezone(timezone):
        raise HTTPException(
            status_code=403,
            detail=f"No wordle token generated, timezone {timezone} doesn't exist.",
        )

    todays_wordle = ""
    # Convert current time to user's timezone to get correct date for their location
    today_str = datetime.now(ZoneInfo(timezone)).date().isoformat()

    key = await build_redis_key(
        conn=redis_conn,
        service="crApi",
        resource="wordleAnswer",
        params={"timezone": timezone},
    )
    cached_wordle_answer = await get_redis_json(redis_conn, key)

    # Verify cached answer is from today's date to prevent using yesterday's answer
    if cached_wordle_answer and cached_wordle_answer.get("print_date", "") == today_str:
        todays_wordle = cached_wordle_answer.get("solution", "").lower()
    # If not get todays answer from the Wordle-API
    else:
        try:
            response = await get_todays_wordle(timezone)
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
    if todays_wordle.lower() == wordle_guess.lower():
        return {"wordle_token": create_access_token(type="wordle")}

    raise HTTPException(
        status_code=403,
        detail="No wordle token generated, incorrect answer given.",
    )


@router.post("/{player_tag}")
async def add_tracked_player(player_tag: str, mongo_conn: DbConn, cr_api: CrApi):
    try:
        player = await cr_api.check_existing_player(player_tag)
        # API returns empty response when player doesn't exist
        if not player:
            raise HTTPException(
                status_code=404, detail=f"Player with tag {player_tag} does not exist"
            )
    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)

    try:
        status_insert = await insert_tracked_player(mongo_conn, player_tag, player)

        if status_insert == "reactivated":
            return {"status": "Player is now being tracked again", "tag": player_tag}
        if status_insert == "created":
            return {"status": "Player is now being tracked", "tag": player_tag}
        if status_insert == "already_tracked":
            return {"status": "Player is already being tracked", "tag": player_tag}

        return {"status": "Player is being tracked", "tag": player_tag}

    except Exception:
        raise HTTPException(
            status_code=500, detail=f"Player {player_tag} could not be tracked"
        )


@router.delete("/{player_tag}")
async def remove_tracked_player(
    mongo_conn: DbConn,
    security_token: str = Depends(extract_security_token),
    wordle_token: str = Depends(extract_wordle_token),
    player_tag: str = Depends(require_tracked_player),
):
    try:
        # Require both security questions AND wordle tokens for admin operations
        if not validate_access_token(
            security_token, "security"
        ) or not validate_access_token(wordle_token, "wordle"):
            raise HTTPException(
                status_code=403,
                detail="No admin access granted to un-track players",
            )

        affected_player_count = await deactivate_tracked_player(mongo_conn, player_tag)

        # Database operation returns 0 if no matching records were modified
        if affected_player_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Player with tag {player_tag} is not being tracked",
            )

        return {"status": "Player is not being tracked anymore", "tag": player_tag}

    except HTTPException:
        raise  # keep original FastAPI errors
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=f"Player {player_tag} could not be removed from tracking",
        )
