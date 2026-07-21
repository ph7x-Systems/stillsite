"""Backend conformance suite (ADR-0004): every engine must pass unchanged.

The `backend` fixture (tests/conftest.py) parameterizes these tests over all
implemented engines — SQLite always, PostgreSQL when a server is available.
"""

from datetime import UTC, datetime

from cms_core import (
    AdminSession,
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    MenuItem,
    PageContent,
    Role,
    Section,
    SectionContent,
    User,
    new_article,
    new_page,
)
from cms_core.storage import MIGRATIONS, StorageBackend


def test_connect_applies_all_migrations(backend: StorageBackend) -> None:
    assert backend.schema_version() == len(MIGRATIONS)
    # A second migrate call is a no-op, not an error.
    assert backend.migrate() == len(MIGRATIONS)


def test_article_round_trip(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First", body_markdown="Hello."))
    article.set_translation(Language.PT_PT, ArticleContent(title="Primeiro", body_markdown="Olá."))
    article.status = ContentStatus.REVIEW
    article.category = "field-notes"
    article.tags = ("craft", "maps")

    backend.save_article(article)
    assert backend.load_article("first-post") == article


def test_save_is_an_upsert(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First"))
    backend.save_article(article)

    article.source = ArticleContent(title="First, revised")
    article.set_translation(Language.ES, ArticleContent(title="Primero"))
    backend.save_article(article)

    loaded = backend.load_article("first-post")
    assert loaded is not None
    assert loaded.source.title == "First, revised"
    assert set(loaded.translations) == {Language.ES}


def test_delete_cascades_to_translations(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First"))
    article.set_translation(Language.FR, ArticleContent(title="Premier"))
    backend.save_article(article)

    assert backend.delete_article("first-post")
    assert not backend.delete_article("first-post")
    assert backend.list_article_ids() == []


def test_missing_article_loads_as_none(backend: StorageBackend) -> None:
    assert backend.load_article("nope") is None


def test_page_round_trip_preserves_section_order(backend: StorageBackend) -> None:
    page = new_page("home", PageContent(title="Home", slug="home"))
    for key in ("hero", "features", "contact"):
        page.sections.append(
            Section(key=key, kind=key, source=SectionContent(fields={"heading": key.title()}))
        )
    page.sections[0].set_translation(
        Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"})
    )
    page.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))
    backend.save_page(page)

    loaded = backend.load_page("home")
    assert loaded is not None
    assert loaded == page
    assert [section.key for section in loaded.sections] == ["hero", "features", "contact"]


def test_page_round_trip_preserves_items_and_body(backend: StorageBackend) -> None:
    """ADR-0037 phase 1: the repeating group and the long-form body
    survive every engine, translations included, order intact."""
    page = new_page(
        "faq-page",
        PageContent(title="FAQ", slug="faq", body_markdown="A **document** page."),
    )
    faq = Section(
        key="faq",
        kind="faq",
        source=SectionContent(
            fields={"heading": "Questions"},
            items=[
                {"question": "What is it?", "answer": "A CMS."},
                {"question": "Is it fast?", "answer": "It is static."},
            ],
        ),
    )
    faq.set_translation(
        Language.PT_PT,
        SectionContent(
            fields={"heading": "Perguntas"},
            items=[
                {"question": "O que é?", "answer": "Um CMS."},
                {"question": "É rápido?", "answer": "É estático."},
            ],
        ),
    )
    page.sections.append(faq)
    page.set_translation(
        Language.PT_PT,
        PageContent(title="FAQ", slug="faq-pt", body_markdown="Uma página **documento**."),
    )
    backend.save_page(page)

    loaded = backend.load_page("faq-page")
    assert loaded is not None
    assert loaded == page
    assert loaded.sections[0].source.items[1]["answer"] == "It is static."
    translated = loaded.sections[0].translations[Language.PT_PT]
    assert translated.content.items[0]["question"] == "O que é?"
    assert loaded.source.body_markdown == "A **document** page."
    assert loaded.translations[Language.PT_PT].content.body_markdown == "Uma página **documento**."


def test_page_delete_removes_page(backend: StorageBackend) -> None:
    page = new_page("home", PageContent(title="Home", slug="home"))
    hero = Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Welcome"}))
    hero.set_translation(Language.FR, SectionContent(fields={"heading": "Bienvenue"}))
    page.sections.append(hero)
    backend.save_page(page)

    assert backend.delete_page("home")
    assert backend.list_page_ids() == []
    assert backend.load_page("home") is None


def test_media_round_trip_and_delete(backend: StorageBackend) -> None:
    asset = MediaAsset(
        id="logo",
        path="images/logo.svg",
        mime_type="image/svg+xml",
        width=64,
        height=64,
        alt={Language.EN: "Company logo", Language.PT_PT: "Logótipo da empresa"},
        collection="brand",
        content_hash="ab" * 32,
        crop="1,1,30,30",
        focal="0.5,0.5",
    )
    backend.save_media_asset(asset)
    assert backend.load_media_asset("logo") == asset
    assert backend.list_media_ids() == ["logo"]

    assert backend.delete_media_asset("logo")
    assert backend.load_media_asset("logo") is None


def test_has_content_reflects_all_collections(backend: StorageBackend) -> None:
    assert not backend.has_content()
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))
    assert backend.has_content()
    backend.delete_page("home")
    assert not backend.has_content()


