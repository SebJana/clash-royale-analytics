"""Bearer token extraction shared by the authentication challenge routes."""

from fastapi.security import HTTPBearer

round_token_scheme = HTTPBearer(auto_error=False)
