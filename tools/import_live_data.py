"""Import categories and sites from the live TaoHuaYuan instance.

The live site is a static build: its whole dataset is a JS array literal inside
the single bundle under ``/assets/``. This script pulls that array, copies every
referenced logo into our own storage (64x64 PNG base64 / SVG data URI), backs up
the SQLite file, and rewrites ``st_category`` / ``st_site``.

It also rewrites ``app/services/seed_sites.json`` so a fresh deployment starts
with the real data instead of the demo set.

Usage:
    .venv\\Scripts\\python.exe tools/import_live_data.py [--source URL] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import delete

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import DATA_DIR, DEFAULT_SITE_ICON, SITE_ICON_SIZE  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Category, Site  # noqa: E402
from app.services.images import (  # noqa: E402
    BROWSER_UA,
    fetch_remote_image,
    image_bytes_to_stored,
    letter_avatar_stored,
)
from app.services.scraper import scrape_site  # noqa: E402

SOURCE_DIR = ROOT / "data" / "source"
SEED_FILE = ROOT / "app" / "services" / "seed_sites.json"


# --- 1. 抓线上数据 -----------------------------------------------------------


def bundle_url(base: str) -> str:
    html = httpx.get(base + "/", timeout=30, headers={"User-Agent": BROWSER_UA}, follow_redirects=True).text
    match = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if not match:
        raise SystemExit("首页里没找到 bundle 地址")
    return base + match.group(1)


def extract_array(js: str, anchor: str = 'name:"常用推荐"') -> str:
    hit = js.find(anchor)
    if hit < 0:
        raise SystemExit(f"bundle 里没有锚点 {anchor}，线上站可能改了结构")
    start = js.rfind("[", 0, hit)
    depth = 0
    quote = ""
    escape = False
    for i in range(start, len(js)):
        char = js[i]
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = ""
            continue
        if char in "\"'`":
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
            if depth == 0:
                return js[start : i + 1]
    raise SystemExit("数据数组没有闭合")


def load_live_groups(base: str) -> list[dict]:
    url = bundle_url(base)
    print(f"bundle: {url}")
    js = httpx.get(url, timeout=90, headers={"User-Agent": BROWSER_UA}, follow_redirects=True).text
    literal = extract_array(js)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    raw = SOURCE_DIR / "live-array.js"
    raw.write_text(literal, encoding="utf-8")

    # 数组字面量不是 JSON（键没引号、有单引号），交给 node 求值后再转 JSON
    out = SOURCE_DIR / "live-array.json"
    script = (
        "const fs=require('fs');"
        f"const src=fs.readFileSync({json.dumps(raw.as_posix())},'utf8');"
        "const data=new Function('return '+src)();"
        f"fs.writeFileSync({json.dumps(out.as_posix())}, JSON.stringify(data,null,2));"
    )
    subprocess.run(["node", "-e", script], check=True)
    return json.loads(out.read_text(encoding="utf-8"))


# --- 2. 搬运图标 -------------------------------------------------------------


def localize_logo(base: str, site: dict) -> str:
    """Return a stored icon value for one live entry."""
    logo = str(site.get("logo") or "").strip()
    if logo:
        url = logo if logo.startswith(("http://", "https://")) else f"{base}/{logo.lstrip('/')}"
        for attempt in range(2):
            stored = image_bytes_to_stored(fetch_remote_image(url, timeout=8), SITE_ICON_SIZE)
            if stored:
                return stored
            if attempt:
                print(f"  ! logo 下载失败，改抓页面: {site.get('title')} ({url})")

    try:
        scraped = scrape_site(str(site.get("url") or ""))
        return scraped.icon
    except Exception as exc:  # 站点挂了就退到占位图
        print(f"  ! 抓取失败 {site.get('url')}: {exc}")

    return letter_avatar_stored(str(site.get("title") or ""), str(site.get("url") or ""), SITE_ICON_SIZE) or DEFAULT_SITE_ICON


def localize_group(base: str, group: dict) -> dict:
    entries: list[dict] = []
    for site in list(group.get("web") or []) + [w for child in group.get("children") or [] for w in child.get("web") or []]:
        entries.append(site)

    icons: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(localize_logo, base, site): index for index, site in enumerate(entries)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                icons[index] = future.result()
            except Exception as exc:
                print(f"  ! 图标处理异常: {exc}")
                icons[index] = DEFAULT_SITE_ICON

    def build(items: list[dict], offset: int) -> list[tuple[dict, str]]:
        return [(item, icons[offset + i]) for i, item in enumerate(items)]

    result = {
        "name": group["name"],
        "en_name": group.get("en_name", ""),
        "icon": group.get("icon", ""),
        "web": build(list(group.get("web") or []), 0),
        "children": [],
    }
    offset = len(group.get("web") or [])
    for child in group.get("children") or []:
        child_web = build(list(child.get("web") or []), offset)
        offset += len(child.get("web") or [])
        result["children"].append(
            {
                "name": child["name"],
                "en_name": child.get("en_name", ""),
                "icon": child.get("icon", "") or group.get("icon", ""),
                "web": child_web,
            }
        )
    return result


# --- 3. 写库 -----------------------------------------------------------------


def backup_database() -> Path:
    target = DATA_DIR / "backup"
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = target / f"webstack-{stamp}.db"
    source = sqlite3.connect(str(DATA_DIR / "webstack.db"))
    dest = sqlite3.connect(str(path))
    with dest:
        source.backup(dest)  # WAL 里的未提交内容也会一并落下
    source.close()
    dest.close()
    return path


def load_into_database(groups: list[dict]) -> tuple[int, int]:
    """Rewrite st_category / st_site.

    IDs are assigned explicitly (roots 1..N, children right after) so a freshly
    imported instance looks the same as one seeded from the JSON, instead of
    inheriting leftovers of the demo rows.
    """
    db = SessionLocal()
    try:
        db.execute(delete(Site))
        db.execute(delete(Category))
        db.flush()

        site_count = 0
        next_child_id = len(groups) + 1
        for group_index, group in enumerate(groups, start=1):
            root = Category(
                id=group_index,
                parent_id=0,
                sort=group_index * 100,
                title=group["name"][:50],
                icon=group.get("icon", "")[:60],
                level=1,
                is_used=True,
            )
            db.add(root)
            db.flush()

            for index, (item, icon) in enumerate(group["web"], start=1):
                db.add(_site_row(item, icon, root.id, group_index * 1000 + index))
                site_count += 1

            for child_index, child in enumerate(group["children"], start=1):
                child_row = Category(
                    id=next_child_id,
                    parent_id=root.id,
                    sort=group_index * 100 + child_index * 10,
                    title=child["name"][:50],
                    icon=(child.get("icon") or group.get("icon", ""))[:60],
                    level=2,
                    is_used=True,
                )
                next_child_id += 1
                db.add(child_row)
                db.flush()
                for index, (item, icon) in enumerate(child["web"], start=1):
                    db.add(_site_row(item, icon, child_row.id, group_index * 1000 + child_index * 100 + index))
                    site_count += 1

        db.commit()
        return len(groups), site_count
    finally:
        db.close()


def _site_row(item: dict, icon: str, category_id: int, sort: int) -> Site:
    return Site(
        category_id=category_id,
        title=str(item.get("title") or item.get("url") or "")[:50],
        icon=icon,
        description=str(item.get("desc") or "")[:500],
        url=str(item.get("url") or "")[:255],
        is_used=True,
        sort=sort,
    )


# --- 4. 生成新的种子文件 -----------------------------------------------------


def write_seed(groups: list[dict]) -> None:
    if SEED_FILE.exists():
        demo = SOURCE_DIR / "seed_sites.demo.json"
        if not demo.exists():
            shutil.copy2(SEED_FILE, demo)
    payload = []
    for group in groups:
        payload.append(
            {
                "name": group["name"],
                "icon": group.get("icon", ""),
                "web": [{"title": item["title"], "url": item["url"], "desc": item.get("desc", ""), "logo": icon} for item, icon in group["web"]],
                "children": [
                    {
                        "name": child["name"],
                        "icon": child.get("icon") or group.get("icon", ""),
                        "web": [
                            {"title": item["title"], "url": item["url"], "desc": item.get("desc", ""), "logo": icon}
                            for item, icon in child["web"]
                        ],
                    }
                    for child in group["children"]
                ],
            }
        )
    SEED_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="https://go.huangtang.link")
    parser.add_argument("--dry-run", action="store_true", help="只抓取和打印，不改数据库/种子文件")
    args = parser.parse_args()

    groups = load_live_groups(args.source)
    print(f"线上数据: {len(groups)} 个顶级分类")
    for group in groups:
        print(f"  - {group['name']}: {len(group.get('web') or [])} 个直挂站点, {len(group.get('children') or [])} 个子分类")

    localized = [localize_group(args.source, group) for group in groups]
    total = sum(len(g["web"]) + sum(len(c["web"]) for c in g["children"]) for g in localized)
    print(f"图标处理完成，站点总数 {total}")

    if args.dry_run:
        print("--dry-run，未写库")
        return

    db_file = DATA_DIR / "webstack.db"
    if db_file.exists():
        print("数据库备份:", backup_database())

    categories, sites = load_into_database(localized)
    write_seed(localized)
    print(f"已写入 {categories} 个顶级分类、{sites} 个站点；种子文件已更新: {SEED_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
