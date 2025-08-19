from pydantic import BaseModel, Field
from datetime import date

# --- Request model ---
class PlayerBetweenRequest(BaseModel):
    player_tag: str = Field(..., description="Clash Royale player tag, e.g. #YYRJQY28")
    start_date: date = Field(..., description="Start date (inclusive, YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (exclusive, YYYY-MM-DD)")