def test_load_all_collections(backend: StorageBackend) -> None:
    backend.save_article(new_article("b-post", ArticleContent(title="B")))
    backend.save_article(new_article("a-post", ArticleContent(title="A")))
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))

    assert [article.id for article in backend.load_all_articles()] == ["a-post", "b-post"]
    assert [page.id for page in backend.load_all_pages()] == ["home"]
    assert backend.load_all_media_assets() == []


def test_backend_is_a_context_manager(backend: StorageBackend) -> None:
    with backend as storage:
        storage.save_article(new_article("post", ArticleContent(title="Post")))


# Admin accounts and sessions (never part of the export)


def _user(username: str = "ana", role: Role = Role.EDITOR) -> User:
    return User(
        username=username,
        password_hash="argon2-hash-placeholder",
        role=role,
        created_at=datetime(2026, 7, 18, 12, 0, 0),
    )


def test_user_round_trip_and_upsert(backend: StorageBackend) -> None:
    backend.save_user(_user())
    assert backend.load_user("ana") == _user()
    backend.save_user(_user(role=Role.ADMIN))
    loaded = backend.load_user("ana")
    assert loaded is not None
    assert loaded.role is Role.ADMIN
    assert loaded.language is None  # unset preference follows the browser
    assert backend.list_usernames() == ["ana"]


def test_publish_at_round_trips_on_articles_and_pages(backend: StorageBackend) -> None:
    """ADR-0024: the scheduling moment persists (and clears) on every engine."""
    moment = datetime(2027, 1, 1, 9, 0, tzinfo=UTC)
    article = new_article("scheduled-post", ArticleContent(title="Later"))
    article.publish_at = moment
    backend.save_article(article)
    loaded = backend.load_article("scheduled-post")
    assert loaded is not None and loaded.publish_at == moment
    article.publish_at = None
    backend.save_article(article)
    reloaded = backend.load_article("scheduled-post")
    assert reloaded is not None and reloaded.publish_at is None
    page = new_page("scheduled-page", PageContent(title="Later", slug="later"))
    page.publish_at = moment
    backend.save_page(page)
    stored = backend.load_page("scheduled-page")
    assert stored is not None and stored.publish_at == moment


