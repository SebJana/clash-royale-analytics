from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

user = os.getenv("MONGO_APP_USER")
password = os.getenv("MONGO_APP_PWD")
host = "mongo"
port = 27017
db_name = os.getenv("MONGO_APP_DB")
uri = f"mongodb://{user}:{password}@{host}:{port}/{db_name}?authSource={db_name}"

client = None
db = None

# Initialize MongoDB client and database
def init_db_connection():
    global client, db
    try:
        client = MongoClient(uri)
        db = client[db_name]
        print("[DB] Connected to MongoDB successfully.")
    except Exception as e:
        print("[DB] Failed to connect to MongoDB:", e)
        raise

def insert_battle_logs(battle_logs):
    try:
        if not isinstance(battle_logs, list):
            raise ValueError("battle_logs must be a list of dictionaries.")

        print("[DEBUG] Attempting simple insert_many operation")
        result = db.battles.insert_many(battle_logs)
        print("[DB] Inserted documents IDs:", result.inserted_ids)
    except Exception as e:
        print("[DB] Error during insertion:", e)