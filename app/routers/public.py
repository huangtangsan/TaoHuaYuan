"""Public data used by the Vue front page and about page."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Category, Site, SysConfig
from ..serializers import config_dict, site_public_item

router = APIRouter()


def _first_config(db: Session) -> SysConfig:
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
            site_logo="",
            site_favicon="",
            site_url="",
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _visible_categories(db: Session) -> list[Category]:
    rows = list(
        db.scalars(
            select(Category)
            .where(Category.is_used.is_(True))
            .order_by(Category.sort, Category.id)
        )
    )
    by_parent: dict[int, list[Category]] = {}
    by_id = {row.id: row for row in rows}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    visible: list[Category] = []

    def walk(parent_id: int) -> None:
        for row in by_parent.get(parent_id, []):
            visible.append(row)
            walk(row.id)

    walk(0)
    # Only categories reachable from an enabled root are visible.
    return [row for row in visible if row.parent_id == 0 or row.parent_id in by_id]


@router.get("/home")
def home(db: Session = Depends(get_db)) -> dict:
    config = _first_config(db)
    categories = _visible_categories(db)
    visible_ids = {category.id for category in categories}
    sites = list(
        db.scalars(
            select(Site)
            .where(Site.is_used.is_(True))
            .order_by(Site.sort, Site.id)
        )
    )

    public_config = config_dict(config)
    public_config.pop("about_site", None)
    public_config.pop("about_author", None)
    return {
        "config": public_config,
        "categories": [
            {
                "id": category.id,
                "parent_id": category.parent_id,
                "name": category.title,
                "icon": category.icon,
                "level": category.level,
                "sort": category.sort,
            }
            for category in categories
        ],
        "sites": [
            site_public_item(site)
            for site in sites
            if site.category_id in visible_ids
        ],
    }


@router.get("/about")
def about(db: Session = Depends(get_db)) -> dict:
    config = _first_config(db)
    return {
        "about_site": config.about_site,
        "about_author": config.about_author,
        "is_about": config.is_about,
        "site_title": config.site_title,
        "site_logo": config.site_logo,
    }
