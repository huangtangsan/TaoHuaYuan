"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import CORS_ORIGINS, ENABLE_DOCS, FRONTEND_DIST
from .database import Base, SessionLocal, engine
from .errors import ApiError, api_error_handler, error_body, validation_error_handler
from .routers import auth, categories, config, dashboard, public, sites
from .services.seed import seed_database

logger = logging.getLogger("webstack")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    logger.info("WebStack Python ready; frontend dist: %s", FRONTEND_DIST)
    yield


app = FastAPI(
    title="WebStack Python",
    version="1.0.0",
    docs_url="/api/docs" if ENABLE_DOCS else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if ENABLE_DOCS else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=7200,
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exc)
    return JSONResponse(status_code=500, content=error_body(500, "Internal Server Error"))


app.include_router(public.router, prefix="/api", tags=["public"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(categories.router, prefix="/api", tags=["categories"])
app.include_router(sites.router, prefix="/api", tags=["sites"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])


@app.get("/api/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
    response_model=None,
)
def spa(full_path: str) -> FileResponse | JSONResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    if FRONTEND_DIST.exists():
        candidate = (FRONTEND_DIST / full_path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST)
        except ValueError:
            candidate = Path()
        if full_path and candidate.is_file():
            cache = "public, max-age=31536000, immutable" if full_path.startswith("assets/") else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})

        index = FRONTEND_DIST / "index.html"
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return JSONResponse(
        status_code=503,
        content={
            "code": 503,
            "message": "前端尚未构建，请在 frontend 目录执行 npm install && npm run build",
            "data": {},
        },
    )
