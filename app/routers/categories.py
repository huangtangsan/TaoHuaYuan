"""Category administration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..errors import ApiError
from ..models import Category, Site, User
from ..serializers import category_admin_item, category_detail, category_list_item
from ._helpers import as_bool, as_int, first_text, read_request_data

router = APIRouter(prefix="/admin/category", dependencies=[Depends(current_user)])


def _get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise ApiError(500, 500, "分类不存在")
    return category


@router.get("")
def list_categories(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(Category).order_by(func.abs(Category.sort), Category.id)
    )
    return {"list": [category_list_item(row) for row in rows]}


@router.get("/{category_id}")
def get_category(category_id: int, db: Session = Depends(get_db)) -> dict:
    return category_detail(_get_category(db, category_id))


@router.post("")
async def create_category(request: Request, db: Session = Depends(get_db)) -> dict:
    data, _files = await read_request_data(request)
    name = (first_text(data, "name") or "").strip()
    if not name:
        raise ApiError(400, 400, "分类名称不能为空")

    parent_id = as_int(data.get("parent_id"), 0) or 0
    parent: Category | None = None
    if parent_id:
        parent = _get_category(db, parent_id)
        if parent.parent_id != 0:
            raise ApiError(400, 400, "最多支持两级分类")

    category = Category(
        parent_id=parent_id,
        sort=as_int(data.get("sort_id"), 0) or 0,
        title=name[:50],
        icon=(first_text(data, "icon") or "")[:60],
        level=(parent.level + 1) if parent else 1,
        is_used=as_bool(data.get("is_used"), True) is not False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category_admin_item(category)


@router.put("/update")
async def update_category(request: Request, db: Session = Depends(get_db)) -> dict:
    data, _files = await read_request_data(request)
    category_id = as_int(data.get("id"))
    if not category_id:
        raise ApiError(400, 400, "Bad Request")
    category = _get_category(db, category_id)

    if "name" in data and (first_text(data, "name") or "").strip():
        category.title = (first_text(data, "name") or "").strip()[:50]
    if "icon" in data:
        category.icon = (first_text(data, "icon") or "")[:60]
    if "sort_id" in data:
        category.sort = as_int(data.get("sort_id"), category.sort) or 0
    if "used" in data:
        category.is_used = as_bool(data.get("used"), category.is_used) is not False
    if "parent_id" in data:
        parent_id = as_int(data.get("parent_id"), category.parent_id) or 0
        if parent_id == category.id:
            raise ApiError(400, 400, "不能把分类设为自己的子分类")
        if parent_id:
            parent = _get_category(db, parent_id)
            if parent.parent_id != 0:
                raise ApiError(400, 400, "最多支持两级分类")
            category.level = parent.level + 1
        else:
            category.level = 1
        category.parent_id = parent_id

    db.add(category)
    db.commit()
    db.refresh(category)
    return category_admin_item(category)


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    category = _get_category(db, category_id)
    has_children = db.scalar(select(Category.id).where(Category.parent_id == category_id).limit(1))
    has_sites = db.scalar(select(Site.id).where(Site.category_id == category_id).limit(1))
    if has_children or has_sites:
        raise ApiError(400, 400, "该分类下还有子分类或网站，请先移动或删除它们")
    db.delete(category)
    db.commit()
    return {}
