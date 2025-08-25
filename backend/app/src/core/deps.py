from fastapi import Depends, Request, HTTPException
from typing import Annotated

from redis_service import RedisConn
from clash_royale_api import ClashRoyaleAPI
from mongo import MongoConn

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
