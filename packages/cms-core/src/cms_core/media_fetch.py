"""Fetch migrated media into the library (ADR-0045).

The orchestration is pure: network access happens only through the
injected fetch callable. The default fetcher (stdlib only) enforces the
transport rules — public http(s) hosts, a size cap, a timeout and three
attempts with backoff — because the admin flow will run this same code
where request forgery is a real attack.
"""

from __future__ import annotations

import hashlib
import ipaddress
import mimetypes
import re
import socket
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from cms_core.languages import Language
from cms_core.media import MediaAsset
from cms_core.models import Article

MAX_MEDIA_BYTES = 25 * 1024 * 1024
FETCH_ATTEMPTS = 3
FETCH_TIMEOUT_SECONDS = 10.0

_MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>https?://[^)\s]+)\)")

Fetcher = Callable[[str], tuple[bytes, str]]
"""Returns ``(body, content_type)`` for a URL or raises ``ValueError``."""


@dataclass(frozen=True)
class FetchedUrl:
    """The accounted outcome of one referenced URL (never summarized away)."""

    url: str
    asset_id: str | None
    reused: bool
    error: str | None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class MediaFetchResult:
    outcomes: tuple[FetchedUrl, ...]
    files: dict[str, bytes]
    """New library files to write, keyed by media-relative path."""
    assets: tuple[MediaAsset, ...]
    articles: tuple[Article, ...]
    """Articles whose bodies were rewritten to ``/media/…`` paths."""


def _host_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            return False
    return bool(infos)


def default_fetcher(url: str) -> tuple[bytes, str]:
    """Stdlib fetcher enforcing the ADR-0045 transport rules."""
    import urllib.error
    import urllib.request

    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported scheme {parts.scheme!r}")
    if not parts.hostname or not _host_is_public(parts.hostname):
        raise ValueError("host does not resolve to a public address")
    last = "unreachable"
    for attempt in range(FETCH_ATTEMPTS):
        if attempt:
            time.sleep(0.5 * (2 ** (attempt - 1)))
        try:
            with urllib.request.urlopen(  # nosec B310 — scheme and host validated above
                url, timeout=FETCH_TIMEOUT_SECONDS
            ) as response:
                body = response.read(MAX_MEDIA_BYTES + 1)
                if len(body) > MAX_MEDIA_BYTES:
                    raise ValueError(f"larger than {MAX_MEDIA_BYTES} bytes")
                content_type = response.headers.get_content_type()
                return body, content_type
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            last = str(error)
    raise ValueError(f"failed after {FETCH_ATTEMPTS} attempts: {last}")


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _image_size(data: bytes) -> tuple[int, int]:
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError as error:
        raise ValueError(
            "cannot determine image dimensions — install the imaging dependency"
        ) from error
    try:
        with Image.open(BytesIO(data)) as image:
            return int(image.width), int(image.height)
    except Exception as error:
        raise ValueError(f"unreadable image: {error}") from error


def fetch_media_for_articles(
    articles: Iterable[Article],
    existing_assets: Iterable[MediaAsset],
    *,
    source_language: Language,
    fetch: Fetcher = default_fetcher,
    collection: str = "imported",
) -> MediaFetchResult:
    """Fetch the remote images the articles' bodies reference.

    Deterministic given its inputs: URLs are processed in sorted order and
    every referenced URL appears exactly once in the outcomes.
    """

    articles = list(articles)
    by_hash = {asset.content_hash: asset for asset in existing_assets if asset.content_hash}
    used_ids = {asset.id for asset in by_hash.values()}
    for asset in existing_assets:
        used_ids.add(asset.id)

    references: dict[str, str] = {}
    for article in articles:
        for match in _MARKDOWN_IMAGE.finditer(article.source.body_markdown):
            references.setdefault(match.group("url"), match.group("alt").strip())

    outcomes: list[FetchedUrl] = []
    files: dict[str, bytes] = {}
    assets: list[MediaAsset] = []
    rewrites: dict[str, str] = {}
    for url in sorted(references):
        try:
            data, content_type = fetch(url)
        except ValueError as error:
            outcomes.append(FetchedUrl(url=url, asset_id=None, reused=False, error=str(error)))
            continue
        digest = hashlib.sha256(data).hexdigest()
        known = by_hash.get(digest)
        if known is not None:
            rewrites[url] = f"/media/{known.path}"
            outcomes.append(FetchedUrl(url=url, asset_id=known.id, reused=True, error=None))
            continue
        filename = urlsplit(url).path.rsplit("/", 1)[-1] or "asset"
        stem, _, extension = filename.rpartition(".")
        mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        width = height = None
        if mime.startswith("image/"):
            try:
                width, height = _image_size(data)
            except ValueError as error:
                outcomes.append(FetchedUrl(url=url, asset_id=None, reused=False, error=str(error)))
                continue
        base = _slug(stem or filename) or "asset"
        asset_id = base
        suffix = 2
        while asset_id in used_ids:
            asset_id = f"{base}-{suffix}"
            suffix += 1
        used_ids.add(asset_id)
        path = (
            f"{collection}/{asset_id}.{extension.lower()}"
            if extension
            else (f"{collection}/{asset_id}")
        )
        alt = references[url] or asset_id.replace("-", " ")
        asset = MediaAsset(
            id=asset_id,
            path=path,
            mime_type=mime,
            width=width,
            height=height,
            alt={source_language: alt},
            collection=collection,
            content_hash=digest,
        )
        by_hash[digest] = asset
        files[path] = data
        assets.append(asset)
        rewrites[url] = f"/media/{path}"
        outcomes.append(FetchedUrl(url=url, asset_id=asset_id, reused=False, error=None))

    rewritten: list[Article] = []
    for article in articles:
        body = article.source.body_markdown
        replaced = _MARKDOWN_IMAGE.sub(
            lambda match: (
                f"![{match.group('alt')}]({rewrites[match.group('url')]})"
                if match.group("url") in rewrites
                else match.group(0)
            ),
            body,
        )
        if replaced != body:
            article.source.body_markdown = replaced
            rewritten.append(article)

    return MediaFetchResult(
        outcomes=tuple(outcomes),
        files=files,
        assets=tuple(assets),
        articles=tuple(rewritten),
    )
