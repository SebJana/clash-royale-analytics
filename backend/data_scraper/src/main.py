from api import fetch_battle_logs
from clean import clean_battle_log_list
from access_mongo_db import init_db_connection, insert_battles, print_all_battles
import time

# Morten "#R09228V"
TAG = "#YYRJQY28"


# TODO check if mongo is up and running
# TODO time interval based refreshs
time.sleep(60) # upon start sleep for database to settle in

while True:
    print("[DEBUG] Fetching battle logs")
    battle_logs = fetch_battle_logs(player_tag=TAG)

    # TODO proper error handling and exception checking
    # TODO check if there is team and opponent and both have cards

    # Check if the API call failed and returned an empty json
    if battle_logs != {}:
        # API response when there is a maintenance break
        if battle_logs[0].get('reason') != 'inMaintenance':
            print("[DEBUG] Cleaning battle logs")
            cleaned_battle_logs = clean_battle_log_list(battle_logs, player_tag=TAG)

            print("[DEBUG] Initializing DB connection")
            init_db_connection()

            print("[DEBUG] Inserting battle logs into DB")
            insert_battles(cleaned_battle_logs)

            # Optional debug
            print_all_battles()
    
    time.sleep(60*60)
