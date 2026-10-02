from fastapi import APIRouter, HTTPException
import httpx

from core.deps import CrApi, DbConn, RedConn
from core.settings import settings
from clash_royale_api import ClashRoyaleMaintenanceError
from api_key_store import NoKeyAvailable, KeyStoreUnavailable
from redis_service import get_redis_json, set_redis_json, CARDS_CACHE_KEY
from mongo import get_cards as get_stored_cards, save_cards

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
async def get_cards(cr_api: CrApi, mongo_conn: DbConn, redis_conn: RedConn):
    try:
        # The data scraper refreshes the cards in Mongo and the cache on its
        # own timer. The cache can still evict them, so Mongo is the fallback.
        cached_cards = await get_redis_json(redis_conn, CARDS_CACHE_KEY)

        if cached_cards is not None:
            return cached_cards

        stored = await get_stored_cards(mongo_conn)
        if stored and stored.get("payload"):
            cards = stored["payload"]
        else:
            # Only on a fresh install, before the scraper's first card refresh
            cards = await cr_api.get_cards()
            await save_cards(mongo_conn, cards)

        await set_redis_json(
            redis_conn, CARDS_CACHE_KEY, cards, ttl=settings.CACHE_TTL_CARDS
        )
        return cards

    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)

    except NoKeyAvailable as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
            headers={"Retry-After": str(int(e.retry_after))},
        ) from e

    except KeyStoreUnavailable as e:
        raise HTTPException(
            status_code=503, detail="Clash Royale key store unavailable"
        ) from e

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
        # Network / timeout / DNS errors / Redis or Mongo error
        raise HTTPException(
            status_code=502, detail=f"Error trying to fetch the cards: {e}"
        )
