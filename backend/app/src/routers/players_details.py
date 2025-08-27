from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Annotated
from datetime import datetime
import httpx

from core.deps import DbConn, CrApi, RedConn, require_tracked_player
from core.settings import settings
from models.schema import BetweenRequest, BattlesRequest
from clash_royale_api import ClashRoyaleMaintenanceError
from redis_service import get_redis_json, set_redis_json, build_redis_key
from mongo import get_last_battles, get_decks_win_percentage, get_cards_win_percentage

router = APIRouter(prefix="/players", tags=["Player Details"], dependencies=[Depends(require_tracked_player)])

@router.get("/{player_tag}/profile")
async def get_player_profile(player_tag: str, cr_api: CrApi, redis_conn: RedConn):
    try:
        params = {"playerTag": player_tag}
        key = build_redis_key(service="cr_api", resource="player_profile", params=params)
        cached_stats = await get_redis_json(redis_conn, key)

        if cached_stats is not None:
            return cached_stats

        player_stats = await cr_api.get_player_info(player_tag)
        await set_redis_json(redis_conn, key, player_stats, ttl=settings.CACHE_TTL_PLAYER_STATS)
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

@router.get("/{player_tag}/battles")
async def last_battles(player_tag: str, mongo_conn: DbConn, redis_conn: RedConn, req: BattlesRequest = Depends()):
    try:
        # Cap the amount of battles a user can query at once
        if req.limit < 1 or req.limit > 50:
            raise HTTPException(status_code=403, detail=f"Given limit is invalid: {req.limit}")
        
        # Either use:
        # 1) the specified before datetime
        # 2) the current datetime, which equals the last req.limit battles
        cutoff = req.before or datetime.now()
        
        params = {"playerTag": player_tag, "before": cutoff, "limit": req.limit}
        key = build_redis_key(service="cr_api", resource="player_battles", params=params)
        cached_battles = await get_redis_json(redis_conn, key)
        
        if cached_battles is not None:
            return {"player_tag": player_tag, "last_battles": cached_battles}
        
        battles = await get_last_battles(mongo_conn, player_tag, cutoff, req.limit)
        
        if not battles:
            raise HTTPException(status_code=404, detail=f"No battles found for {player_tag}")

        await set_redis_json(redis_conn, key, battles, ttl=settings.CACHE_TTL_BATTLES)
        return {"player_tag": player_tag, "last_battles": battles}
    
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Given datetime is invalid: {cutoff.isoformat()}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch battles for player {player_tag} {e}")
 
@router.get("/{player_tag}/decks/stats")
async def deck_percentage_stats(player_tag: str, mongo_conn: DbConn, redis_conn: RedConn, game_modes: Annotated[list[str] | None, Query()], req: BetweenRequest = Depends()):
    try:
        params = {"playerTag": player_tag, "startDate": req.start_date, "endDate": req.end_date, "gameModes": game_modes}
        key = build_redis_key(service="cr_api", resource="player_decks", params=params)
        cached_decks = await get_redis_json(redis_conn, key)

        if cached_decks is not None:
            return {"player_tag": player_tag, "game_modes": game_modes, "deck_statistics": cached_decks}
        
        decks = await get_decks_win_percentage(mongo_conn, player_tag, req.start_date, req.end_date, game_modes)
        
        if not decks:
            raise HTTPException(status_code=404, detail=f"No decks found for {player_tag}")

        await set_redis_json(redis_conn, key, decks, ttl=settings.CACHE_TTL_DECK_STATS)
        return {"player_tag": player_tag, "game_modes": game_modes, "deck_statistics": decks}
    
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Given date range is invalid: {req.start_date} – {req.end_date}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch deck statistics for player {player_tag}: {e}")
    
@router.get("/{player_tag}/cards/stats")
async def card_percentage_stats(player_tag: str, mongo_conn: DbConn, redis_conn: RedConn, game_modes: Annotated[list[str] | None, Query()], req: BetweenRequest = Depends()):
    try:        
        params = {"playerTag": player_tag, "startDate": req.start_date, "endDate": req.end_date, "gameModes": game_modes}
        key = build_redis_key(service="cr_api", resource="player_cards", params=params)
        cached_cards = await get_redis_json(redis_conn, key)
        
        if cached_cards is not None:
            return {"player_tag": player_tag, "game_modes": game_modes, "card_statistics": cached_cards}
        
        cards = await get_cards_win_percentage(mongo_conn, player_tag, req.start_date, req.end_date, game_modes)

        if not cards:
            raise HTTPException(status_code=404, detail=f"No cards found for {player_tag}")

        await set_redis_json(redis_conn, key, cards, ttl=settings.CACHE_TTL_CARD_STATS)
        return {"player_tag": player_tag, "game_modes": game_modes, "card_statistics": cards}
    
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Given date range is invalid: {req.start_date} – {req.end_date}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch the card statistics for player {player_tag}: {e}")
