from .connection import MongoConn
from .utils import ensure_connected, check_valid_date_range
from datetime import datetime, timedelta

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
    
    try:
        await ensure_connected(conn)
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

    try:
        await ensure_connected(conn)
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

    try:
        await ensure_connected(conn)
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

async def get_decks_win_percentage(conn: MongoConn, player_tag, start_date, end_date):
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

    try:
        await ensure_connected(conn)
        check_valid_date_range(start_date, end_date)

        # Convert date to date and time
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt   = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

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

async def get_cards_win_percentage(conn: MongoConn, player_tag, start_date, end_date):
    """
    Fetches a usage and win percentage for every used card for the player in the specified time range.

    Args:
        conn (MongoConn): Active connection to the MongoDB database.
        player_tag (str): The tag of the player whose unique decks are to be fetched.
        start_date (str): Date after which the game happened.
        end_date (str): Date before which the game happened.

    Returns:
        list: A list of dictionaries containing the card win-rate and usages
    Raises:
        Exception: If there is an error while fetching the battles from the database.
    """

    try:
        await ensure_connected(conn)
        check_valid_date_range(start_date, end_date)

        # Convert date to date and time
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt   = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

        pipeline = [
            {"$match": {
                "referencePlayerTag": player_tag,
                "battleTime": {"$gte": start_dt, "$lt": end_dt}
            }},
            # Extract the cards from the decks for the given player
            {"$addFields": {
                "deckCards": {
                    "$map": {
                        "input": {
                            "$ifNull": [
                                {"$getField": {
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
                                }},
                                []
                            ]
                        },
                        "as": "c",
                        "in": { "id": "$$c.id", "name": {"$ifNull": ["$$c.name", "UNKNOWN"]} }
                    }
                }
            }},
            {"$facet": {
                "cards": [
                    {"$unwind": "$deckCards"},
                    {"$group": {
                        "_id": {"id": "$deckCards.id", "name": "$deckCards.name"},
                        "usage": {"$sum": 1},  # Usage in battle
                        "wins":  {"$sum": {"$cond": [{"$eq": ["$gameResult", "Victory"]}, 1, 0]}}
                    }},
                    {"$project": {
                        "_id": 0,
                        "card": "$_id",
                        "usage": 1,
                        "wins": 1,
                        "winRate": {
                            "$cond": [
                                {"$eq": ["$usage", 0]},
                                0,
                                {"$multiply": [{"$divide": ["$wins", "$usage"]}, 100]}
                            ]
                        },
                        "firstSeen": 1,
                        "lastSeen": 1
                    }},
                    {"$sort": {"usage": -1, "lastSeen": -1}}
                ],
                "meta": [
                    {"$count": "totalBattles"}
                ]
            }},
            # usagePct = usage / totalBattles * 100
            {"$set": {
                "totalBattles": {"$ifNull": [{"$first": "$meta.totalBattles"}, 0]}
            }},
            {"$project": {
                "totalBattles": 1,
                "cards": {
                    "$map": {
                        "input": "$cards",
                        "as": "c",
                        "in": {
                            "$mergeObjects": [
                                "$$c",
                                {
                                    "usageRate": {
                                        "$cond": [
                                            {"$eq": ["$totalBattles", 0]},
                                            0,
                                            {"$multiply": [
                                                {"$divide": ["$$c.usage", "$totalBattles"]},
                                                100
                                            ]}
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }}
        ]

        res = await conn.db.battles.aggregate(pipeline, allowDiskUse=True).to_list(length=1)
        if not res:
            return {"cards": [], "totalBattles": 0}

        return res[0]

    except Exception as e:
        print(f"[DB] [ERROR] fetching card stats: {e}")
        raise
