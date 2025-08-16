from .connection import MongoConn

def _ensure_connected(conn: MongoConn):
    if not conn.is_connection_alive():
        print("[DB] Connection lost, attempting to reconnect...")
        conn.connect()

def get_battles_count(conn: MongoConn):
    """
    Gets the total count of documents in the battles collection.
    
    Args:
        conn (MongoConn): Active connection to the mongo database

    Returns:
        int: Number of documents in the collection
        
    Raises:
        Exception: If query fails
    """

    _ensure_connected(conn)
    
    try:
        count = conn.db.battles.count_documents({})
        return count
    except Exception as e:
        print(f"[DB] [ERROR] fetching document count: {e}")
        raise

def print_first_battles(conn: MongoConn, limit=5):
    """
    Prints collection count and previews a few documents.
    
    Args:
        conn (MongoConn): Active connection to the mongo database
        limit (int): Number of documents to preview (default: 5)
    """

    _ensure_connected(conn)

    try:
        # Preview first few documents
        print(f"[DB] Previewing first {limit} documents:")
        for doc in conn.db.battles.find().limit(limit):
            print(doc)

    except Exception as e:
        print(f"[DB] [ERROR] fetching collection info: {e}")