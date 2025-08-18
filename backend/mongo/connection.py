import os
from pymongo import MongoClient

def build_uri_from_parts():
    user = os.getenv("MONGO_APP_USER")
    pwd  = os.getenv("MONGO_APP_PWD")
    host = "mongo"
    port = "27017"
    db   = os.getenv("MONGO_APP_DB")

    if not all([user, pwd, db]):
        raise ValueError("MONGO_APP_USER, MONGO_APP_PWD, MONGO_APP_DB have to exist in .env file")
    return f"mongodb://{user}:{pwd}@{host}:{port}/{db}?authSource={db}"

# TODO make mongo connection async
class MongoConn:
    """
    Manages MongoDB connections and operations for the Clash Royale analytics application.
    One Instance for each working process (API and Data Scraper).
    """
    def __init__(self, app_name: str = "default"):

        self._uri = build_uri_from_parts()
        self._db_name = os.getenv("MONGO_APP_DB")
        self._app_name = app_name
        self.client: MongoClient | None = None
        self.db = None
        self.is_connected = False

    def connect(self):
        '''Connect to the database and send a test ping'''
        try:
            self.client = MongoClient(self._uri, appname=self._app_name)
            self.db = self.client[self._db_name]
            self.client.admin.command("ping")
            self.is_connected = True
            print("[DB] Connected to MongoDB successfully.")
        except Exception as e:
            self.is_connected = False
            print(f"[DB] Failed to connect to MongoDB: {e}")
            raise

    def is_connection_alive(self):
        '''Ping the database to check if it is up and running'''
        if not self.client or not self.is_connected:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            self.is_connected = False
            return False

    def close(self):
        if self.client:
            self.client.close()
            self.is_connected = False
            print("[DB] MongoDB connection closed.")