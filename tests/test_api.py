from __future__ import annotations

import atexit
import json
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="webstack-python-test-"))
atexit.register(lambda: shutil.rmtree(TEST_ROOT, ignore_errors=True))
os.environ["WEBSTACK_DATA_DIR"] = str(TEST_ROOT)
os.environ["WEBSTACK_DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["WEBSTACK_FRONTEND_DIST"] = str(TEST_ROOT / "dist")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import md5_hex  # noqa: E402
from app.services.seed import SEED_FILE  # noqa: E402


def seed_counts() -> tuple[int, int]:
    """Expected (categories, sites) from the seed file, so content edits don't
    break the tests."""
    groups = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    categories = len(groups) + sum(len(group.get("children") or []) for group in groups)
    sites = sum(
        len(group.get("web") or []) + sum(len(child.get("web") or []) for child in group.get("children") or [])
        for group in groups
    )
    return categories, sites


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": md5_hex("admin")},
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    return {"Token": token}


def test_public_home_is_seeded(client: TestClient) -> None:
    expected_categories, expected_sites = seed_counts()
    response = client.get("/api/home")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) == expected_categories
    assert len(data["sites"]) == expected_sites
    assert any(item["name"] == "常用推荐" for item in data["categories"])
    assert all("icon" in item for item in data["sites"])


def test_admin_auth_required(client: TestClient) -> None:
    assert client.get("/api/admin/info").status_code == 401
    bad = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 500
    assert bad.json()["code"] == 100


def test_admin_info_and_categories(client: TestClient, auth_headers: dict[str, str]) -> None:
    info = client.get("/api/admin/info", headers=auth_headers)
    assert info.status_code == 200
    assert info.json()["username"] == "admin"
    assert len(info.json()["menu"]) == 6

    categories = client.get("/api/admin/category", headers=auth_headers).json()["list"]
    assert len(categories) == seed_counts()[0]

    created = client.post(
        "/api/admin/category",
        headers=auth_headers,
        json={
            "parent_id": 0,
            "level": 1,
            "name": "测试分类",
            "icon": "linecons-lab",
            "is_used": True,
            "sort_id": 999,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["title"] == "测试分类"


def test_site_create_update_public_and_export(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import sites as sites_router

    def fake_scrape(url: str):
        return SimpleNamespace(
            title=f"抓取 {url}",
            description="由测试桩生成的简介",
            icon="/assets/images/default-site.svg",
            icon_source="link:icon",
        )

    monkeypatch.setattr(sites_router, "scrape_site", fake_scrape)

    categories = client.get("/api/admin/category", headers=auth_headers).json()["list"]
    root = next(item for item in categories if item["pid"] == 0)
    payload = {
        "category_id": root["id"],
        "url": "https://example.com\nhttps://example.org",
        "is_used": True,
        "fail_switch": True,
    }
    created = client.post("/api/admin/site", headers=auth_headers, json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["successCount"] == 2
    assert created.json()["failCount"] == 0
    # 新增接口会回报每个站点的图标来源，便于后台提示是否退回了默认图
    assert created.json()["iconSources"]["https://example.com"] == "link:icon"

    listed = client.get(
        "/api/admin/site",
        headers=auth_headers,
        params={"page": 1, "page_size": 100, "category_id": root["id"]},
    )
    assert listed.status_code == 200
    rows = listed.json()["list"]
    assert rows
    target = next(item for item in rows if item["url"] == "https://example.com")

    updated = client.put(
        f"/api/admin/site/{target['id']}",
        headers=auth_headers,
        data={"title": "示例站点", "is_used": "true", "sort": "7"},
    )
    assert updated.status_code == 200, updated.text

    home = client.get("/api/home").json()
    assert any(site["title"] == "示例站点" for site in home["sites"])

    exported = client.get("/api/admin/site/export", headers=auth_headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/octet-stream")
    assert exported.content.startswith(b"PK")


def test_config_update_and_about(client: TestClient, auth_headers: dict[str, str]) -> None:
    updated = client.put(
        "/api/admin/config",
        headers=auth_headers,
        json={"site_title": "测试导航", "about_site": "## 测试关于页", "is_about": True},
    )
    assert updated.status_code == 200, updated.text

    config = client.get("/api/admin/config", headers=auth_headers).json()
    assert config["site_title"] == "测试导航"
    assert config["about_site"] == "## 测试关于页"

    about = client.get("/api/about")
    assert about.status_code == 200
    assert about.json()["is_about"] is True

    home_config = client.get("/api/home").json()["config"]
    assert home_config["site_title"] == "测试导航"


def test_wrong_old_password(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/api/admin/modify_password",
        headers=auth_headers,
        data={"old_password": md5_hex("not-admin"), "new_password": md5_hex("new-password")},
    )
    assert response.status_code == 500
    assert response.json()["code"] == 100
