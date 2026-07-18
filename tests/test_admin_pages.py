"""Admin pages: metadata, ordered typed sections, and their translations.

Real flows over HTTP, no mocked internals. The aggregate language state is
the model's worst-state rule: one untranslated section keeps the whole page
incomplete no matter how complete the page's own content is.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.pages import parse_media
from cms_admin.security import hash_password
from cms_core import (
    Language,
    Page,
    PageContent,
    Role,
    Section,
    SectionContent,
    User,
    create_storage,
    new_page,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 18, tzinfo=UTC)


def _page(page_id: str, *sections: Section) -> Page:
    page = new_page(page_id, PageContent(title=page_id.title(), slug=page_id), now=NOW)
    page.sections.extend(sections)
    return page


def _hero(**fields: str) -> Section:
    return Section(
        key="hero-main",
        kind="hero",
        source=SectionContent(fields=fields or {"heading": "Welcome"}),
    )


def _app(tmp_path: Path, *pages: Page) -> FastAPI:
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
        for page in pages:
            storage.save_page(page)
    return create_app(AdminSettings(storage_url=url))


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _sign_in(client: TestClient) -> str:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "ana",
            "password": PASSWORD,
            "login_csrf": form.cookies["stillsite_login_csrf"],
        },
    )
    dashboard: str = client.get("/").text
    return dashboard.split('name="csrf_token" value="')[1].split('"')[0]


def _stored_page(tmp_path: Path, page_id: str) -> Page:
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        page = storage.load_page(page_id)
    assert page is not None
    return page


def test_parse_media_splits_lines() -> None:
    assert parse_media(" one \n\n two \n") == ["one", "two"]
    assert parse_media("") == []


def test_pages_require_a_session(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.get("/pages", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_list_aggregates_the_worst_state_across_sections(tmp_path: Path) -> None:
    page = _page("home", _hero())
    for language in (Language.PT_PT, Language.ES, Language.FR, Language.DE):
        page.set_translation(
            language, PageContent(title="Translated", slug=f"home-{language.value}")
        )
    app = _app(tmp_path, page)
    with _client(app) as client:
        _sign_in(client)
        listing = client.get("/pages").text
    # the page's own content is complete everywhere, but the hero is not
    assert "admin-state-missing" in listing
    assert "admin-state-complete" not in listing


def test_create_redirects_and_persists(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages",
            data={
                "csrf_token": csrf,
                "id": "about",
                "title": "About us",
                "description": "Who we are.",
                "slug": "about",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/pages/about"
        editor = client.get("/pages/about").text
    assert "About us" in editor
    assert _stored_page(tmp_path, "about").source.slug == "about"


def test_create_requires_a_valid_slug(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages",
            data={"csrf_token": csrf, "id": "about", "title": "Kept", "slug": "Bad Slug"},
        )
    assert response.status_code == 422
    assert "The form was not saved" in response.text
    assert 'value="Kept"' in response.text


def test_create_refuses_a_duplicate_id(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home"))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages",
            data={"csrf_token": csrf, "id": "home", "title": "Again", "slug": "again"},
        )
    assert response.status_code == 422
    assert "already exists" in response.text


def test_editing_the_page_content_marks_its_translation_outdated(tmp_path: Path) -> None:
    page = _page("home")
    page.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))
    app = _app(tmp_path, page)
    with _client(app) as client:
        csrf = _sign_in(client)
        client.post(
            "/pages/home",
            data={"csrf_token": csrf, "title": "New title", "slug": "home"},
        )
        editor = client.get("/pages/home").text
    assert "admin-state-outdated" in editor


def test_page_translation_save_completes_the_own_state(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero()))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home/translations/pt-pt",
            data={"csrf_token": csrf, "title": "Início", "description": "", "slug": "inicio"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        translation_page = client.get("/pages/home/translations/pt-pt").text
        listing = client.get("/pages").text
    assert "admin-state-complete" in translation_page
    # aggregate stays missing: the hero section has no PT-PT translation
    assert "admin-state-missing" in listing
    stored = _stored_page(tmp_path, "home")
    assert stored.translations[Language.PT_PT].content.slug == "inicio"


def test_add_section_redirects_to_its_editor(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home"))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home/sections",
            data={"csrf_token": csrf, "key": "story-one", "kind": "story"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/pages/home/sections/story-one"
    stored = _stored_page(tmp_path, "home")
    assert [section.key for section in stored.sections] == ["story-one"]


def test_add_section_refuses_duplicate_keys_and_bad_kinds(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero()))
    with _client(app) as client:
        csrf = _sign_in(client)
        duplicate = client.post(
            "/pages/home/sections",
            data={"csrf_token": csrf, "key": "hero-main", "kind": "hero"},
        )
        invalid = client.post(
            "/pages/home/sections",
            data={"csrf_token": csrf, "key": "ok-key", "kind": "Bad Kind"},
        )
    assert duplicate.status_code == 422
    assert "already exists" in duplicate.text
    assert invalid.status_code == 422


def test_section_editor_suggests_the_kind_fields(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero(heading="Welcome")))
    with _client(app) as client:
        _sign_in(client)
        editor = client.get("/pages/home/sections/hero-main").text
    assert 'value="Welcome"' in editor  # existing field
    assert 'value="kicker"' in editor  # suggested by the hero kind, still empty


def test_section_save_updates_adds_and_drops_fields(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero(heading="Welcome", kicker="Old kick")))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home/sections/hero-main",
            data={
                "csrf_token": csrf,
                "field_name": ["heading", "kicker", "accent", ""],
                "field_value": ["New heading", "", "shine", "ignored"],
                "media": "tin-rocket\n",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    stored = _stored_page(tmp_path, "home").sections[0]
    assert stored.source.fields == {"heading": "New heading", "accent": "shine"}
    assert stored.source.media == ["tin-rocket"]


def test_section_translation_side_by_side_and_state(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero(heading="Welcome", kicker="Kick")))
    with _client(app) as client:
        csrf = _sign_in(client)
        form_page = client.get("/pages/home/sections/hero-main/translations/pt-pt").text
        assert "Welcome" in form_page  # source shown next to the inputs
        assert 'name="field__heading"' in form_page
        response = client.post(
            "/pages/home/sections/hero-main/translations/pt-pt",
            data={
                "csrf_token": csrf,
                "field__heading": "Bem-vindo",
                "field__kicker": "",
                "media": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        saved = client.get("/pages/home/sections/hero-main/translations/pt-pt").text
    assert "admin-state-complete" in saved
    stored = _stored_page(tmp_path, "home").sections[0]
    assert stored.translations[Language.PT_PT].content.fields == {"heading": "Bem-vindo"}


def test_editing_the_section_source_marks_its_translation_outdated(tmp_path: Path) -> None:
    page = _page("home", _hero(heading="Welcome"))
    page.sections[0].set_translation(
        Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"})
    )
    app = _app(tmp_path, page)
    with _client(app) as client:
        csrf = _sign_in(client)
        client.post(
            "/pages/home/sections/hero-main",
            data={"csrf_token": csrf, "field_name": ["heading"], "field_value": ["Changed"]},
        )
        editor = client.get("/pages/home/sections/hero-main").text
    assert "admin-state-outdated" in editor


def test_sections_reorder_and_remove(tmp_path: Path) -> None:
    first = Section(key="one", kind="story", source=SectionContent())
    second = Section(key="two", kind="story", source=SectionContent())
    app = _app(tmp_path, _page("home", first, second))
    with _client(app) as client:
        csrf = _sign_in(client)
        client.post("/pages/home/sections/two/move", data={"csrf_token": csrf, "direction": "up"})
        assert [s.key for s in _stored_page(tmp_path, "home").sections] == ["two", "one"]
        client.post("/pages/home/sections/two/delete", data={"csrf_token": csrf})
        assert [s.key for s in _stored_page(tmp_path, "home").sections] == ["one"]


def test_unknown_targets_are_404(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero()))
    with _client(app) as client:
        _sign_in(client)
        assert client.get("/pages/missing").status_code == 404
        assert client.get("/pages/home/sections/missing").status_code == 404
        assert client.get("/pages/home/translations/en").status_code == 404
        assert client.get("/pages/home/sections/hero-main/translations/xx").status_code == 404


def test_page_posts_require_the_csrf_token(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero()))
    with _client(app) as client:
        _sign_in(client)
        response = client.post("/pages/home", data={"title": "No token", "slug": "home"})
    assert response.status_code == 403


def test_section_field_values_never_render_as_raw_html(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home", _hero(heading="<img src=x onerror=alert(1)>")))
    with _client(app) as client:
        _sign_in(client)
        editor = client.get("/pages/home/sections/hero-main").text
        translation = client.get("/pages/home/sections/hero-main/translations/es").text
    assert "<img src=x" not in editor
    assert "<img src=x" not in translation
