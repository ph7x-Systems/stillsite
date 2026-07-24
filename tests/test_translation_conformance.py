"""The translation-provider conformance suite (ADR-0054): the fixture
providers are certified by the public checks, deliberately broken
providers are caught by name — the suite has teeth — and the glossary
travels end to end through both faces (CLI and panel) only when the
provider declares support.
"""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_cli.app import app
from cms_cli.project import load_project
from cms_core import Language, Role, TranslationState, User, create_storage
from cms_core.models import ArticleContent, new_article
from cms_core.translation_conformance import (
    TRANSLATION_CONFORMANCE_VERSION,
    conformance_checks,
)
from cms_core.translations import TranslationRequest, TranslationSuggestion
from fastapi.testclient import TestClient
from test_translation_provider_contract import RECEIVED, EchoProvider, PlainEchoProvider
from typer.testing import CliRunner

runner = CliRunner()

NOW = datetime(2026, 7, 24, tzinfo=UTC)
PASSWORD = "correct horse battery staple"


def test_the_conformance_version_is_one() -> None:
    assert TRANSLATION_CONFORMANCE_VERSION == 1


# --- Certification: the bundled fixture providers pass every check ----
# Third-party authors run exactly this against their own provider:


@pytest.mark.parametrize("provider_type", (EchoProvider, PlainEchoProvider))
@pytest.mark.parametrize(("name", "check"), conformance_checks())
def test_the_fixture_providers_are_certified(
    name: str, check: Callable[[EchoProvider], None], provider_type: type[EchoProvider]
) -> None:
    check(provider_type())


# --- The suite has teeth: each defect is caught by its named check ----


class ReversedEcho(EchoProvider):
    """Answers out of order — batch correlation broken."""

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        return tuple(reversed(super().suggest(requests)))


class PlaceholderLosingEcho(EchoProvider):
    """Translates a template placeholder away."""

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        return tuple(
            TranslationSuggestion(
                target_text=s.target_text.replace("{name}", "name"),
                source_text=s.source_text,
            )
            for s in super().suggest(requests)
        )


class OverconfidentEcho(EchoProvider):
    """Silently answers languages it never declared."""

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        return tuple(
            TranslationSuggestion(
                target_text=f"[{req.target_language}] {req.source_text}",
                source_text=req.source_text,
            )
            for req in requests
        )


class GlossaryIgnoringEcho(EchoProvider):
    """Claims glossary support and ignores the required terms."""

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        stripped = [
            TranslationRequest(
                source_text=req.source_text,
                source_language=req.source_language,
                target_language=req.target_language,
                context=req.context,
            )
            for req in requests
        ]
        return super().suggest(stripped)


@pytest.mark.parametrize(
    ("check_name", "provider_type"),
    (
        ("batch-order-preserved", ReversedEcho),
        ("placeholders-preserved", PlaceholderLosingEcho),
        ("undeclared-language-fails-structurally", OverconfidentEcho),
        ("glossary-honored", GlossaryIgnoringEcho),
    ),
)
def test_the_suite_catches_each_defect_by_name(
    check_name: str, provider_type: type[EchoProvider]
) -> None:
    checks = dict(conformance_checks())
    with pytest.raises(AssertionError):
        checks[check_name](provider_type())


# --- The glossary: parsed deterministically, gated on capability ------

GLOSSARY_TOML = """
extensions = ["test_translation_provider_contract:extension"]

[site]
name = "Aurora Cartography"
base_url = "https://example.com"
languages = ["pt-pt", "de", "it"]

[translations]
provider = "echo"

[translations.glossary.de]
tide = "Gezeiten"
lighthouse = "Leuchtturm"

[translations.glossary.pt-pt]
lighthouse = "farol"

[storage]
url = "sqlite:///content.sqlite3"

[build]
output = "_site"
"""


def _seed_article(tmp_path: Path) -> str:
    (tmp_path / "sardine.toml").write_text(GLOSSARY_TOML, encoding="utf-8")
    article = new_article(
        "tides",
        ArticleContent(
            title="Tides",
            summary="S",
            body_markdown="The lighthouse stands against the tide.",
        ),
        now=NOW,
    )
    with create_storage(f"sqlite:///{tmp_path / 'content.sqlite3'}") as storage:
        storage.save_article(article)
    return article.id


def test_the_glossary_parses_ordered_by_source_term(tmp_path: Path) -> None:
    _seed_article(tmp_path)
    project = load_project(tmp_path)
    assert project.glossary_for("de") == (("lighthouse", "Leuchtturm"), ("tide", "Gezeiten"))
    assert project.glossary_for("pt-pt") == (("lighthouse", "farol"),)
    assert project.glossary_for("fr") == ()


def test_cms_translate_sends_the_glossary_and_lands_a_draft(tmp_path: Path) -> None:
    _seed_article(tmp_path)
    RECEIVED.clear()
    result = runner.invoke(app, ["translate", "--language", "de", "-p", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "suggested 1" in result.output
    assert RECEIVED[-1].glossary == (("lighthouse", "Leuchtturm"), ("tide", "Gezeiten"))
    with create_storage(f"sqlite:///{tmp_path / 'content.sqlite3'}") as storage:
        stored = storage.load_all_articles()[0]
    body = stored.translations[Language.DE].content.body_markdown
    assert body == "[de] The Leuchtturm stands against the Gezeiten."


def test_the_glossary_is_gated_on_the_declared_capability(tmp_path: Path) -> None:
    _seed_article(tmp_path)
    toml = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
    (tmp_path / "sardine.toml").write_text(
        toml.replace('provider = "echo"', 'provider = "echo-plain"'), encoding="utf-8"
    )
    RECEIVED.clear()
    result = runner.invoke(app, ["translate", "--language", "de", "-p", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert RECEIVED[-1].glossary == ()


def test_a_structured_failure_reaches_the_operator_classified(tmp_path: Path) -> None:
    _seed_article(tmp_path)
    result = runner.invoke(app, ["translate", "--language", "it", "-p", str(tmp_path)])
    assert result.exit_code == 1
    assert "unsupported-language" in result.output


# --- The panel face: Suggest prefills with the glossary applied -------


def test_the_panel_suggest_prefills_with_the_glossary_applied(tmp_path: Path) -> None:
    article_id = _seed_article(tmp_path)
    url = f"sqlite:///{tmp_path / 'content.sqlite3'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
    admin = create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )
    with TestClient(admin, base_url="https://testserver") as client:
        form = client.get("/login")
        client.post(
            "/login",
            data={
                "username": "ana",
                "password": PASSWORD,
                "login_csrf": form.cookies["__Host-sardine_login_csrf"],
            },
        )
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]

        RECEIVED.clear()
        done = client.post(
            f"/articles/{article_id}/translations/pt-pt/suggest",
            data={"csrf_token": csrf},
        )
        assert done.status_code == 200
        assert "[pt-pt] The farol stands against the tide." in done.text
        assert RECEIVED[-1].glossary == (("lighthouse", "farol"),)

    # A suggestion prefills the form; nothing persists until the editor
    # saves — editorial sovereignty (ADR-0054).
    with create_storage(url) as storage:
        stored = storage.load_all_articles()[0]
    assert stored.translation_state(Language.PT_PT) is TranslationState.MISSING
