"""JSON serializers shared by public and admin endpoints."""

from __future__ import annotations

from datetime import datetime

from .models import Category, Site, SysConfig


def dt_iso(value: datetime | None) -> str:
    return value.isoformat(timespec="seconds") if value else ""


def dt_display(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def category_list_item(category: Category) -> dict:
    return {
        "id": category.id,
        "pid": category.parent_id,
        "name": category.title,
        "link": "",
        "icon": category.icon,
        "is_used": category.is_used,
        "sort": category.sort,
        "level": category.level,
    }


def category_admin_item(category: Category) -> dict:
    return {
        "id": category.id,
        "parent_id": category.parent_id,
        "sort": category.sort,
        "title": category.title,
        "icon": category.icon,
        "created_at": dt_iso(category.created_at),
        "updated_at": dt_iso(category.updated_at),
        "is_used": category.is_used,
        "level": category.level,
    }


def category_detail(category: Category) -> dict:
    return {
        "id": category.id,
        "pid": category.parent_id,
        "name": category.title,
        "icon": category.icon,
        "is_add": category.parent_id == 0,
        "sort_id": category.sort,
        "level": category.level,
        "is_used": category.is_used,
    }


def site_public_item(site: Site) -> dict:
    return {
        "id": site.id,
        "category_id": site.category_id,
        "title": site.title,
        "url": site.url,
        "description": site.description,
        "icon": site.icon,
        "sort": site.sort,
    }


def site_admin_item(site: Site, category_name: str = "") -> dict:
    return {
        "id": site.id,
        "icon": site.icon,
        "title": site.title,
        "url": site.url,
        "category": category_name,
        "category_id": site.category_id,
        "description": site.description,
        "is_used": site.is_used,
        "sort": site.sort,
        "created_at": dt_display(site.created_at),
        "updated_at": dt_display(site.updated_at),
    }


def config_dict(config: SysConfig) -> dict:
    return {
        "id": config.id,
        "about_site": config.about_site,
        "about_author": config.about_author,
        "is_about": config.is_about,
        "is_search": config.is_search,
        "site_title": config.site_title,
        "site_keyword": config.site_keyword,
        "site_desc": config.site_desc,
        "site_record": config.site_record,
        "site_logo": config.site_logo,
        "site_favicon": config.site_favicon,
        "site_url": config.site_url,
    }
