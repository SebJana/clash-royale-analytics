from fastapi import APIRouter, HTTPException

from core.deps import DbConn
from mongo import get_game_modes

router = APIRouter(prefix="/game_modes", tags=["Game Modes"])


@router.get("")
async def fetch_game_modes(mongo_conn: DbConn):
    try:
        # Fetch the current game modes saved in Mongo
        game_modes = await get_game_modes(mongo_conn)
        return game_modes

    except Exception as e:
        # Upon any lookup error
        raise HTTPException(
            status_code=502, detail=f"Error trying to fetch the game modes: {e}"
        )
