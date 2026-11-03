"""Image conversion helpers.

Raster images are stored as bare base64 like webstack-go; SVG keeps a full data
URI. The bundled frontend's imgSrc() already understands both forms plus URLs and
site-relative paths.
"""

from __future__ import annotations

import base64
import hashlib
import io
import warnings
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..config import MAX_REMOTE_IMAGE_BYTES, MAX_SVG_BYTES


def looks_like_svg(raw: bytes) -> bool:
    head = raw[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    head = head.lower()
    return b"<svg" in head and (head.startswith(b"<?xml") or head.startswith(b"<svg") or b"<!doctype svg" in head)


# Kept for older call sites inside the package.
_looks_like_svg = looks_like_svg


def image_bytes_to_stored(raw: bytes, size: tuple[int, int]) -> str | None:
    if not raw:
        return None
    if _looks_like_svg(raw):
        if len(raw) > MAX_SVG_BYTES:
            return None
        return "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            image = Image.open(io.BytesIO(raw))
            image.load()
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")
            # 16px favicons would sit as a dot in the middle of a 64px card, so
            # small rasters are scaled up to fill the tile before centring.
            if max(image.size) < size[0]:
                scale = size[0] / max(image.size)
                image = image.resize(
                    (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            image.thumbnail(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            left = (size[0] - image.width) // 2
            top = (size[1] - image.height) // 2
            canvas.alpha_composite(image.convert("RGBA"), (left, top))
            output = io.BytesIO()
            canvas.save(output, format="PNG", optimize=True)
            return base64.b64encode(output.getvalue()).decode("ascii")
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


def fetch_remote_image(
    url: str,
    timeout: float = 8.0,
    referer: str | None = None,
    client: httpx.Client | None = None,
) -> bytes | None:
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    try:
        if client is not None:
            return _read_image(client.stream("GET", url, timeout=timeout, headers=headers))
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
            headers=headers,
        ) as own:
            return _read_image(own.stream("GET", url, timeout=timeout))
    except (httpx.HTTPError, ValueError):
        return None


def _read_image(stream) -> bytes | None:
    with stream as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_REMOTE_IMAGE_BYTES:
                return None
            chunks.append(chunk)
        return b"".join(chunks)


def stored_image_from_url(url: str, size: tuple[int, int]) -> str | None:
    raw = fetch_remote_image(url)
    return image_bytes_to_stored(raw, size) if raw else None


def local_asset_to_stored(path: Path, size: tuple[int, int]) -> str | None:
    try:
        return image_bytes_to_stored(path.read_bytes(), size)
    except OSError:
        return None


# --- Generated fallback tile -------------------------------------------------
#
# A site can be perfectly real and still ship no icon at all (a plain GitHub
# Pages doc, an internal tool). Storing the same grey placeholder for every one
# of those makes the grid look broken, so we draw the first character of the
# title on a colour derived from the domain instead.

_CJK_FONTS = (
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
)
_LATIN_FONTS = (
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)
_TILE_COLORS = (
    (47, 111, 235),
    (224, 83, 61),
    (46, 158, 107),
    (139, 92, 246),
    (217, 119, 6),
    (15, 118, 110),
    (190, 24, 93),
    (51, 65, 85),
)


def _first_font(paths: tuple[str, ...]) -> str | None:
    for path in paths:
        if Path(path).is_file():
            return path
    return None


def _first_char(text: str, cjk: bool) -> str:
    for char in text:
        if not char.isalnum():
            continue
        if cjk or ord(char) < 128:
            return char.upper() if ord(char) < 128 else char
    return ""


def letter_avatar_stored(text: str, seed: str, size: tuple[int, int]) -> str | None:
    """Draw ``text``'s first character on a coloured rounded tile.

    Returns bare base64 PNG (same form as scraped icons), or ``None`` when no
    font is available — the caller then keeps the shared placeholder.
    """
    cjk_font = _first_font(_CJK_FONTS)
    font_path = cjk_font or _first_font(_LATIN_FONTS)
    if not font_path:
        return None
    # Only ask for a CJK glyph when the font we found can actually draw it.
    letter = _first_char(text, cjk=cjk_font is not None)
    if not letter:
        host = urlparse(seed).hostname or ""
        letter = _first_char(host.removeprefix("www."), cjk=False) or "•"

    tile = size[0]
    color = _TILE_COLORS[hashlib.blake2s(seed.encode("utf-8")).digest()[0] % len(_TILE_COLORS)]
    try:
        canvas = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        radius = max(2, tile // 5)
        draw.rounded_rectangle((0, 0, tile - 1, tile - 1), radius=radius, fill=(*color, 255))
        font = ImageFont.truetype(font_path, int(tile * 0.56))
        draw.text((tile / 2, tile / 2 - tile * 0.02), letter, font=font, fill=(255, 255, 255, 255), anchor="mm")
        output = io.BytesIO()
        canvas.save(output, format="PNG", optimize=True)
        return base64.b64encode(output.getvalue()).decode("ascii")
    except (OSError, ValueError):
        return None

