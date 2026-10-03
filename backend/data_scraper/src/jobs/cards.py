"""Periodic refresh of the Clash Royale card list.

Cards change rarely and do not belong to any player, so they are refreshed on
their own timer instead of with the battle syncs. Mongo keeps the durable copy
and Redis the fast one. This job is the only writer of both: the API reads Redis,
then Mongo, never caches what it read, and never calls the Clash Royale API for
cards. A single writer keeps an older list from overwriting a newer one.
"""

import asyncio
import logging
from datetime import datetime, timezone

from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn, get_cards, save_cards
from redis_service import CacheRedisConn, CARDS_CACHE_KEY, set_redis_json
from settings import settings

logger = logging.getLogger(__name__)


def is_valid_card_list(cards) -> bool:
    """Check the card list response before it replaces the stored one.

    Args:
        cards: Response of the Clash Royale /cards endpoint.

    Returns:
        bool: True for {"items": [...]} with at least one card that has an id
            and a name. The frontend reads exactly these fields.
    """

    if not isinstance(cards, dict):
        return False
    items = cards.get("items")
    if not isinstance(items, list) or not items:
        return False
    return all(
        isinstance(card, dict) and card.get("id") is not None and card.get("name")
        for card in items
    )


async def refresh_cards(
    cr_api: ClashRoyaleAPI, mongo_conn: MongoConn, redis_conn: CacheRedisConn
):
    """Fetch the card list and store it in Mongo and the Redis cache.

    Raises:
        ValueError: If the response is not a usable card list. The stored list
            stays in place.
        Exception: Any API, Mongo, or Redis error; the caller retries later.
    """

    cards = await cr_api.get_cards()
    # A successful but empty or error-shaped response would otherwise replace
    # the last good list and count as fresh for a full refresh interval.
    if not is_valid_card_list(cards):
        raise ValueError("Card list response has an unexpected shape")
    await save_cards(mongo_conn, cards)
    await set_redis_json(
        conn=redis_conn, key=CARDS_CACHE_KEY, value=cards, ttl=settings.CACHE_TTL_CARDS
    )
    logger.info("Cards refreshed in Mongo and cache")


def seconds_until_cards_due(stored: dict | None) -> float:
    """Time until the stored card list is older than the refresh interval.

    A restart therefore does not trigger an extra card request when the stored
    list is still recent.

    Args:
        stored (dict | None): The stored card document (see get_cards).

    Returns:
        float: Seconds until the next refresh, 0 if it is due now.
    """

    if not stored or not stored.get("updatedAt"):
        return 0
    # Motor returns naive datetimes that are UTC
    updated_at = stored["updatedAt"].replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return max(0.0, settings.CARDS_REFRESH_INTERVAL - age)


async def restore_cards_cache(stored: dict | None, redis_conn: CacheRedisConn):
    """Copy the stored card list into the cache if the cache lost it.

    The cache can lose the list to eviction, a redis-cache restart, or a write
    that failed after the Mongo save. Rebuilding it from Mongo costs no Clash
    Royale request, so it does not wait for the next refresh.

    Args:
        stored (dict | None): The stored card document (see get_cards).
        redis_conn (CacheRedisConn): Connection to the cache Redis the API reads.
    """

    if not stored or not stored.get("payload"):
        return
    if await redis_conn.client.exists(CARDS_CACHE_KEY):
        return
    await set_redis_json(
        conn=redis_conn,
        key=CARDS_CACHE_KEY,
        value=stored["payload"],
        ttl=settings.CACHE_TTL_CARDS,
    )
    logger.info("Card cache restored from Mongo")


async def cards_loop(
    cr_api: ClashRoyaleAPI, mongo_conn: MongoConn, redis_conn: CacheRedisConn
):
    """Refresh the card list every CARDS_REFRESH_INTERVAL until cancelled.

    Between refreshes the loop wakes every CARDS_CACHE_CHECK_INTERVAL to
    restore a lost cache entry from Mongo.
    """

    while True:
        try:
            stored = await get_cards(mongo_conn)
            delay = seconds_until_cards_due(stored)
            if delay <= 0:
                await refresh_cards(cr_api, mongo_conn, redis_conn)
                continue
            await restore_cards_cache(stored, redis_conn)
            await asyncio.sleep(min(delay, settings.CARDS_CACHE_CHECK_INTERVAL))
        except asyncio.CancelledError:
            raise
        except Exception:
            # The API keeps serving the previous cards from Redis or Mongo.
            logger.exception("Card refresh failed, retrying later")
            await asyncio.sleep(settings.CARDS_RETRY_DELAY)
