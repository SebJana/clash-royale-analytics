from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager

from routers import players_details, players_tracked
from core.settings import settings
from redis_service import RedisConn
from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn
from routers import cards

# TODO swap out sleep with retry and cool down connection logic
# TODO global check if player exists in db via get_tracked_players()
# TODO (potentially) global error handling
# TODO add internal logging and don't send error detail as HttpException

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await asyncio.sleep(settings.INIT_SLEEP_DURATION) # upon start sleep for database/redis to settle in

    # Redis
    redis_conn = RedisConn(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD)
    try:
        await redis_conn.connect()
        app.state.redis = redis_conn
    except Exception as e:
        print(f"[ERROR] Failed to connect to redis: {e}")
        print("[ERROR] Exiting api")
        exit(1)

    # Clash Royale API
    cr_api = ClashRoyaleAPI(api_key=settings.API_TOKEN)
    app.state.cr_api = cr_api

    # MongoDB
    mongo_conn = MongoConn(settings.MONGO_CLIENT_NAME)
    try:
        await mongo_conn.connect()
        app.state.mongo = mongo_conn
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        print("[ERROR] Exiting api")
        exit(1)
    yield

    # Shutdown
    await app.state.cr_api.close()
    mongo_conn.close()
    await redis_conn.close()

app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(players_tracked.router)
app.include_router(players_details.router)
app.include_router(cards.router)

@app.get("/ping")
async def ping():
    return {"status": "ok"}