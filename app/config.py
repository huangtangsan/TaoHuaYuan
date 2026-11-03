"""Application settings, kept deliberately small and environment-driven."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("WEBSTACK_DATA_DIR", BASE_DIR / "data")).resolve()
FRONTEND_DIST = Path(os.getenv("WEBSTACK_FRONTEND_DIST", BASE_DIR / "frontend" / "dist")).resolve()

DATABASE_URL = os.getenv(
    "WEBSTACK_DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'webstack.db').as_posix()}",
)
JWT_SECRET = os.getenv("WEBSTACK_JWT_SECRET", "change-me-in-production-webstack-python")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("WEBSTACK_TOKEN_EXPIRE_HOURS", "24"))
TOKEN_COOKIE = "_login_token_"

# Behind HTTPS the login cookie must carry Secure, otherwise a browser will also
# send it over plain HTTP (e.g. a user typing the bare domain). Kept opt-in so
# local development over http://127.0.0.1 still works.
COOKIE_SECURE = os.getenv("WEBSTACK_COOKIE_SECURE", "0") == "1"

# /api/docs and /api/openapi.json are handy while developing but hand strangers a
# full map of the admin API, so production can turn them off entirely.
ENABLE_DOCS = os.getenv("WEBSTACK_DOCS", "1") != "0"

# The Vite dev server needs CORS because it runs on a different port. Production is same-origin.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "WEBSTACK_CORS_ORIGINS",
        "http://localhost:4173,http://127.0.0.1:4173,"
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

DEFAULT_SITE_ICON = "/assets/images/default-site.svg"
DEFAULT_SITE_LOGO = "/assets/images/logo@2x.png"
DEFAULT_FAVICON = "/favicon.png"

MAX_REMOTE_IMAGE_BYTES = 8 * 1024 * 1024
MAX_SVG_BYTES = 32 * 1024
SITE_ICON_SIZE = (64, 64)
SITE_LOGO_SIZE = (200, 50)

# Icon discovery: how long a single candidate may take, and which third-party
# mirrors are tried only after the site itself has no usable icon.
ICON_FETCH_TIMEOUT = float(os.getenv("WEBSTACK_ICON_TIMEOUT", "3"))
# Hard cap for the whole icon hunt, so a dead host cannot stall a batch import.
ICON_TOTAL_BUDGET = float(os.getenv("WEBSTACK_ICON_BUDGET", "12"))
ICON_FALLBACK_TEMPLATES = [
    item.strip()
    for item in os.getenv(
        "WEBSTACK_ICON_FALLBACK",
        "https://icons.duckduckgo.com/ip3/{host}.ico",
    ).split(",")
    if item.strip()
]
# Manifest parsing costs one extra request per site; it is where modern sites
# keep their 192/512px icons, so it stays on by default.
ICON_READ_MANIFEST = os.getenv("WEBSTACK_ICON_MANIFEST", "1") != "0"
# Sites with no usable icon at all get a generated letter tile instead of the
# shared grey placeholder, so a card never looks broken. Set to 0 to keep the
# placeholder (and the "no icon found" report) unchanged.
ICON_LETTER_FALLBACK = os.getenv("WEBSTACK_ICON_LETTER", "1") != "0"

DATA_DIR.mkdir(parents=True, exist_ok=True)
