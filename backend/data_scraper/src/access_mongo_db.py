from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())


class MongoDBWriter:
    """
    Manages MongoDB connections and operations for the Clash Royale analytics application.
    
    Handles connection initialization, battle log insertion, and collection querying
    with proper error handling and logging.
    """
    
    def __init__(self):
        """
        Initialize the MongoDB manager with connection parameters from environment variables.
        """
        self.user = os.getenv("MONGO_APP_USER")
        self.password = os.getenv("MONGO_APP_PWD")
        self.host = "mongo"
        self.port = 27017
        self.db_name = os.getenv("MONGO_APP_DB")
        self.uri = f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}?authSource={self.db_name}"
        
        self.client = None
        self.db = None
        self.is_connected = False

    def connect(self):
        """
        Establishes connection to MongoDB database.
        
        Raises:
            Exception: If connection to MongoDB fails
        """
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            # Test the connection
            self.client.admin.command('ping')
            self.is_connected = True
            print("[DB] Connected to MongoDB successfully.")
        except Exception as e:
            self.is_connected = False
            print(f"[DB] Failed to connect to MongoDB: {e}")
            raise

    def is_connection_alive(self):
        """
        Checks if the MongoDB connection is still alive.
        
        Returns:
            bool: True if connection is alive, False otherwise
        """
        if not self.client or not self.is_connected:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            self.is_connected = False
            return False

    def insert_battles(self, battle_logs):
        """
        Inserts battle logs into the battles collection.
        
        Args:
            battle_logs (list): List of battle log dictionaries to insert
            
        Raises:
            ValueError: If battle_logs is not a list
            Exception: If insertion fails
        """
        if not self.is_connection_alive():
            print("[DB] Connection lost, attempting to reconnect...")
            self.connect()
        
        try:
            if not isinstance(battle_logs, list):
                raise ValueError("battle_logs must be a list of dictionaries.")

            result = self.db.battles.insert_many(battle_logs)
            print(f"[DB] Inserted {len(result.inserted_ids)} documents into battles collection")
        
        except BulkWriteError as bwe:
            # Check if it's a duplicate key error (E11000)
            if any(err.get("code") == 11000 for err in bwe.details.get("writeErrors", [])):
                print("[DB] [INFO] Duplicate key error — some documents were already in the collection.")
            else:
                print(f"[DB] Bulk write error: {bwe.details}")
                raise
        except Exception as e:
            print(f"[DB] [ERROR] during insertion: {e}")
            raise

    def get_collection_count(self):
        """
        Gets the total count of documents in the battles collection.
        
        Returns:
            int: Number of documents in the collection
            
        Raises:
            Exception: If query fails
        """
        if not self.is_connection_alive():
            print("[DB] Connection lost, attempting to reconnect...")
            self.connect()
        
        try:
            count = self.db.battles.count_documents({})
            return count
        except Exception as e:
            print(f"[DB] [ERROR] fetching document count: {e}")
            raise

    def print_collection_info(self, limit=5):
        """
        Prints collection count and previews a few documents.
        
        Args:
            limit (int): Number of documents to preview (default: 5)
        """
        try:
            count = self.get_collection_count()
            print(f"[DB] Found {count} documents in 'battles' collection")

            # Preview first few documents
            print(f"[DB] Previewing first {limit} documents:")
            for doc in self.db.battles.find().limit(limit):
                print(doc)

        except Exception as e:
            print(f"[DB] [ERROR] fetching collection info: {e}")

    def close_connection(self):
        """
        Closes the MongoDB connection.
        """
        if self.client:
            self.client.close()
            self.is_connected = False
            print("[DB] MongoDB connection closed.")