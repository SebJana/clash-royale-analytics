from clean import clean_battle_log_list, check_if_valid_logs
from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn
from mongo import insert_battles, get_battles_count, print_first_battles
from mongo import get_tracked_players
from dotenv import load_dotenv, find_dotenv
import os
import httpx
import asyncio

INIT_SLEEP_DURATION = 60 # 60 seconds
REQUEST_CYCLE_DURATION = 60 * 60 # 1 hour
COOL_DOWN_SLEEP_DURATION = 30 # 30 seconds

load_dotenv(find_dotenv())
API_TOKEN = os.getenv("DATA_SCRAPER_API_KEY")

async def main():
    """Main async function for the data scraper"""
    
    await asyncio.sleep(INIT_SLEEP_DURATION) # upon start sleep for database to settle in

    # Init the CR API connection
    cr_api = ClashRoyaleAPI(api_key=API_TOKEN)

    # Init the database connection
    conn = MongoConn(app_name="cr-analytics-data-scraper")
    try:
        await conn.connect()
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        print("[ERROR] Exiting data scraper")
        exit(1)

    while True:
        print("[INFO] Starting new data scraping cycle...")
        
        # Loop over every tracked player
        players = set()
        try:
            players = await get_tracked_players(conn)
            print(f"[INFO] Found {len(players)} tracked players: {players}")
        except Exception as e:
            continue

        if not players:
            print("[WARNING] No players to track, sleeping until next cycle")
            await asyncio.sleep(REQUEST_CYCLE_DURATION)
            continue

        for player in players:
            print(f"[INFO] Running data scraping cycle for Player {player} ...")
            # Try to fetch the last battles for each player
            try:
                battle_logs = await cr_api.get_player_battle_logs(player_tag=player)

                # Check if we got any battle logs
                if not battle_logs:
                    print(f"[WARNING] No battle logs returned for player {player}")
                    continue
                
                # TODO move this check to the API module
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
                await insert_battles(conn, cleaned_battle_logs)

                # Optional debug (uncomment to check first documents and document count)
                battles_count = await get_battles_count(conn)
                print(f"[INFO] There are now {battles_count} battles in the collection")
                # await print_first_battles(conn)
            
            # Check which type of error occurred
            except httpx.HTTPStatusError as http_err:
                code = http_err.response.status_code
                # Sending too many requests
                if code == 429: # TODO upon too many request, wait and retry fetching
                    print("[ERROR] Rate limit hit - consider increasing COOL_DOWN_SLEEP_TIME")
                    await asyncio.sleep(COOL_DOWN_SLEEP_DURATION * 10) # Extra delay for rate limiting
                elif code == 403:
                    print("[ERROR] API access forbidden - check your API token")
                elif code == 404:
                    print(f"[ERROR] Player {player} not found")
                else:
                    body = http_err.response.text[:200]
                    reason = http_err.response.reason_phrase
                    print(f"[ERROR] HTTP {code} {reason}: {body}")
            
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as net_err:
                print(f"[ERROR] Network/timeout error: {net_err}")
                # Small backoff to avoid tight loops
                await asyncio.sleep(1)

            except httpx.RequestError as req_err:
                # Catch-all for other client-side errors (DNS, TLS, etc.)
                print(f"[ERROR] Request error: {req_err}")

            except ValueError as val_err:
                # e.g., JSON decode issues if you do resp.json() on non-JSON
                print(f"[ERROR] Data validation error: {val_err}")

            except Exception as e:
                print(f"[ERROR] Unknown error occurred for player {player}: {e}")

            # Space out the API calls
            await asyncio.sleep(COOL_DOWN_SLEEP_DURATION) # Additional delay to runtime of code

        await asyncio.sleep(REQUEST_CYCLE_DURATION)


if __name__ == "__main__":
    asyncio.run(main())
