"""Login, session info, logout, and password change."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import COOKIE_SECURE, TOKEN_COOKIE, TOKEN_EXPIRE_HOURS
from ..database import get_db
from ..deps import current_user
from ..errors import ApiError
from ..models import Menu, User, UserMenu
from ..security import create_token, password_digest, verify_password
from ._helpers import first_text, read_request_data

router = APIRouter()


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    data, _files = await read_request_data(request)
    username = (first_text(data, "username") or "").strip()
    password = first_text(data, "password") or ""
    if not username:
        raise ApiError(400, 400, "Bad Request")

    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password):
        # Legacy frontend expects HTTP 500 + code 100 for bad credentials.
        raise ApiError(500, 100, "用户名和密码错误")

    token = create_token(user.id)
    response = JSONResponse({"token": token})
    response.set_cookie(
        TOKEN_COOKIE,
        token,
        max_age=TOKEN_EXPIRE_HOURS * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/admin/info")
def admin_info(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Menu)
        .join(UserMenu, UserMenu.menu_id == Menu.id)
        .where(UserMenu.user_id == user.id, Menu.is_used.is_(True))
        .order_by(Menu.sort, Menu.id)
    ).scalars()
    return {
        "username": user.username,
        "menu": [
            {
                "id": menu.id,
                "pid": menu.pid,
                "name": menu.name,
                "link": menu.link,
                "icon": menu.icon,
            }
            for menu in rows
        ],
    }


@router.post("/admin/logout")
def logout() -> JSONResponse:
    response = JSONResponse({})
    response.delete_cookie(TOKEN_COOKIE, path="/")
    return response


@router.patch("/admin/modify_password")
async def modify_password(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    data, _files = await read_request_data(request)
    old_password = first_text(data, "old_password") or ""
    new_password = first_text(data, "new_password") or ""
    if not old_password or not new_password:
        raise ApiError(400, 400, "Bad Request")
    if not verify_password(old_password, user.password):
        raise ApiError(500, 100, "原密码错误")
    user.password = password_digest(new_password)
    db.add(user)
    db.commit()
    return {}
