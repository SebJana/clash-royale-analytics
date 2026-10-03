"""Per-player battle sync intervals.

The base interval comes from the capacity estimate (see scrape_schedule's
capacity module): the shortest interval the usable keys can sustain for the
current mix of heavy, active, and idle players. Each player's next interval is
then adjusted by what its last sync found, so requests go where battles can
actually be lost.

battle_demand prices that mix for any candidate base with the same rules
next_battle_interval applies, so the estimate and the actual intervals cannot
drift apart.
"""

from collections.abc import Iterable

from settings import settings


def high_activity_factor(base_interval_s: float) -> float:
    """Share of the base interval a very active player gets.

    The shortened interval is paid for by the other players. Once the base has
    to stretch towards MAX_SYNC_INTERVAL there is nothing left to pay with, so
    the factor rises linearly from HIGH_ACTIVITY_INTERVAL_FACTOR at
    HIGH_ACTIVITY_FADE_START to 1 at MAX_SYNC_INTERVAL. At full load every
    player, however active, then syncs at the longest interval.

    Args:
        base_interval_s (float): Current capacity based interval.

    Returns:
        float: Factor between HIGH_ACTIVITY_INTERVAL_FACTOR and 1.
    """

    start = settings.HIGH_ACTIVITY_FADE_START
    end = settings.MAX_SYNC_INTERVAL
    if base_interval_s <= start:
        return settings.HIGH_ACTIVITY_INTERVAL_FACTOR
    if base_interval_s >= end:
        return 1.0
    progress = (base_interval_s - start) / (end - start)
    factor = settings.HIGH_ACTIVITY_INTERVAL_FACTOR
    return factor + (1.0 - factor) * progress


def _clamp_battle_interval(interval_s: float) -> float:
    return min(max(interval_s, settings.MIN_SYNC_INTERVAL), settings.MAX_SYNC_INTERVAL)


def next_battle_interval(
    base_interval_s: float, previous_interval_s: float | None, new_battles: int
) -> float:
    """Seconds until a player's next battle sync, based on its recent activity.

    Args:
        base_interval_s (float): Current capacity based interval.
        previous_interval_s (float | None): The player's last interval, None
            if it has none yet.
        new_battles (int): Battles the sync just inserted.

    Returns:
        float: The next interval, always within [MIN_SYNC_INTERVAL, MAX_SYNC_INTERVAL].
    """

    if new_battles >= settings.HIGH_ACTIVITY_BATTLES:
        # Close to the battle log window: sync sooner, so a long session
        # does not overflow it before the next sync.
        interval = base_interval_s * high_activity_factor(base_interval_s)
    elif new_battles > 0:
        interval = base_interval_s
    else:
        # Idle since the last sync: stretch the previous interval step by
        # step. A single new battle resets the player to the base interval.
        previous = previous_interval_s or base_interval_s
        interval = max(base_interval_s, previous * settings.IDLE_INTERVAL_GROWTH)

    return _clamp_battle_interval(interval)


def planned_battle_interval(
    base_interval_s: float,
    sync_interval_s: float | None,
    last_new_battles: int | None,
) -> float:
    """Interval a player is planned at if the base were base_interval_s.

    Unlike next_battle_interval, an idle player is priced at its current
    interval, not the stretched next one: its next sync has not happened yet.

    Args:
        base_interval_s (float): Candidate base interval.
        sync_interval_s (float | None): The player's stored interval.
        last_new_battles (int | None): Battles its last successful sync
            inserted. None (never synced, or synced before the count was
            stored) counts as an active player.

    Returns:
        float: The interval, within [MIN_SYNC_INTERVAL, MAX_SYNC_INTERVAL].
    """

    if last_new_battles is None or last_new_battles > 0:
        return next_battle_interval(base_interval_s, None, last_new_battles or 1)
    current = sync_interval_s or base_interval_s
    return _clamp_battle_interval(max(base_interval_s, current))


def battle_demand(players: Iterable[dict], base_interval_s: float) -> float:
    """Battle sync requests per second the players need at a candidate base.

    Args:
        players (Iterable[dict]): Tracked players with syncIntervalS and
            lastSyncNewBattles (see get_tracked_players_sync_times).
        base_interval_s (float): Candidate base interval.

    Returns:
        float: Requests per second. Never increases with a longer base.
    """

    return sum(
        1
        / planned_battle_interval(
            base_interval_s, player["syncIntervalS"], player["lastSyncNewBattles"]
        )
        for player in players
    )


def profile_demand(players: Iterable[dict]) -> float:
    """Profile requests per second the players currently need.

    Args:
        players (Iterable[dict]): Tracked players with profileSyncIntervalS
            (see get_tracked_players_sync_times).

    Returns:
        float: Requests per second. A player without an interval yet is
            refreshed at PROFILE_MIN_INTERVAL first.
    """

    return sum(
        1 / (player["profileSyncIntervalS"] or settings.PROFILE_MIN_INTERVAL)
        for player in players
    )


def next_profile_interval(
    previous_interval_s: float | None, played_since_last_refresh: bool
) -> float:
    """Seconds until a player's next profile refresh.

    Args:
        previous_interval_s (float | None): The player's last profile interval,
            None if it has none yet.
        played_since_last_refresh (bool): The player has battles newer than the
            previous profile refresh, so the profile stats changed.

    Returns:
        float: The next interval, within [PROFILE_MIN_INTERVAL, PROFILE_MAX_INTERVAL].
    """

    if played_since_last_refresh or previous_interval_s is None:
        return settings.PROFILE_MIN_INTERVAL
    # Unchanged since the last refresh: check less often, the stats can only
    # change once the player plays again.
    return min(
        previous_interval_s * settings.PROFILE_IDLE_GROWTH,
        settings.PROFILE_MAX_INTERVAL,
    )


def failure_backoff(consecutive_failures: int) -> float:
    """Delay before retrying a player after its n-th consecutive failure."""

    exponent = max(0, consecutive_failures - 1)
    return min(
        settings.FAILURE_BACKOFF_BASE * 2 ** min(exponent, 16),
        settings.FAILURE_BACKOFF_MAX,
    )


def not_found_delay(base_interval_s: float, consecutive_not_found: int) -> float:
    """Delay before checking a player again after its n-th consecutive 404.

    Starts at the normal interval, so a single false 404 delays the player by
    one sync at most, and doubles up to NOT_FOUND_RETRY_MAX for accounts that
    are really gone.
    """

    exponent = max(0, consecutive_not_found - 1)
    return min(base_interval_s * 2 ** min(exponent, 16), settings.NOT_FOUND_RETRY_MAX)
