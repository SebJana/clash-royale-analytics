from datetime import datetime, timezone
from .connection import MongoConn
from .validation_utils import ensure_connected
from .cards_read import CARDS_DOC_ID


async def save_cards(conn: MongoConn, cards):
    """
    Stores the latest Clash Royale card list, replacing the previous one.

    Mongo is the durable copy of the cards: the Redis cache may evict them at
    any time, and the API falls back to this document instead of the CR API.

    Args:
        conn (MongoConn): Active connection to the mongo database
        cards: Card list response of the Clash Royale API

    Raises:
        Exception: If the update fails
    """

    try:
        await ensure_connected(conn)
        await conn.db.cards.update_one(
            {"_id": CARDS_DOC_ID},
            {"$set": {"payload": cards, "updatedAt": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception as e:
        print(f"[DB] [ERROR] saving the cards: {e}")
        raise
