import requests
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

API_TOKEN = os.getenv("DATA_SCRAPER_API_KEY")
BASE_URL = "https://api.clashroyale.com/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}


def url_encode_player_tag(player_tag: str):
    """
    URL encodes a Clash Royale player tag for use in API requests.
    
    Replaces the '#' character with '%23' to make the player tag URL-safe
    for use in HTTP requests to the Clash Royale API.
    
    Args:
        player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")
        
    Returns:
        str: URL-encoded player tag (e.g., "%23YYRJQY28")
    """
    return player_tag.replace("#", "%23")


def fetch_battle_logs(player_tag):
    """
    Fetches battle logs for a specific player from the Clash Royale API.
    
    Makes an HTTP GET request to the Clash Royale API to retrieve the battle
    history for the specified player. The response contains a list of recent
    battle logs with detailed information about each match.
    
    Args:
        player_tag (str): The player tag (e.g., "#YYRJQY28")
        
    Returns:
        list: List of battle log dictionaries from the API response
        
    Raises:
        HTTPError: If the API request fails (4xx/5xx status codes)
        RequestException: If there are network connectivity issues
    """
    tag = url_encode_player_tag(player_tag)
    battle_url = BASE_URL + f"/players/{tag}/battlelog"
    
    response = requests.get(battle_url, headers=headers)
    response.raise_for_status()  # will throw HTTPError for 4xx/5xx
    
    return response.json()