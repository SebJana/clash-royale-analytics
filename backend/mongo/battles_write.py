from pymongo.errors import BulkWriteError
from .connection import MongoConn
from .validation_utils import ensure_connected


async def insert_battles(conn: MongoConn, battle_logs):
    """
    Inserts battle logs into the battles collection.

    Args:
        conn (MongoConn): Active connection to the mongo database
        battle_logs (list): List of battle log dictionaries to insert

    Raises:
        ValueError: If battle_logs is not a list
        Exception: If insertion fails
    """

    try:
        await ensure_connected(conn)

        if not isinstance(battle_logs, list):
            raise ValueError("battle_logs must be a list of dictionaries.")

        await conn.db.battles.insert_many(battle_logs, ordered=False)

    except BulkWriteError as bwe:
        # Check if it's a duplicate key error (E11000)
        if any(err.get("code") == 11000 for err in bwe.details.get("writeErrors", [])):
            print(
                "[DB] [INFO] Duplicate — some battles were already in the collection."
            )
        else:
            print(f"[DB] Bulk write error: {bwe.details}")
            raise
    except Exception as e:
        print(f"[DB] [ERROR] during insertion: {e}")
        raise
