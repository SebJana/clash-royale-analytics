from api import fetch_battle_logs
from clean import clean_battle_log_list, check_if_valid_logs
from mongo import MongoConn
from mongo import insert_battles, get_battles_count, print_first_battles
from mongo import get_tracked_players
import time
import requests
import json

INIT_SLEEP_DURATION = 60 # 60 seconds
REQUEST_CYCLE_DURATION = 60 * 60 # 1 hour
COOL_DOWN_SLEEP_DURATION = 30 # 30 seconds


time.sleep(INIT_SLEEP_DURATION) # upon start sleep for database to settle in

# Init the database connection
conn = MongoConn(app_name="cr-analytics-data-scraper")
try:
    conn.connect()
except Exception as e:
    print(f"[ERROR] Failed to connect to database: {e}")
    print("[ERROR] Exiting data scraper")
    exit(1)

while True:
    print("[INFO] Starting new data scraping cycle...")
    
    # Loop over every tracked player
    players = set()
    try:
        players = get_tracked_players(conn)
        print(f"[INFO] Found {len(players)} tracked players: {players}")
    except Exception as e:
        continue

    if not players:
        print("[WARNING] No players to track, sleeping until next cycle")
        time.sleep(REQUEST_CYCLE_DURATION)
        continue

    # Space out the API calls
    time.sleep(COOL_DOWN_SLEEP_DURATION) # Additional delay to runtime of code

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
            insert_battles(conn, cleaned_battle_logs)

            # Optional debug (uncomment to check first documents and document count)
            battles_count = get_battles_count(conn)
            print(f"[INFO] There are now {battles_count} battles in the collection")
            print_first_battles(conn)
        

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
