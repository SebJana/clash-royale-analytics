from fastapi import FastAPI, Depends, Request, HTTPException
import httpx
from dotenv import load_dotenv, find_dotenv
import os
import asyncio
from datetime import datetime
from typing import Annotated
from contextlib import asynccontextmanager
from redis_service import RedisConn, get_redis_json, set_redis_json, build_redis_key
from clash_royale_api import ClashRoyaleAPI, ClashRoyaleMaintenanceError
from mongo import MongoConn, insert_tracked_player, get_tracked_players, get_last_battles
from mongo import get_decks_win_percentage, get_cards_win_percentage
from pymongo.errors import DuplicateKeyError

from models import BetweenRequest, BattlesRequest


load_dotenv(find_dotenv())
API_TOKEN = os.getenv("APP_API_KEY")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

INIT_SLEEP_DURATION = 60 # 60 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # TODO swap out sleep with retry and cool down connection logic
    await asyncio.sleep(INIT_SLEEP_DURATION) # upon start sleep for database/redis to settle in

    # Redis
    redis_conn = RedisConn(host="redis", port=6379, password=REDIS_PASSWORD)
    try:
        await redis_conn.connect()
        app.state.redis = redis_conn
    except Exception as e:
        print(f"[ERROR] Failed to connect to redis: {e}")
        print("[ERROR] Exiting api")
        exit(1)

    # Clash Royale API
    cr_api = ClashRoyaleAPI(api_key=API_TOKEN)
    app.state.cr_api = cr_api

    # MongoDB
    mongo_conn = MongoConn("cr-analytics-api")
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

# Dependency that returns the database connection
def get_mongo(request: Request) -> MongoConn:
    db = getattr(request.app.state, "mongo", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db

# Dependency that returns the redis connection
def get_redis(request: Request) -> RedisConn:
    r = getattr(request.app.state, "redis", None)
    if r is None:
        raise HTTPException(status_code=500, detail="Redis not initialized")
    return r

# Dependency that returns the Cr API client
def get_cr_api(request: Request) -> ClashRoyaleAPI:
    api = getattr(request.app.state, "cr_api", None)
    if api is None:
        # should not happen if lifespan ran correctly
        raise HTTPException(status_code=500, detail="API client not initialized")
    return api

# Global dependencies for usage in the routes
CrApi = Annotated[ClashRoyaleAPI, Depends(get_cr_api)]
DbConn = Annotated[MongoConn, Depends(get_mongo)]
RedConn = Annotated[RedisConn, Depends(get_redis)]


app = FastAPI(lifespan=lifespan)

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/players/{player_tag}")
async def add_tracked_player(player_tag: str, mongo_conn: DbConn, cr_api: CrApi):
    try:
        if not await cr_api.check_existing_player(player_tag):
            raise HTTPException(status_code=403, detail=f"Player with tag {player_tag} does not exist")
    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)
    
    try:
       await insert_tracked_player(mongo_conn, player_tag)
       return {"status": "Player is now being tracked", "tag": player_tag} 
    except DuplicateKeyError:
        return {"status": "Player is already tracked", "tag": player_tag}
    except Exception:
        raise HTTPException(status_code=500, detail="Player could not be inserted")

@app.get("/players")
async def list_tracked_players(mongo_conn: DbConn):
    tags = await get_tracked_players(mongo_conn)
    return {"activePlayers": list(tags)}

@app.get("/players/{player_tag}/stats")
async def get_player_stats(player_tag: str, cr_api: CrApi, redis_conn: RedConn):
    try:
        params = {"playerTag": player_tag}
        key = build_redis_key("stats", "cr_api", params)
        cached_stats = await get_redis_json(redis_conn, key)

        if cached_stats is not None:
            return cached_stats

        player_stats = await cr_api.get_player_info(player_tag)
        await set_redis_json(redis_conn, key, player_stats, ttl= 15 * 60) # 15 mins
        return player_stats
    
    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)

    except httpx.HTTPStatusError as http_err:
        status = http_err.response.status_code if http_err.response else 502
        # Common Clash Royale API errors
        if status == 404:
            raise HTTPException(status_code=404, detail="Player not found")
        elif status == 403:
            raise HTTPException(status_code=403, detail="Forbidden – check API token or IP whitelist")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
        else:
            raise HTTPException(status_code=status, detail="Clash Royale API error")

    except Exception as e:
        # Network / timeout / DNS errors / unknown error
        raise HTTPException(status_code=500, detail=f"Error while contacting Clash Royale API: {e}")
    
