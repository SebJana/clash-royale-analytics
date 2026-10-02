"""Per-player battle sync intervals.

The base interval comes from the capacity estimate (see scrape_schedule's
capacity module): the shortest interval every tracked player can get with the
usable keys. Each player's next interval is then adjusted by what its last sync
found, so requests go where battles can actually be lost.
"""

from settings import settings


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
        interval = base_interval_s * settings.HIGH_ACTIVITY_INTERVAL_FACTOR
    elif new_battles > 0:
        interval = base_interval_s
    else:
        # Idle since the last sync: stretch the previous interval step by
        # step. A single new battle resets the player to the base interval.
        previous = previous_interval_s or base_interval_s
        interval = max(base_interval_s, previous * settings.IDLE_INTERVAL_GROWTH)

    return min(max(interval, settings.MIN_SYNC_INTERVAL), settings.MAX_SYNC_INTERVAL)


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
    return min(
        base_interval_s * 2 ** min(exponent, 16), settings.NOT_FOUND_RETRY_MAX
    )
