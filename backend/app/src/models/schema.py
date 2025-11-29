from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from core.settings import settings


# --- Request model ---
class BetweenRequest(BaseModel):
    start_date: date = Field(..., description="Start date (inclusive, YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (inclusive, YYYY-MM-DD)")
    timezone: str = Field(
        ..., description=("Timezone of the given start and end dates")
    )


class BattlesRequest(BaseModel):
    before: Optional[datetime] = Field(
        None,
        description="Optional before datetime; if set, returns battles strictly before that instant",
    )
    limit: int = Field(
        ...,
        description=f"Max battles to fetch ({settings.MIN_BATTLES}–{settings.MAX_BATTLES})",
    )


class SecurityQuestionsRequest(BaseModel):
    most_annoying_card: str = Field(
        ..., description="What is the single most annoying card in Clash Royale?"
    )
    most_skillful_card: str = Field(
        ..., description="What is the single most skillful card in Clash Royale?"
    )
    most_mousey_card: str = Field(
        ...,
        description="What is the most 'mausig (english: sweetie)' card in Clash Royale?",
    )
