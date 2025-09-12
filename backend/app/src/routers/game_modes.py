from fastapi import APIRouter, HTTPException

from core.deps import DbConn, RedConn
from core.settings import settings
from mongo import get_game_modes
from redis_service import get_redis_json, set_redis_json, build_redis_key


router = APIRouter(prefix="/game_modes", tags=["Game Modes"])


@router.get("")
async def fetch_game_modes(mongo_conn: DbConn, redis_conn: RedConn):

    try:
        key = await build_redis_key(
            conn=redis_conn, service="crApi", resource="allGameModes"
        )
        cached_game_modes = await get_redis_json(redis_conn, key)

        if cached_game_modes is not None:
            return cached_game_modes
        # Fetch the current game modes saved in Mongo
        game_modes = await get_game_modes(mongo_conn)
        await set_redis_json(
            redis_conn, key, game_modes, ttl=settings.CACHE_TTL_GAME_MODES
        )
        return game_modes

    except Exception as e:
        # Upon any lookup/redis error
        raise HTTPException(
            status_code=502, detail=f"Error trying to fetch the game modes: {e}"
        )
