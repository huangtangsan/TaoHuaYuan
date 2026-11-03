"""First-run database seeding.

Unlike the Go version, this never drops menu tables on restart. Content is seeded
only when the category table is empty, so admin edits survive restarts.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DEFAULT_FAVICON, DEFAULT_SITE_ICON, DEFAULT_SITE_LOGO
from ..models import Category, Menu, Site, SysConfig, User, UserMenu
from ..security import md5_hex

SEED_FILE = Path(__file__).with_name("seed_sites.json")

ABOUT_SITE = """### 关于桃花源

桃花源是一个给自己用的网址收藏夹，也是一个可以随时带走的小型导航站。

这里收集日常真正会打开的站点：开发文档、AI 工具、社区资讯，以及几台服务器和网盘的入口。界面沿用 TaoHuaYuan 的侧栏与卡片设计，后台用来维护分类、站点和站点信息。

- 前台：Vue 3 + TypeScript + Vite
- 后端：Python + FastAPI + SQLite
- 管理端：沿用 WebStack 的完整管理流程
"""

ABOUT_AUTHOR = """### 关于站长

**克杰**，具身智能工程师，日常写 Python、ROS 2 和一点 Linux 运维。

喜欢把 AI 能力真正做进产品里，也喜欢把散落在浏览器书签栏里的网址整理成一个清爽的入口。

> 缘溪行，忘路之远近。忽逢桃花林，夹岸数百步，中无杂树，芳草鲜美，落英缤纷。
"""


def _normalize_icon(icon: str | None) -> str:
    if not icon:
        return DEFAULT_SITE_ICON
    if icon.startswith(("http://", "https://", "/", "data:")):
        return icon
    return "/" + icon.lstrip("./")


def seed_database(db: Session) -> None:
    config = db.scalar(select(SysConfig).order_by(SysConfig.id))
    if config is None:
        config = SysConfig(
            id=1,
            about_site=ABOUT_SITE,
            about_author=ABOUT_AUTHOR,
            is_about=True,
            is_search=True,
            site_title="桃花源 · 网址导航",
            site_keyword="网址导航,桃花源,开发资源,AI工具",
            site_desc="一个清爽、可维护的个人网址导航站，基于 Vue 3 与 FastAPI 构建。",
            site_record="",
            site_logo=DEFAULT_SITE_LOGO,
            site_favicon=DEFAULT_FAVICON,
            site_url="",
        )
        db.add(config)

    admin = db.scalar(select(User).where(User.username == "admin"))
    if admin is None:
        admin = User(username="admin", password=md5_hex("admin"))
        db.add(admin)
        db.flush()

    if db.scalar(select(Menu.id).limit(1)) is None:
        menus = [
            Menu(id=1, pid=0, name="网站管理", link="", icon="users", level=1, sort=500, is_used=True),
            Menu(id=2, pid=1, name="网站分类", link="/admin/category", icon="", level=1, sort=501, is_used=True),
            Menu(id=3, pid=1, name="网站信息", link="/admin/site", icon="", level=1, sort=502, is_used=True),
            Menu(id=4, pid=0, name="系统管理", link="", icon="", level=1, sort=600, is_used=True),
            Menu(id=5, pid=4, name="网站配置", link="/admin/config", icon="", level=1, sort=601, is_used=True),
            Menu(id=6, pid=4, name="关于页面设置", link="/admin/about_page", icon="", level=1, sort=602, is_used=True),
        ]
        db.add_all(menus)
        db.flush()
        db.add_all(UserMenu(user_id=admin.id, menu_id=menu.id) for menu in menus)

    if db.scalar(select(Category.id).limit(1)) is None and SEED_FILE.exists():
        _seed_content(db)

    db.commit()


def _seed_content(db: Session) -> None:
    groups = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    # IDs are fixed (roots 1..N, children after them) so a seeded instance and an
    # instance rewritten by tools/import_live_data.py look identical.
    next_child_id = len(groups) + 1
    for root_index, group in enumerate(groups, start=1):
        root = Category(
            id=root_index,
            parent_id=0,
            sort=root_index * 100,
            title=group["name"][:50],
            icon=group.get("icon", ""),
            level=1,
            is_used=True,
        )
        db.add(root)
        db.flush()

        direct_sites = group.get("web") or []
        for site_index, item in enumerate(direct_sites, start=1):
            _add_seed_site(db, root_index * 1000 + site_index, root.id, item)

        for child_index, child in enumerate(group.get("children") or [], start=1):
            child_row = Category(
                id=next_child_id,
                parent_id=root.id,
                sort=root_index * 100 + child_index * 10,
                title=child["name"][:50],
                icon=child.get("icon", group.get("icon", "")),
                level=2,
                is_used=True,
            )
            next_child_id += 1
            db.add(child_row)
            db.flush()
            for site_index, item in enumerate(child.get("web") or [], start=1):
                _add_seed_site(db, root_index * 1000 + child_index * 100 + site_index, child_row.id, item)


def _add_seed_site(db: Session, sort: int, category_id: int, item: dict) -> None:
    db.add(
        Site(
            category_id=category_id,
            title=str(item.get("title", ""))[:50],
            icon=_normalize_icon(item.get("logo")),
            description=str(item.get("desc", ""))[:500],
            url=str(item.get("url", "")),
            is_used=True,
            sort=sort,
        )
    )
