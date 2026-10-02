"""Periodic refresh of the Clash Royale card list.

Cards change rarely and do not belong to any player, so they are refreshed on
their own timer instead of with the battle syncs. Mongo keeps the durable copy
and Redis the fast one; the API reads Redis, then Mongo, and only calls the
Clash Royale API when both are empty (a fresh install).
"""

import asyncio
import logging
from datetime import datetime, timezone

from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn, get_cards, save_cards
from redis_service import CacheRedisConn, CARDS_CACHE_KEY, set_redis_json
from settings import settings

logger = logging.getLogger(__name__)


async def refresh_cards(
    cr_api: ClashRoyaleAPI, mongo_conn: MongoConn, redis_conn: CacheRedisConn
):
    """Fetch the card list and store it in Mongo and the Redis cache.

    Raises:
        Exception: Any API, Mongo, or Redis error; the caller retries later.
    """

    cards = await cr_api.get_cards()
    await save_cards(mongo_conn, cards)
    await set_redis_json(
        conn=redis_conn, key=CARDS_CACHE_KEY, value=cards, ttl=settings.CACHE_TTL_CARDS
    )
    logger.info("Cards refreshed in Mongo and cache")


async def seconds_until_cards_due(mongo_conn: MongoConn) -> float:
    """Time until the stored card list is older than the refresh interval.

    A restart therefore does not trigger an extra card request when the stored
    list is still recent.
    """

    stored = await get_cards(mongo_conn)
    if not stored or not stored.get("updatedAt"):
        return 0
    # Motor returns naive datetimes that are UTC
    updated_at = stored["updatedAt"].replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return max(0.0, settings.CARDS_REFRESH_INTERVAL - age)


async def cards_loop(
    cr_api: ClashRoyaleAPI, mongo_conn: MongoConn, redis_conn: CacheRedisConn
):
    """Refresh the card list every CARDS_REFRESH_INTERVAL until cancelled."""

    while True:
        try:
            delay = await seconds_until_cards_due(mongo_conn)
            if delay > 0:
                await asyncio.sleep(delay)
            await refresh_cards(cr_api, mongo_conn, redis_conn)
        except asyncio.CancelledError:
            raise
        except Exception:
            # The API keeps serving the previous cards from Redis or Mongo.
            logger.exception("Card refresh failed, retrying later")
            await asyncio.sleep(settings.CARDS_RETRY_DELAY)
