from .connection import MongoConn

def _ensure_connected(conn: MongoConn):
    if not conn.is_connection_alive():
        print("[DB] Connection lost, attempting to reconnect...")
        conn.connect()

def get_tracked_players(conn: MongoConn):
        """
        Retrieves a set of all players that are tracked.
        
        Args:
            conn (MongoConn): Active connection to the mongo database
        
        Returns:
            set: Tags of the active players 
            
        Raises:
            Exception: If fetching tracked players fails
        """
        _ensure_connected(conn)

        try:
            cursor = conn.db.players.find(
                # only active/tracked players
                {"active": True},
                # projection: only fetch player tags
                {"_id": 0, "playerTag": 1}
            )

            # Turn the player tags into a set to avoid duplicates if those were
            # to happen in the players collection
            tags = set()
            for doc in cursor:
                tags.add(doc["playerTag"])
            return tags

        except Exception as e:
            print(f"[DB] [ERROR] trying to fetch the tracked players: {e}")
            raise