def test_user_language_preference_round_trips(backend: StorageBackend) -> None:
    backend.save_user(_user().model_copy(update={"language": Language.PT_PT}))
    loaded = backend.load_user("ana")
    assert loaded is not None
    assert loaded.language is Language.PT_PT
    backend.save_user(_user())  # upsert back to unset
    reloaded = backend.load_user("ana")
    assert reloaded is not None
    assert reloaded.language is None


def test_user_delete_and_missing_user(backend: StorageBackend) -> None:
    backend.save_user(_user())
    assert backend.delete_user("ana")
    assert not backend.delete_user("ana")
    assert backend.load_user("ana") is None
    assert backend.list_usernames() == []


def test_users_do_not_count_as_content(backend: StorageBackend) -> None:
    backend.save_user(_user())
    assert not backend.has_content()


def test_session_round_trip_and_cascade(backend: StorageBackend) -> None:
    backend.save_user(_user())
    session = AdminSession(
        token_hash="digest-1",
        username="ana",
        csrf_token="csrf-1",
        expires_at=datetime(2026, 7, 18, 23, 59, 59),
    )
    backend.save_session(session)
    assert backend.load_session("digest-1") == session
    backend.delete_user("ana")
    assert backend.load_session("digest-1") is None


def test_expired_sessions_are_purged(backend: StorageBackend) -> None:
    backend.save_user(_user())
    stale = AdminSession(
        token_hash="digest-old",
        username="ana",
        csrf_token="csrf-old",
        expires_at=datetime(2026, 7, 18, 1, 0, 0),
    )
    fresh = AdminSession(
        token_hash="digest-new",
        username="ana",
        csrf_token="csrf-new",
        expires_at=datetime(2026, 7, 18, 23, 0, 0),
    )
    backend.save_session(stale)
    backend.save_session(fresh)
    assert backend.delete_expired_sessions(datetime(2026, 7, 18, 12, 0, 0)) == 1
    assert backend.load_session("digest-old") is None
    assert backend.load_session("digest-new") == fresh
    assert backend.delete_session("digest-new")
    assert not backend.delete_session("digest-new")


def test_revisions_append_list_load_and_prune(backend: StorageBackend) -> None:
    """ADR-0025: bounded per-entity history on every engine."""
    when = datetime(2027, 1, 1, tzinfo=UTC)
    first = backend.save_revision("article", "post", "ana", '{"v": 1}', when)
    second = backend.save_revision("article", "post", "rui", '{"v": 2}', when)
    assert (first, second) == (1, 2)
    listed = backend.list_revisions("article", "post")
    assert [(number, author) for number, _, author in listed] == [(2, "rui"), (1, "ana")]
    assert backend.load_revision("article", "post", 1) == '{"v": 1}'
    assert backend.load_revision("article", "post", 99) is None
    assert backend.list_revisions("article", "other") == []
    for extra in range(backend.REVISION_LIMIT + 3):
        backend.save_revision("article", "post", "ana", f'{{"v": {extra + 3}}}', when)
    kept = backend.list_revisions("article", "post")
    assert len(kept) == backend.REVISION_LIMIT
    assert backend.load_revision("article", "post", 1) is None  # pruned


def test_deleted_at_round_trips(backend: StorageBackend) -> None:
    """ADR-0026: the trash flag persists and clears on every engine."""
    when = datetime(2027, 2, 1, tzinfo=UTC)
    article = new_article("bin-me", ArticleContent(title="Binned"))
    article.deleted_at = when
    backend.save_article(article)
    loaded = backend.load_article("bin-me")
    assert loaded is not None and loaded.deleted_at == when
    article.deleted_at = None
    backend.save_article(article)
    restored = backend.load_article("bin-me")
    assert restored is not None and restored.deleted_at is None
    page = new_page("bin-page", PageContent(title="Binned", slug="binned"))
    page.deleted_at = when
    backend.save_page(page)
    stored = backend.load_page("bin-page")
    assert stored is not None and stored.deleted_at == when


