"""Keeps the schedules consistent with the tracked players in Mongo.

Mongo is the source of truth. The API adds and removes players in the schedules
directly, but a failed Redis write, a lost Redis volume, or players tracked
before the schedules existed would otherwise leave players unscheduled forever.
"""

import logging
import time
from datetime import datetime, timezone

from mongo import MongoConn, get_tracked_players_sync_times
from scrape_schedule import Schedule
from settings import settings

logger = logging.getLogger(__name__)


def _epoch_ms(value: datetime, plus_s: float) -> int:
    # Motor returns naive datetimes that are UTC
    return int((value.replace(tzinfo=timezone.utc).timestamp() + plus_s) * 1000)


def _battle_due_ms(sync: dict) -> int:
    if sync["lastBattlesSyncAt"] is None:
        # Never synced: in front of the queue
        return 0
    # Continue the player's own rhythm instead of syncing every rebuilt
    # player at once after a Redis data loss.
    interval = sync["syncIntervalS"] or settings.MIN_SYNC_INTERVAL
    return _epoch_ms(sync["lastBattlesSyncAt"], interval)


def _profile_due_ms(sync: dict) -> int:
    if sync["lastProfileSyncAt"] is None:
        # Players tracked before snapshots existed. Due now but not at score 0:
        # profiles never jump ahead of due battle syncs unless they are late
        # by more than PROFILE_MAX_LATENESS.
        return int(time.time() * 1000)
    interval = sync["profileSyncIntervalS"] or settings.PROFILE_MIN_INTERVAL
    return _epoch_ms(sync["lastProfileSyncAt"], interval)


async def reconcile_schedules(
    battles: Schedule, profiles: Schedule, mongo_conn: MongoConn
) -> int:
    """Reconcile both schedules with the tracked players.

    Both schedules are read BEFORE Mongo. The API writes Mongo first and the
    schedules second, so a player added during this run is either already in
    the schedule snapshot or already in Mongo, and is never removed as stale.

    Returns:
        int: Number of tracked players.
    """

    battles_snapshot = await battles.scheduled_tags()
    profiles_snapshot = await profiles.scheduled_tags()
    tracked = await get_tracked_players_sync_times(mongo_conn)

    results = {}
    for name, schedule, snapshot, due_ms in (
        ("battles", battles, battles_snapshot, _battle_due_ms),
        ("profiles", profiles, profiles_snapshot, _profile_due_ms),
    ):
        missing = {
            tag: due_ms(sync) for tag, sync in tracked.items() if tag not in snapshot
        }
        stale = snapshot - tracked.keys()
        # NX keeps a due time the API set between the reads above.
        await schedule.add_many(missing)
        await schedule.remove(*stale)
        results[name] = (len(missing), len(stale))

    for name, (added, removed) in results.items():
        if added or removed:
            logger.info(
                "%s schedule reconciled: %d players added, %d removed",
                name.capitalize(),
                added,
                removed,
            )
    return len(tracked)
