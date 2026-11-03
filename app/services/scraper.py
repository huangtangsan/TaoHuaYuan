"""Small, dependency-light website metadata scraper."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import DEFAULT_SITE_ICON, ICON_FETCH_TIMEOUT, ICON_LETTER_FALLBACK, ICON_TOTAL_BUDGET, SITE_ICON_SIZE
from .icons import collect_candidates, manifest_icon_candidates, resolve_icon
from .images import BROWSER_UA, letter_avatar_stored


@dataclass(slots=True)
class ScrapedSite:
    title: str
    description: str
    icon: str
    # Where the icon came from: link:icon / manifest / img:logo / service:mirror / default
    icon_source: str = "default"


def is_valid_web_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _clean_text(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


def scrape_site(url: str, timeout: float = 8.0) -> ScrapedSite:
    """Fetch a page and return title, description, and the best icon found.

    Raises httpx errors / ValueError when the page itself cannot be fetched;
    callers decide whether that is fatal.
    """
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    icon_timeout = min(timeout, ICON_FETCH_TIMEOUT)
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(timeout), headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower() and not response.text.lstrip().startswith("<"):
            raise ValueError("目标地址不是 HTML 页面")
        soup = BeautifulSoup(response.text, "html.parser")
        # Redirects change the base URL, so relative icon paths must resolve
        # against the final address rather than the submitted one.
        page_url = str(response.url)
        candidates, pending_manifests = collect_candidates(
            soup, page_url, client=client, timeout=icon_timeout
        )

        started = monotonic()
        resolved = resolve_icon(
            page_url,
            candidates,
            timeout=icon_timeout,
            client=client,
            budget=ICON_TOTAL_BUDGET,
        )
        # The manifest is only fetched when every declared icon failed; it is
        # the last cheap chance before falling back to a placeholder.
        remaining = ICON_TOTAL_BUDGET - (monotonic() - started)
        if not resolved.stored and pending_manifests and remaining > 1.5:
            extra = manifest_icon_candidates(pending_manifests, page_url, client, icon_timeout)
            if extra:
                resolved = resolve_icon(
                    page_url,
                    extra,
                    timeout=icon_timeout,
                    client=client,
                    budget=remaining,
                )

    title_tag = soup.select_one("head > title") or soup.find("title")
    title = _clean_text(title_tag.get_text(" ", strip=True) if title_tag else "", 50) or url

    description = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = _clean_text(str(meta["content"]), 500)
    if not description:
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = _clean_text(str(og_desc["content"]), 500)

    if resolved.stored:
        return ScrapedSite(
            title=title,
            description=description,
            icon=resolved.stored,
            icon_source=resolved.source,
        )

    # Nothing on the site itself, so draw a tile from the first character of the
    # title rather than handing every icon-less site the same grey placeholder.
    if ICON_LETTER_FALLBACK:
        letter = letter_avatar_stored(title, page_url, SITE_ICON_SIZE)
        if letter:
            return ScrapedSite(title=title, description=description, icon=letter, icon_source="letter")

    return ScrapedSite(title=title, description=description, icon=DEFAULT_SITE_ICON, icon_source="default")
