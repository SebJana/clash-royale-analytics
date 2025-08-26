from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

# --- Request model ---
class BetweenRequest(BaseModel):
    start_date: date = Field(..., description="Start date (inclusive, YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (inclusive, YYYY-MM-DD)")
    
class BattlesRequest(BaseModel):
    before: Optional[datetime] = Field(
        None, description="Optional before datetime; if set, returns battles strictly before that instant"
    )
    limit: int = Field(..., description="Max battles to fetch (1–50)")