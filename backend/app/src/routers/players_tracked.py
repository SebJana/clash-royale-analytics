from fastapi import APIRouter, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from core.deps import (
    DbConn,
    CrApi,
    require_tracked_player,
    require_remove_player_token,
)
from clash_royale_api import (
    ClashRoyaleMaintenanceError,
    ClashRoyalePlayerCheckError,
    ClashRoyaleInvalidTagError,
    ClashRoyalePlayerNotFoundError,
    ClashRoyaleAuthError,
    ClashRoyaleConnectionError,
    ClashRoyaleInvalidResponseError,
)
from api_key_store import NoKeyAvailable, KeyStoreUnavailable
from mongo import (
    get_tracked_players,
    insert_tracked_player,
    deactivate_tracked_player,
    get_players_count,
)

router = APIRouter(prefix="/players", tags=["Tracked Players"])


@router.get(
    "",
    dependencies=[Depends(RateLimiter(times=15, seconds=60))],
    responses={500: {"description": "Tracked player lookup failed"}},
)
async def list_tracked_players(mongo_conn: DbConn):
    try:
        players = await get_tracked_players(mongo_conn)
        return {"activePlayers": players}
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to fetch all tracked players"
        )


@router.get(
    "/count",
    responses={500: {"description": "Tracked player count lookup failed"}},
)
async def fetch_tracked_player_count(mongo_conn: DbConn):
    try:
        players_count = await get_players_count(mongo_conn)
        return {"activePlayerCount": players_count}
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to fetch the count of all tracked players"
        )


@router.post(
    "/{player_tag}",
    dependencies=[Depends(RateLimiter(times=3, seconds=60))],
    responses={
        404: {"description": "Player tag invalid or player not found"},
        500: {"description": "Could not save tracked player"},
        502: {"description": "Clash Royale API request failed"},
        503: {"description": "Clash Royale API or key store unavailable"},
    },
)
async def add_tracked_player(player_tag: str, mongo_conn: DbConn, cr_api: CrApi):
    # Use the same trimmed tag for the Clash Royale check and the stored player.
    player_tag = player_tag.strip()
    try:
        player = await cr_api.check_existing_player(player_tag)
    # Keep missing players and Clash Royale failures separate for the frontend.
    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(
            status_code=e.code,
            detail={"code": "CR_API_MAINTENANCE", "message": e.detail},
        ) from e
    except NoKeyAvailable as e:
        raise HTTPException(status_code=503, detail={"code": "CR_API_KEYS_BUSY", "message": str(e)},
                            headers={"Retry-After": str(int(e.retry_after))}) from e
    except KeyStoreUnavailable as e:
        raise HTTPException(status_code=503, detail={"code": "CR_API_KEY_STORE_UNAVAILABLE",
                                                     "message": "Clash Royale key store unavailable"}) from e
    except ClashRoyaleInvalidTagError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "INVALID_PLAYER_TAG", "message": e.detail},
        ) from e
    except ClashRoyalePlayerNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAYER_NOT_FOUND", "message": e.detail},
        ) from e
    except ClashRoyaleAuthError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "CR_API_AUTH_FAILED", "message": e.detail},
        ) from e
    except ClashRoyaleConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "CR_API_UNAVAILABLE", "message": e.detail},
        ) from e
    except ClashRoyaleInvalidResponseError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "CR_API_INVALID_RESPONSE", "message": e.detail},
        ) from e
    except ClashRoyalePlayerCheckError as e:
        # Other Clash Royale failures still need to stay separate from backend errors.
        raise HTTPException(
            status_code=502,
            detail={"code": "CR_API_UNAVAILABLE", "message": e.detail},
        ) from e

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


@router.delete(
    "/{player_tag}",
    dependencies=[Depends(RateLimiter(times=3, seconds=60))],
    responses={
        403: {"description": "Invalid or untracked player, or invalid removal token"},
        404: {"description": "Tracked player not found"},
        500: {"description": "Could not remove tracked player"},
    },
)
async def remove_tracked_player(
    mongo_conn: DbConn,
    _=Depends(require_remove_player_token),
    player_tag: str = Depends(require_tracked_player),
):
    try:
        affected_player_count = await deactivate_tracked_player(mongo_conn, player_tag)

        # Database operation returns 0 if no matching records were modified
        # Tracked player is verified with every given player tag, but handle async untrack issues
        # with this catch here
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
