from fastapi import APIRouter, HTTPException
import httpx

from core.deps import CrApi, RedConn
from core.settings import settings
from clash_royale_api import ClashRoyaleMaintenanceError
from api_key_store import NoKeyAvailable, KeyStoreUnavailable
from redis_service import get_redis_json, set_redis_json, build_redis_key

router = APIRouter(prefix="/cards", tags=["Cards"])


@router.get(
    "",
    responses={
        403: {"description": "Clash Royale API rejected the request"},
        429: {"description": "Clash Royale API rate limit exceeded"},
        502: {"description": "Clash Royale API request failed"},
        503: {"description": "Clash Royale API or key store unavailable"},
    },
)
async def get_cards(cr_api: CrApi, redis_conn: RedConn):
    try:
        # Check cache
        # Data scraper re-news card cache on every run, so only request cards here as fallback
        # if the cache happens to be empty upon some error or async issue
        key = await build_redis_key(
            conn=redis_conn, service="crApi", resource="allCards"
        )
        cached_cards = await get_redis_json(redis_conn, key)

        if cached_cards is not None:
            return cached_cards

        # If not cached, fetch them from Clash Royale and cache them
        cards = await cr_api.get_cards()
        await set_redis_json(redis_conn, key, cards, ttl=settings.CACHE_TTL_CARDS)
        return cards

    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)

    except NoKeyAvailable as e:
        raise HTTPException(status_code=503, detail=str(e), headers={"Retry-After": str(int(e.retry_after))}) from e

    except KeyStoreUnavailable as e:
        raise HTTPException(status_code=503, detail="Clash Royale key store unavailable") from e

    except httpx.HTTPStatusError as http_err:
        status = http_err.response.status_code if http_err.response else 502
        # Common Clash Royale API errors
        if status == 403:
            raise HTTPException(
                status_code=403, detail="Forbidden – check API token or IP whitelist"
            )
        elif status == 429:
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded, try again later"
            )
        else:
            raise HTTPException(status_code=status, detail="Clash Royale API error")

    except Exception as e:
        # Network / timeout / DNS errors / Redis error
        raise HTTPException(
            status_code=502, detail=f"Error trying to fetch the cards: {e}"
        )
