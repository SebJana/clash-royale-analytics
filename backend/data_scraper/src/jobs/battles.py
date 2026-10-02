"""Battle sync of a single player.

Fetches the battle log, keeps only battles newer than the player's stored
watermark (lastBattleTime), writes them, and reports when the player is due
again. Retries happen through the schedule, never inside the job: a failing
player is acknowledged with a longer delay, so it cannot block a worker or
consume requests in a tight loop.
"""

import logging
from datetime import datetime, timezone

import httpx

from api_key_store import NoKeyAvailable, KeyStoreUnavailable
from clash_royale_api import ClashRoyaleAPI, ClashRoyaleMaintenanceError
from clean import (
    clean_battle_log_list,
    validate_battle_log_structure,
    validate_battle_log_content,
    get_player_name,
)
from game_modes import UniqueGameModes
from intervals import failure_backoff, next_battle_interval, not_found_delay
from jobs.common import JobResult, pool_level_result
from mongo import (
    MongoConn,
    deactivate_tracked_player,
    get_player_sync_state,
    insert_battles,
    record_battle_sync,
    record_battle_sync_failure,
)
from settings import settings

logger = logging.getLogger(__name__)


async def _failed(
    mongo_conn: MongoConn,
    player_tag: str,
    base_interval_s: float,
    not_found: bool = False,
) -> JobResult:
    """Count a player level failure and decide when to try again."""

    counters = await record_battle_sync_failure(
        mongo_conn, player_tag, not_found=not_found
    )
    if not not_found:
        return JobResult(
            "failed", failure_backoff(counters.get("consecutiveFailures", 1))
        )

    not_found_count = counters.get("consecutiveNotFound", 1)
    first_not_found = counters.get("firstNotFoundAt")
    if first_not_found is not None and not_found_count >= (
        settings.NOT_FOUND_DEACTIVATE_COUNT
    ):
        # Motor returns naive datetimes that are UTC
        missing_for = (
            datetime.now(timezone.utc) - first_not_found.replace(tzinfo=timezone.utc)
        ).total_seconds()
        # Both conditions are required: several 404s in a row rule out a
        # single glitch, the time span rules out a short API outage.
        if missing_for >= settings.NOT_FOUND_MIN_SPAN:
            await deactivate_tracked_player(mongo_conn, player_tag, reason="not_found")
            logger.warning(
                "Untracked %s after %d consecutive 404s over %.0f hours",
                player_tag,
                not_found_count,
                missing_for / 3600,
            )
            return JobResult("deactivated", 0)

    return JobResult("not_found", not_found_delay(base_interval_s, not_found_count))


async def sync_player_battles(
    player_tag: str,
    cr_api: ClashRoyaleAPI,
    mongo_conn: MongoConn,
    mode_store: UniqueGameModes,
    base_interval_s: float,
) -> JobResult:
    """Fetch, validate, clean, and persist the new battles of one player.

    Args:
        player_tag (str): Player tag (e.g., "#YYRJQY28").
        cr_api (ClashRoyaleAPI): API client backed by the scraper key pool.
        mongo_conn (MongoConn): Mongo connection used to read state and write data.
        mode_store (UniqueGameModes): Collects game modes until the next flush.
        base_interval_s (float): Current capacity based battle interval.

    Returns:
        JobResult: What happened and when the player is due again.

    Raises:
        Exception: Mongo errors propagate; the caller retries the player later.
    """

    state = await get_player_sync_state(mongo_conn, player_tag)
    if not state or not state.get("active"):
        # Untracked while it was still scheduled. The reconciler would remove
        # it as well, but there is no reason to spend a request on it first.
        return JobResult("inactive", 0)

    try:
        battle_logs = await cr_api.get_player_battle_logs(player_tag=player_tag)

    except (
        ClashRoyaleMaintenanceError,
        NoKeyAvailable,
        KeyStoreUnavailable,
        httpx.HTTPStatusError,
    ) as e:
        pool_result = pool_level_result(e)
        if pool_result is not None:
            return pool_result
        # Only HTTP errors that belong to the player get here
        code = e.response.status_code if e.response is not None else 0
        logger.warning("HTTP %s for %s", code, player_tag)
        return await _failed(
            mongo_conn, player_tag, base_interval_s, not_found=code == 404
        )

    except httpx.RequestError as e:
        logger.warning("Network error for %s: %r", player_tag, e)
        return await _failed(mongo_conn, player_tag, base_interval_s)

    previous_interval = state.get("syncIntervalS")

    if not battle_logs:
        # A player without recent battles is still a successful sync.
        interval = next_battle_interval(base_interval_s, previous_interval, 0)
        await record_battle_sync(mongo_conn, player_tag, None, None, 0, interval)
        return JobResult("synced", interval)

    # Check if the response has all the necessary fields and correct content
    if not validate_battle_log_structure(
        battle_logs
    ) or not validate_battle_log_content(battle_logs):
        logger.error("Battle logs for %s couldn't be used", player_tag)
        return await _failed(mongo_conn, player_tag, base_interval_s)

    # Prepare the data for storage
    cleaned = clean_battle_log_list(battle_logs, player_tag=player_tag)
    player_name = get_player_name(cleaned, player_tag=player_tag)

    # Collect modes from every fetched battle, not only the new ones. Modes
    # lost in a failed flush are then seen again on the next sync.
    for battle in cleaned:
        if battle.get("gameMode"):
            mode_store.add(battle["gameMode"])

    # Only battles after the watermark are new. Without this filter nearly
    # every insert would be a duplicate rejected by the unique index.
    last_battle_time = state.get("lastBattleTime")
    new_battles = [
        battle
        for battle in cleaned
        if last_battle_time is None or battle["battleTime"] > last_battle_time
    ]
    inserted = await insert_battles(mongo_conn, new_battles)

    # Activity is judged by the battles that are new to the database, not by
    # the size of the battle log, which always holds up to ~25 old battles.
    interval = next_battle_interval(base_interval_s, previous_interval, inserted)

    # The watermark comes from all fetched battles, not only the new ones, so
    # it is also set for players whose battles were stored before this field
    # existed and the backfill found none.
    newest = max(battle["battleTime"] for battle in cleaned)
    # The name is updated on every sync: users find players by name, which
    # can change at any time.
    await record_battle_sync(
        mongo_conn, player_tag, newest, player_name, inserted, interval
    )

    return JobResult("synced", interval, inserted)
