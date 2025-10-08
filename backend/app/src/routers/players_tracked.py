from fastapi import APIRouter, HTTPException, Depends

from core.deps import DbConn, CrApi, require_tracked_player
from clash_royale_api import ClashRoyaleMaintenanceError
from mongo import get_tracked_players, insert_tracked_player, deactivate_tracked_player

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
    mongo_conn: DbConn, player_tag: str = Depends(require_tracked_player)
):
    try:
        affected_player_count = await deactivate_tracked_player(mongo_conn, player_tag)

        if affected_player_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Player with tag {player_tag} is not being tracked",
            )

        return {"status": "Player is not being tracked anymore", "tag": player_tag}

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=f"Player {player_tag} could not be removed from tracking",
        )
