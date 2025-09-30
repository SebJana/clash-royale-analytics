from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# --- Request model ---
class BetweenRequest(BaseModel):
    # TODO add date range validation - prevent dates before 2016 (Clash Royale launch) and future dates
    # TODO add cross-field validation - ensure end_date > start_date
    # TODO add reasonable range limits - prevent queries spanning more than X years for performance
    start_date: date = Field(..., description="Start date (inclusive, YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (inclusive, YYYY-MM-DD)")
    # TODO add timezone validation - ensure valid timezone strings (e.g., "America/New_York")
    timezone: str = Field(
        ..., description=("Timezone of the given start and end dates")
    )


class BattlesRequest(BaseModel):
    # TODO add datetime validation - prevent future dates and dates before Clash Royale launch
    before: Optional[datetime] = Field(
        None,
        description="Optional before datetime; if set, returns battles strictly before that instant",
    )
    limit: int = Field(..., description="Max battles to fetch (1–50)")
