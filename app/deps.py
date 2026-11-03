"""Authentication dependencies."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .config import TOKEN_COOKIE
from .database import get_db
from .errors import unauthorized
from .models import User
from .security import decode_token


def bearer_or_cookie_token(request: Request) -> str | None:
    # Compatibility order copied from webstack-go: header, cookie, query.
    return (
        request.headers.get("Token")
        or request.cookies.get(TOKEN_COOKIE)
        or request.query_params.get("Token")
        or request.query_params.get("token")
    )


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = bearer_or_cookie_token(request)
    if not token:
        raise unauthorized()
    user_id = decode_token(token)
    if not user_id:
        raise unauthorized()
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user
