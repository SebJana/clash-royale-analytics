from api import fetch_battle_logs
from clean import clean_battle_log_list, check_if_valid_logs
from access_mongo_db import MongoDBWriter
import time
import requests
import json

INIT_SLEEP_DURATION = 60 # 60 seconds
REQUEST_CYCLE_DURATION = 60 * 60 # 1 hour
COOL_DOWN_SLEEP_DURATION = 30 # 30 seconds

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


time.sleep(INIT_SLEEP_DURATION) # upon start sleep for database to settle in

# Init the database connection
db_manager = MongoDBWriter()
db_manager.connect()

while True:
    # Loop over every tracked player
    players = []
    try:
        players = read_tracked_players()
    # If error occurs upon reading the file stop the data scraping loop
    except FileNotFoundError:
        print("[ERROR] tracked_players.json file not found")
        break
    except json.JSONDecodeError:
        print("[ERROR] tracked_players.json file is malformed")
        break

    # Space out the API calls
    time.sleep(COOL_DOWN_SLEEP_DURATION) # Additional to runtime of code

    for player in players:
        # Try to fetch the last battles for each player
        try:
            battle_logs = fetch_battle_logs(player_tag=player)

            # Check if we got any battle logs
            if not battle_logs:
                print(f"[WARNING] No battle logs returned for player {player}")
                continue

            # API response if there is a maintenance break
            if isinstance(battle_logs, list) and len(battle_logs) > 0 and battle_logs[0].get('reason') == 'inMaintenance':
                print("[INFO] API is in maintenance mode, skipping this cycle")
                break # Leave the requests loop and return in the next cycle

            # Check if the response has all the necessary fields
            if not check_if_valid_logs(battle_logs):
                print(f"[ERROR] Battle logs for Player {player} couldn't be used")
                continue 

            # Prepare the data for storage
            cleaned_battle_logs = clean_battle_log_list(battle_logs, player_tag=player)

            # Insert battles into MongoDB
            # If any error occurs here, the class handles the output for the logs 
            db_manager.insert_battles(cleaned_battle_logs)

            # Optional debug (uncomment to check first documents and document count)
            # db_manager.print_collection_info()
        

        # Check which type of error occurred
        except requests.exceptions.HTTPError as http_err:
            # Sending too many requests
            if http_err.response.status_code == 429:
                print("[ERROR] Rate limit hit - consider increasing COOL_DOWN_SLEEP_TIME")
                time.sleep(COOL_DOWN_SLEEP_DURATION * 10) # Extra delay for rate limiting
            elif http_err.response.status_code == 403:
                print("[ERROR] API access forbidden - check your API token")
            elif http_err.response.status_code == 404:
                print(f"[ERROR] Player {player} not found")
            else:
                print(f"[ERROR] HTTP error {http_err.response.status_code}: {http_err}")
        
        except requests.exceptions.RequestException as req_err:
            print(f"[ERROR] Network error: {req_err}")
        except ValueError as val_err:
            print(f"[ERROR] Data validation error: {val_err}")
        except Exception as e:
            print(f"[ERROR] Unknown error occurred for player {player}: {e}")

    time.sleep(REQUEST_CYCLE_DURATION)
