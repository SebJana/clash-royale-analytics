import os
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient


def build_uri_from_parts():
    user = os.getenv("MONGO_APP_USER")
    pwd = os.getenv("MONGO_APP_PWD")
    host = "mongo"
    port = "27017"
    db = os.getenv("MONGO_APP_DB")

    if not all([user, pwd, db]):
        raise ValueError(
            "MONGO_APP_USER, MONGO_APP_PWD, MONGO_APP_DB have to exist in .env file"
        )
    return f"mongodb://{user}:{pwd}@{host}:{port}/{db}?authSource={db}"


# A successful ping is trusted for this long. Every Mongo helper checks the
# connection first, and a ping per call adds a round trip to each operation.
# An operation that fails in between still raises from the driver.
ALIVE_CHECK_INTERVAL_S = 10.0


class MongoConn:
    """
    Async MongoDB connection manager using Motor for the Clash Royale analytics application.
    Fully async implementation for all backend services.
    """

    def __init__(self, app_name: str = "default"):
        self._uri = build_uri_from_parts()
        self._db_name = os.getenv("MONGO_APP_DB")
        self._app_name = app_name
        self.client: AsyncIOMotorClient | None = None
        self.db = None
        self.is_connected = False
        self._last_alive_at = 0.0
        # Concurrent callers that all see a failed ping reconnect once, instead
        # of each creating a client that is never closed.
        self._reconnect_lock = asyncio.Lock()

    async def connect(self):
        """Connect to the database and send a test ping.

        The previous client is closed only after the new one answered, so a
        failed reconnect leaves the old client in place for the next attempt.
        """
        # TODO Bound the time a slow Mongo can hold a caller. Without
        # waitQueueTimeoutMS, a caller waits indefinitely for a free pooled
        # connection once all maxPoolSize (default 100) are busy, and requests
        # hang instead of failing. Set an explicit maxPoolSize per service,
        # plus a deterministic limit of ~10 seconds (waitQueueTimeoutMS and
        # timeoutMS), and map the resulting timeout to a 503 in the API.
        client = AsyncIOMotorClient(self._uri, appname=self._app_name)
        try:
            await client.admin.command("ping")
        except Exception as e:
            client.close()
            self.is_connected = False
            print(f"[DB] Failed to connect to MongoDB: {e}")
            raise

        previous = self.client
        self.client = client
        self.db = client[self._db_name]
        self.is_connected = True
        self._last_alive_at = time.monotonic()
        if previous is not None:
            previous.close()
        print("[DB] Connected to MongoDB successfully.")

    async def is_connection_alive(self):
        """Ping the database to check if it is up and running.

        A ping within the last ALIVE_CHECK_INTERVAL_S counts without a new one.
        """
        if not self.client or not self.is_connected:
            return False
        if time.monotonic() - self._last_alive_at < ALIVE_CHECK_INTERVAL_S:
            return True
        try:
            await self.client.admin.command("ping")
            self._last_alive_at = time.monotonic()
            return True
        except Exception:
            self.is_connected = False
            return False

    async def ensure_connection(self):
        """Ensure connection is alive, reconnect if necessary"""
        if await self.is_connection_alive():
            return
        async with self._reconnect_lock:
            # Another caller may have reconnected while this one waited
            if await self.is_connection_alive():
                return
            print("[DB] Connection lost, attempting to reconnect...")
            await self.connect()

    def close(self):
        """Close the database connection"""
        if self.client:
            self.client.close()
            self.is_connected = False
            print("[DB] MongoDB connection closed.")
