from .connection import MongoConn
from datetime import datetime, timedelta

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

async def get_unique_decks(conn: MongoConn, player_tag, start_date, end_date):
    """
    Fetches every unique deck that the player has played in the given time frame.

    Args:
        conn (MongoConn): Active connection to the MongoDB database.
        player_tag (str): The tag of the player whose unique decks are to be fetched.
        start_date (str): Date after which the game happened.
        end_date (str): Date before which the game happened.

    Returns:
        list: A list of dictionaries containing the players unique decks and their win-rates
    Raises:
        Exception: If there is an error while fetching the battles from the database.
    """

    await _ensure_connected(conn)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    try:
        pipeline = [
            # Match the relevant files for the player and the time frame
            {
                "$match": {
                    "referencePlayerTag": player_tag,
                    "battleTime": {"$gte": start_dt, "$lt": end_dt}
                }
            },

            # Pull the cards for the referencedPlayer
            {
                "$addFields": {
                    "deckCards": {
                        "$map": {
                            "input": {
                                "$ifNull": [
                                    {
                                        "$getField": {
                                            "field": "cards",
                                            "input": {
                                                "$first": {
                                                    "$filter": {
                                                        "input": "$team",
                                                        "as": "m",
                                                        "cond": {"$eq": ["$$m.tag", player_tag]}
                                                    }
                                                }
                                            }
                                        }
                                    },
                                    []
                                ]
                            },
                            "as": "c",
                            "in": {
                                "id": "$$c.id",
                                "name": {"$ifNull": ["$$c.name", "UNKNOWN"]}
                            }
                        }
                    }
                }
            },

            # Sort the decks 
            {"$addFields": {
                "deckSorted": {
                    "$sortArray": { "input": "$deckCards", "sortBy": { "id": 1 } }
                }
            }},

            # Group by decks
            {
                "$group": {
                    "_id": "$deckSorted",
                    "count": {"$sum": 1},
                    "wins": {
                        "$sum": {"$cond": [{"$eq": ["$gameResult", "Victory"]}, 1, 0]}
                    },
                    "firstSeen": {"$min": "$battleTime"},
                    "lastSeen": {"$max": "$battleTime"},
                    "modes": {"$addToSet": "$gameMode"}
                }
            },
            # Calculate a win rate for the end result
            {
                "$project": {
                    "_id": 0,
                    "deck": "$_id", # array of {id, name} for every card
                    "count": 1,
                    "wins": 1,
                    "winRate": {
                        "$cond": [
                            {"$eq": ["$count", 0]},
                            0,
                            {"$multiply": [{"$divide": ["$wins", "$count"]}, 100]}
                        ]
                    },
                    "firstSeen": 1,
                    "lastSeen": 1,
                    "modes": 1
                }
            },

            # Sort unique decks by count and lastSeen 
            {"$sort": {"count": -1, "lastSeen": -1}}
        ]

        cursor = conn.db.battles.aggregate(pipeline, allowDiskUse=True)
        return await cursor.to_list(length=None)

    except Exception as e:
        print(f"[DB] [ERROR] fetching decks info: {e}")
        raise