def test_notes_append_list_and_delete(backend: StorageBackend) -> None:
    """M5: the editorial note trail works on every engine."""
    when = datetime(2027, 3, 1, tzinfo=UTC)
    first = backend.add_note("article", "post", "ana", "Needs a better title.", when)
    second = backend.add_note("article", "post", "rui", "Agreed.", when)
    assert (first, second) == (1, 2)
    notes = backend.list_notes("article", "post")
    assert [(seq, author, body) for seq, _, author, body in notes] == [
        (2, "rui", "Agreed."),
        (1, "ana", "Needs a better title."),
    ]
    assert backend.delete_note("article", "post", 1)
    assert not backend.delete_note("article", "post", 1)
    assert len(backend.list_notes("article", "post")) == 1


def test_article_custom_fields_round_trip(backend: StorageBackend) -> None:
    """ADR-0028: free-form custom fields persist on every engine."""
    article = new_article("fielded", ArticleContent(title="Fielded"))
    article.fields = {"subtitle": "A tin odyssey", "sponsor": "The canteen"}
    backend.save_article(article)
    loaded = backend.load_article("fielded")
    assert loaded is not None
    assert loaded.fields == {"sponsor": "The canteen", "subtitle": "A tin odyssey"}


def test_menu_items_round_trip_ordering_and_delete(backend: StorageBackend) -> None:
    """M6: explicit menu items persist per language and order stably."""
    backend.save_menu_item(
        MenuItem(id="docs", url="/docs/", position=2, labels={Language.EN: "Docs"})
    )
    backend.save_menu_item(
        MenuItem(
            id="home",
            url="/",
            position=1,
            labels={Language.EN: "Home", Language.PT_PT: "Início"},
        )
    )
    items = backend.load_menu_items()
    assert [item.id for item in items] == ["home", "docs"]
    assert items[0].label(Language.PT_PT) == "Início"
    assert items[0].label(Language.ES) == "Home"  # source-language fallback
    backend.save_menu_item(
        MenuItem(id="docs", url="/documentation/", position=0, labels={Language.EN: "Docs"})
    )
    assert backend.load_menu_items()[0].url == "/documentation/"  # upsert + reorder
    assert backend.delete_menu_item("home")
    assert not backend.delete_menu_item("home")


def test_user_email_round_trips(backend: StorageBackend) -> None:
    user = _user().model_copy(update={"email": "ana@example.com"})
    backend.save_user(user)
    loaded = backend.load_user("ana")
    assert loaded is not None and loaded.email == "ana@example.com"
    backend.save_user(user.model_copy(update={"email": None}))
    reloaded = backend.load_user("ana")
    assert reloaded is not None and reloaded.email is None


def test_password_reset_is_single_use_and_expires(backend: StorageBackend) -> None:
    from cms_core import PasswordReset

    backend.save_user(_user())
    reset = PasswordReset(
        token_hash="reset-1", username="ana", expires_at=datetime(2026, 7, 18, 12, 0, 0)
    )
    backend.save_password_reset(reset)
    # single use: the first pop returns it, the second finds nothing
    popped = backend.pop_password_reset("reset-1", datetime(2026, 7, 18, 11, 0, 0))
    assert popped == reset
    assert backend.pop_password_reset("reset-1", datetime(2026, 7, 18, 11, 0, 0)) is None
    # expiry: a pop after the moment removes the row and returns nothing
    backend.save_password_reset(reset)
    assert backend.pop_password_reset("reset-1", datetime(2026, 7, 18, 12, 0, 0)) is None
    # bulk removal for an account
    backend.save_password_reset(reset)
    assert backend.delete_password_resets_for("ana") == 1
    # user deletion cascades to pending resets
    backend.save_password_reset(reset)
    backend.delete_user("ana")
    assert backend.pop_password_reset("reset-1", datetime(2026, 7, 18, 11, 0, 0)) is None


