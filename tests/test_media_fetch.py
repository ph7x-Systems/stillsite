"""Migrated media fetch: injected transport, accounted outcomes (ADR-0045)."""

import struct
import zlib

import pytest
from cms_core import Article, ArticleContent, Language, MediaAsset, new_article
from cms_core.media_fetch import default_fetcher, fetch_media_for_articles


def _png(width: int = 3, height: int = 2) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        raw = kind + data
        return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanlines = b"".join(b"\x00" + b"\x00" * (3 * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(scanlines))
        + chunk(b"IEND", b"")
    )


def _article(article_id: str, body: str) -> Article:
    article = new_article(
        article_id,
        ArticleContent(title=article_id, summary="s", body_markdown=body, slug=article_id),
    )
    article.fields = {"wxr_post_id": article_id}
    return article


def test_fetch_stores_rewrites_and_accounts_for_every_url() -> None:
    png = _png()
    calls: list[str] = []

    def fake(url: str) -> tuple[bytes, str]:
        calls.append(url)
        if url.endswith("broken.png"):
            raise ValueError("failed after 3 attempts: unreachable")
        return png, "image/png"

    article = _article(
        "launch",
        "![A rocket](https://example.test/img/rocket.png) and "
        "![](https://example.test/img/broken.png)",
    )
    result = fetch_media_for_articles([article], [], source_language=Language.EN, fetch=fake)

    assert sorted(calls) == [
        "https://example.test/img/broken.png",
        "https://example.test/img/rocket.png",
    ]
    outcomes = {o.url: o for o in result.outcomes}
    assert len(outcomes) == 2  # every referenced URL is accounted for
    ok = outcomes["https://example.test/img/rocket.png"]
    assert ok.ok and not ok.reused and ok.asset_id == "rocket"
    bad = outcomes["https://example.test/img/broken.png"]
    assert not bad.ok and "3 attempts" in (bad.error or "")

    (asset,) = result.assets
    assert asset.path == "imported/rocket.png"
    assert (asset.width, asset.height) == (3, 2)
    assert asset.alt == {Language.EN: "A rocket"}
    assert asset.collection == "imported"
    assert result.files["imported/rocket.png"] == png

    (rewritten,) = result.articles
    assert "![A rocket](/media/imported/rocket.png)" in rewritten.source.body_markdown
    # The failed URL stays a remote reference — visible, never dropped.
    assert "https://example.test/img/broken.png" in rewritten.source.body_markdown


def test_fetch_reuses_an_existing_asset_by_content_hash() -> None:
    png = _png()
    import hashlib

    existing = MediaAsset(
        id="already-here",
        path="uploads/already-here.png",
        mime_type="image/png",
        width=3,
        height=2,
        alt={Language.EN: "kept"},
        content_hash=hashlib.sha256(png).hexdigest(),
    )
    article = _article("launch", "![x](https://example.test/dup.png)")
    result = fetch_media_for_articles(
        [article], [existing], source_language=Language.EN, fetch=lambda url: (png, "image/png")
    )
    (outcome,) = result.outcomes
    assert outcome.reused and outcome.asset_id == "already-here"
    assert result.assets == () and result.files == {}
    (rewritten,) = result.articles
    assert "(/media/uploads/already-here.png)" in rewritten.source.body_markdown


def test_rerun_finds_nothing_left_to_fetch() -> None:
    article = _article("launch", "![x](/media/imported/rocket.png)")

    def explode(url: str) -> tuple[bytes, str]:
        raise AssertionError("no remote references remain")

    result = fetch_media_for_articles([article], [], source_language=Language.EN, fetch=explode)
    assert result.outcomes == () and result.articles == ()


def test_default_fetcher_refuses_unsafe_urls() -> None:
    with pytest.raises(ValueError, match="scheme"):
        default_fetcher("ftp://example.test/a.png")
    with pytest.raises(ValueError, match="public"):
        default_fetcher("http://127.0.0.1/a.png")
    with pytest.raises(ValueError, match="public"):
        default_fetcher("http://169.254.1.1/a.png")
