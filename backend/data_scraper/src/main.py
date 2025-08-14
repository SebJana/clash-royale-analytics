from api import fetch_battle_logs
from clean import clean_battle_log_list
from db import init_db_connection, insert_battle_logs
import time

# Morten "#R09228V"
TAG = "#YYRJQY28"

time.sleep(10)

print("[DEBUG] Fetching battle logs")
battle_logs = fetch_battle_logs(player_tag=TAG)

# Check if the API call failed and returned an empty json
if battle_logs != {}:
    # API response when there is a maintenance break
    if battle_logs.get('reason') != 'inMaintenance':
        print("[DEBUG] Cleaning battle logs")
        cleaned_battle_logs = clean_battle_log_list(battle_logs, player_tag=TAG)

        print("[DEBUG] Initializing DB connection")
        init_db_connection()

        print("[DEBUG] Inserting battle logs into DB")
        insert_battle_logs(cleaned_battle_logs)
