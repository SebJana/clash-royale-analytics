from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from core.jwt import validate_access_token, AvailableTokenTypes
from redis_service import RedisConn
from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn, check_player_tracked


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


# Dependency that ensures the given player tag is active in the players collection
async def require_tracked_player(player_tag: str, cr_api: CrApi, mongo_conn: DbConn):
    """
    FastAPI dependency that ensures a given player tag is valid and currently tracked.

    Args:
        player_tag (str): Player tag from the path.
        cr_api (CrApi): Injected Clash Royale API client (for syntax validation).
        mongo_conn (DbConn): Injected Mongo connection (for tracked/active check).

    Returns:
        str: The player tag when validation succeeds.

    Raises:
        HTTPException 403 if the tag is syntactically invalid or the player is not being tracked.
    """

    # Check the syntax is valid (takes load off of db and ensures tag is mongo query safe)
    if not cr_api.check_tag_syntax(player_tag):
        raise HTTPException(
            status_code=403, detail=f"Player with tag {player_tag} doesn't exist"
        )

    # Check if the player is in players collection and active
    if not await check_player_tracked(mongo_conn, player_tag):
        raise HTTPException(
            status_code=403, detail=f"Player with tag {player_tag} isn't being tracked"
        )

    return player_tag  # When its a valid and tracked player, return the tag


# OAuth2 scheme used only for extracting "Authorization: Bearer <token>"
# FastAPI automatically parses the header and provides the raw token.
auth_scheme = HTTPBearer()


# Dependency that ensures authorization token is received and validated
def require_auth(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """
    Validates a Bearer token provided via the Authorization header.
    """
    token = credentials.credentials

    if not validate_access_token(token, AvailableTokenTypes.AUTH.value):
        raise HTTPException(
            status_code=403,
            detail="No authorization, invalid or expired auth token.",
        )

    return token
