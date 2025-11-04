# === core/security.py ===

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from core.config import settings

argon2_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Generate an Argon2 hash for the provided password."""
    return argon2_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if the plaintext password matches the Argon2 hash."""
    try:
        return argon2_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE_DAYS = int(settings.REFRESH_TOKEN_EXPIRE_DAYS)


def _base_payload(user_data: dict, token_type: str, exp_delta: timedelta) -> dict:
    """Construct the base JWT payload for access or refresh tokens."""
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_data["id"]),
        "email": user_data["email"],
        "role": user_data["role"],
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "type": token_type,
        "iat": now,
        "exp": now + exp_delta,
        "jti": str(uuid4()),
    }


def create_access_token(user_data: dict) -> str:
    """Generate a signed JWT access token."""
    payload = _base_payload(user_data, "access", timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_data: dict) -> str:
    """Generate a signed JWT refresh token."""
    payload = _base_payload(user_data, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
