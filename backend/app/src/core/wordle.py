import httpx
from datetime import datetime
from zoneinfo import ZoneInfo


async def get_todays_wordle(timezone: str):
    """
    Fetch today's Wordle game data from the New York Times API.

    Makes an asynchronous HTTP GET request to the NYT Wordle API endpoint
    to retrieve the current day's puzzle information.

    Note: No error handling upon request issue is handled here.

    Args:
        timezone (str): Timezone for the definition of 'today'

    Returns:
        dict: A dictionary containing Wordle game data with the following keys:
            - id (int): Unique puzzle identifier (e.g., 2323)
            - solution (str): The solution word for today's puzzle (e.g., 'stare')
            - print_date (str): Publication date in YYYY-MM-DD format (e.g., '2025-11-30')
            - days_since_launch (int): Number of days since Wordle launched (e.g., 1625)
            - editor (str): Name of the puzzle editor (e.g., 'Tracy Bennett')
    """
    today = datetime.now(ZoneInfo(timezone)).date().isoformat()
    url = f"https://www.nytimes.com/svc/wordle/v2/{today}.json"

    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
