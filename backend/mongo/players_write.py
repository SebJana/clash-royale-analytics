from pymongo.errors import DuplicateKeyError
from datetime import datetime
from .connection import MongoConn
from .validation_utils import ensure_connected

async def insert_tracked_player(conn: MongoConn, player_tag):
        """
        Inserts a player to be tracked into the players collection.
        
        Args:
            conn (MongoConn): Active connection to the mongo database
            player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")
                        
        Raises:
            DuplicateKeyError: If the player already exists in the collection
            Exception: If insertion fails
        """

        try:
            await ensure_connected(conn)
            current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

            await conn.db.players.insert_one({
                "playerTag": player_tag,
                "active": True,
                "insertedAt": current_time
            })

            print(f"[DB] Inserted player {player_tag} into players collection")
        
        except DuplicateKeyError:
            print("[DB] [INFO] Duplicate key — player already exists.")
            raise
        except Exception as e:
            print(f"[DB] [ERROR] during insertion: {e}")
            raise