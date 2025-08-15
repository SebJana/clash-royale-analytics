from api import fetch_battle_logs
from clean import clean_battle_log_list, check_if_valid_logs
from access_mongo_db import init_db_connection, insert_battles, print_collection_count
import time
import requests
import json


REQUEST_CYCLE_TIME = 60 * 60 # 1 hour
COOL_DOWN_SLEEP_TIME = 30 # 30 seconds

def read_tracked_players():
    """
    Reads the list of tracked players from the JSON configuration file.
    
    Loads the tracked_players.json file which contains a mapping of player tags
    to player names, and returns the player tags (keys) as a list for API requests.
    
    Returns:
        list: List of player tag strings (e.g., ["#YYRJQY28", "#YQQYGJ82"])
        
    Raises:
        FileNotFoundError: If tracked_players.json file doesn't exist
        json.JSONDecodeError: If the JSON file is malformed
    """
    with open("tracked_players.json", "r", encoding="utf-8") as f:
        tracked_players = json.load(f)
    
    player_tag_list = list(tracked_players.keys())

    return player_tag_list

# TODO actual health check to see if mongo is up and running
time.sleep(10) # upon start sleep for database to settle in

init_db_connection()

while True:
    # Loop over every tracked player
    players = []
    try:
        players = read_tracked_players()
    # If error occurs upon reading the file, the loop will iterate over an empty list
    # and just remain idle
    except FileNotFoundError:
        print("[ERROR] tracked_players.json file not found")
        continue
    except json.JSONDecodeError:
        print("[ERROR] tracked_players.json file is malformed")
        continue

    # Space out the API calls
    time.sleep(COOL_DOWN_SLEEP_TIME) # Additional to runtime of code

    for player in players:
        # Try to fetch the last battles for each player
        try:
            battle_logs = fetch_battle_logs(player_tag=player)

            # API response if there is a maintenance break
            if battle_logs[0].get('reason') == 'inMaintenance':
                break # Leave the requests loop and return in the next cycle

            # Check if the response has all the necessary fields
            if not check_if_valid_logs(battle_logs):
                print(f"[ERROR] Battle logs for Player {player} couldn't be used")
                continue 

            # Prepare the data for storage
            cleaned_battle_logs = clean_battle_log_list(battle_logs, player_tag=player)

            # Insert battles into MongoDB
            insert_battles(cleaned_battle_logs)

            # Optional debug
            # print_collection_count()
            
        except requests.exceptions.HTTPError as http_err:
            # Sending too many requests
            if http_err.response.status_code == 429:
                print("[ERROR] Rate limit hit")
        except requests.exceptions.RequestException as req_err:
            print("[ERROR] Network error")
        except Exception as e:
            print("[ERROR] Unknown error occurred")

    time.sleep(REQUEST_CYCLE_TIME)
