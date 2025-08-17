from fastapi import FastAPI, Depends, Request, HTTPException
import requests
from contextlib import asynccontextmanager
from mongo import MongoConn, insert_tracked_player, get_tracked_players
from pymongo.errors import DuplicateKeyError

from clash_royale_api import check_valid_player_tag, fetch_player_stats, fetch_cards

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    conn = MongoConn("cr-analytics-api")
    try:
        conn.connect()
        app.state.mongo = conn
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        print("[ERROR] Exiting api")
        exit(1)
    yield
    # Shutdown
    conn.close()

# Dependency that returns the database connection
def get_conn(request: Request) -> MongoConn:
    return request.app.state.mongo

app = FastAPI(lifespan=lifespan)

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/tracked-players/{player_tag}")
async def add_tracked_player(player_tag: str, conn: MongoConn = Depends(get_conn)):
    if not check_valid_player_tag(player_tag):
        raise HTTPException(status_code=403, detail=f"Player with tag {player_tag} does not exist")
    try:
       insert_tracked_player(conn, player_tag)
       return {"status": "Player is now being tracked", "tag": player_tag} 
    except DuplicateKeyError:
        return {"status": "Player is already tracked", "tag": player_tag}
    except Exception:
        raise HTTPException(status_code=500, detail="Player could not be inserted")

@app.get("/tracked-players")
async def list_players(conn: MongoConn = Depends(get_conn)):
    tags = get_tracked_players(conn)
    print(tags)
    return {"activePlayers": list(tags)}

@app.get("/player-stats/{player_tag}")
async def get_player_stats(player_tag: str):
    try:
        player_stats = fetch_player_stats(player_tag)
        return player_stats
    
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else 502
        # Common Clash Royale API errors
        if status == 404:
            raise HTTPException(status_code=404, detail="Player not found")
        elif status == 403:
            raise HTTPException(status_code=403, detail="Forbidden – check API token or IP whitelist")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
        else:
            raise HTTPException(status_code=status, detail="Clash Royale API error")

    except requests.RequestException:
        # Network / timeout / DNS errors
        raise HTTPException(status_code=502, detail="Network error while contacting Clash Royale API")
    
@app.get("/cards")
async def get_cards():
    try:
        cards = fetch_cards()
        return cards
    
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else 502
        # Common Clash Royale API errors
        if status == 403:
            raise HTTPException(status_code=403, detail="Forbidden – check API token or IP whitelist")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")
        else:
            raise HTTPException(status_code=status, detail="Clash Royale API error")

    except requests.RequestException:
        # Network / timeout / DNS errors
        raise HTTPException(status_code=502, detail="Network error while contacting Clash Royale API")