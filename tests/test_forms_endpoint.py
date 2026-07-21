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

import pytest
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


def _storing_app(tmp_path: Path, retention_days: int = 0) -> FastAPI:
    app = _app(tmp_path)
    toml = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
    extra = "store = true\n" + (f"retention_days = {retention_days}\n" if retention_days else "")
    (tmp_path / "sardine.toml").write_text(toml + extra, encoding="utf-8")
    return app


def test_storage_is_a_consumer_of_the_accepted_submission(tmp_path: Path) -> None:
    """ADR-0039: with [forms] store the accepted values persist —
    operational fields queryable, visitor values opaque — while the
    HTTP behaviour is unchanged; spam and invalid submissions never
    reach storage."""
    with _client(_storing_app(tmp_path)) as client:
        ok = client.post("/forms/submit", data=GOOD)
        bad = client.post("/forms/submit", data={**GOOD, "field_name": ""})
        spam = client.post("/forms/submit", data={**GOOD, "website": "spam"})
    assert (ok.status_code, bad.status_code, spam.status_code) == (200, 422, 403)
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.list_form_submissions()
    assert len(stored) == 1
    assert stored[0].page_id == "contact" and stored[0].section_key == "write-us"
    assert stored[0].values["name"] == "Ana"
    assert len(SENT) == 1  # mail unaffected by storage


def test_the_submissions_screen_lists_filters_and_deletes(tmp_path: Path) -> None:
    from cms_admin.security import hash_password
    from cms_core import Role, User

    app = _storing_app(tmp_path)
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password("correct horse battery staple"),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
    with _client(app) as client:
        client.post("/forms/submit", data=GOOD)
        form = client.get("/login")
        client.post(
            "/login",
            data={
                "username": "ana",
                "password": "correct horse battery staple",
                "login_csrf": form.cookies["__Host-sardine_login_csrf"],
            },
        )
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        screen = client.get("/submissions").text
        assert "contact/write-us" in screen
        assert "Ana" in screen  # the value shows as an opaque payload
        filtered = client.get("/submissions", params={"form_id": "contact/other"}).text
        assert "contact/write-us" not in filtered
        with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
            submission_id = storage.list_form_submissions()[0].id
        response = client.post(
            f"/submissions/{submission_id}/delete",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        assert response.status_code == 303
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        assert storage.list_form_submissions() == []


def test_retention_prunes_at_startup(tmp_path: Path) -> None:
    from datetime import timedelta

    from cms_core import FormSubmission

    app = _storing_app(tmp_path, retention_days=7)
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_form_submission(
            FormSubmission(
                id="old-one",
                received_at=datetime.now(tz=UTC) - timedelta(days=30),
                page_id="contact",
                section_key="write-us",
                language="en",
                values={},
            )
        )
        storage.save_form_submission(
            FormSubmission(
                id="fresh-one",
                received_at=datetime.now(tz=UTC),
                page_id="contact",
                section_key="write-us",
                language="en",
                values={},
            )
        )
    with _client(app):
        pass  # startup runs the retention prune
    with create_storage(url) as storage:
        remaining = [s.id for s in storage.list_form_submissions()]
    assert remaining == ["fresh-one"]


def test_a_storage_failure_is_contained_and_audited(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    import cms_core.storage.sqlite as sqlite_backend
    from cms_core import FormSubmission
    from cms_core.storage.sqlite import SQLiteBackend

    def explode(self: SQLiteBackend, submission: FormSubmission) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(sqlite_backend.SQLiteBackend, "save_form_submission", explode)
    with _client(_storing_app(tmp_path)) as client:
        response = client.post("/forms/submit", data=GOOD)
    assert response.status_code == 200  # never visitor-facing
    assert len(SENT) == 1  # the mail leg still ran
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        actions = [record.action for record in storage.list_activity(limit=10)]
    assert "form-store-failed" in actions
