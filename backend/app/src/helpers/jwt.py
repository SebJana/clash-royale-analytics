from datetime import datetime, timedelta
from jose import jwt, JWTError
import uuid
from enum import StrEnum
from core.settings import settings


# Types of tokens the api gives out and validates
class AvailableTokenTypes(StrEnum):
    CAPTCHA = "captcha"
    SECURITY = "security"
    WORDLE = "wordle"
    AUTH = "auth"


def create_access_token(type: str, expires_minutes: int = 30):
    """
    Create a JWT token with admin scope and expiration time.

    This function generates a JSON Web Token (JWT) that grants privileges
    for the specified duration. The token includes an expiration time and admin scope.

    Args:
        type (str): The type/role the token should be and enable.
        expires_minutes (int, optional): Token expiration time in minutes.
            Defaults to 5 minutes for security purposes.

    Returns:
        str: Encoded JWT token string that can be used for admin authentication.
    """
    expire = datetime.now() + timedelta(minutes=expires_minutes)

    payload = {
        "sub": "admin",
        "type": type,
        "jti": str(uuid.uuid4()),
        "exp": expire,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def validate_access_token(token: str, type: str):
    """
    Validate and decode a JWT access token.

    This function attempts to decode and validate a JWT token to ensure it's
    valid, not expired, and properly signed. Returns True if the token is valid
    and has the given type.

    Args:
        type (str): The type/role the token should be.
        token (str): The JWT token string to validate and decode.

    Returns:
        bool: True if the token is valid and has the specified type,
              False otherwise (token is malformed, expired, or improperly signed).
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload.get("type") == type
    except JWTError:
        return False
