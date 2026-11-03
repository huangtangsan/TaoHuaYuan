"""Password hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .config import JWT_ALGORITHM, JWT_SECRET, TOKEN_EXPIRE_HOURS


def md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def password_digest(value: str) -> str:
    """Accept the legacy client-side MD5 or a plain password.

    The bundled frontend still hashes passwords before sending them. Accepting
    both keeps direct API clients convenient without weakening stored values.
    """
    if len(value) == 32 and all(ch in "0123456789abcdefABCDEF" for ch in value):
        return value.lower()
    return md5_hex(value)


def verify_password(submitted: str, stored: str) -> bool:
    return hmac.compare_digest(password_digest(submitted), stored.lower())


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "user_id": user_id,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("user_id", 0))
        return user_id or None
    except (jwt.PyJWTError, TypeError, ValueError):
        return None
