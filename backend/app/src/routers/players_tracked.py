from fastapi import APIRouter, HTTPException, Depends
from rapidfuzz import fuzz

from core.deps import DbConn, CrApi, require_tracked_player, extract_admin_token
from core.jwt import create_admin_token, validate_admin_token
from clash_royale_api import ClashRoyaleMaintenanceError
from models.schema import SecurityQuestionsRequest
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
@router.post("/admin_token")
async def get_admin_token(answers: SecurityQuestionsRequest):
    q1 = fuzz.ratio(
        settings.MOST_ANNOYING_CARD.lower(), answers.most_annoying_card.lower()
    )
    q2 = fuzz.ratio(
        settings.MOST_SKILLFUL_CARD.lower(), answers.most_skillful_card.lower()
    )
    q3 = fuzz.ratio(settings.MOST_MOUSEY_CARD.lower(), answers.most_mousey_card.lower())

    # Allow slight typos by using fuzzy matching
    if min(q1, q2, q3) >= settings.SECURITY_FUZZY_THRESHOLD:
        # Generate and return a valid token upon matching answers
        return {"admin_token": create_admin_token()}

    raise HTTPException(
        status_code=403,
        detail="No admin token generated, incorrect answers",
    )


@router.post("/{player_tag}")
async def add_tracked_player(player_tag: str, mongo_conn: DbConn, cr_api: CrApi):
    try:
        player = await cr_api.check_existing_player(player_tag)
        # Check if an empty string was returned --> player with that tag doesn't exist
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
    admin_token: str = Depends(extract_admin_token),
    player_tag: str = Depends(require_tracked_player),
):
    try:
        # Check if request has a valid admin token
        if not validate_admin_token(admin_token):
            raise HTTPException(
                status_code=403,
                detail="No admin access granted to un-track players",
            )

        affected_player_count = await deactivate_tracked_player(mongo_conn, player_tag)

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
