"""Icon discovery for sites added from the admin console.

A navigation card is only as good as its icon, so brand assets are looked up in
this order:

1. ``<link rel="icon|apple-touch-icon|mask-icon">`` — the site's own declaration
2. web app manifest icons — usually the crispest 192/512 px source
3. ``og:image`` / ``twitter:image`` — often a wide share banner, heavily demoted
4. ``<img>`` tags whose src/class/alt clearly say "logo"
5. conventional paths — ``<page dir>/favicon.ico``, ``/apple-touch-icon.png``,
   ``/favicon.ico``, ``/favicon.svg``
6. a third-party favicon mirror (DuckDuckGo by default)

Every candidate is downloaded and validated before use: it must decode, be at
least 16 px on both sides, and must not be a wide banner. The highest scoring
candidate that passes wins.
"""

from __future__ import annotations

import io
import json
import posixpath
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from time import monotonic
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from PIL import Image

from ..config import (
    ICON_FALLBACK_TEMPLATES,
    ICON_FETCH_TIMEOUT,
    ICON_READ_MANIFEST,
    ICON_TOTAL_BUDGET,
    MAX_SVG_BYTES,
    SITE_ICON_SIZE,
)
from .images import fetch_remote_image, image_bytes_to_stored, looks_like_svg

# Hints that an <img> is the site's own mark rather than content artwork.
HINT_WORDS = ("logo", "brand", "favicon", "icon", "mark")
# Things that look like a logo by name but never work as a 64 px card icon.
BAD_WORDS = (
    "banner",
    "cover",
    "poster",
    "screenshot",
    "hero",
    "sprite",
    "placeholder",
    "spinner",
    "loading",
    "qrcode",
    "qr-code",
    "wechat",
    "weixin",
    "payment",
    "avatar",
    "slogan",
    "footer",
)
# UI icons that share the "icon" naming convention.
UI_ICON_RE = re.compile(
    r"icon[-_](?:arrow|menu|search|close|chevron|star|heart|user|cart|play|pause|sun|moon|"
    r"share|copy|edit|delete|plus|minus|check|down|up|left|right)",
    re.IGNORECASE,
)
# Tailwind-ish size classes such as h-6 / w-8 mean a compact mark.
SMALL_SIZE_RE = re.compile(r"(?:^|[\s\"])(?:h|w)-(\d{1,2})(?:[\s\"]|$)")


@dataclass(slots=True)
class IconCandidate:
    url: str
    score: int
    source: str


@dataclass(slots=True)
class IconProbe:
    ok: bool
    edge: int = 0
    square: bool = True
    kind: str = ""


@dataclass(slots=True)
class ResolvedIcon:
    stored: str | None = None
    source: str = "default"
    url: str = ""


@dataclass(slots=True)
class _Collected:
    candidates: list[IconCandidate] = field(default_factory=list)
    manifests: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)


def _first_text(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value)
    return str(value) if isinstance(value, str) else ""


def parse_size(value: object) -> int:
    """Return the smallest edge described by ``sizes="16x16 32x32"``.

    ``any`` is what SVG icons declare; treat it as a large vector source.
    """
    text = _first_text(value).strip().lower()
    if not text:
        return 0
    if "any" in text:
        return 512
    best = 0
    for part in re.split(r"[\s,]+", text):
        match = re.match(r"(\d+)\s*[x×]\s*(\d+)", part)
        if match:
            best = max(best, min(int(match.group(1)), int(match.group(2))))
        elif part.isdigit():
            best = max(best, int(part))
    return best


def best_from_srcset(value: object) -> str:
    """Pick the widest entry of a ``srcset`` attribute."""
    text = _first_text(value).strip()
    if not text:
        return ""
    best_url, best_width = "", -1
    for part in text.split(","):
        pieces = part.strip().split()
        if not pieces:
            continue
        url = pieces[0]
        width = 0
        if len(pieces) > 1:
            spec = pieces[1].lower().rstrip("w")
            if spec.isdigit():
                width = int(spec)
        if width > best_width:
            best_url, best_width = url, width
    return best_url


def _score_with_size(base: int, edge: int) -> int:
    return base + min(edge, 512) // 8


def _add(collected: _Collected, url: str, score: int, source: str) -> None:
    if not url or url.startswith(("data:", "blob:", "javascript:")):
        return
    if url.startswith("//"):
        url = "https:" + url
    if not url.lower().startswith(("http://", "https://")):
        return
    if url in collected.seen:
        return
    collected.seen.add(url)
    collected.candidates.append(IconCandidate(url=url, score=score, source=source))


