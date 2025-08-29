from clean import (
    clean_battle_log_list,
    validate_battle_log_structure,
    validate_battle_log_content,
    get_player_name,
)
from clash_royale_api import ClashRoyaleAPI, ClashRoyaleMaintenanceError
from mongo import MongoConn
from mongo import (
    insert_battles,
    set_player_name,
    get_battles_count,
    print_first_battles,
)
from mongo import get_tracked_player_tags
from redis_service import RedisConn, build_redis_key, set_redis_json
from api_rate_limiter import ApiRateLimiter
from settings import settings

import httpx
import time
import asyncio


# TODO switch to logger


async def init():
    """Initialize API, Redis, and MongoDB clients. Does a health/connection

    Returns:
        tuple[ClashRoyaleAPI, RedisConn, MongoConn]: Initialized clients.

    Raises:
        SystemExit: If either Redis or MongoDB connection fails.
    """

    # Retry Clash Royale API
    cr_api = ClashRoyaleAPI(api_key=settings.API_TOKEN)
    await retry_async(cr_api.check_connection, name="Clash Royale API")

    # Retry Redis
    redis_conn = RedisConn(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )
    await retry_async(redis_conn.connect, name="Redis")

    # Retry MongoDB
    mongo_conn = MongoConn(app_name=settings.MONGO_CLIENT_NAME)
    await retry_async(mongo_conn.connect, name="MongoDB")

    print("[INFO] Successfully connected to all services")
    # Upon successful connection, return all three
    return cr_api, redis_conn, mongo_conn


async def retry_async(func, name):
    """
    Retry an asynchronous connection or operation multiple times with delay.

    This function attempts to execute the provided asynchronous `func` up to
    `settings.INIT_RETRIES` times. If it fails, it waits for
    `settings.INIT_RETRY_DELAY` seconds between attempts. On success, it
    returns the result of `func`. If all retries fail, the process exits
    with status code 1.

    Args:
        func (Callable[[], Awaitable]): An asynchronous function (e.g., `redis.connect`) that will be retried.
        name (str): A readable identifier for logging (e.g., "Redis", "MongoDB").

    Returns:
        Any: The result of the successfully awaited `func`.

    Raises:
        SystemExit: If all retries are exhausted without success.
    """

    retries = settings.INIT_RETRIES
    delay = settings.INIT_RETRY_DELAY

    for attempt in range(1, settings.INIT_RETRIES + 1):
        try:
            return await func()
        except Exception as e:
            print(
                f"[ERROR] Failed to connect to {name} (attempt {attempt}/{retries}): {e}"
            )
            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                print(
                    f"[ERROR] Exiting after {retries} failed attempts to connect to {name}"
                )
                exit(1)


api_rl = ApiRateLimiter(per_second=settings.REQUESTS_PER_SECOND)


