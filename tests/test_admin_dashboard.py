"""Admin shell and dashboard (Milestone 3 phase 4).

The dashboard aggregates real storage content through the public APIs —
status counts, the translation coverage matrix, a live validation report —
and the shell serves the vendored hTWOo assets locally (ADR-0013: no CDN).
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.dashboard import coverage_percent, status_counts, translation_matrix
from cms_admin.security import hash_password
from cms_core import (
    TARGET_LANGUAGES,
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    Role,
    TranslationState,
    User,
    create_storage,
    new_article,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 18, tzinfo=UTC)


def _article(article_id: str, status: ContentStatus, *translated: Language) -> Article:
    article = new_article(article_id, ArticleContent(title=article_id.title()), now=NOW)
    article.status = status
    for language in translated:
        article.set_translation(language, ArticleContent(title=f"{article_id} ({language})"))
    return article


def _app(tmp_path: Path, *articles: Article) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.EDITOR,
                created_at=NOW,
            )
        )
        for article in articles:
            storage.save_article(article)
    return create_app(AdminSettings(storage_url=url))


def _sign_in(client: TestClient) -> None:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "ana",
            "password": PASSWORD,
            "login_csrf": form.cookies["stillsite_login_csrf"],
        },
    )


def test_status_counts_cover_every_workflow_status() -> None:
    entries = [
        _article("one", ContentStatus.DRAFT),
        _article("two", ContentStatus.DRAFT),
        _article("three", ContentStatus.PUBLISHED, *TARGET_LANGUAGES),
    ]
    counts = status_counts(entries)
    assert counts[ContentStatus.DRAFT] == 2
    assert counts[ContentStatus.PUBLISHED] == 1
    assert counts[ContentStatus.REVIEW] == 0
    assert counts[ContentStatus.ARCHIVED] == 0


def test_translation_matrix_counts_states_per_target_language() -> None:
    entries = [
        _article("one", ContentStatus.DRAFT, Language.PT_PT),
        _article("two", ContentStatus.DRAFT),
    ]
    matrix = translation_matrix(entries)
    assert set(matrix) == set(TARGET_LANGUAGES)
    assert matrix[Language.PT_PT][TranslationState.COMPLETE] == 1
    assert matrix[Language.PT_PT][TranslationState.MISSING] == 1
    assert matrix[Language.ES][TranslationState.MISSING] == 2


def test_translation_matrix_marks_stale_translations_outdated() -> None:
    article = _article("one", ContentStatus.DRAFT, Language.FR)
    article.source = ArticleContent(title="Edited after the FR translation")
    matrix = translation_matrix([article])
    assert matrix[Language.FR][TranslationState.OUTDATED] == 1


def test_coverage_percent_rounds_and_defaults_to_full() -> None:
    assert coverage_percent(dict.fromkeys(TranslationState, 0)) == 100
    cells = {
        TranslationState.COMPLETE: 1,
        TranslationState.OUTDATED: 1,
        TranslationState.MISSING: 1,
    }
    assert coverage_percent(cells) == 33


def test_dashboard_shows_the_shell_chrome(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/").text
    assert "hoo-cmdbar" in page
    assert "hoo-nav" in page
    assert 'aria-current="page"' in page
    assert "ana" in page
    assert "/static/vendor/htwoo.min.css" in page
    assert "/static/admin.css" in page


def test_dashboard_reports_content_and_coverage(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _article("draft-one", ContentStatus.DRAFT),
        _article("live-one", ContentStatus.PUBLISHED, *TARGET_LANGUAGES),
    )
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/").text
    assert "2 articles, 0 pages, 0 media assets." in page
    assert "PT-PT" in page
    # one of two entries is fully translated in every target language
    assert "50%" in page


def test_dashboard_shows_validation_errors_that_block_publishing(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("live-one", ContentStatus.PUBLISHED, Language.PT_PT))
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/").text
    assert "required-translations" in page
    assert "Publishing is blocked" in page


def test_dashboard_empty_states(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/").text
    assert "No content yet" in page
    assert "All validation rules pass" in page
    assert "No build or export has run from this panel yet." in page


def test_htwoo_assets_are_served_locally_with_their_license(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path)) as client:
        css = client.get("/static/vendor/htwoo.min.css")
        license_file = client.get("/static/vendor/HTWOO-LICENSE.txt")
        admin_css = client.get("/static/admin.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "hoo-cmdbar" in css.text
    assert license_file.status_code == 200
    assert "MIT" in license_file.text
    assert admin_css.status_code == 200
    assert "--themePrimary" in admin_css.text


def test_static_assets_do_not_require_a_session(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path)) as client:
        response = client.get("/static/admin.css", follow_redirects=False)
    assert response.status_code == 200
