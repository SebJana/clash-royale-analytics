from .connection import MongoConn
from .validation_utils import ensure_connected


async def check_player_tracked(conn: MongoConn, player_tag: str):
    """
    Checks if a given player tag is in the 'players' collection and has the field 'active=true'

    Args:
        conn (MongoConn): Active connection to the mongo database
        player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")

    Returns:
        bool: True if player is in collection and active; False otherwise

    Raises:
        Exception: If fetching tracked players fails
    """
    try:
        await ensure_connected(conn)

        doc = await conn.db.players.find_one(
            {"playerTag": player_tag, "active": True}, {"_id": 1}
        )

        if not doc:
            return False
        return True

    except Exception as e:
        print(f"[DB] [ERROR] trying to fetch the tracked players: {e}")
        raise


async def get_tracked_player_tags(conn: MongoConn):
    """
    Retrieves a set of all players tags that are tracked.

    Args:
        conn (MongoConn): Active connection to the mongo database

    Returns:
        set: Tags of the active players

    Raises:
        Exception: If fetching tracked players fails
    """

    try:
        await ensure_connected(conn)

        cursor = conn.db.players.find(
            # only active/tracked players
            {"active": True},
            # projection: only fetch player tags
            {"_id": 0, "playerTag": 1},
        ).sort(
            "playerTag", 1
        )  # sort ascending

        # Turn the player tags into a set to avoid duplicates if those were
        # to happen in the players collection
        tags = set()
        async for doc in cursor:
            tags.add(doc["playerTag"])
        return tags

    except Exception as e:
        print(f"[DB] [ERROR] trying to fetch the tracked players tags: {e}")
        raise


async def get_tracked_players(conn: MongoConn):
    """
    Retrieves a set of all players tags and names that are tracked.

    Args:
        conn (MongoConn): Active connection to the mongo database

    Returns:
        dict: Tags of the active players and their names

    Raises:
        Exception: If fetching tracked players fails
    """

    try:
        await ensure_connected(conn)

        cursor = conn.db.players.find(
            # only active/tracked players
            {"active": True},
            # projection: only fetch player tags and names
            {"_id": 0, "playerTag": 1, "playerName": 1},
        ).sort(
            "playerTag", 1
        )  # sort ascending

        # Return a dict
        players = {}
        async for doc in cursor:
            players[doc["playerTag"]] = doc.get("playerName")
        return players

    except Exception as e:
        print(f"[DB] [ERROR] trying to fetch the tracked players: {e}")
        raise
