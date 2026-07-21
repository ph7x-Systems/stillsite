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
    TranslationState,
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
            "login_csrf": form.cookies["__Host-sardine_login_csrf"],
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
    assert "admin-coverage" in listing
    assert "missing" in listing
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


def test_page_autosave_persists_without_consuming_revision_history(tmp_path: Path) -> None:
    app = _app(tmp_path, _page("home"))
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/pages/home").text
        assert 'data-autosave-url="/pages/home/autosave"' in editor
        saved = client.post(
            "/pages/home/autosave",
            data={
                "csrf_token": csrf,
                "title": "Autosaved home",
                "description": "Still a draft",
                "slug": "home",
            },
        )
        assert saved.status_code == 200
        assert saved.json() == {"ok": True, "preview_path": None}
    stored = _stored_page(tmp_path, "home")
    assert stored.source.title == "Autosaved home"
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        assert storage.list_revisions("page", "home") == []


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
    assert "admin-coverage" in listing
    assert "missing" in listing
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


def test_editor_kind_hints_are_the_bundled_gallery(tmp_path: Path) -> None:
    """The editor's kind suggestions come from the one bundled gallery the
    themes implement — no drift between admin hints and theme contracts."""
    from cms_build.themes import SECTION_KIND_GALLERY

    app = _app(tmp_path, _page("home", _hero()))
    with _client(app) as client:
        _sign_in(client)
        editor = client.get("/pages/home").text
    for kind in SECTION_KIND_GALLERY:
        assert kind in editor, kind


def test_extension_section_kinds_join_the_editor_hints(tmp_path: Path) -> None:
    """ADR-0028: kinds an activated extension advertises appear in the kind
    suggestions and drive the section editor's suggested field rows."""
    (tmp_path / "sardine.toml").write_text(
        'extensions = ["test_extensions:extension"]\n'
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n',
        encoding="utf-8",
    )
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
        timeline = Section(key="era-one", kind="timeline", source=SectionContent())
        storage.save_page(_page("home", timeline))
    app = create_app(AdminSettings(storage_url=url, project_dir=tmp_path))
    with _client(app) as client:
        _sign_in(client)
        editor = client.get("/pages/home").text
        section = client.get("/pages/home/sections/era-one").text
    assert "timeline" in editor  # advertised kind joins the hint list
    # the extension's advertised fields become suggested empty rows
    assert 'value="heading"' in section
    assert 'value="moments"' in section


def _faq(items: list[dict[str, str]] | None = None) -> Section:
    return Section(
        key="faq-main",
        kind="faq",
        source=SectionContent(fields={"heading": "Questions"}, items=items or []),
    )