def test_sessions_revoke_per_account(backend: StorageBackend) -> None:
    backend.save_user(_user())
    for index in range(2):
        backend.save_session(
            AdminSession(
                token_hash=f"digest-{index}",
                username="ana",
                csrf_token=f"csrf-{index}",
                expires_at=datetime(2026, 7, 18, 23, 0, 0),
            )
        )
    assert backend.delete_sessions_for("ana") == 2
    assert backend.load_session("digest-0") is None
    assert backend.load_session("digest-1") is None


def test_totp_state_round_trips(backend: StorageBackend) -> None:
    user = _user().model_copy(update={"totp_secret": "JBSWY3DPEHPK3PXP", "totp_step": 12345})
    backend.save_user(user)
    loaded = backend.load_user("ana")
    assert loaded is not None
    assert loaded.totp_secret == "JBSWY3DPEHPK3PXP"
    assert loaded.totp_step == 12345
    backend.save_user(user.model_copy(update={"totp_secret": None, "totp_step": None}))
    cleared = backend.load_user("ana")
    assert cleared is not None and cleared.totp_secret is None and cleared.totp_step is None


def test_search_finds_content_across_kinds(backend: StorageBackend) -> None:
    """#129: one query finds articles, pages, sections and media by any
    text — translations included — and the trash never matches."""
    from cms_core import MediaAsset
    from cms_core.models import ArticleContent, new_article

    article = new_article(
        "voyage", ArticleContent(title="The tin voyage", summary="S", body_markdown="B")
    )
    article.set_translation(Language.PT_PT, ArticleContent(title="A viagem da lata", summary="S"))
    backend.save_article(article)

    trashed = new_article(
        "gone", ArticleContent(title="Trashed voyage entry", summary="S", body_markdown="B")
    )
    trashed.deleted_at = trashed.created_at
    backend.save_article(trashed)

    page = new_page("crew", PageContent(title="The crew", slug="crew"))
    page.sections.append(
        Section(
            key="faq",
            kind="faq",
            source=SectionContent(items=[{"question": "Voyage length?", "answer": "Weeks."}]),
        )
    )
    backend.save_page(page)
    backend.save_media_asset(
        MediaAsset(
            id="voyage-cover",
            path="images/voyage.svg",
            mime_type="image/svg+xml",
            width=64,
            height=64,
            alt={Language.EN: "A tin on a voyage"},
        )
    )

    hits = backend.search_content("voyage")
    kinds = {(hit.kind, hit.id) for hit in hits}
    assert ("article", "voyage") in kinds
    assert ("section", "crew/faq") in kinds
    assert ("media", "voyage-cover") in kinds
    assert not any(hit.id == "gone" for hit in hits)
    # translated text matches too, and LIKE wildcards stay literal
    assert any(hit.id == "voyage" for hit in backend.search_content("viagem da lata"))
    assert backend.search_content("%") == []


def test_activity_records_append_filter_and_prune(backend: StorageBackend) -> None:
    """#134: append-only activity — recorded, filtered, pruned; records
    survive the deletion of what they describe."""
    from datetime import timedelta

    from cms_core.activity import ActivityRecord

    base = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
    for offset, (actor, action, kind, subject) in enumerate(
        [
            ("ana", "published", "article", "voyage"),
            ("maria", "trashed", "page", "old-promo"),
            ("ana", "signed-in", "session", "ana"),
        ]
    ):
        backend.record_activity(
            ActivityRecord(
                at=base + timedelta(minutes=offset),
                actor=actor,
                action=action,
                subject_kind=kind,
                subject_id=subject,
            )
        )

    everything = backend.list_activity()
    assert [record.action for record in everything] == ["signed-in", "trashed", "published"]
    only_ana = backend.list_activity(actor="ana")
    assert {record.actor for record in only_ana} == {"ana"}
    windowed = backend.list_activity(
        since=base + timedelta(minutes=1), until=base + timedelta(minutes=2)
    )
    assert [record.action for record in windowed] == ["trashed"]

    pruned = backend.prune_activity(before=base + timedelta(minutes=1))
    assert pruned == 1
    assert len(backend.list_activity()) == 2


