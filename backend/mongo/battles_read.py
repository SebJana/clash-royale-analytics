from .connection import MongoConn

async def _ensure_connected(conn: MongoConn):
    if not await conn.is_connection_alive():
        print("[DB] Connection lost, attempting to reconnect...")
        await conn.connect()

async def get_battles_count(conn: MongoConn):
    """
    Gets the total count of documents in the battles collection.
    
    Args:
        conn (MongoConn): Active connection to the mongo database

    Returns:
        int: Number of documents in the collection
        
    Raises:
        Exception: If query fails
    """

    await _ensure_connected(conn)
    
    try:
        count = await conn.db.battles.count_documents({})
        return count
    except Exception as e:
        print(f"[DB] [ERROR] fetching document count: {e}")
        raise

async def print_first_battles(conn: MongoConn, limit=5):
    """
    Prints collection count and previews a few documents.
    
    Args:
        conn (MongoConn): Active connection to the mongo database
        limit (int): Number of documents to preview (default: 5)
    """

    await _ensure_connected(conn)

    try:
        # Preview first few documents
        async for doc in conn.db.battles.find().limit(limit):
            print(doc)

    except Exception as e:
        print(f"[DB] [ERROR] fetching collection info: {e}")

async def get_last_battles(conn: MongoConn, player_tag, limit = 30):
    """
    Fetches the most recent battles for a specific player.

    Args:
        conn (MongoConn): Active connection to the MongoDB database.
        player_tag (str): The tag of the player whose battles are to be fetched.
        limit (int): The maximum number of battles to fetch (default: 30).

    Returns:
        list: A list of dictionaries containing the players last battles

    Raises:
        Exception: If there is an error while fetching the battles from the database.
    """

    await _ensure_connected(conn)

    try:
        projection = {
            "_id": 0,
            "battleTime": 1,
            "gameResult": 1,
            "gameMode": 1,
            "team": 1,
            "opponent": 1,
            "arena": 1
        }

        last_battles = (
            conn.db.battles
            .find({"referencePlayerTag": player_tag}, projection)
            .sort("battleTime", -1)
            .limit(limit)
        )
        
        return await last_battles.to_list(length=None)

    except Exception as e:
        print(f"[DB] [ERROR] fetching collection info: {e}")
        raise