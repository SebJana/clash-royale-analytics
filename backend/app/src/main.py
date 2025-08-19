from fastapi import FastAPI, Depends, Request, HTTPException
import requests
from contextlib import asynccontextmanager
from mongo import MongoConn, insert_tracked_player, get_tracked_players, get_last_battles, get_unique_decks
from pymongo.errors import DuplicateKeyError

from models import PlayerBetweenRequest
from clash_royale_api import check_valid_player_tag, fetch_player_stats, fetch_cards

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    conn = MongoConn("cr-analytics-api")
    try:
        await conn.connect()
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
       await insert_tracked_player(conn, player_tag)
       return {"status": "Player is now being tracked", "tag": player_tag} 
    except DuplicateKeyError:
        return {"status": "Player is already tracked", "tag": player_tag}
    except Exception:
        raise HTTPException(status_code=500, detail="Player could not be inserted")

@app.get("/tracked-players")
async def list_players(conn: MongoConn = Depends(get_conn)):
    tags = await get_tracked_players(conn)
    return {"activePlayers": list(tags)}

@app.get("/player-stats/{player_tag}")
async def get_player_stats(player_tag: str):
    try:
        # TODO cache the player stats (minutes/hours)
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
        # TODO cache the cards result (hours-day)
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
    
@app.get("/battles/{player_tag}/last/{amount}")
async def last_battles(player_tag: str, amount: int, conn: MongoConn = Depends(get_conn)):
    try:
        battles = await get_last_battles(conn, player_tag, amount)
        
        if not battles:
            raise HTTPException(status_code=404, detail=f"No battles found for {player_tag}")

        return {"player_tag": player_tag, "count": len(battles), "battles": battles}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch last {amount} of games for Player {player_tag}")
    
@app.post("/decks/unique")
async def unique_decks(request: PlayerBetweenRequest, conn: MongoConn = Depends(get_conn)):
    try:
        # TODO check valid player (is in get_tracked_players() response?)
        # TODO check valid date range

        unique_decks = await get_unique_decks(conn, request.player_tag, request.start_date, request.end_date)
        
        if not unique_decks:
            raise HTTPException(status_code=404, detail=f"No decks found for {request.player_tag}")

        return {"player_tag": request.player_tag, "count": len(unique_decks), "unique decks": unique_decks}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch unique decks for Player {request.player_tag}")