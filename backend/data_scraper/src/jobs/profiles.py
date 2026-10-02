"""Profile snapshot refresh of a single player.

The API serves profiles from these snapshots instead of calling the Clash
Royale API per page view. A profile may be far staler than the battle data, so
it runs on its own schedule with a long period and a low priority.
"""

import logging

import httpx

from api_key_store import NoKeyAvailable, KeyStoreUnavailable
from clash_royale_api import ClashRoyaleAPI, ClashRoyaleMaintenanceError
from intervals import next_profile_interval
from jobs.common import JobResult, pool_level_result
from mongo import MongoConn, get_player_sync_state, save_player_profile
from settings import settings

logger = logging.getLogger(__name__)


async def refresh_player_profile(
    player_tag: str, cr_api: ClashRoyaleAPI, mongo_conn: MongoConn
) -> JobResult:
    """Fetch the player's profile and store it as the latest snapshot.

    Failures only delay the next attempt. They do not count towards the
    player's failure or not-found counters; the battle job owns those, so a
    deleted account is untracked through one path only.

    Args:
        player_tag (str): Player tag (e.g., "#YYRJQY28").
        cr_api (ClashRoyaleAPI): API client backed by the scraper key pool.
        mongo_conn (MongoConn): Mongo connection used to read state and write data.

    Returns:
        JobResult: What happened and when the profile is due again.

    Raises:
        Exception: Mongo errors propagate; the caller retries the player later.
    """

    state = await get_player_sync_state(mongo_conn, player_tag)
    if not state or not state.get("active"):
        return JobResult("inactive", 0)

    try:
        profile = await cr_api.get_player_info(player_tag)

    except (
        ClashRoyaleMaintenanceError,
        NoKeyAvailable,
        KeyStoreUnavailable,
        httpx.HTTPStatusError,
    ) as e:
        pool_result = pool_level_result(e)
        if pool_result is not None:
            return pool_result
        code = e.response.status_code if e.response is not None else 0
        logger.warning("HTTP %s for the profile of %s", code, player_tag)
        return JobResult("failed", settings.PROFILE_RETRY_DELAY)

    except httpx.RequestError as e:
        logger.warning("Network error for the profile of %s: %r", player_tag, e)
        return JobResult("failed", settings.PROFILE_RETRY_DELAY)

    if not isinstance(profile, dict) or not profile.get("name"):
        # Keep the previous snapshot rather than replacing it with an
        # unusable response.
        logger.error("Profile of %s couldn't be used", player_tag)
        return JobResult("failed", settings.PROFILE_RETRY_DELAY)

    # Battles stored after the previous refresh mean the profile stats changed
    last_battle = state.get("lastBattleTime")
    last_refresh = state.get("lastProfileSyncAt")
    played = last_refresh is None or (
        last_battle is not None and last_battle > last_refresh
    )
    interval = next_profile_interval(state.get("profileSyncIntervalS"), played)

    await save_player_profile(mongo_conn, player_tag, profile, interval)
    return JobResult("synced", interval)
