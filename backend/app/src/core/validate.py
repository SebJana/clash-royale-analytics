from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo
from models.schema import BetweenRequest, BattlesRequest
from .settings import settings


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
    today = date.today()

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

    # Check if timezone exists
    try:
        _ = ZoneInfo(request.timezone)
    except Exception:
        raise ParamsRequestError(f"Timezone {request.timezone} does not exist")


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