async def process_player(
    player_tag: str, cr_api: ClashRoyaleAPI, mongo_conn: MongoConn
):
    """Fetch, validate, clean, and persist the latest battles for a single player.

    The API call is throttled by a global rate limiter (max REQUESTS_PER_SECOND).
    Transient HTTP/network errors are retried with exponential backoff.
    A maintenance error intentionally propagates to abort the entire cycle.

    Args:
        player_tag (str): Player tag (e.g., "#YYRJQY28").
        cr_api (ClashRoyaleAPI): API client to fetch battle logs.
        mongo_conn (MongoConn): Mongo connection used to write data.

    Returns:
        None: Returns early on any "non-retriable" error or on success.

    Raises:
        ClashRoyaleMaintenanceError: Propagated to stop the current cycle for all players.
    """

    print(f"[INFO] Running data scraping cycle for Player {player_tag} ...")
    attempt = 0
    while True:
        try:
            async with api_rl:
                # Try to fetch the last battles for each player
                battle_logs = await cr_api.get_player_battle_logs(player_tag=player_tag)

            # Check if we got any battle logs
            if not battle_logs:
                print(f"[WARNING] No battle logs returned for player {player_tag}")
                return

            # Check if the response has all the necessary fields and correct content
            if not validate_battle_log_structure(
                battle_logs
            ) or not validate_battle_log_content(battle_logs):
                print(f"[ERROR] Battle logs for Player {player_tag} couldn't be used")
                return

            # Prepare the data for storage
            cleaned_battle_logs = clean_battle_log_list(
                battle_logs, player_tag=player_tag
            )
            player_name = get_player_name(battle_logs, player_tag=player_tag)

            # Insert battles into MongoDB
            # If any error occurs here, the class handles the output for the logs
            await insert_battles(mongo_conn, cleaned_battle_logs)

            # Set the name of the player into MongoDB
            # Update the name on every run of the scraping, because this name is basis for users
            # being able to find people by name, which can be changed and therefore needs to be updated
            await set_player_name(
                mongo_conn, player_tag=player_tag, player_name=player_name
            )

            return

        except ClashRoyaleMaintenanceError as e:
            # Global stop, raise error
            print(
                f"[WARNING] {getattr(e, 'detail', str(e))} ... Skipping the current cycle"
            )
            raise  # Only raise this error

        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response else 0
            if code in (403, 404):
                print(f"[ERROR] HTTP {code} for {player_tag} – not retrying")
                return
            if code in (429, 500, 502, 503, 504) and attempt < settings.MAX_RETRIES:
                backoff = settings.BASE_BACKOFF * (2**attempt)
                print(
                    f"[WARNING] HTTP {code} for {player_tag} – retry in {backoff:.1f}s"
                )
                await asyncio.sleep(backoff)
                continue
            print(f"[ERROR] HTTP {code} for {player_tag}")
            return

        except httpx.RequestError as e:
            if attempt < settings.MAX_RETRIES:
                backoff = settings.BASE_BACKOFF * (2**attempt)
                print(f"[WARN] Net error {e!r} – retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                continue
            print(f"[ERROR] Network error for {player_tag}: {e}")
            return

        except Exception as e:
            print(f"[ERROR] Unknown error for {player_tag}: {e}")
            return


async def run_players_cycle(
    players: list[str], cr_api: ClashRoyaleAPI, mongo_conn: MongoConn
):
    """Run a concurrent fetch/clean/store cycle for all tracked players.

    Uses an asyncio.TaskGroup so all player tasks start together. Any
    ClashRoyaleMaintenanceError raised by an individual task cancels the group
    and is handled here, effectively aborting the entire cycle.

    Args:
        players (list[str]): Collection of player tags to process.
        cr_api (ClashRoyaleAPI): API client instance.
        mongo_conn (MongoConn): MongoDB connection for writes.
    """

    try:
        async with asyncio.TaskGroup() as tg:
            for p in players:
                tg.create_task(process_player(p, cr_api, mongo_conn))
    except* ClashRoyaleMaintenanceError:
        print("[INFO] Maintenance detected – aborting cycle")


async def cache_cards(cr_api: ClashRoyaleAPI, redis_conn: RedisConn):
    """Fetch all card metadata and write it to Redis using 'version-ahead'.

    The card cache is set with a TTL and marked as one version ahead; after
    the cycle, a version increment validates these entries. This
    function does not retry, as on-demand API calls can retrieve cards if
    this step fails.

    Args:
        cr_api (ClashRoyaleAPI): API client to fetch the cards.
        redis_conn (RedisConn): Redis connection used to store the cache.
    """

    try:
        # Fetch cards and save them to the redis cache as one version AHEAD
        cards = await cr_api.get_cards()
        key = await build_redis_key(
            conn=redis_conn, service="crApi", resource="allCards", version_ahead=True
        )
        await set_redis_json(
            conn=redis_conn, key=key, value=cards, ttl=2 * settings.CACHE_TTL_CARDS
        )
        print(
            "[CACHE] [INFO] Cards successfully fetched and set in cache with version ahead"
        )
    except Exception as e:
        print(
            f"[ERROR] Unknown error occurred for while trying to update the cache {e}"
        )


async def main():
    """Start and run the continuous scraping loop.

    - Waits for dependent services to be ready (`INIT_SLEEP_DURATION`).
    - Initializes API, Redis, and Mongo connections.
    - Every cycle:
        * Loads tracked player tags from Mongo.
        * Runs a concurrent player processing cycle (rate-limited fetch).
        * Refreshes the card cache (version-ahead), then increments the Redis version
          to invalidate old keys and validate the new ones.
        * Sleeps `REQUEST_CYCLE_DURATION` before the next cycle.
    """

    cr_api, redis_conn, mongo_conn = await init()

    while True:
        print("[INFO] Starting new data scraping cycle...")

        start_time = time.time()

        # TODO upon hitting "Player doesn't exist" remove from tracked players, as player deleted their account?

        # Loop over every tracked player
        players = set()
        try:
            players = await get_tracked_player_tags(mongo_conn)
            print(f"[INFO] Found {len(players)} tracked players: {players}")
        except Exception:
            continue

        if not players:
            print("[WARNING] No players to track, sleeping until next cycle")
            await asyncio.sleep(settings.REQUEST_CYCLE_DURATION)
            continue

        # Run fetching, cleaning and storing of data concurrently
        await run_players_cycle(players=players, cr_api=cr_api, mongo_conn=mongo_conn)

        # Optional debug (uncomment to check first documents and document count)
        battles_count = await get_battles_count(mongo_conn)
        print(f"[INFO] There are now {battles_count} battles in the collection")
        # await print_first_battles(mongo_conn)

        # Save new cards as the version ahead
        await cache_cards(cr_api=cr_api, redis_conn=redis_conn)
        # Increment redis key version, invalidate cache
        new_version = await redis_conn.increment_version()
        # Existing current version keys will be invalid; not looked up anymore, and be deleted via expiring ttl
        # All cards key, that was one version ahead, will be validated with this increment
        print(
            f"[CACHE] [INFO] Redis version incremented to v{new_version}, cache invalidated."
        )

        # Determine how long to sleep for to meet aimed at cycle time
        end_time = time.time()
        elapsed_time = end_time - start_time
        sleep_time = settings.REQUEST_CYCLE_DURATION - elapsed_time
        print(f"[INFO] Cycle took {elapsed_time:.2f}s for {len(players)} players")

        # Check if valid sleep time remains
        if sleep_time <= 0:
            print("[WARNING] Cycle duration is too low. Running without sleep")
            sleep_time = 0  # Don't sleep at all

        await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    asyncio.run(main())
