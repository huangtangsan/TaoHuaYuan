"""Site configuration and about-page settings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DEFAULT_FAVICON, DEFAULT_SITE_LOGO, SITE_ICON_SIZE, SITE_LOGO_SIZE
from ..database import get_db
from ..deps import current_user
from ..models import SysConfig
from ..serializers import config_dict
from ..services.images import image_bytes_to_stored
from ._helpers import as_bool, first_text, read_request_data

router = APIRouter(prefix="/admin/config", dependencies=[Depends(current_user)])

TEXT_FIELDS = (
    "about_site",
    "about_author",
    "site_title",
    "site_keyword",
    "site_desc",
    "site_record",
    "site_url",
)
BOOL_FIELDS = ("is_about", "is_search")


def _get_config(db: Session) -> SysConfig:
    config = db.scalar(select(SysConfig).order_by(SysConfig.id))
    if config is None:
        config = SysConfig(
            id=1,
            about_site="",
            about_author="",
            is_about=False,
            is_search=True,
            site_title="桃花源 · 网址导航",
            site_keyword="",
            site_desc="",
            site_record="",
            site_logo=DEFAULT_SITE_LOGO,
            site_favicon=DEFAULT_FAVICON,
            site_url="",
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("")
def get_config(db: Session = Depends(get_db)) -> dict:
    return config_dict(_get_config(db))


@router.put("")
async def update_config(request: Request, db: Session = Depends(get_db)) -> dict:
    config = _get_config(db)
    data, files = await read_request_data(request)

    for key in TEXT_FIELDS:
        if key in data:
            setattr(config, key, first_text(data, key) or "")
    for key in BOOL_FIELDS:
        if key in data:
            current = bool(getattr(config, key))
            setattr(config, key, as_bool(data.get(key), current) is not False)

    logo = files.get("logo")
    if logo is not None:
        stored = image_bytes_to_stored(_read_upload(logo), SITE_LOGO_SIZE)
        config.site_logo = stored or DEFAULT_SITE_LOGO
    favicon = files.get("favicon")
    if favicon is not None:
        stored = image_bytes_to_stored(_read_upload(favicon), SITE_ICON_SIZE)
        config.site_favicon = stored or DEFAULT_FAVICON

    db.add(config)
    db.commit()
    return {}


def _read_upload(upload) -> bytes:  # type: ignore[no-untyped-def]
    try:
        return upload.file.read()
    except (OSError, ValueError):
        return b""
