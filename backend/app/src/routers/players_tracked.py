from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError

from core.deps import DbConn, CrApi
from clash_royale_api import ClashRoyaleMaintenanceError
from mongo import get_tracked_players, insert_tracked_player

router = APIRouter(prefix="/players", tags=["Tracked Players"])

@router.get("/")
async def list_tracked_players(mongo_conn: DbConn):
    try:
        tags = await get_tracked_players(mongo_conn)
        return {"activePlayers": list(tags)}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch all tracked players")
    
@router.post("/{player_tag}")
async def add_tracked_player(player_tag: str, mongo_conn: DbConn, cr_api: CrApi):
    try:
        if not await cr_api.check_existing_player(player_tag):
            raise HTTPException(status_code=403, detail=f"Player with tag {player_tag} does not exist")
    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)
    
    try:
       await insert_tracked_player(mongo_conn, player_tag)
       return {"status": "Player is now being tracked", "tag": player_tag} 
    except DuplicateKeyError:
        return {"status": "Player is already tracked", "tag": player_tag}
    except Exception:
        raise HTTPException(status_code=500, detail="Player could not be inserted")

# TODO untrack player endpoint (setting player active=false)
