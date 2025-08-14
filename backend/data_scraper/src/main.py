from api import fetch_battle_logs
from clean import clean_battle_log_list

# Morten "#R09228V"
TAG = "#YYRJQY28"
   

battle_logs = fetch_battle_logs(player_tag=TAG)
cleaned_battle_logs = clean_battle_log_list(battle_logs, player_tag=TAG)

for battle in cleaned_battle_logs:
    print(battle)
    break
