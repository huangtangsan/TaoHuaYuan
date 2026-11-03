"""Request parsing helpers shared by admin endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from starlette.datastructures import UploadFile


async def read_request_data(request: Request) -> tuple[dict[str, Any], dict[str, UploadFile]]:
    content_type = request.headers.get("content-type", "").lower()
    data: dict[str, Any] = {}
    files: dict[str, UploadFile] = {}

    if "application/json" in content_type:
        try:
            body = await request.json()
        except ValueError:
            body = {}
        if isinstance(body, dict):
            data.update(body)
    elif (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        form = await request.form()
        for key, value in form.multi_items():
            if isinstance(value, UploadFile):
                files[key] = value
            else:
                data[key] = value

    return data, files


def as_bool(value: Any, default: bool | None = None) -> bool | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def as_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def first_text(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    return str(value)
