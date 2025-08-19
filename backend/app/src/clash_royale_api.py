import requests
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

API_TOKEN = os.getenv("APP_API_KEY")
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


def check_tag_syntax(player_tag: str):
    """
    Checks wether the player tag starts with a '#' and has the correct length
    
    Args:
        player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")
        
    Returns:
        bool: True if valid, False otherwise
    """

    ALPHABET = set("0289PYLQGRJCUV")  # Supercell-Tag-Alphabet

    # Strip the tag 
    tag = player_tag.strip()

    # Missing the starting code symbol
    if not tag.startswith("#"):
        return False

    core = tag[1:]  # Part without the leading '#'

    # Invalid length
    if len(core) < 8  or len(core) > 11:
        return False
    
    # Check if the tag without the '#' is only numbers and upper letters
    if not all(ch in ALPHABET for ch in core):
        return False
    
    # Valid if all checks passed
    return True


def check_valid_player_tag(player_tag: str):
    """
    Validates the tag syntax and verifies the tag exists
    by fetching the player profile from the Clash Royale API.
    
    Args:
        player_tag (str): The player tag starting with '#' (e.g., "#YYRJQY28")
        
    Returns:
        bool: True if syntax is valid AND the API confirms the player exists; else False.
    """

    if not check_tag_syntax(player_tag):
        return False

    try:
        _ = fetch_player_stats(player_tag)  # raises on non-2xx --> player with that tag exists
        return True
    except requests.HTTPError as e:
        return False
    except requests.RequestException:
        # Network/timeout/etc.
        return False

# TODO rework Clash Royale API calls to async using httpx

def fetch_player_stats(player_tag: str):
    """
    Fetches player information for a specific player from the Clash Royale API.

    Makes an HTTP GET request to the Clash Royale API to retrieve the profile
    information for the specified player.

    Args:
        player_tag (str): The player tag (e.g., "#YYRJQY28")
        
    Returns:
        list: All of the player's stats and information
        
    Raises:
        HTTPError: If the API request fails (4xx/5xx status codes)
        RequestException: If there are network connectivity issues
    """

    tag = url_encode_player_tag(player_tag)
    player_url = BASE_URL + f"/players/{tag}"

    response = requests.get(player_url, headers=headers)
    response.raise_for_status()  # will throw HTTPError for 4xx/5xx

    return response.json()

def fetch_cards():
    """
    Fetches every card's information from the Clash Royale API.

    Makes an HTTP GET request to the Clash Royale API to retrieve all game cards.
        
    Returns:
        list: All cards in the game as items
        
    Raises:
        HTTPError: If the API request fails (4xx/5xx status codes)
        RequestException: If there are network connectivity issues
    """

    cards_url = BASE_URL + "/cards"

    response = requests.get(cards_url, headers=headers)
    response.raise_for_status()  # will throw HTTPError for 4xx/5xx

    return response.json()