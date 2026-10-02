"""Scraping capacity estimate shared by the data scraper and the API.

The data scraper knows its usable keys and the number of tracked players, so it
computes the capacity and publishes it to Redis. The API reads the published
values to decide whether one more player can be tracked; it never sees the
scraper's key pool itself.

The model: every battle sync and every profile refresh costs one Clash Royale
request. The scraper pool can start ``usable_keys * per_key_rps`` requests per
second; a utilization factor below 1 keeps headroom for retries, 429 cooldowns,
and card refreshes. Profile refreshes take their share first, the rest is
available for battle syncs.
"""

import math
import time
from dataclasses import dataclass, asdict

from redis.asyncio import Redis

CAPACITY_KEY = "crsched:capacity"


@dataclass(frozen=True)
class Capacity:
    """Capacity of the scraper pool for the current number of tracked players.

    base_interval_s is the battle sync interval every player can get right now.
    max_players is the most players the pool can sync within the admission
    limit; None means unknown (no usable keys yet), in which case nothing is
    rejected.
    """

    active_players: int
    usable_keys: int
    request_rate: float
    battle_rate: float
    base_interval_s: float
    max_players: int | None
    updated_at: float


def compute_capacity(
    active_players: int,
    usable_keys: int,
    per_key_rps: float,
    utilization: float,
    profile_max_age_s: float,
    min_interval_s: float,
    max_interval_s: float,
    admission_fraction: float,
) -> Capacity:
    """Compute the base battle interval and the admission limit.

    Args:
        active_players (int): Currently tracked players.
        usable_keys (int): Usable keys in the scraper pool.
        per_key_rps (float): Requests per second each key may start.
        utilization (float): Share of the raw request rate that is planned for
            (0..1). The rest is headroom.
        profile_max_age_s (float): Profile refresh period; costs
            ``active_players / profile_max_age_s`` requests per second.
        min_interval_s (float): Shortest battle interval; a small deployment
            never syncs more often than this.
        max_interval_s (float): Longest battle interval that still keeps every
            player within the battle log window.
        admission_fraction (float): New players are admitted while the base
            interval stays within this fraction of max_interval_s. Keeps room
            for very active players, whose interval is shortened.

    Returns:
        Capacity: The estimate, stamped with the current time.
    """

    request_rate = usable_keys * per_key_rps * utilization
    battle_rate = request_rate - active_players / profile_max_age_s

    if battle_rate > 0:
        needed = active_players / battle_rate
        base_interval_s = min(max(needed, min_interval_s), max_interval_s)
    else:
        # More players than the keys can serve at all: everyone gets the
        # longest interval and is late anyway.
        base_interval_s = max_interval_s

    max_players = None
    if request_rate > 0:
        # Admission limit: the most players N whose base interval stays
        # within the allowed interval A.
        #   R = request_rate, requests per second the keys may start
        #   P = profile_max_age_s, every player costs one profile request
        #       per P seconds
        #   A = allowed_interval, seconds within which every player has to
        #       be synced once
        # N players need N / P requests per second for profiles, which leaves
        # R - N / P for battle syncs. Syncing each of the N players once then
        # takes N / (R - N / P) seconds, and that has to stay within A:
        #   N / (R - N / P) <= A
        #   N <= A * R - A * N / P        (multiply by R - N / P > 0)
        #   N * (1 + A / P) <= A * R
        #   N <= A * R / (1 + A / P)
        # Example with the default settings and 1 key at 1 request/s:
        # R = 0.8, A = 0.8 * 3600 s = 2880 s, P = 86400 s
        # -> N <= 2880 * 0.8 / (1 + 2880 / 86400) = 2229 players
        allowed_interval = admission_fraction * max_interval_s
        max_players = math.floor(
            allowed_interval
            * request_rate
            / (1 + allowed_interval / profile_max_age_s)
        )

    return Capacity(
        active_players=active_players,
        usable_keys=usable_keys,
        request_rate=request_rate,
        battle_rate=max(battle_rate, 0.0),
        base_interval_s=base_interval_s,
        max_players=max_players,
        updated_at=time.time(),
    )


async def publish_capacity(redis: Redis, capacity: Capacity):
    """Store the capacity estimate for the API (and the status output)."""

    # Redis hashes hold strings; "" stands for None.
    fields = {
        key: "" if value is None else str(value)
        for key, value in asdict(capacity).items()
    }
    await redis.hset(CAPACITY_KEY, mapping=fields)


async def read_capacity(redis: Redis, max_age_s: float) -> Capacity | None:
    """Read the published estimate.

    Args:
        redis (Redis): Client for redis-key-store with ``decode_responses=True``.
        max_age_s (float): Older estimates are ignored, e.g. while the scraper
            is down and the number no longer reflects its keys.

    Returns:
        Capacity | None: The estimate, or None if missing or outdated.
    """

    fields = await redis.hgetall(CAPACITY_KEY)
    if not fields or "updated_at" not in fields:
        return None
    if time.time() - float(fields["updated_at"]) > max_age_s:
        return None
    return Capacity(
        active_players=int(fields["active_players"]),
        usable_keys=int(fields["usable_keys"]),
        request_rate=float(fields["request_rate"]),
        battle_rate=float(fields["battle_rate"]),
        base_interval_s=float(fields["base_interval_s"]),
        max_players=int(fields["max_players"]) if fields["max_players"] else None,
        updated_at=float(fields["updated_at"]),
    )
