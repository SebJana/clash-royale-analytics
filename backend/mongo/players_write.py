from pymongo.errors import DuplicateKeyError
from datetime import datetime
from .connection import MongoConn
from .validation_utils import ensure_connected

async def insert_tracked_player(conn: MongoConn, player_tag: str) -> str:
    """
    Insert (or reactivate) a player in the `players` collection.

    - If the player doesn't exist: create with active=True.
    - If the player exists: set active=True again (reactivate).

    Returns:
        str: "created", "reactivated", or "already_active"
    """
    try:
        await ensure_connected(conn)
        now = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        # Try to reactivate if it exists but is inactive
        res = await conn.db.players.update_one(
            {"playerTag": player_tag, "active": False},
            {"$set": {"active": True, "reactivatedAt": now, "updatedAt": now}},
            upsert=False,
        )
        if res.matched_count == 1:
            return "reactivated"

        # If not matched above, upsert (create if missing, otherwise just ensure active)
        res = await conn.db.players.update_one(
            {"playerTag": player_tag},
            {
                "$set": {"playerTag": player_tag, "active": True, "updatedAt": now},
                "$setOnInsert": {"insertedAt": now},
            },
            upsert=True,
        )

        if res.upserted_id is not None:
            return "created"

        return "already_active"

    except Exception as e:
        print(f"[DB] [ERROR] during insert/reactivate for player: {player_tag}", e)
        raise

async def set_player_name(conn: MongoConn, player_tag: str, player_name: str):
    """
    Updates the name of an existing player (by tag) in the players collection.
    It does not insert a new document if the player does not exist (upsert=False).

    Args:
        conn (MongoConn): Active MongoDB connection instance.
        player_tag (str): The unique tag of the player (e.g., "#YYRJQY28").
        player_name (str): The new name to set for the player.

    Raises:
        Exception: Any exception that occurs during the database update operation.
    """
    
    try:
        await ensure_connected(conn)
        
        # Set the name for the player with the specified tag
        res = await conn.db.players.update_one(
            {"playerTag": player_tag},
            {"$set": {"playerName": player_name}},
            upsert=False,
        )
        
        if res.matched_count == 0:
            print(f"[DB] [WARNING] player {player_tag} was not found in collection and couldn't set player name.")

    except Exception as e:
        print(f"[DB] [ERROR] during name setting for player: {player_tag}", e)
        raise

async def deactivate_tracked_player(conn: MongoConn, player_tag) -> int:
        """
        Deactivates a player that is being tracked into the players collection.
        
        Args:
            conn (MongoConn): Active connection to the mongo database
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")
        
        Returns:
            int: The amount of affected players by the update
                        
        Raises:
            Exception: If the update of the player fails
        """

        try:
            await ensure_connected(conn)
            current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            
            res = await conn.db.players.update_one(
                {"playerTag": player_tag, "active": True},
                {"$set": {"active": False, "deactivatedAt": current_time}},
            )
            
            # Return the amount of players updated 
            return res.matched_count 
        
        except Exception as e:
            print(f"[DB] [ERROR] during update: {e}")
            raise