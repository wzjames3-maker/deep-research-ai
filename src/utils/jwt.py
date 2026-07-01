from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import jwt, JWTError

from src.config import settings
from src.errors import TokenInvalidError


def create_token(user_id: UUID, username: str, expires_delta: int = 86400) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=expires_delta),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise TokenInvalidError("Token 无效")


def decode_token(token: str) -> dict:
    """Decode token without expiry check (for testing/debugging)."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_exp": False})
    except JWTError:
        raise TokenInvalidError("Token 无效")
