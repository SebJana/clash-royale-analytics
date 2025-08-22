from pydantic import BaseModel, Field
from datetime import date

# --- Request model ---
class BetweenRequest(BaseModel):
    start_date: date = Field(..., description="Start date (inclusive, YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (exclusive, YYYY-MM-DD)")