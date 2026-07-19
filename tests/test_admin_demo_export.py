"""The static admin snapshot for the public demo site.

The exporter boots the real admin over a throwaway copy of the content,
captures the editorial pages, and neutralizes them: prefixed links, no CSRF
tokens, no live forms, a visible read-only banner. The source database must
never gain the demo user.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin.demo_export import export_demo, neutralize
from cms_core import (
    ArticleContent,
    Language,
    MediaAsset,
    PageContent,
    Section,
    SectionContent,
    create_storage,
    new_article,
    new_page,
)

NOW = datetime(2026, 7, 18, tzinfo=UTC)


def _storage_file(tmp_path: Path) -> Path:
    db = tmp_path / "content.sqlite3"
    with create_storage(f"sqlite:///{db}") as storage:
        article = new_article("hello-orbit", ArticleContent(title="Hello orbit"), now=NOW)
        article.set_translation(Language.PT_PT, ArticleContent(title="Olá órbita"))
        storage.save_article(article)
        page = new_page("home", PageContent(title="Home", slug="home"), now=NOW)
        page.sections.append(
            Section(key="hero-main", kind="hero", source=SectionContent(fields={"heading": "Hi"}))
        )
        storage.save_page(page)
    return db


def test_snapshot_captures_the_editorial_surface(tmp_path: Path) -> None:
    db = _storage_file(tmp_path)
    out = tmp_path / "admin"
    pages = export_demo(db, out)
    assert pages >= 15  # dashboard, lists, editors, translations, login
    for expected in [
        "index.html",
        "login/index.html",
        "articles/index.html",
        "articles/hello-orbit/index.html",
        "articles/hello-orbit/translations/pt-pt/index.html",
        "pages/home/index.html",
        "trash/index.html",
        "pages/home/sections/hero-main/index.html",
        "pages/home/sections/hero-main/translations/es/index.html",
        "static/admin.css",
        "static/vendor/source-sans/source-sans-3-latin-wght-normal.woff2",
        "static/vendor/bootstrap-icons/bootstrap-icons.min.css",
        "static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2",
    ]:
        assert (out / expected).is_file(), expected


def test_snapshot_pages_are_inert_and_prefixed(tmp_path: Path) -> None:
    db = _storage_file(tmp_path)
    out = tmp_path / "admin"
    export_demo(db, out)
    editor = (out / "articles/hello-orbit/index.html").read_text(encoding="utf-8")
    assert "Read-only demo" in editor
    assert 'name="csrf_token"' not in editor
    assert 'method="post"' not in editor
    assert '<button type="submit"' not in editor
    assert "disabled" in editor
    assert 'href="/admin/articles' in editor
    assert 'href="/admin/static/' in editor or "/admin/static/" in editor


def test_the_source_database_never_gains_the_demo_user(tmp_path: Path) -> None:
    db = _storage_file(tmp_path)
    export_demo(db, tmp_path / "admin")
    with create_storage(f"sqlite:///{db}") as storage:
        assert storage.load_user("demo") is None


def test_media_previews_are_prefixed_in_the_snapshot(tmp_path: Path) -> None:
    """Regression: image sources must move under /admin/ like every link."""
    db = tmp_path / "content.sqlite3"
    with create_storage(f"sqlite:///{db}") as storage:
        storage.save_media_asset(
            MediaAsset(
                id="tin",
                path="tin.svg",
                mime_type="image/svg+xml",
                width=10,
                height=10,
                alt={Language.EN: "A tin"},
            )
        )
    out = tmp_path / "admin"
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "tin.svg").write_text('<svg xmlns="x" width="10" height="10"/>')
    export_demo(db, out, media_dir=media_dir)
    listing = (out / "media/index.html").read_text(encoding="utf-8")
    assert 'src="/admin/media-files/tin.svg"' in listing
    assert 'src="/media-files/' not in listing
    assert (out / "media-files" / "tin.svg").is_file()


def test_neutralize_rewrites_only_root_relative_links() -> None:
    html = (
        '<head></head><body><a href="/articles">a</a> '
        '<a href="https://example.com/x">b</a>'
        '<form method="post" action="/logout"><input type="hidden" '
        'name="csrf_token" value="tok"><button type="submit">Go</button></form></body>'
    )
    result = neutralize(html)
    assert 'href="/admin/articles"' in result
    assert 'href="https://example.com/x"' in result
    assert "tok" not in result
    assert 'method="get"' in result
    assert "disabled" in result


def test_snapshot_publishing_page_shows_the_full_report(tmp_path: Path) -> None:
    db = _storage_file(tmp_path)
    out = tmp_path / "admin"
    export_demo(db, out)
    publishing = (out / "publishing/index.html").read_text(encoding="utf-8")
    assert "admin-rules-table" in publishing
    for rule in ("required-translations", "unique-slugs", "media-alt-coverage"):
        assert rule in publishing


def test_snapshot_preview_link_points_at_the_public_site(tmp_path: Path) -> None:
    """The static snapshot cannot serve /preview/ — the public site is the
    preview, so the navbar link goes to the site root instead of a 404."""
    db = _storage_file(tmp_path)
    out = tmp_path / "admin"
    export_demo(db, out)
    dashboard = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="/admin/preview/"' not in dashboard