def test_section_items_edit_add_and_remove(tmp_path: Path) -> None:
    """ADR-0037 phase 3: item rows save from per-column inputs; a fully
    cleared row is a removal, blank trailing rows add."""
    app = _app(tmp_path, _page("home", _faq([{"question": "Old?", "answer": "Yes."}])))
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/pages/home/sections/faq-main").text
        assert 'name="item_question"' in editor and "Old?" in editor
        response = client.post(
            "/pages/home/sections/faq-main",
            data={
                "csrf_token": csrf,
                "field_name": ["heading"],
                "field_value": ["Questions"],
                "item_question": ["Old?", "New?", ""],
                "item_answer": ["", "Indeed.", ""],
                "media": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    stored = _stored_page(tmp_path, "home").sections[0]
    assert stored.source.items == [
        {"question": "Old?"},
        {"question": "New?", "answer": "Indeed."},
    ]


def test_section_markdown_field_saves_from_its_own_widget(tmp_path: Path) -> None:
    """A kind's declared Markdown field leaves the generic table and
    saves from its md_ textarea."""
    story = Section(key="story-main", kind="story", source=SectionContent(fields={"heading": "H"}))
    app = _app(tmp_path, _page("home", story))
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/pages/home/sections/story-main").text
        assert 'name="md_body"' in editor
        response = client.post(
            "/pages/home/sections/story-main",
            data={
                "csrf_token": csrf,
                "field_name": ["heading"],
                "field_value": ["H"],
                "md_body": "Some **bold** prose.",
                "media": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    stored = _stored_page(tmp_path, "home").sections[0]
    assert stored.source.fields["body"] == "Some **bold** prose."


def test_section_items_translate_row_aligned(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _page("home", _faq([{"question": "What?", "answer": "This."}])),
    )
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/pages/home/sections/faq-main/translations/pt-pt").text
        assert "What?" in editor  # the source shows beside the inputs
        response = client.post(
            "/pages/home/sections/faq-main/translations/pt-pt",
            data={
                "csrf_token": csrf,
                "field__heading": "Perguntas",
                "item_question": ["O quê?"],
                "item_answer": ["Isto."],
                "media": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    stored = _stored_page(tmp_path, "home").sections[0]
    translated = stored.translations[Language.PT_PT].content
    assert translated.items == [{"question": "O quê?", "answer": "Isto."}]
    assert stored.translation_state(Language.PT_PT) is TranslationState.COMPLETE


def test_page_body_saves_and_translates(tmp_path: Path) -> None:
    """ADR-0037 phase 3: the long-form page body edits and translates."""
    app = _app(tmp_path, _page("home"))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home",
            data={
                "csrf_token": csrf,
                "title": "Home",
                "description": "",
                "slug": "home",
                "body_markdown": "A **document** page.",
                "publish_at": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        response = client.post(
            "/pages/home/translations/pt-pt",
            data={
                "csrf_token": csrf,
                "title": "Início",
                "description": "",
                "slug": "inicio",
                "body_markdown": "Uma página **documento**.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    stored = _stored_page(tmp_path, "home")
    assert stored.source.body_markdown == "A **document** page."
    assert stored.translations[Language.PT_PT].content.body_markdown == "Uma página **documento**."


def test_block_gallery_adds_with_an_auto_key(tmp_path: Path) -> None:
    """#127: editors never invent slugs — a gallery card posts only the
    kind; keys derive from it and stay unique."""
    app = _app(tmp_path, _page("home", _hero()))
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/pages/home").text
        assert "admin-block-gallery" in editor
        for expected_key in ("faq", "faq-2"):
            response = client.post(
                "/pages/home/sections",
                data={"csrf_token": csrf, "kind": "faq"},
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"].endswith(f"/sections/{expected_key}")


def test_duplicate_copies_content_translations_and_position(tmp_path: Path) -> None:
    hero = _hero(heading="Welcome")
    hero.set_translation(Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"}))
    page = _page("home", hero)
    page.sections.append(Section(key="tail", kind="cta", source=SectionContent()))
    app = _app(tmp_path, page)
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home/sections/hero-main/duplicate",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        assert response.status_code == 303
    stored = _stored_page(tmp_path, "home")
    assert [section.key for section in stored.sections] == ["hero-main", "hero", "tail"]
    copy = stored.sections[1]
    assert copy.source.fields == {"heading": "Welcome"}
    assert copy.translations[Language.PT_PT].content.fields == {"heading": "Bem-vindo"}


def test_hidden_sections_skip_builds_and_never_block_parity(tmp_path: Path) -> None:
    """#127: hide keeps the content but drops it from the artifact, and
    an untranslated hidden section does not block the page's parity."""
    from cms_build import build_site
    from cms_core import ContentStatus, TranslationState
    from cms_validation import SiteContent

    page = _page("home", _hero(heading="Visible welcome"))
    page.sections.append(
        Section(key="wip", kind="story", source=SectionContent(fields={"body": "Unfinished"}))
    )
    app = _app(tmp_path, page)
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home/sections/wip/visibility",
            data={"csrf_token": csrf, "action": "hide"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        listing = client.get("/pages/home").text
        assert "Hidden" in listing
    stored = _stored_page(tmp_path, "home")
    assert stored.sections[1].hidden
    # parity: only the visible hero counts
    stored.sections[0].set_translation(
        Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"})
    )
    stored.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))
    assert stored.translation_state(Language.PT_PT) is TranslationState.COMPLETE
    # builds: the hidden body never renders
    stored.status = ContentStatus.PUBLISHED
    from cms_build import SiteConfig

    artifact = build_site(
        SiteConfig(name="T", base_url="https://t.example", languages=(Language.PT_PT,)),
        SiteContent(pages=[stored], articles=[], media=[]),
        now=NOW,
    )
    html = artifact.files["index.html"].decode("utf-8")  # id "home" is the root page
    assert "Visible welcome" in html
    assert "Unfinished" not in html


def test_delete_offers_undo_and_restore_brings_everything_back(tmp_path: Path) -> None:
    hero = _hero(heading="Welcome")
    hero.set_translation(Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"}))
    app = _app(tmp_path, _page("home", hero))
    with _client(app) as client:
        csrf = _sign_in(client)
        deleted = client.post("/pages/home/sections/hero-main/delete", data={"csrf_token": csrf})
        assert deleted.status_code == 200
        assert "was deleted" in deleted.text and 'name="payload"' in deleted.text
        assert _stored_page(tmp_path, "home").sections == []
        payload = deleted.text.split('name="payload" value="')[1].split('"')[0]
        import html as html_lib

        restored = client.post(
            "/pages/home/sections/restore",
            data={"csrf_token": csrf, "payload": html_lib.unescape(payload), "position": "0"},
            follow_redirects=False,
        )
        assert restored.status_code == 303
    stored = _stored_page(tmp_path, "home")
    assert stored.sections[0].key == "hero-main"
    assert stored.sections[0].translations[Language.PT_PT].content.fields == {
        "heading": "Bem-vindo"
    }


def test_drag_order_endpoint_applies_a_full_permutation(tmp_path: Path) -> None:
    page = _page("home", _hero())
    page.sections.append(Section(key="middle", kind="story", source=SectionContent()))
    page.sections.append(Section(key="tail", kind="cta", source=SectionContent()))
    app = _app(tmp_path, page)
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/pages/home/sections/order",
            data={"csrf_token": csrf, "key_order": ["tail", "hero-main", "middle"]},
            follow_redirects=False,
        )
        assert response.status_code == 303
        partial = client.post(
            "/pages/home/sections/order",
            data={"csrf_token": csrf, "key_order": ["tail"]},
        )
        assert partial.status_code == 400
    stored = _stored_page(tmp_path, "home")
    assert [section.key for section in stored.sections] == ["tail", "hero-main", "middle"]


def test_the_section_picker_appends_without_duplicates(tmp_path: Path) -> None:
    """#136: the media adder appends library picks to the section's
    ordered list; the textarea stays the precise no-JS path."""
    from cms_core import MediaAsset

    page = new_page("home", PageContent(title="Home", slug="home"), now=NOW)
    page.sections.append(
        Section(key="hero", kind="hero", source=SectionContent(fields={}, media=["existing-art"]))
    )
    app = _app(tmp_path, page)
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        for asset_id in ("existing-art", "fresh-art"):
            storage.save_media_asset(
                MediaAsset(
                    id=asset_id,
                    path=f"{asset_id}.png",
                    mime_type="image/png",
                    width=640,
                    height=480,
                    alt={Language.EN: f"The {asset_id}"},
                )
            )
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/pages/home/sections/hero").text
        assert 'name="media_add"' in editor
        assert "fresh-art" in editor
        client.post(
            "/pages/home/sections/hero",
            data={
                "csrf_token": csrf,
                "media": "existing-art",
                "media_add": ["fresh-art", "existing-art"],
            },
            follow_redirects=False,
        )
        with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
            saved = storage.load_page("home")
    assert saved is not None
    hero = next(s for s in saved.sections if s.key == "hero")
    assert hero.source.media == ["existing-art", "fresh-art"]  # appended once, order kept
