from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo
from models.schema import BetweenRequest, BattlesRequest
from core.deps import RedConn
from redis_service import GAME_MODES_CACHE_KEY, get_redis_json
from typing import Optional, List
from core.settings import settings


class ParamsRequestError(Exception):
    """Raised when a BetweenRequest contains invalid date ranges."""

    def __init__(
        self,
        detail: str,
        code: int = 403,
    ):
        super().__init__(detail)
        self.detail = detail
        self.code = code


def str_to_date(date_str: str) -> date:
    """Convert a date string in YYYY-MM-DD format to a date object.

    Args:
        date_str (str): A date string in the format "YYYY-MM-DD".

    Returns:
        date: A date object representing the parsed date.

    Raises:
        ValueError: If the date string is not in the correct format or represents an invalid date.
    """
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def get_clash_royale_release_date() -> date:
    """Get the official release date of Clash Royale.

    Returns:
        date: The official launch date of Clash Royale (March 2, 2016).
    """
    # Official launch date for Clash Royale
    return str_to_date("2016-03-02")


def valid_timezone(timezone: str):
    """ "
    Checks if a given timezone exists and is valid.

    Args:
        timezone (str): timezone

    Return:
        bool: True if it is valid, false otherwise.

    """

    # Check if timezone exists
    try:
        _ = ZoneInfo(timezone)
        return True
    except Exception:
        return False


def validate_between_request(request: BetweenRequest):
    """Validate a BetweenRequest for date range and timezone constraints.

    Performs comprehensive validation of a date range request including:
    - Start date is not before Clash Royale's release date
    - End date is not before start date
    - End date is not in the future
    - Date range does not exceed maximum allowed days
    - Timezone is valid and exists

    Args:
        request (BetweenRequest): The request object containing start_date, end_date, and timezone.

    Raises:
        ParamsRequestError: If any validation constraint is violated, with specific error details.
    """
    start = request.start_date
    end = request.end_date
    release = get_clash_royale_release_date()

    # The request dates are calendar dates in the user's timezone. Validate the
    # timezone before using it to decide which calendar day is "today".
    if not valid_timezone(request.timezone):
        raise ParamsRequestError(f"Timezone {request.timezone} does not exist")
    today = datetime.now(ZoneInfo(request.timezone)).date()

    # Check if start is after release
    if start < release:
        raise ParamsRequestError(
            f"Start date can not be before {release}, the Clash Royale release date"
        )
    # Check if end is after start
    if end < start:
        raise ParamsRequestError("Start date can not be after end date")
    # Check if end is today or before today
    if end > today:
        raise ParamsRequestError("End date can not be after today")

    # Check if the delta between start and date is valid
    date_diff = end - start
    if date_diff.days > settings.MAX_TIME_RANGE_DAYS:
        raise ParamsRequestError(
            f"Request can only span {settings.MAX_TIME_RANGE_DAYS} days"
        )


def validate_battles_request(request: BattlesRequest):
    """Validate a BattlesRequest for limit and date constraints.

    Performs validation of a battles request including:
    - Battle limit is within allowed minimum and maximum range
    - If specified, 'before' date is not before Clash Royale's release date
    - If specified, 'before' date is not in the future

    Args:
        request (BattlesRequest): The request object containing limit and optional before date.

    Raises:
        ParamsRequestError: If any validation constraint is violated, with specific error details.
    """
    tomorrow = datetime.today() + timedelta(days=1)
    release = get_clash_royale_release_date()

    # Check if the limit is in the allowed range
    if request.limit < settings.MIN_BATTLES or request.limit > settings.MAX_BATTLES:
        raise ParamsRequestError(f"Given limit {request.limit} is invalid")

    # Only check before time if there was any given
    if not request.before:
        return

    # Convert release date to datetime for comparison
    release_datetime = datetime.combine(release, time(0, 0, 0))

    # Normalize timezone awareness for comparison
    # If request.before is timezone-aware, make other datetimes timezone-aware too
    # If request.before is timezone-naive, ensure all comparisons are timezone-naive
    if request.before.tzinfo is not None:
        # request.before is timezone-aware, convert others to UTC for comparison
        if release_datetime.tzinfo is None:
            release_datetime = release_datetime.replace(tzinfo=ZoneInfo("UTC"))
        if tomorrow.tzinfo is None:
            tomorrow = tomorrow.replace(tzinfo=ZoneInfo("UTC"))
    else:
        # request.before is timezone-naive, make others timezone-naive too
        if release_datetime.tzinfo is not None:
            release_datetime = release_datetime.replace(tzinfo=None)
        if tomorrow.tzinfo is not None:
            tomorrow = tomorrow.replace(tzinfo=None)

    # Check if start is after release
    if request.before < release_datetime:
        raise ParamsRequestError(
            f"Start date can not be before {release}, the Clash Royale release date"
        )

    # Check if end is on or after tomorrow
    if request.before >= tomorrow:
        raise ParamsRequestError("End date can not be after today")


async def validate_game_modes(redis_conn: RedConn, game_modes: Optional[List[str]]):
    """Deduplicate the requested game modes and drop a filter that covers every mode.

    Modes missing from the cached list are kept. The cache can lag behind the
    battles by a flush, so a missing mode may already exist in Mongo. Dropping
    it would narrow the result, and dropping every requested mode would turn
    the request into an unfiltered one. An unknown mode that really does not
    exist simply matches no battle. The values are plain strings in an $in
    match, so they cannot inject query operators.

    Args:
        redis_conn (RedConn): Active Redis connection instance for accessing cached data.
        game_modes (Optional[List[str]]): List of game mode names to validate.
            Can be None or empty list.

    Returns:
        Optional[List[str]]: None or an empty list unchanged, an empty list if
            the request names exactly the cached modes (no filter needed),
            otherwise the requested modes without duplicates, in request order.
    """
    if not game_modes:
        return game_modes

    unique_modes = list(dict.fromkeys(game_modes))

    all_game_modes = await get_redis_json(redis_conn, GAME_MODES_CACHE_KEY)
    # Without the cached list the request cannot be compared to all modes
    if not all_game_modes:
        return unique_modes

    # Mongo applies no game mode filter for an empty list, which saves the $in
    # match. Only an exact match qualifies: a request with an extra, uncached
    # mode is not known to cover every mode.
    if set(unique_modes) == set(all_game_modes.keys()):
        return []

    return unique_modes