@app.get("/cards")
async def get_cards(cr_api: CrApi, redis_conn: RedConn):
    try:
        # Check cache
        key = build_redis_key("cards", "cr_api")
        cached_cards = await get_redis_json(redis_conn, key)

        if cached_cards is not None:
            return cached_cards
        
        # If not cached, fetch them from Clash Royale and cache them
        cards = await cr_api.get_cards()
        await set_redis_json(redis_conn, key, cards, ttl= 24 * 60 * 60) # 24 Hour TTL
        return cards

    except ClashRoyaleMaintenanceError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)

    except httpx.HTTPStatusError as http_err:
        status = http_err.response.status_code if http_err.response else 502
        # Common Clash Royale API errors
        if status == 403:
            raise HTTPException(status_code=403, detail="Forbidden – check API token or IP whitelist")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
        else:
            raise HTTPException(status_code=status, detail="Clash Royale API error")

    except Exception as e:
        # Network / timeout / DNS errors / Redis error
        raise HTTPException(status_code=502, detail=f"Error trying to fetch the cards: {e}")
    

@app.get("/players/{player_tag}/battles")
async def last_battles(player_tag: str, mongo_conn: DbConn, redis_conn: RedConn, req: BattlesRequest = Depends()):
    try:
        # TODO check valid player (is in get_tracked_players() response?)    
        # Cap the amount of battles a user can query at once
        if req.limit < 1 or req.limit > 50:
            raise HTTPException(status_code=403, detail=f"Given limit is invalid: {req.limit}")
        
        # Either use:
        # 1) the specified before datetime
        # 2) the current datetime, which equals the last req.limit battles
        cutoff = req.before or datetime.now()
        
        params = {"playerTag": player_tag, "before": cutoff}
        key = build_redis_key("battles", "cr_api", params)
        cached_battles = await get_redis_json(redis_conn, key)
        
        if cached_battles is not None:
            return {"player_tag": player_tag, "last_battles": cached_battles}
        
        battles = await get_last_battles(mongo_conn, player_tag, cutoff, req.limit)
        
        if not battles:
            raise HTTPException(status_code=404, detail=f"No battles found for {player_tag}")

        await set_redis_json(redis_conn, key, battles, ttl= 15 * 60) # 15 min TTL
        return {"player_tag": player_tag, "last_battles": battles}
    
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Given datetime is invalid: {cutoff.isoformat()}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch battles for player {player_tag} {e}")
 
@app.get("/players/{player_tag}/decks/stats")
async def deck_percentage_stats(player_tag: str, mongo_conn: DbConn, redis_conn: RedConn, req: BetweenRequest = Depends()):
    try:
        # TODO check valid player (is in get_tracked_players() response?)
        params = {"playerTag": player_tag, "startDate": req.start_date, "endDate": req.end_date}
        key = build_redis_key("decks", "cr_api", params)
        cached_decks = await get_redis_json(redis_conn, key)

        if cached_decks is not None:
            return {"player_tag": player_tag, "deck_statistics": cached_decks}
        
        decks = await get_decks_win_percentage(mongo_conn, player_tag, req.start_date, req.end_date)
        
        if not decks:
            raise HTTPException(status_code=404, detail=f"No decks found for {player_tag}")

        await set_redis_json(redis_conn, key, decks, ttl= 15 * 60) # 15 min TTL
        return {"player_tag": player_tag, "deck_statistics": decks}
    
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Given date range is invalid: {req.start_date} – {req.end_date}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch deck statistics for player {player_tag}: {e}")
    
@app.get("/players/{player_tag}/cards/stats")
async def card_percentage_stats(player_tag: str, mongo_conn: DbConn, redis_conn: RedConn, req: BetweenRequest = Depends()):
    try:
        # TODO check valid player (is in get_tracked_players() response?)
        params = {"playerTag": player_tag, "startDate": req.start_date, "endDate": req.end_date}
        key = build_redis_key("cards", "cr_api", params)
        cached_cards = await get_redis_json(redis_conn, key)
        
        if cached_cards is not None:
            return {"player_tag": player_tag, "card_statistics": cached_cards}
        
        cards = await get_cards_win_percentage(mongo_conn, player_tag, req.start_date, req.end_date)

        if not cards:
            raise HTTPException(status_code=404, detail=f"No cards found for {player_tag}")

        await set_redis_json(redis_conn, key, cards, ttl= 15 * 60) # 15 min TTL
        return {"player_tag": player_tag, "card_statistics": cards}
    
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Given date range is invalid: {req.start_date} – {req.end_date}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch the card statistics for player {player_tag}: {e}")