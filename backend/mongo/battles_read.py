from .connection import MongoConn
from .validation_utils import ensure_connected, check_valid_date_range
from .query_utils import match_tag_before_datetime_stage, match_tag_date_mode_range_stage, extract_deck_cards_stage
from datetime import datetime, date
from typing import Optional, Iterable

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

async def print_first_battles(conn: MongoConn, limit: int = 5):
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

async def get_last_battles(conn: MongoConn, player_tag: str, before_datetime: datetime, limit: int = 20):
    """
    Fetches all battles within the limited amount that the player had before a given date and time 

    Args:
        conn (MongoConn): Active connection to the MongoDB database.
        player_tag (str): The tag of the player whose last battles are to be fetched.
        before_datetime (datetime.datetime): Date and time before which the game happened.
        limit (int): Amount of battles to be fetched that happened before the given datetime (default: 20)

    Returns:
        dict: Containing
            - battles (list) : a list of dictionaries containing the players last battles
            - latestBattleTime (datetime): latest battleTime of the returned battles
            - earliestBattleTime (datetime): earliest battleTime of the returned battles
            
    Raises:
        Exception: If there is an error while fetching the battles from the database.
    """

    try:
        await ensure_connected(conn)
        
        if not isinstance(before_datetime, datetime):
            raise TypeError("end_datetime must be a datetime")

        pipeline = [
            match_tag_before_datetime_stage(player_tag, before_datetime),
            # Keep only what's needed in downstream stages 
            {"$project": {
                "_id": 0,
                "battleTime": 1,
                "gameResult": 1,
                "gameMode": 1,
                "team": 1,
                "opponent": 1,
                "arena": 1
            }},

            {"$facet": {
                "battles": [
                    {"$sort": {"battleTime": -1}},  # newest first, stable
                    {"$limit": limit},
                    # Drop _id from the output
                    {"$project": {
                        "_id": 0,
                        "battleTime": 1,
                        "gameResult": 1,
                        "gameMode": 1,
                        "team": 1,
                        "opponent": 1,
                        "arena": 1
                    }}
                ],
                "meta": [
                    {"$group": {
                        "_id": None,
                        "latest": {"$max": "$battleTime"},
                        "earliest": {"$min": "$battleTime"},
                    }}
                ]
            }},

            # Flatten meta fields, handle empty input safely
            {"$project": {
                "battles": 1, # Include battles list
                "latestBattleTime":  {"$ifNull": [{"$first": "$meta.latest"}, None]},
                "earliestBattleTime":{"$ifNull": [{"$first": "$meta.earliest"}, None]}
            }}
        ]
        
        res = await conn.db.battles.aggregate(pipeline, allowDiskUse=True).to_list(length=1)
        if not res:
            return {"battles": [], "latestBattleTime": None, "earliestBattleTime": None}
        return res[0]

    except Exception as e:
        print(f"[DB] [ERROR] fetching decks info: {e}")
        raise


async def get_decks_win_percentage(conn: MongoConn, player_tag: str, start_date: date, end_date: date, game_modes: Optional[Iterable[str]] = None):
    """
    Fetches every unique deck that the player has played in the given time frame.

    Args:
        conn (MongoConn): Active connection to the MongoDB database.
        player_tag (str): The tag of the player whose unique decks are to be fetched.
        start_date (date): Date after which the game happened.
        end_date (date): Date before which the game happened.
        game_modes (Optional[Iterable[str]]): If provided/non-empty, filter to these game modes in which the game happened.

    Returns:
        list: A list of dictionaries containing the players unique decks and their win-rates
    Raises:
        Exception: If there is an error while fetching the battles from the database.
    """

    try:
        await ensure_connected(conn)
        check_valid_date_range(start_date, end_date)

        pipeline = [
            # Match the relevant files for the player and the time frame
            match_tag_date_mode_range_stage(player_tag, start_date, end_date, game_modes),
            extract_deck_cards_stage(player_tag),
            # Sort the decks by card properties - evolution level first, then id
            {"$addFields": {
                "deckSorted": {
                    "$sortArray": { 
                        "input": "$deckCards", 
                        "sortBy": { 
                            "evolutionLevel": -1,
                            "id": 1
                        } 
                    }
                }
            }},

            # Group by decks and get metadata
            {"$facet": {
                "decks": [
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
                    # Calculate a win rate and evolution metrics for the end result
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
                    # Sort unique decks by count (descending) and lastSeen 
                    {"$sort": {"count": -1, "lastSeen": -1}}
                ],
                "meta": [
                    {"$count": "totalBattles"}
                ]
            }},
            {"$project": {
                "totalBattles": {"$ifNull": [{"$first": "$meta.totalBattles"}, 0]},
                "decks": "$decks"
            }}
        ]

        result = await conn.db.battles.aggregate(pipeline, allowDiskUse=True).to_list(length=1)
        if not result:
            return {"decks": [], "totalBattles": 0}

        return result[0]

    except Exception as e:
        print(f"[DB] [ERROR] fetching decks info: {e}")
        raise

async def get_cards_win_percentage(conn: MongoConn, player_tag: str, start_date: date, end_date: date, game_modes: Optional[Iterable[str]] = None):
    """
    Fetches a usage and win percentage for every used card for the player in the specified time range.

    Args:
        conn (MongoConn): Active connection to the MongoDB database.
        player_tag (date): The tag of the player whose unique decks are to be fetched.
        start_date (date): Date after which the game happened.
        end_date (date): Date before which the game happened.
        game_modes (Optional[Iterable[str]]): If provided/non-empty, filter to these game modes in which the game happened.

    Returns:
        list: A list of dictionaries containing the card win-rate and usages
    Raises:
        Exception: If there is an error while fetching the battles from the database.
    """

    try:
        await ensure_connected(conn)
        check_valid_date_range(start_date, end_date)

        pipeline = [
            match_tag_date_mode_range_stage(player_tag, start_date, end_date, game_modes),
            extract_deck_cards_stage(player_tag),
            {"$facet": {
                "cards": [
                    {"$unwind": "$deckCards"},
                    {"$group": {
                        "_id": {
                            "id": "$deckCards.id", 
                            "name": "$deckCards.name",
                            "evolutionLevel": "$deckCards.evolutionLevel"
                        },
                        "usage": {"$sum": 1},  # Usage in battle
                        "wins":  {"$sum": {"$cond": [{"$eq": ["$gameResult", "Victory"]}, 1, 0]}},
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
                        }
                    }},
                    {"$sort": {"usage": -1}}
                ],
                "meta": [
                    {"$count": "totalBattles"}
                ]
            }},
            {"$set": {
                "totalBattles": {"$ifNull": [{"$first": "$meta.totalBattles"}, 0]}
            }},
            {"$project": {
                "totalBattles": 1,
                "cards": "$cards"
            }}
        ]

        res = await conn.db.battles.aggregate(pipeline, allowDiskUse=True).to_list(length=1)
        if not res:
            return {"cards": [], "totalBattles": 0}

        return res[0]

    except Exception as e:
        print(f"[DB] [ERROR] fetching card stats: {e}")
        raise
