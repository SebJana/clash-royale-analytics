import requests
import re
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

    TAG_PATTERN = re.compile(r"^[A-Z0-9]$")

    # Strip and captialize 
    tag = player_tag.strip().upper()

    # Missing the starting code symbol
    if tag.startswith != '#':
        return False

    # Invalid Length
    if len(tag) < 8  or len(tag) > 11:
        return False
    
    # Check if the tag without the '#' is only numbers and upper letters
    if not TAG_PATTERN.fullmatch(tag[1::]):
        return False
    
    # Valid, if all checks passed
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


def fetch_player_stats(player_tag: str):
    """
    Fetches player information for a specific player from the Clash Royale API.

    Makes an HTTP GET request to the Clash Royale API to retrieve the profile
    information for the specified player.

    Args:
        player_tag (str): The player tag (e.g., "#YYRJQY28")
        
    Returns:
        dict: Dictionary of the player information
        
    Raises:
        HTTPError: If the API request fails (4xx/5xx status codes)
        RequestException: If there are network connectivity issues
    """

    tag = url_encode_player_tag(player_tag)
    player_url = BASE_URL + f"/players/{tag}"

    response = requests.get(player_url, headers=headers)
    response.raise_for_status()  # will throw HTTPError for 4xx/5xx

    return response.json()