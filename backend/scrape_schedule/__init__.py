"""Per-player scraping schedule, shared by the data scraper and the API.

This is a separate package instead of part of the data scraper because the API
also writes to the schedule: a newly tracked player is added as due immediately,
so its first sync starts within seconds, and an untracked player is removed
right away. The API image does not contain the scraper source, and a second
copy of the Redis key names and Lua scripts would drift apart.
"""

from .schedule import Schedule, Claim
from .capacity import (
    Capacity,
    compute_capacity,
    publish_capacity,
    read_capacity,
)

# Names shared by the scraper (claims and acks) and the API (add and remove).
BATTLES_SCHEDULE = "battles"
PROFILES_SCHEDULE = "profiles"

# A published capacity older than this is ignored by the API. Three missed
# reconciliations mean the scraper is down, and its last estimate may no
# longer match its keys.
CAPACITY_MAX_AGE_S = 15 * 60  # 15 minutes

# Snapshot of the scraper's monitoring metrics (JSON), read by the status CLI.
METRICS_KEY = "crsched:metrics"

__all__ = [
    "Schedule",
    "Claim",
    "Capacity",
    "compute_capacity",
    "publish_capacity",
    "read_capacity",
    "BATTLES_SCHEDULE",
    "PROFILES_SCHEDULE",
    "CAPACITY_MAX_AGE_S",
    "METRICS_KEY",
]