def _image_hint(img: Tag) -> tuple[str, int]:
    """Return (src, score); score 0 means "not a brand mark"."""
    src = ""
    for attr in ("src", "data-src", "data-original", "data-lazy-src", "data-url"):
        value = img.get(attr)
        if isinstance(value, str) and value.strip():
            src = value.strip()
            break
    if not src:
        src = best_from_srcset(img.get("srcset"))

    tokens = " ".join(
        [
            src,
            _first_text(img.get("class")),
            _first_text(img.get("id")),
            _first_text(img.get("alt")),
            _first_text(img.get("aria-label")),
        ]
    ).lower()

    if UI_ICON_RE.search(tokens):
        return src, 0
    if not any(word in tokens for word in HINT_WORDS):
        return src, 0
    if any(word in tokens for word in BAD_WORDS):
        return src, 0

    score = 74
    if src.lower().split("?")[0].endswith(".svg"):
        score += 14
    if SMALL_SIZE_RE.search(tokens):
        score += 6
    return src, score


def collect_candidates(
    soup: BeautifulSoup,
    page_url: str,
    client: httpx.Client | None = None,
    timeout: float = ICON_FETCH_TIMEOUT,
) -> tuple[list[IconCandidate], list[str]]:
    """Collect icon candidates from a parsed page.

    Returns ``(candidates, pending_manifests)``. The manifest is expanded right
    away only when the page declares no icon link at all — that is the common
    shape for modern SPA sites. Otherwise it is left pending so the caller can
    skip that extra request when a declared icon already worked.
    """
    base = page_url
    base_tag = soup.find("base", href=True)
    if base_tag:
        base = urljoin(page_url, str(base_tag["href"]))

    collected = _Collected()

    for tag in soup.find_all("link"):
        rel = {str(item).lower() for item in (tag.get("rel") or [])}
        href = tag.get("href")
        if not rel or not isinstance(href, str) or not href.strip():
            continue
        edge = parse_size(tag.get("sizes"))
        absolute = urljoin(base, href.strip())
        if "manifest" in rel:
            collected.manifests.append(absolute)
        elif "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
            _add(collected, absolute, _score_with_size(112, edge), "link:apple-touch-icon")
        elif "mask-icon" in rel:
            # Monochrome by design, so only a last resort before /favicon.ico.
            _add(collected, absolute, 64, "link:mask-icon")
        elif "icon" in rel or "shortcut" in rel:
            _add(collected, absolute, _score_with_size(100, edge), "link:icon")

    declared = [item for item in collected.candidates if item.source.startswith("link:")]
    pending_manifests: list[str] = []
    if collected.manifests and ICON_READ_MANIFEST:
        if declared:
            pending_manifests = collected.manifests[:2]
        else:
            for candidate in manifest_icon_candidates(collected.manifests[:2], base, client, timeout):
                _add(collected, candidate.url, candidate.score, candidate.source)

    # Windows tiles: usually a clean 144x144 PNG.
    for tag in soup.find_all("meta", attrs={"name": re.compile("^msapplication-TileImage$", re.I)}):
        content = tag.get("content")
        if isinstance(content, str) and content.strip():
            _add(collected, urljoin(base, content.strip()), 98, "meta:tile-image")

    # Share images are wide banners, so they sit below every real icon.
    for prop, score in (("og:image", 48), ("og:image:url", 48), ("twitter:image", 44)):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        content = tag.get("content") if tag else None
        if isinstance(content, str) and content.strip():
            _add(collected, urljoin(base, content.strip()), score, f"meta:{prop}")

    for img in soup.find_all("img", limit=80):
        src, score = _image_hint(img)
        if not src or score <= 0:
            continue
        _add(collected, urljoin(base, src), score, "img:logo")

    # Conventional locations, only worth trying after declared icons. Project
    # sites (GitHub Pages, apps mounted under /app) keep the favicon next to the
    # page rather than at the origin root, so that path is tried first.
    parsed = urlparse(base)
    if parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        directory = posixpath.dirname(parsed.path) or "/"
        if not directory.endswith("/"):
            directory += "/"
        if directory != "/":
            _add(collected, f"{origin}{directory}favicon.ico", 42, "guess:dir-favicon.ico")
        _add(collected, f"{origin}/apple-touch-icon.png", 44, "guess:apple-touch-icon.png")
        _add(collected, f"{origin}/favicon.ico", 40, "guess:favicon.ico")
        _add(collected, f"{origin}/favicon.svg", 39, "guess:favicon.svg")

    return sorted(collected.candidates, key=lambda item: (-item.score, len(item.url))), pending_manifests


def manifest_icon_candidates(
    manifest_urls: list[str],
    base: str,
    client: httpx.Client | None,
    timeout: float,
) -> list[IconCandidate]:
    out: list[IconCandidate] = []
    for manifest_url in manifest_urls[:2]:
        out.extend(_manifest_candidates(manifest_url, base, client, timeout))
    return sorted(out, key=lambda item: -item.score)


