from fastapi import APIRouter, HTTPException

from core.deps import DbConn, RedConn
from core.settings import settings
from mongo import get_battles_count
from redis_service import get_redis_json, set_redis_json, build_redis_key


router = APIRouter(prefix="/battles", tags=["Total battles"])


@router.get("/total_count")
async def fetch_battles_count(mongo_conn: DbConn, redis_conn: RedConn):
    try:
        key = await build_redis_key(
            conn=redis_conn, service="crApi", resource="totalBattles"
        )
        cached_battle_count = await get_redis_json(redis_conn, key)

        if cached_battle_count is not None:
            return {"totalBattleCount": cached_battle_count}
        # Fetch the amount of battles saved in Mongo
        battle_count = await get_battles_count(mongo_conn)
        await set_redis_json(
            redis_conn, key, battle_count, ttl=settings.CACHE_TTL_TOTAL_BATTLES
        )
        return {"totalBattleCount": battle_count}

    except Exception as e:
        # Upon any lookup/redis error
        raise HTTPException(
            status_code=502, detail=f"Error trying to fetch the total battle count: {e}"
        )
