"""Icon discovery tests: parsing, validation, and end-to-end scraping."""

from __future__ import annotations

import base64
import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from bs4 import BeautifulSoup
from PIL import Image

from app.services import icons as icons_module
from app.services.icons import (
    IconCandidate,
    best_from_srcset,
    collect_candidates,
    parse_size,
    probe_icon,
    resolve_icon,
)
from app.services.scraper import scrape_site

SVG_LOGO = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    b'<rect width="64" height="64" fill="#2f6feb"/></svg>'
)


def png_bytes(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (47, 111, 235, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_parse_size() -> None:
    assert parse_size("32x32") == 32
    assert parse_size("16x16 32x32 48x48") == 48
    assert parse_size("any") == 512
    assert parse_size(None) == 0
    assert parse_size(["180x180"]) == 180
    assert parse_size("garbage") == 0


def test_best_from_srcset() -> None:
    assert best_from_srcset("a.png 100w, b.png 400w, c.png 200w") == "b.png"
    assert best_from_srcset("only.png") == "only.png"
    assert best_from_srcset("") == ""


def test_candidates_are_ordered_by_quality() -> None:
    soup = soup_of(
        """
        <html><head>
        <base href="https://example.com/app/">
        <link rel="icon" href="favicon-32.png" sizes="32x32">
        <link rel="apple-touch-icon" href="/touch-180.png" sizes="180x180">
        <link rel="manifest" href="/site.webmanifest">
        <meta property="og:image" content="/share.jpg">
        </head><body>
        <img src="/static/logo.svg" class="inline-block max-w-none h-6">
        <img src="/static/cover.jpg" class="hero">
        </body></html>
        """
    )
    candidates, pending = collect_candidates(soup, "https://example.com/app/", timeout=1)

    sources = [item.source for item in candidates]
    assert sources[0] == "link:apple-touch-icon"
    assert "link:icon" in sources
    assert "img:logo" in sources
    # 分享大图和占位路径永远排在真实图标之后
    assert sources.index("meta:og:image") > sources.index("img:logo")
    guesses = [item.source for item in candidates if item.source.startswith("guess:")]
    assert sources[-len(guesses) :] == guesses
    assert "guess:favicon.ico" in guesses
    # 子目录 favicon 比站点根目录更贴近当前页面，先试它
    dir_guess = next(item for item in candidates if item.source == "guess:dir-favicon.ico")
    assert dir_guess.url == "https://example.com/app/favicon.ico"
    # 页面已声明图标时，manifest 留到失败后再抓
    assert pending == ["https://example.com/site.webmanifest"]
    # <base> 改变了相对路径的解析基准
    apple = next(item for item in candidates if item.source == "link:apple-touch-icon")
    assert apple.url == "https://example.com/touch-180.png"


def test_conventional_paths_include_root_assets() -> None:
    candidates, _ = collect_candidates(soup_of("<html><head></head></html>"), "https://example.com/docs/")
    urls = [item.url for item in candidates]
    assert "https://example.com/apple-touch-icon.png" in urls
    assert "https://example.com/favicon.ico" in urls
    assert "https://example.com/favicon.svg" in urls
    assert "https://example.com/docs/favicon.ico" in urls


def test_img_heuristics_skip_content_images() -> None:
    soup = soup_of(
        """
        <html><body>
        <img src="/img/logo-icon.svg" class="h-8">
        <img src="/img/banner-logo.png">
        <img src="/img/icon-arrow-left.svg">
        </body></html>
        """
    )
    candidates, _ = collect_candidates(soup, "https://example.com/", timeout=1)
    logo_urls = [item.url for item in candidates if item.source == "img:logo"]
    assert logo_urls == ["https://example.com/img/logo-icon.svg"]


def test_manifest_expands_when_no_icon_declared() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/site.webmanifest"
        return httpx.Response(
            200,
            json={
                "icons": [
                    {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                    {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    soup = soup_of('<html><head><link rel="manifest" href="/site.webmanifest"></head><body></body></html>')
    candidates, pending = collect_candidates(soup, "https://example.com/", client=client, timeout=1)

    assert pending == []
    manifest_hits = [item for item in candidates if item.source == "manifest"]
    assert manifest_hits[0].url == "https://example.com/icon-512.png"
    assert manifest_hits[0].score > manifest_hits[1].score


@pytest.mark.parametrize(
    ("raw", "ok"),
    [
        (png_bytes(64, 64), True),
        (png_bytes(512, 512), True),
        (SVG_LOGO, True),
        (png_bytes(8, 8), False),
        (png_bytes(1200, 300), False),
        (b"<html>404 Not Found</html>", False),
        (b"", False),
        (b"<svg>" + b"x" * (33 * 1024) + b"</svg>", False),
    ],
    ids=["png-64", "png-512", "svg", "too-small", "banner", "html-error", "empty", "svg-too-large"],
)
def test_probe_icon_rejects_non_icons(raw: bytes, ok: bool) -> None:
    assert probe_icon(raw).ok is ok


def test_resolve_icon_skips_broken_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    good = png_bytes(64, 64)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/broken.png":
            return httpx.Response(404)
        return httpx.Response(200, content=good, headers={"content-type": "image/png"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    candidates = [
        IconCandidate(url="https://example.com/broken.png", score=120, source="link:icon"),
        IconCandidate(url="https://example.com/good.png", score=100, source="link:apple-touch-icon"),
    ]
    resolved = resolve_icon("https://example.com/", candidates, client=client, timeout=2, budget=5)

    assert resolved.stored
    assert resolved.source == "link:apple-touch-icon"


def test_resolve_icon_falls_back_to_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icons_module, "ICON_FALLBACK_TEMPLATES", ["https://mirror.test/{host}.ico"])
    good = png_bytes(64, 64)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "mirror.test":
            return httpx.Response(200, content=good, headers={"content-type": "image/png"})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    candidates = [IconCandidate(url="https://example.com/favicon.ico", score=40, source="guess:favicon.ico")]
    resolved = resolve_icon("https://example.com/", candidates, client=client, timeout=2, budget=5)

    assert resolved.source == "service:mirror"
    assert resolved.url == "https://mirror.test/example.com.ico"


@pytest.fixture()
def serve(monkeypatch: pytest.MonkeyPatch):
    """Start a local site with the given handler class and return its base URL."""
    # 本机环境可能配置了 HTTP 代理，回环地址必须直连
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")

    servers: list[ThreadingHTTPServer] = []

    def _serve(handler: type[BaseHTTPRequestHandler]) -> str:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}"

    try:
        yield _serve
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


def _respond(handler: BaseHTTPRequestHandler, status: int, body: bytes, content_type: str) -> None:
    handler.send_response(status)
    handler.send_header("content-type", content_type)
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class _ManifestOnlyHandler(BaseHTTPRequestHandler):
    """Declared icon 404s, manifest still holds a usable 192 px PNG."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/":
            body = (
                b"<html><head><title>Manifest Only</title>"
                b'<link rel="icon" href="/dead.ico">'
                b'<link rel="manifest" href="/site.webmanifest">'
                b"</head><body></body></html>"
            )
            _respond(self, 200, body, "text/html; charset=utf-8")
        elif self.path == "/site.webmanifest":
            payload = b'{"icons":[{"src":"/icon-192.png","sizes":"192x192"}]}'
            _respond(self, 200, payload, "application/manifest+json")
        elif self.path == "/icon-192.png":
            _respond(self, 200, png_bytes(192, 192), "image/png")
        else:
            _respond(self, 404, b"not found", "text/plain")

    def log_message(self, *args: object) -> None:
        pass


class _IconlessHandler(BaseHTTPRequestHandler):
    """No icon link, no manifest, no logo img, and every conventional path 404s."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/":
            body = b"<html><head><title>\xe6\x97\xa0\xe5\x9b\xbe\xe6\xa0\x87\xe7\xab\x99\xe7\x82\xb9</title></head><body></body></html>"
            _respond(self, 200, body, "text/html; charset=utf-8")
        else:
            _respond(self, 404, b"not found", "text/plain")

    def log_message(self, *args: object) -> None:
        pass


def test_scrape_keeps_manifest_icon_when_declared_icon_is_dead(serve) -> None:
    """声明图标全挂时，manifest 的结果不能被二次解析覆盖掉。"""
    result = scrape_site(serve(_ManifestOnlyHandler) + "/", timeout=5)

    assert result.icon_source == "manifest"
    image = Image.open(io.BytesIO(base64.b64decode(result.icon)))
    assert image.size == (64, 64)


def test_scrape_generates_letter_tile_when_site_has_no_icon(serve) -> None:
    result = scrape_site(serve(_IconlessHandler) + "/", timeout=5)

    assert result.icon_source == "letter"
    image = Image.open(io.BytesIO(base64.b64decode(result.icon)))
    assert image.size == (64, 64)


class _SiteHandler(BaseHTTPRequestHandler):
    """Serves a page whose only brand asset is an inline <img> logo."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/":
            body = (
                b"<html><head><title>Example Site</title>"
                b'<meta name="description" content="a test page">'
                b'</head><body><img src="/static/logo.svg" class="inline-block h-6">'
                b"</body></html>"
            )
            _respond(self, 200, body, "text/html; charset=utf-8")
        elif self.path == "/static/logo.svg":
            _respond(self, 200, SVG_LOGO, "image/svg+xml")
        else:
            _respond(self, 404, b"not found", "text/plain")

    def log_message(self, *args: object) -> None:
        pass


def test_scrape_site_uses_page_logo(serve) -> None:
    result = scrape_site(serve(_SiteHandler) + "/", timeout=5)

    assert result.title == "Example Site"
    assert result.description == "a test page"
    assert result.icon_source == "img:logo"
    assert result.icon.startswith("data:image/svg+xml;base64,")
