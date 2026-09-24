from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

from routers import (
    players_details,
    players_tracked,
    cards,
    game_modes,
    total_battles,
    auth,
)
from core.settings import settings
from redis_service import CacheRedisConn, RedisConn
from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn
from helpers.ip_utils import rate_limit_key_func

# NOTE time response from Clash Royale/MongoDB is in UTC so frontend needs conversion logic
# both for the query parameter time but also the times the user gets back, which needs to be displayed in their local time
# TODO add ip-based request limitations for routes
# TODO (potentially) global error handling
# TODO add internal for whole backend via logger and don't send full error detail as HttpException
# TODO timestamp based logging

# TODO (potentially) add optional query param to tracked players
# so that user can search the players with a name/tag or a substring of them
# TODO (potentially) add own game mode id to keep query params short


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Retry Clash Royale API
    cr_api = ClashRoyaleAPI(api_key=settings.API_TOKEN)
    await retry_async(cr_api.check_connection, name="Clash Royale API")
    app.state.cr_api = cr_api

    # Retry Redis
    redis_conn = CacheRedisConn(
        host=settings.CACHE_REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )
    await retry_async(redis_conn.connect, name="cache Redis")
    app.state.redis = redis_conn

    # Both clients use the same redis-cache server and keyspace. Card templates
    # contain raw PNG bytes, so this client disables UTF-8 response decoding
    # used by the ordinary JSON cache connection.
    card_image_redis = RedisConn(
        host=settings.CACHE_REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=False,
    )
    await retry_async(card_image_redis.connect, name="card image Redis")
    app.state.card_image_redis = card_image_redis

    # Challenge state is isolated from evictable response/media cache entries.
    # A cache memory spike can no longer remove a valid CAPTCHA or Wordle game.
    auth_state_redis = RedisConn(
        host=settings.AUTH_STATE_REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )
    await retry_async(auth_state_redis.connect, name="auth state Redis")
    app.state.auth_state_redis = auth_state_redis

    # Retry MongoDB
    mongo_conn = MongoConn(app_name=settings.MONGO_CLIENT_NAME)
    await retry_async(mongo_conn.connect, name="MongoDB")
    app.state.mongo = mongo_conn

    async def initialize_rate_limit_redis() -> Redis:
        """Connect rate limiting separately so it cannot reuse auth/cache clients."""

        rate_limit_redis = Redis(
            host="redis-rate-limit",
            port=6379,
            password=settings.REDIS_PASSWORD,
            db=0,
        )
        await rate_limit_redis.ping()
        await FastAPILimiter.init(rate_limit_redis, identifier=rate_limit_key_func)
        return rate_limit_redis

    # Rate-limit startup receives the same retry treatment as the other stores.
    rate_limit_redis = await retry_async(
        initialize_rate_limit_redis, name="rate-limit Redis"
    )

    yield

    # Shutdown
    await app.state.cr_api.close()
    mongo_conn.close()
    await redis_conn.close()
    await card_image_redis.close()
    await auth_state_redis.close()
    await rate_limit_redis.aclose()


app = FastAPI(lifespan=lifespan)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default dev server
        "http://localhost:5173",  # Vite default dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Halli-Galli-Image-Version"],
)

# Include routers
app.include_router(players_tracked.router, prefix="/api")
app.include_router(players_details.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(game_modes.router, prefix="/api")
app.include_router(total_battles.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/api/ping")
async def ping():
    return {"status": "ok"}
