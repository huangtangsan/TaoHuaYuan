"""API error shape compatible with webstack-go's `{code, message, data}` body."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.data = {} if data is None else data


def error_body(code: int, message: str, data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "data": {} if data is None else data}


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.data),
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body(400, "Bad Request", exc.errors()),
    )


def unauthorized() -> ApiError:
    return ApiError(401, 401, "Unauthorized")
