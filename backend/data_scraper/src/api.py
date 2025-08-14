import requests
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

API_TOKEN = os.getenv("DATA_SCRAPER_KEY")
BASE_URL = "https://api.clashroyale.com/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}


def url_encode_player_tag(player_tag: str):
    return player_tag.replace("#", "%23")


def fetch_battle_logs(player_tag):
    tag = url_encode_player_tag(player_tag)
    battle_url = BASE_URL + f"/players/{tag}/battlelog"
    
    try:
        response = requests.get(battle_url, headers=headers)
        return response.json()
    
    except Exception as e:
        print("Error fetching data:", e)
        return {}