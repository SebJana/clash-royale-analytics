from fastapi import FastAPI, Depends, Request, HTTPException
from contextlib import asynccontextmanager
from mongo import MongoConn, insert_tracked_player, get_tracked_players
from pymongo.errors import DuplicateKeyError

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

@app.post("/players/{player_tag}")
async def add_player(player_tag: str, conn: MongoConn = Depends(get_conn)):
    # TODO add check if thats a valid tag via calling Clash Royale API
    try:
       insert_tracked_player(conn, player_tag)
       return {"status": "Player is now being tracked", "tag": player_tag} 
    except DuplicateKeyError:
        return {"status": "Player is already tracked", "tag": player_tag}
    except Exception:
        raise HTTPException(status_code=500, detail="Player could not be inserted")

@app.get("/players")
async def list_players(conn: MongoConn = Depends(get_conn)):
    tags = get_tracked_players(conn)
    print(tags)
    return {"activePlayers": list(tags)}