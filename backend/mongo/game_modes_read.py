from .connection import MongoConn
from .validation_utils import ensure_connected


async def get_game_modes(conn: MongoConn):
    """
    Fetch game modes from 'game_modes' collection

    Args:
        conn (MongoConn): Active connection to the mongo database

    Returns:
        dict[str, datetime]: Map of mode name to last-seen timestamp.
    """

    try:
        await ensure_connected(conn)

        cursor = conn.db.game_modes.find(
            {},  # filter
            # projection: only fetch game mode name and lastSeen timestamp
            {"_id": 0, "name": 1, "lastSeen": 1},
        ).sort(
            "lastSeen", -1
        )  # sort descending

        # Return a dict
        game_modes = {}
        async for doc in cursor:
            game_modes[doc["name"]] = doc.get("lastSeen")
        return game_modes

    except Exception as e:
        print("[DB] [ERROR] fetching game modes", e)
        raise
