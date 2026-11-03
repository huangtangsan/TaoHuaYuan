"""Website administration, batch creation, sync, and Excel export."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from ..config import DEFAULT_SITE_ICON, SITE_ICON_SIZE
from ..database import get_db
from ..deps import current_user
from ..errors import ApiError
from ..models import Category, Site
from ..serializers import site_admin_item
from ..services.images import image_bytes_to_stored, stored_image_from_url
from ..services.scraper import is_valid_web_url, scrape_site
from ._helpers import as_bool, as_int, first_text, read_request_data

router = APIRouter(prefix="/admin/site", dependencies=[Depends(current_user)])


def _get_site(db: Session, site_id: int) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise ApiError(500, 500, "网站不存在")
    return site


def _category_exists(db: Session, category_id: int) -> bool:
    return db.scalar(select(Category.id).where(Category.id == category_id).limit(1)) is not None


@router.get("/preview")
def preview_site(url: str = Query(..., min_length=1)) -> dict:
    """Scrape a single URL without writing anything, for the admin form."""
    target = url.strip()
    if not is_valid_web_url(target):
        raise ApiError(400, 400, "网址格式不正确")
    try:
        result = scrape_site(target)
    except Exception as exc:
        raise ApiError(500, 500, f"抓取失败：{exc}") from exc
    return {
        "title": result.title,
        "description": result.description,
        "icon": result.icon,
        "icon_source": result.icon_source,
    }


@router.get("")
def list_sites(
    page: int = Query(1),
    page_size: int = Query(10),
    search: str = Query(""),
    category_id: int = Query(0),
    db: Session = Depends(get_db),
) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    conditions = []
    keyword = search.strip()
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(
                Site.title.like(pattern),
                Site.description.like(pattern),
                Site.url.like(pattern),
            )
        )
    if category_id:
        conditions.append(Site.category_id == category_id)

    total = db.scalar(select(func.count(Site.id)).where(*conditions)) or 0
    order = Site.sort.asc() if category_id else Site.created_at.desc()
    rows = db.execute(
        select(Site, Category.title)
        .outerjoin(Category, Category.id == Site.category_id)
        .where(*conditions)
        .order_by(order, Site.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "list": [site_admin_item(site, category_name or "") for site, category_name in rows],
        "pagination": {
            "total": total,
            "current_page": page,
            "per_page_count": page_size,
        },
    }


@router.post("")
async def create_sites(request: Request, db: Session = Depends(get_db)) -> dict:
    data, _files = await read_request_data(request)
    raw_urls = first_text(data, "url") or ""
    category_id = as_int(data.get("category_id"), 0) or 0
    is_used = as_bool(data.get("is_used"), True) is not False
    fail_switch = as_bool(data.get("fail_switch"), False) is True

    if category_id and not _category_exists(db, category_id):
        raise ApiError(400, 400, "分类不存在")

    candidates = [line.strip() for line in raw_urls.splitlines() if line.strip()]
    fail_urls: list[str] = []
    valid: list[str] = []
    existing = {
        url
        for url in db.scalars(select(Site.url).where(Site.url.in_(candidates)))
        if url
    } if candidates else set()

    for url in candidates:
        if not is_valid_web_url(url) or url in existing or url in fail_urls:
            fail_urls.append(url)
        else:
            valid.append(url)

    scraped: dict[str, object] = {}
    errors: dict[str, str] = {}
    if valid:
        with ThreadPoolExecutor(max_workers=min(5, len(valid))) as pool:
            future_map = {pool.submit(scrape_site, url): url for url in valid}
            for future in as_completed(future_map):
                url = future_map[future]
                try:
                    scraped[url] = future.result()
                except Exception as exc:  # network and parsing failures are data, not crashes
                    errors[url] = str(exc)

    success_count = 0
    icon_sources: dict[str, str] = {}
    for url in valid:
        result = scraped.get(url)
        if result is None and not fail_switch:
            fail_urls.append(url)
            continue
        if result is not None:
            title = result.title or url  # type: ignore[attr-defined]
            description = result.description  # type: ignore[attr-defined]
            icon = result.icon  # type: ignore[attr-defined]
            icon_sources[url] = result.icon_source  # type: ignore[attr-defined]
        else:
            title, description, icon = url, "", DEFAULT_SITE_ICON
            icon_sources[url] = "default"
        db.add(
            Site(
                category_id=category_id,
                title=title[:50],
                icon=icon,
                description=description[:500],
                url=url,
                is_used=is_used,
                sort=0,
            )
        )
        success_count += 1

    db.commit()
    return {
        "successCount": success_count,
        "failCount": len(fail_urls),
        "failURLs": fail_urls,
        "iconSources": icon_sources,
    }


@router.put("/{site_id}")
async def update_site(site_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    site = _get_site(db, site_id)
    data, files = await read_request_data(request)

    if first_text(data, "title"):
        site.title = (first_text(data, "title") or "").strip()[:50]
    if first_text(data, "description"):
        site.description = (first_text(data, "description") or "").strip()[:500]
    if first_text(data, "url"):
        url = (first_text(data, "url") or "").strip()
        if not is_valid_web_url(url):
            raise ApiError(400, 400, "网址格式不正确")
        site.url = url[:255]
    category_id = as_int(data.get("category_id"), 0) or 0
    if category_id and _category_exists(db, category_id):
        site.category_id = category_id
    if "is_used" in data:
        site.is_used = as_bool(data.get("is_used"), site.is_used) is not False
    if "sort" in data:
        site.sort = as_int(data.get("sort"), site.sort) or 0

    icon_source = files.get("file") or None
    if icon_source is not None:
        stored = _store_upload(icon_source)
        if stored:
            site.icon = stored
        else:
            site.icon = DEFAULT_SITE_ICON
    elif first_text(data, "thumb"):
        stored = stored_image_from_url(first_text(data, "thumb") or "", SITE_ICON_SIZE)
        site.icon = stored or DEFAULT_SITE_ICON

    db.add(site)
    db.commit()
    return {"id": site.id}


def _store_upload(upload: UploadFile) -> str | None:
    try:
        raw = upload.file.read()
    except (OSError, ValueError):
        return None
    return image_bytes_to_stored(raw, SITE_ICON_SIZE)


@router.get("/sync/{site_id}")
def sync_site(site_id: int, db: Session = Depends(get_db)) -> dict:
    site = _get_site(db, site_id)
    try:
        result = scrape_site(site.url.strip())
    except Exception as exc:
        raise ApiError(500, 500, f"同步失败：{exc}") from exc

    # 同步只用来「补全」，绝不覆盖用户手动填过的内容。
    # 否则一个没有 meta description / favicon 的站点（例如 GitHub Pages 上的
    # 纯文档页），一次同步就会把管理员手工写的描述和上传的图标清成空。
    site.title = result.title[:50] or site.title
    if not site.description:
        site.description = result.description[:500]
    if not site.icon or site.icon == DEFAULT_SITE_ICON:
        site.icon = result.icon
    db.add(site)
    db.commit()
    return {"id": site.id, "icon_source": result.icon_source}


@router.delete("/{site_id}")
def delete_site(site_id: int, db: Session = Depends(get_db)) -> dict:
    site = _get_site(db, site_id)
    db.delete(site)
    db.commit()
    return {"id": site_id}


@router.get("/export")
def export_sites(
    search: str = Query(""),
    category_id: int = Query(0),
    db: Session = Depends(get_db),
) -> Response:
    conditions = []
    keyword = search.strip()
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(
                Site.title.like(pattern),
                Site.description.like(pattern),
                Site.url.like(pattern),
            )
        )
    if category_id:
        conditions.append(Site.category_id == category_id)

    order = Site.sort.asc() if category_id else Site.created_at.desc()
    rows = db.execute(
        select(Site, Category.title)
        .outerjoin(Category, Category.id == Site.category_id)
        .where(*conditions)
        .order_by(order, Site.id.asc())
        .limit(10000)
    ).all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["ID", "Logo", "名称简介", "链接", "分类", "创建日期", "更新日期", "状态"])
    for site, category_name in rows:
        sheet.append(
            [
                site.id,
                site.icon,
                site.title,
                site.url,
                category_name or "",
                site.created_at.strftime("%Y-%m-%d %H:%M:%S") if site.created_at else "",
                site.updated_at.strftime("%Y-%m-%d %H:%M:%S") if site.updated_at else "",
                "启用" if site.is_used else "禁用",
            ]
        )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=sites.xlsx",
            "Content-Transfer-Encoding": "binary",
        },
    )
