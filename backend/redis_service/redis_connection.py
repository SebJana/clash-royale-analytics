import redis.asyncio as redis
import hashlib
import json
import random

class RedisConn:
    """
    Wrapper for an async Redis connection.

    Args:
        host (str): Redis server hostname or IP.
        port (int): Redis server port (default 6379).
        password (str): Password for Redis authentication (if required).
        decode_responses (bool): If True, automatically decode bytes to str.
    """

    def __init__(self, host: str, port: int, password: str, decode_responses: bool = True):
        self._host = host
        self._port = port
        self._password = password
        self._decode = decode_responses
        self.client: redis.Redis

    async def connect(self):
        """
        Establish an async connection to Redis and perform a ping to fail if unreachable.
        """

        self.client = redis.Redis(
            host=self._host, port=self._port, password=self._password,
            decode_responses=self._decode, socket_connect_timeout=3, socket_timeout=5
        )
        # Perform health check to confirm connection works
        await self.client.ping()  # fail if connection couldn't be established

    async def close(self):
        """
        Close the Redis connection if it's open.
        """

        if self.client:
            await self.client.aclose()

async def get_redis_json(conn: RedisConn, key: str):
    """
    Fetch a JSON value from Redis and deserialize it.

    Args:
        conn (RedisConn): Wrapper around an async Redis connection.
        key (str): Redis key to fetch.

    Returns:
        The deserialized Python object if found, otherwise None.
    """

    raw_data = await conn.client.get(key)
    return json.loads(raw_data) if raw_data else None

async def set_redis_json(conn: RedisConn, key: str, value, ttl: int):
    """
    Serialize a Python object to JSON and store it in Redis with TTL.

    Args:
        conn (RedisConn): Wrapper around an async Redis connection.
        key (str): Redis key to set.
        value: Python object to serialize and store.
        ttl (int): Time-to-live in seconds (key expires automatically).
    """
    jittered_ttl = jitter_ttl(ttl)
    await conn.client.setex(key, jittered_ttl, json.dumps(value))

def jitter_ttl(ttl: int) ->  int:
    """
    Return a TTL jittered by ±10% to avoid synchronized expirations

    Jittering spreads key expirations over a small random window, smoothing load and
    improving cache hit stability.

    Args:
        ttl (int): Base time-to-live in seconds.

    Returns:
        int: Jittered TTL in seconds.
    """
    
    random_multiplier = random.uniform(0.9, 1.1) # ±10% variance
    
    return ttl * random_multiplier

def build_redis_key(resource: str, service: str, params: dict | None = None) -> str:
    """
    Build a consistent Redis key string.

    Args:
        resource (str): The type of data or entity, e.g. "decks", "player", "leaked-elixir" ...
        service (str): The service or namespace prefix, e.g. "cr_api" or "mongo"
        params (dict): Additional key-value pairs describing this cache entry.
                These will be sorted and appended as 'key=value' segments.
                e.g. {"player_tag": "YYRJQY28", "start_date": "2025-08-01", "end_date": 2025-08-01})
    Returns:
        str: A Redis key in the format 'service:resource:param1=val1:param2=val2'.
    """

    # Sort params to keep key deterministic even if order changes
    parts = [service, resource]
    if params: # Only append params to key if they exist
        for k, v in sorted(params.items()):
            parts.append(f"{k}={v}")
    key = ":".join(parts) # Build key string

    # Check if the key is not too long
    if len(key) < 512:
        return key
    
    # Uniquely hash key if it is too long
    return service + ":" + hashlib.md5(key.encode()).hexdigest()
