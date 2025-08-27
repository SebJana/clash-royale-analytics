from fastapi import APIRouter, HTTPException
import httpx

from core.deps import CrApi, RedConn
from core.settings import settings
from clash_royale_api import ClashRoyaleMaintenanceError
from redis_service import get_redis_json, set_redis_json, build_redis_key

router = APIRouter(prefix="/cards", tags=["Cards"])

@router.get("")
async def get_cards(cr_api: CrApi, redis_conn: RedConn):
    try:
        # Check cache
        key = build_redis_key(service="cr_api", resource="all_cards")
        cached_cards = await get_redis_json(redis_conn, key)

        if cached_cards is not None:
            return cached_cards
        
        # If not cached, fetch them from Clash Royale and cache them
        cards = await cr_api.get_cards()
        await set_redis_json(redis_conn, key, cards, ttl=settings.CACHE_TTL_CARDS)
        return cards

    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)

    except httpx.HTTPStatusError as http_err:
        status = http_err.response.status_code if http_err.response else 502
        # Common Clash Royale API errors
        if status == 403:
            raise HTTPException(status_code=403, detail="Forbidden – check API token or IP whitelist")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
        else:
            raise HTTPException(status_code=status, detail="Clash Royale API error")

    except Exception as e:
        # Network / timeout / DNS errors / Redis error
        raise HTTPException(status_code=502, detail=f"Error trying to fetch the cards: {e}")