def test_writes_survive_the_connection(backend_url: str) -> None:
    """A second, independent connection must see committed writes —
    the cross-connection contract every engine honors (a missing
    autocommit once made PostgreSQL keep everything in a phantom
    transaction that vanished on close)."""
    from cms_core import create_storage

    article = new_article(
        "durable", ArticleContent(title="Durable", summary="S", body_markdown="B")
    )
    with create_storage(backend_url) as writer:
        writer.save_article(article)
    with create_storage(backend_url) as reader:
        loaded = reader.load_article("durable")
        assert loaded is not None and loaded.source.title == "Durable"
        reader.delete_article("durable")


def test_form_submissions_round_trip_filter_delete_and_prune(backend: StorageBackend) -> None:
    """ADR-0039: operational fields are queryable; values are opaque;
    deletion is definitive and retention pruning works by date."""
    from cms_core import FormSubmission

    early = FormSubmission(
        id="sub-1",
        received_at=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        page_id="about",
        section_key="write-us",
        language="en",
        values={"name": "Ana", "message": "Ahoy"},
    )
    late = FormSubmission(
        id="sub-2",
        received_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
        page_id="about",
        section_key="write-us",
        language="pt-pt",
        values={"name": "Rui"},
    )
    other = FormSubmission(
        id="sub-3",
        received_at=datetime(2026, 7, 21, 10, 0, tzinfo=UTC),
        page_id="landing",
        section_key="signup",
        language="en",
        values={},
    )
    for submission in (early, late, other):
        backend.save_form_submission(submission)

    everything = backend.list_form_submissions()
    assert [s.id for s in everything] == ["sub-3", "sub-2", "sub-1"]  # newest first
    assert everything[-1].values == {"name": "Ana", "message": "Ahoy"}

    one_form = backend.list_form_submissions(page_id="about", section_key="write-us")
    assert [s.id for s in one_form] == ["sub-2", "sub-1"]
    recent = backend.list_form_submissions(since=datetime(2026, 7, 15, tzinfo=UTC))
    assert [s.id for s in recent] == ["sub-3", "sub-2"]

    assert backend.delete_form_submission("sub-2")
    assert not backend.delete_form_submission("sub-2")  # definitive
    assert backend.prune_form_submissions(datetime(2026, 7, 15, tzinfo=UTC)) == 1  # sub-1
    assert [s.id for s in backend.list_form_submissions()] == ["sub-3"]


def test_seo_round_trips_on_articles_and_pages(backend: StorageBackend) -> None:
    """ADR-0041: the per-language SEO payload survives storage on the
    source and on every translation."""
    from cms_core.translatable import Seo

    seo = Seo(
        seo_title="The launch, optimized",
        seo_description="A description for robots and cards",
        noindex=True,
        canonical="https://example.com/launch-canonical/",
        og_image="harbor-photo",
    )
    article = new_article("launch", ArticleContent(title="Launch", seo=seo))
    article.set_translation(
        Language.PT_PT, ArticleContent(title="Lancamento", seo=Seo(seo_title="Titulo PT"))
    )
    backend.save_article(article)
    loaded_article = backend.load_article("launch")
    assert loaded_article is not None
    assert loaded_article.source.seo == seo
    assert loaded_article.translations[Language.PT_PT].content.seo.seo_title == "Titulo PT"

    page = new_page("about", PageContent(title="About", slug="about", seo=seo))
    page.set_translation(
        Language.DE, PageContent(title="Uber", slug="ueber", seo=Seo(noindex=True))
    )
    backend.save_page(page)
    loaded_page = backend.load_page("about")
    assert loaded_page is not None
    assert loaded_page.source.seo == seo
    assert loaded_page.translations[Language.DE].content.seo.noindex is True
