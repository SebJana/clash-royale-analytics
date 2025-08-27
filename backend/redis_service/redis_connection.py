import redis.asyncio as redis
import hashlib
import json
from urllib.parse import quote
from datetime import date, datetime, time
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

def _json_default(object):
    """
    JSON serializer function for objects not serializable by default.
    
    Handles datetime, date, and time objects by converting them to ISO format strings.
    Used as the 'default' parameter in json.dumps() to handle these common types.
    
    Args:
        object: The object that couldn't be serialized by the default JSON encoder.
        
    Returns:
        str: ISO format string representation of datetime/date/time objects.
        
    Raises:
        TypeError: If the object type is not supported for serialization.
    """
    
    if isinstance(object, (datetime, date, time)):
        return object.isoformat()  # format datetimes as string for storage
    raise TypeError(f"Object of type {type(object)} is not JSON serializable")

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
    payload = json.dumps(value, default=_json_default, separators=(",", ":"))
    await conn.client.setex(key, jittered_ttl, payload)

def jitter_ttl(ttl: int, pct: float = 0.10, min_ttl: int = 60) -> int:
    """
    Return a TTL jittered by pct% to avoid synchronized expirations

    Jittering spreads key expirations over a small random window, smoothing load and
    improving cache hit stability.

    Args:
        ttl (int): Base time-to-live in seconds.

    Returns:
        int: Jittered TTL in seconds.
    """
    
    if ttl <= 0:
        raise ValueError(f"ttl must be > 0 (got {ttl})")
    
    random_factor = random.uniform(1 - pct, 1 + pct)     # e.g., 0.9 .. 1.1 for ±10%
    jittered = int(round(ttl * random_factor))           # round the product to an int
    return max(min_ttl, jittered)

def _to_param_str(val) -> str:
    """
    Convert a parameter value to its string representation for Redis key building.
    
    Handles different data types by converting them to consistent string formats:
    - datetime/date/time objects: ISO format strings
    - lists/tuples: comma-separated values
    - booleans: 'true' or 'false' strings
    - other types: string conversion
    
    Args:
        val: The parameter value to convert to string.
        
    Returns:
        str: String representation of the parameter value.
    """
    
    # Convert param data to a string
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, (list, tuple)):
        return ",".join(_to_param_str(x) for x in val)
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)

def build_redis_key(service: str, resource: str, params: dict | None = None) -> str:
    """
    Build a consistent Redis key string. URL proof all param names and param values (stripping "#", "_", ...)

    Args:
        resource (str): The type of data or entity, e.g. "decks", "player", "leaked-elixir" ...
        service (str): The service or namespace prefix, e.g. "cr_api" or "mongo"
        params (dict): Additional key-value pairs describing this cache entry.
                These will be sorted and appended as 'key=value' segments. 
                If player_tag exists, it will be always at the first param slot in the key.
                Additionally the leading '#' will be replaced by stripped. 
                e.g. {"player_tag": "#YYRJQY28", "start_date": "2025-08-01", "end_date": 2025-08-01})
    Returns:
        str: A Redis key in the format 'service:resource:param1=val1:param2=val2'.
    """

    # Sort params to keep key deterministic even if order changes
    parts = [service, resource]
    
    tag = None
    other_params = []
    if params:
        # Extract playerTag if present
        if "playerTag" in params:
            tag = params["playerTag"]
        # Collect all other params except playerTag
        other_params = [(k, v) for k, v in params.items() if k != "playerTag"]

    # Add playerTag segment first if it exists
    if tag is not None:
        # Clash Royale Tag without the leading '#' (safer for Redis key)
        tag_stripped = str(tag).lstrip("#")
        key_str = quote("playerTag", safe="")
        val_str = quote(_to_param_str(tag_stripped), safe="")
        parts.append(f"{key_str}={val_str}")

    # Add remaining params sorted alphabetically
    for key, val in sorted(other_params):
        key_str = quote(str(key), safe="")
        val_str = quote(_to_param_str(val), safe="")
        parts.append(f"{key_str}={val_str}")
    
    # Return key if the length is appropriate
    key = ":".join(parts)
    key_bytes = key.encode("utf-8")
    if len(key_bytes) <= 512:
        return key
    
    
    # Uniquely hash key if it is too long
    digest = hashlib.md5(key.encode()).hexdigest()
    
    tag = params.get("playerTag")
    if tag:
        # Clash Royale Tag without the leading '#' (safer for Redis key)
        tag_stripped = str(tag).lstrip("#")
        # Always keep player tag readable in key, if it exists in params
        return ":".join([service, resource, f"player_tag={tag_stripped}", digest])

    # Regular key 
    return ":".join([service, resource, digest])

async def delete_by_pattern(conn: RedisConn, pattern: str, scan_count: int = 2000, batch_size: int = 2000) -> int:
    """
    Delete all keys that match a given pattern. Works in batches and unlinks as alternative to blocking deletion.

    Args:
    conn (RedisConn): Wrapper around an async Redis connection.
    pattern (str): Glob pattern, e.g. "player_cards:player_tag=%23YYRJQY28*"
    scan_count (int): How many keys to scan per iteration.
    batch_size (int): How many keys to delete per pipeline batch.

    Returns:
        (int) Amount of deleted keys
    """
    
    cursor = 0
    total_deleted = 0
    buffer: list[str] = []

    async def flush(chunk: list[str]):
        nonlocal total_deleted
        if not chunk:
            return
        await conn.client.unlink(*chunk)  # non-blocking delete
        # Increment count by number of keys deleted
        total_deleted += len(chunk)

    while True:
        # Scan for keys matching the given pattern
        cursor, keys = await conn.client.scan(cursor=cursor, match=pattern, count=scan_count)
        if keys:
            buffer.extend(keys)
            # If buffer reached the batch size, delete a chunk and remove from buffer
            while len(buffer) >= batch_size:
                chunk, buffer = buffer[:batch_size], buffer[batch_size:]
                await flush(chunk)
        if cursor == 0:
            break
    
    # Delete any remaining keys left in the buffer        
    if buffer:
        await flush(buffer)

    return total_deleted
