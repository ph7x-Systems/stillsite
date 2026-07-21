"""The official forms endpoint: deterministic states, layered spam
protection, contained notification.

Every state maps to a fixed HTTP status (200 success, 422 validation,
403 spam/origin, 429 rate limit, 404 unknown form); responses are
localized from the language packs; the notification mail is sent
through the app's configured mailer and its failure never becomes a
visitor-facing error.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.forms_endpoint import RATE_LIMIT_MAX_SUBMISSIONS
from cms_core import (
    ContentStatus,
    PageContent,
    Section,
    SectionContent,
    create_storage,
    new_page,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

NOW = datetime(2026, 7, 21, tzinfo=UTC)

SENT: list[tuple[str, str, str]] = []


class _RecordingMailer:
    def send(self, to: str, subject: str, body: str) -> None:
        SENT.append((to, subject, body))


class _BrokenMailer:
    def send(self, to: str, subject: str, body: str) -> None:
        raise RuntimeError("smtp is down")


def _app(tmp_path: Path, notify: str = "owner@example.com") -> FastAPI:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Live"\nbase_url = "https://live.example"\nlanguages = ["pt-pt"]\n'
        "\n[forms]\n"
        'endpoint = "/forms/submit"\n' + (f'notify = "{notify}"\n' if notify else ""),
        encoding="utf-8",
    )
    url = f"sqlite:///{tmp_path / 'content.db'}"
    page = new_page("contact", PageContent(title="Contact", slug="contact"), now=NOW)
    page.status = ContentStatus.PUBLISHED
    page.sections.append(
        Section(
            key="write-us",
            kind="form",
            source=SectionContent(
                fields={
                    "heading": "Write to the fleet",
                    "consent_label": "I agree to be contacted",
                    "success_heading": "Received!",
                    "success_text": "We answer within two tides.",
                },
                items=[
                    {"key": "name", "type": "text", "label": "Your name", "required": "1"},
                    {"key": "email", "type": "email", "label": "Your e-mail", "required": "1"},
                    {"key": "message", "type": "textarea", "label": "Message", "required": ""},
                ],
            ),
        )
    )
    with create_storage(url) as storage:
        storage.save_page(page)
    return create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )


def _client(app: FastAPI) -> TestClient:
    SENT.clear()
    app.state.mailer = _RecordingMailer()
    return TestClient(app, base_url="https://testserver")


GOOD = {
    "form_page": "contact",
    "form_section": "write-us",
    "form_language": "en",
    "field_name": "Ana",
    "field_email": "ana@example.com",
    "field_message": "Ahoy!",
    "consent": "1",
}


def test_a_valid_submission_notifies_and_answers_200(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.post("/forms/submit", data=GOOD)
    assert response.status_code == 200
    assert "Received!" in response.text  # the section's own success content
    assert "We answer within two tides." in response.text
    assert 'href="https://live.example' in response.text  # the way back
    assert len(SENT) == 1
    to, subject, body = SENT[0]
    assert to == "owner@example.com"
    assert "Write to the fleet" in subject
    assert "name: Ana" in body and "email: ana@example.com" in body


def test_missing_required_fields_answer_422_naming_each_label(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.post(
            "/forms/submit",
            data={**GOOD, "field_name": "", "consent": ""},
        )
    assert response.status_code == 422
    assert "Your name" in response.text
    assert "I agree to be contacted" in response.text
    assert not SENT


def test_responses_speak_the_form_language(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.post(
            "/forms/submit",
            data={**GOOD, "form_language": "pt-pt", "field_name": ""},
        )
    assert response.status_code == 422
    assert 'lang="pt-pt"' in response.text
    assert "obrigatório" in response.text  # pack label, not hardcoded text


def test_honeypot_and_fast_submissions_answer_403(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        trapped = client.post("/forms/submit", data={**GOOD, "website": "spam"})
        hurried = client.post("/forms/submit", data={**GOOD, "form_elapsed": "0.4"})
        patient = client.post("/forms/submit", data={**GOOD, "form_elapsed": "8.2"})
    assert trapped.status_code == 403
    assert hurried.status_code == 403
    assert patient.status_code == 200
    assert len(SENT) == 1  # only the patient one delivered


def test_foreign_origins_answer_403(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.post(
            "/forms/submit", data=GOOD, headers={"origin": "https://evil.example"}
        )
        same = client.post("/forms/submit", data=GOOD, headers={"origin": "https://live.example"})
    assert response.status_code == 403
    assert same.status_code == 200


def test_unknown_forms_answer_404(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        wrong_page = client.post("/forms/submit", data={**GOOD, "form_page": "nowhere"})
        wrong_kind = client.post("/forms/submit", data={**GOOD, "form_section": "hero"})
    assert wrong_page.status_code == 404
    assert wrong_kind.status_code == 404


def test_rate_limiting_answers_429(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        statuses = [
            client.post("/forms/submit", data=GOOD).status_code
            for _ in range(RATE_LIMIT_MAX_SUBMISSIONS + 1)
        ]
    assert statuses[:-1] == [200] * RATE_LIMIT_MAX_SUBMISSIONS
    assert statuses[-1] == 429


def test_a_mail_failure_is_contained_and_audited(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        app.state.mailer = _BrokenMailer()
        response = client.post("/forms/submit", data=GOOD)
    assert response.status_code == 200  # the visitor never sees the failure
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        actions = [record.action for record in storage.list_activity(limit=10)]
    assert "form-mail-failed" in actions


def test_without_notify_the_endpoint_still_validates_and_answers(tmp_path: Path) -> None:
    with _client(_app(tmp_path, notify="")) as client:
        response = client.post("/forms/submit", data=GOOD)
    assert response.status_code == 200
    assert not SENT
