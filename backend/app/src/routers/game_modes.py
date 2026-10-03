from fastapi import APIRouter, HTTPException

from core.deps import DbConn, RedConn
from mongo import get_game_modes
from redis_service import GAME_MODES_CACHE_KEY, get_redis_json

router = APIRouter(prefix="/game_modes", tags=["Game Modes"])


@router.get("", responses={502: {"description": "Game mode lookup failed"}})
async def fetch_game_modes(mongo_conn: DbConn, redis_conn: RedConn):

    try:
        cached_game_modes = await get_redis_json(redis_conn, GAME_MODES_CACHE_KEY)
        if cached_game_modes is not None:
            return cached_game_modes

        # The data scraper is the only writer of this key. Caching this Mongo read
        # could overwrite a newer list written after the read and hide a new mode
        # until the TTL ends. Misses are rare (eviction or a redis-cache restart)
        # and the collection holds only a few documents.
        return await get_game_modes(mongo_conn)

    except Exception as e:
        # Upon any lookup/redis error
        raise HTTPException(
            status_code=502, detail=f"Error trying to fetch the game modes: {e}"
        )
