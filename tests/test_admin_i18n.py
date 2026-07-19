"""Admin i18n (ADR-0022): resolution order, rendering, catalog anti-drift.

The anti-drift part mirrors the docs suite's philosophy: every msgid a
template or route can ask for must exist, translated, in every shipped
catalog — completeness is enforced, not hoped for.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

from babel.messages.pofile import read_po
from cms_admin import AdminSettings, create_app
from cms_admin.i18n import LOCALES, RUNTIME_MSGIDS, negotiate
from cms_admin.security import hash_password
from cms_admin.workflow import LABELS
from cms_core import Language, Role, User, create_storage
from cms_validation import default_ruleset
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 19, tzinfo=UTC)

ADMIN_DIR = Path("apps/admin/src/cms_admin")
TEMPLATES = ADMIN_DIR / "templates"
LOCALE_DIR = ADMIN_DIR / "locale"

_CALL = re.compile(r"""(?<![a-zA-Z_])_\(\s*"((?:[^"\\]|\\.)*)"\s*[\),]""")
_CALL_SQ = re.compile(r"""(?<![a-zA-Z_])_\(\s*'((?:[^'\\]|\\.)*)'\s*[\),]""")
_PLURAL = re.compile(r'''ngettext\(\s*"([^"]+)"\s*,\s*"([^"]+)"''')


def _extracted() -> tuple[set[str], set[tuple[str, str]]]:
    singular: set[str] = set(RUNTIME_MSGIDS)
    plural: set[tuple[str, str]] = set()
    for template in TEMPLATES.glob("*.j2"):
        text = template.read_text(encoding="utf-8")
        singular.update(match.group(1) for match in _CALL.finditer(text))
        singular.update(match.group(1) for match in _CALL_SQ.finditer(text))
        plural.update((m.group(1), m.group(2)) for m in _PLURAL.finditer(text))
    singular.update(LABELS.values())
    singular.update(rule.description for rule in default_ruleset())
    return singular, plural


def test_every_msgid_is_translated_in_every_catalog() -> None:
    singular, plural = _extracted()
    assert singular, "extraction found nothing — the scan is broken"
    for locale in LOCALES.values():
        po_path = LOCALE_DIR / locale / "LC_MESSAGES" / "messages.po"
        with po_path.open("rb") as handle:
            catalog = read_po(handle, locale=locale)
        by_id = {message.id: message for message in catalog if message.id}
        for msgid in sorted(singular):
            message = by_id.get(msgid)
            assert message is not None, f"{locale}: missing msgid {msgid!r}"
            assert message.string, f"{locale}: empty msgstr for {msgid!r}"
        for pair in sorted(plural):
            message = by_id.get(pair)
            assert message is not None, f"{locale}: missing plural {pair!r}"
            forms = message.string if isinstance(message.string, tuple) else (message.string,)
            assert all(forms), f"{locale}: incomplete plural {pair!r}"


def _app(tmp_path: Path, language: Language | None = None) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
                language=language,
            )
        )
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _sign_in(client: TestClient) -> None:
    page = client.get("/login")
    csrf = page.text.split('name="login_csrf" value="')[1].split('"')[0]
    client.post("/login", data={"username": "ana", "password": PASSWORD, "login_csrf": csrf})


def test_accept_language_localizes_the_panel(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/", headers={"Accept-Language": "pt-PT,pt;q=0.9,en;q=0.5"}).text
    assert "Painel" in page
    assert "Publicação aberta" in page
    assert "Publish gate open" not in page
    assert "Terminar sessão" in page


def test_stored_preference_beats_the_browser(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, language=Language.FR), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/", headers={"Accept-Language": "de-DE,de;q=0.9"}).text
    assert "Tableau de bord" in page
    assert "Übersicht" not in page


def test_login_page_follows_the_browser(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        page = client.get("/login", headers={"Accept-Language": "es"}).text
    assert "Iniciar sesión" in page


def test_language_switcher_stores_the_preference(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        response = client.post(
            "/profile/language",
            data={"csrf_token": csrf, "language": "de"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        page = client.get("/").text
    assert "Übersicht" in page  # the stored preference now wins with no header


def test_negotiate_resolution() -> None:
    assert negotiate(None) is Language.EN
    assert negotiate("pt-PT,pt;q=0.9") is Language.PT_PT
    assert negotiate("pt") is Language.PT_PT  # primary-tag fallback
    assert negotiate("fr-CA") is Language.FR
    assert negotiate("ja,en;q=0.1") is Language.EN
