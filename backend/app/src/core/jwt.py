from datetime import datetime, timedelta
from jose import jwt, JWTError
import uuid
from .settings import settings


def create_admin_token(expires_minutes: int = 5):
    """
    Create a JWT token with admin scope and expiration time.

    This function generates a JSON Web Token (JWT) that grants admin privileges
    for the specified duration. The token includes an expiration time and admin scope.

    Args:
        expires_minutes (int, optional): Token expiration time in minutes.
            Defaults to 5 minutes for security purposes.

    Returns:
        str: Encoded JWT token string that can be used for admin authentication.
    """
    expire = datetime.now() + timedelta(minutes=expires_minutes)

    payload = {"sub": "admin", "jti": str(uuid.uuid4()), "exp": expire}

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def validate_admin_token(token: str):
    """
    Validate and decode a JWT admin token.

    This function attempts to decode and validate a JWT token to ensure it's
    valid, not expired, and properly signed. Used for authenticating admin requests.

    Args:
        token (str): The JWT token string to validate and decode.

    Returns:
        dict or None:
            - If valid: Dictionary containing the decoded token payload with keys:
                - exp: Expiration timestamp
                - scope: Token scope (should be "admin")
            - If invalid: None (token is malformed, expired, or improperly signed)
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as e:
        return None
