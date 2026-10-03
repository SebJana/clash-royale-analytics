"""Scraper monitoring: rolling counters, the Redis snapshot, and the status endpoint.

Monitoring is for administrators with a shell on the deployed machine only.
The snapshot is stored in redis-key-store (read by status.py) and served by a
small read-only HTTP endpoint that compose publishes on the host's loopback
interface. Neither is reachable through nginx or the website.
"""

import asyncio
import json
import logging
import time
from collections import Counter, defaultdict

from api_key_store import KeyStore
from scrape_schedule import Capacity, Schedule, METRICS_KEY
from settings import settings

logger = logging.getLogger(__name__)

# Counters are kept per time bucket, so the window slides in steps of this size
_BUCKET_S = 10


class Metrics:
    """Counts job outcomes over the last METRICS_WINDOW seconds.

    All workers run on one event loop and ``record`` contains no ``await``,
    so no lock is needed.
    """

    def __init__(self):
        self.started_at = time.time()
        # bucket index -> kind ("battles"/"profiles") -> counters
        self._buckets: dict[int, dict] = {}
        self.capacity: Capacity | None = None
        self.last_reconcile_at: float | None = None
        # Latest snapshot, served by the status endpoint without a Redis read
        self.latest: dict = {}
        # Since start instead of per window: a gap is rare, and one per hour
        # already matters.
        self.possible_gaps = 0

    def record(
        self,
        kind: str,
        outcome: str,
        inserted: int,
        lateness_s: float,
        possible_gap: bool = False,
    ):
        self.possible_gaps += possible_gap
        bucket = self._buckets.setdefault(
            int(time.time() // _BUCKET_S),
            defaultdict(
                lambda: {"outcomes": Counter(), "inserted": 0, "lateness": 0.0}
            ),
        )
        stats = bucket[kind]
        stats["outcomes"][outcome] += 1
        stats["inserted"] += inserted
        stats["lateness"] = max(stats["lateness"], lateness_s)

    def window(self) -> dict:
        """Sum the buckets inside the window and drop older ones."""

        oldest = int((time.time() - settings.METRICS_WINDOW) // _BUCKET_S) + 1
        for index in [index for index in self._buckets if index < oldest]:
            del self._buckets[index]

        totals = {}
        for kind in ("battles", "profiles"):
            outcomes, inserted, lateness = Counter(), 0, 0.0
            for bucket in self._buckets.values():
                if kind in bucket:
                    outcomes.update(bucket[kind]["outcomes"])
                    inserted += bucket[kind]["inserted"]
                    lateness = max(lateness, bucket[kind]["lateness"])
            totals[kind] = {
                "jobs": sum(outcomes.values()),
                "outcomes": dict(outcomes),
                "inserted": inserted,
                "maxClaimLatenessS": round(lateness, 1),
            }
        return totals


async def build_snapshot(
    metrics: Metrics,
    battles: Schedule,
    profiles: Schedule,
    key_store: KeyStore,
    workers: int,
) -> dict:
    """Collect everything the status outputs show into one JSON-ready dict."""

    info = await key_store.redis.info("memory")
    capacity = metrics.capacity
    return {
        "updatedAt": time.time(),
        "startedAt": metrics.started_at,
        "windowS": settings.METRICS_WINDOW,
        "jobs": metrics.window(),
        "schedules": {
            "battles": await battles.stats(),
            "profiles": await profiles.stats(),
        },
        "capacity": (
            {
                "activePlayers": capacity.active_players,
                "maxPlayers": capacity.max_players,
                "baseIntervalS": round(capacity.base_interval_s),
                "requestRate": round(capacity.request_rate, 2),
                "battleRate": round(capacity.battle_rate, 2),
                "battleDemand": round(capacity.battle_demand, 2),
            }
            if capacity
            else None
        ),
        "keys": await key_store.inventory(),
        "maintenance": await key_store.in_maintenance(),
        "workers": workers,
        "lastReconcileAt": metrics.last_reconcile_at,
        "possibleGaps": metrics.possible_gaps,
        "redis": {
            "usedMemory": info.get("used_memory"),
            "maxMemory": info.get("maxmemory"),
        },
    }


async def publish_snapshot(metrics: Metrics, key_store: KeyStore, snapshot: dict):
    """Keep the snapshot for the endpoint and write it for the status CLI."""

    metrics.latest = snapshot
    # A plain string key: the CLI always reads the whole snapshot at once.
    await key_store.redis.set(METRICS_KEY, json.dumps(snapshot))


async def _handle_status_request(
    metrics: Metrics, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
):
    """Answer ``GET /`` with the latest snapshot as JSON; anything else is 404."""

    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5)
        method, path, *_ = request_line.decode("latin-1").split(" ") + ["", ""]
        if method == "GET" and path in ("/", "/status"):
            status, body = "200 OK", json.dumps(metrics.latest, indent=2)
        else:
            status, body = "404 Not Found", json.dumps({"detail": "Not found"})
        payload = body.encode()
        writer.write(
            f"HTTP/1.1 {status}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Connection: close\r\n\r\n".encode() + payload
        )
        await writer.drain()
    except (asyncio.TimeoutError, ConnectionError):
        pass
    finally:
        writer.close()


async def start_status_server(metrics: Metrics) -> asyncio.base_events.Server:
    """Start the read-only status endpoint on STATUS_PORT.

    It listens on all interfaces inside the container, which Docker needs to
    forward the port. docker-compose.yml publishes it as 127.0.0.1:9100 only,
    so on the host it is reachable from the machine itself (or an SSH tunnel).
    """

    return await asyncio.start_server(
        lambda reader, writer: _handle_status_request(metrics, reader, writer),
        host="0.0.0.0",
        port=settings.STATUS_PORT,
    )