def _manifest_candidates(
    manifest_url: str,
    base: str,
    client: httpx.Client | None,
    timeout: float,
) -> list[IconCandidate]:
    payload: object | None = None
    try:
        if client is not None:
            response = client.get(manifest_url, timeout=min(timeout, 4.0))
            response.raise_for_status()
            payload = response.json()
        else:
            with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(min(timeout, 4.0))) as own:
                response = own.get(manifest_url)
                response.raise_for_status()
                if len(response.content) > 256 * 1024:
                    return []
                payload = json.loads(response.text)
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(payload, dict):
        return []
    icons = payload.get("icons")
    if not isinstance(icons, list):
        return []

    out: list[IconCandidate] = []
    for icon in icons:
        if not isinstance(icon, dict):
            continue
        src = icon.get("src")
        if not isinstance(src, str) or not src.strip():
            continue
        edge = parse_size(icon.get("sizes"))
        score = _score_with_size(96, edge)
        # A 512 px maskable PNG is the best asset a site can offer.
        if icon.get("purpose") and "maskable" in str(icon.get("purpose")).lower():
            score += 4
        out.append(IconCandidate(url=urljoin(base, src.strip()), score=score, source="manifest"))
    return sorted(out, key=lambda item: -item.score)


def probe_icon(raw: bytes | None) -> IconProbe:
    """Decide whether downloaded bytes make a usable card icon."""
    if not raw:
        return IconProbe(False)
    if looks_like_svg(raw):
        return IconProbe(len(raw) <= MAX_SVG_BYTES, edge=512, square=True, kind="svg")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            image = Image.open(io.BytesIO(raw))
            image.load()
            width, height = image.size
    except (OSError, ValueError, Image.DecompressionBombError):
        return IconProbe(False)
    if width < 16 or height < 16:
        return IconProbe(False)
    ratio = width / height
    if ratio > 3 or ratio < 1 / 3:
        return IconProbe(False)
    return IconProbe(True, edge=max(width, height), square=0.75 <= ratio <= 1.33, kind=image.format or "")


def resolve_icon(
    page_url: str,
    candidates: list[IconCandidate],
    timeout: float = ICON_FETCH_TIMEOUT,
    max_tries: int = 8,
    client: httpx.Client | None = None,
    budget: float = ICON_TOTAL_BUDGET,
) -> ResolvedIcon:
    """Download candidates and return the first usable one.

    Candidates are fetched three at a time: a slow first choice (dead CDN, 403)
    then costs one timeout instead of three. Within a batch the highest scoring
    candidate that decoded wins. ``budget`` bounds the whole hunt so a dead host
    cannot stall a batch import, and ``max_tries`` leaves room for the
    conventional-path guesses even when a page declares several dead icons.
    """
    deadline = monotonic() + budget
    queue = candidates[:max_tries]

    def _remaining() -> float:
        return deadline - monotonic()

    def _fetch(url: str) -> bytes | None:
        left = min(timeout, _remaining())
        if left <= 0.2:
            return None
        return fetch_remote_image(url, timeout=left, referer=page_url, client=client)

    def _first_usable(pairs: list[tuple[IconCandidate | None, str, bytes | None]]) -> ResolvedIcon | None:
        for candidate, url, raw in pairs:
            if not probe_icon(raw).ok:
                continue
            stored = image_bytes_to_stored(raw, SITE_ICON_SIZE) if raw else None
            if stored:
                return ResolvedIcon(stored=stored, source=candidate.source if candidate else "service:mirror", url=url)
        return None

    position = 0
    while position < len(queue) and _remaining() > 0.3:
        batch = queue[position : position + 3]
        position += 3
        with ThreadPoolExecutor(max_workers=min(3, len(batch))) as pool:
            payloads = list(pool.map(lambda item: _fetch(item.url), batch))
        hit = _first_usable([(item, item.url, raw) for item, raw in zip(batch, payloads)])
        if hit:
            return hit

    host = urlparse(page_url).hostname or ""
    if host and not host.replace(".", "").isdigit() and _remaining() > 0.3:
        mirrors = [template.format(host=host) for template in ICON_FALLBACK_TEMPLATES]
        mirrors = [url for url in dict.fromkeys(mirrors) if url not in {item.url for item in queue}]
        if mirrors:
            with ThreadPoolExecutor(max_workers=min(3, len(mirrors))) as pool:
                payloads = list(pool.map(_fetch, mirrors))
            hit = _first_usable([(None, url, raw) for url, raw in zip(mirrors, payloads)])
            if hit:
                return hit

    return ResolvedIcon(stored=None, source="default", url="")
