"""Authentication and access control (SECURITY_STRATEGY, admin section).

Server-side sessions in the storage database (revocable, engine-agnostic),
session cookie ``HttpOnly`` + ``SameSite=Strict`` (+ ``Secure`` outside
local development), synchronizer CSRF tokens on authenticated state-changing
requests, a double-submit token on the login form itself, and per-process
rate limiting on failed logins.
"""

import asyncio
import secrets
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from cms_core import Language
from cms_core.accounts import AdminSession, Role, User
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.db import StorageExecutor
from cms_admin.security import (
    MAX_PASSWORD_LENGTH,
    dummy_password_hash,
    hash_password,
    new_token,
    password_needs_rehash,
    token_digest,
    verify_password,
)

SESSION_COOKIE = "__Host-sardine_session"
LOGIN_CSRF_COOKIE = "__Host-sardine_login_csrf"
LOCAL_SESSION_COOKIE = "sardine_session"
LOCAL_LOGIN_CSRF_COOKIE = "sardine_login_csrf"
LOGIN_CSRF_TTL_SECONDS = 600

# Least-privilege ladder (cms_core.accounts.Role docstring).
ROLE_ORDER = (Role.EDITOR, Role.REVIEWER, Role.PUBLISHER, Role.ADMIN)

router = APIRouter()


def session_cookie_name(request: Request) -> str:
    return SESSION_COOKIE if request.app.state.settings.cookie_secure else LOCAL_SESSION_COOKIE


def login_csrf_cookie_name(request: Request) -> str:
    return (
        LOGIN_CSRF_COOKIE if request.app.state.settings.cookie_secure else LOCAL_LOGIN_CSRF_COOKIE
    )


@dataclass
class LoginRateLimiter:
    """Bounded per-process limiter for both client and account keys."""

    max_failures: int = 5
    max_keys: int = 10_000
    window: timedelta = timedelta(minutes=15)
    _failures: OrderedDict[str, list[datetime]] = field(default_factory=OrderedDict)

    def is_blocked(self, key: str, now: datetime) -> bool:
        recent = [moment for moment in self._failures.get(key, []) if now - moment < self.window]
        if recent:
            self._failures[key] = recent
            self._failures.move_to_end(key)
        else:
            self._failures.pop(key, None)
        return len(recent) >= self.max_failures

    def record_failure(self, key: str, now: datetime) -> None:
        if key not in self._failures and len(self._failures) >= self.max_keys:
            self._failures.popitem(last=False)
        self._failures.setdefault(key, []).append(now)
        self._failures.move_to_end(key)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


def get_db(request: Request) -> StorageExecutor:
    db: StorageExecutor = request.app.state.db
    return db


def _login_redirect() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"}, detail="sign in"
    )


async def current_session(request: Request) -> tuple[User, AdminSession]:
    token = request.cookies.get(session_cookie_name(request))
    if not token:
        raise _login_redirect()
    digest = token_digest(token)
    now = datetime.now(UTC)
    db = get_db(request)
    session = await db.run(lambda storage: storage.load_session(digest))
    if session is None or session.expires_at <= now:
        raise _login_redirect()
    user = await db.run(lambda storage: storage.load_user(session.username))
    if user is None:
        raise _login_redirect()
    # ADR-0022: the stored preference wins the language resolution; the
    # i18n context processor reads it from request.state at render time.
    request.state.language = user.language
    # ADR-0035 amendment: a policy-covered account without two-factor is
    # corralled to the enrolment page — signed in, but nowhere else.
    if _two_factor_pending(user, request) and not request.url.path.startswith("/profile/2fa"):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/profile/2fa"}
        )
    return user, session


def _two_factor_pending(user: User, request: Request) -> bool:
    minimum: Role | None = request.app.state.settings.require_2fa_role
    if minimum is None or user.totp_secret is not None:
        return False
    return allowed_role(user.role, minimum)


def allowed_role(role: Role, minimum: Role) -> bool:
    return ROLE_ORDER.index(role) >= ROLE_ORDER.index(minimum)


def require_at_least(minimum: Role) -> Callable[..., Awaitable[User]]:
    async def dependency(
        user_session: tuple[User, AdminSession] = Depends(current_session),
    ) -> User:
        user, _ = user_session
        if ROLE_ORDER.index(user.role) < ROLE_ORDER.index(minimum):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return dependency


async def enforce_csrf(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> tuple[User, AdminSession]:
    form = await request.form()
    token = form.get("csrf_token")
    _, session = user_session
    if not isinstance(token, str) or not secrets.compare_digest(token, session.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    return user_session


def _client_key(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    return f"client:{host}"


def _account_key(username: str) -> str:
    return f"account:{username.strip().lower()}"


@router.get("/login")
async def login_form(request: Request) -> object:
    csrf = new_token()
    response = request.app.state.templates.TemplateResponse(
        request,
        "login.html.j2",
        {"error": None, "login_csrf": csrf, "reset_enabled": _reset_enabled(request)},
    )
    response.set_cookie(
        login_csrf_cookie_name(request),
        csrf,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.cookie_secure,
        max_age=LOGIN_CSRF_TTL_SECONDS,
        path="/",
    )
    return response


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    login_csrf: str = Form(...),
    totp: str = Form(""),
) -> object:
    settings = request.app.state.settings
    login_cookie = request.cookies.get(login_csrf_cookie_name(request))
    if not login_cookie or not secrets.compare_digest(login_cookie, login_csrf):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    now = datetime.now(UTC)
    limiter: LoginRateLimiter = request.app.state.login_limiter
    client_key = _client_key(request)
    if len(username) > 64 or len(password) > MAX_PASSWORD_LENGTH:
        limiter.record_failure(client_key, now)
        response = request.app.state.templates.TemplateResponse(
            request,
            "login.html.j2",
            {
                "error": "Wrong username or password.",
                "login_csrf": login_csrf,
                "reset_enabled": _reset_enabled(request),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        return response
    account_key = _account_key(username)
    if limiter.is_blocked(client_key, now) or limiter.is_blocked(account_key, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many failed attempts; try again later",
        )
    db = get_db(request)
    user = await db.run(lambda storage: storage.load_user(username))
    candidate_hash = user.password_hash if user is not None else dummy_password_hash()
    password_slots: asyncio.Semaphore = request.app.state.password_slots
    if password_slots.locked():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many concurrent sign-in attempts; try again later",
        )
    async with password_slots:
        password_valid = await asyncio.to_thread(verify_password, candidate_hash, password)
    if user is None or not password_valid:
        limiter.record_failure(client_key, now)
        limiter.record_failure(account_key, now)
        response = request.app.state.templates.TemplateResponse(
            request,
            "login.html.j2",
            {
                "error": "Wrong username or password.",
                "login_csrf": login_csrf,
                "reset_enabled": _reset_enabled(request),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        return response
    # ADR-0035: valid credentials alone never create a session when the
    # account carries a second factor. Wrong or replayed codes spend the
    # same rate-limit budget as wrong passwords.
    if user.totp_secret is not None:
        from cms_admin.totp import verify as verify_totp

        accepted = (
            verify_totp(user.totp_secret, totp.strip(), now, user.totp_step)
            if totp.strip()
            else None
        )
        if accepted is None:
            limiter.record_failure(client_key, now)
            limiter.record_failure(account_key, now)
            if totp.strip():
                error = "Wrong authentication code."
            else:
                error = "Authentication code required."
            return request.app.state.templates.TemplateResponse(
                request,
                "login.html.j2",
                {
                    "error": error,
                    "login_csrf": login_csrf,
                    "reset_enabled": _reset_enabled(request),
                    "totp_required": True,
                    "username_value": username,
                },
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        confirmed = user.model_copy(update={"totp_step": accepted})
        user = confirmed
        await db.run(lambda storage: storage.save_user(confirmed))
    # A valid account clears its own failures, but not the client-wide
    # history: otherwise any known low-privilege account could reset the
    # limiter between guesses against a privileged account.
    limiter.reset(account_key)
    if password_needs_rehash(user.password_hash):
        updated_hash = await asyncio.to_thread(hash_password, password)
        user = user.model_copy(update={"password_hash": updated_hash})
        await db.run(lambda storage: storage.save_user(user))
    token = new_token()
    session = AdminSession(
        token_hash=token_digest(token),
        username=user.username,
        csrf_token=new_token(),
        expires_at=now + settings.session_ttl,
    )
    await db.run(lambda storage: storage.save_session(session))
    await db.run(lambda storage: storage.delete_expired_sessions(now))
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        session_cookie_name(request),
        token,
        max_age=int(settings.session_ttl.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/",
    )
    response.delete_cookie(
        login_csrf_cookie_name(request),
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return response


@router.post("/profile/language")
async def set_language(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    language: str = Form(""),
) -> RedirectResponse:
    """Store the signed-in user's admin-language preference (ADR-0022)."""
    user, _ = user_session
    preference: Language | None = None
    if language:
        try:
            preference = Language(language)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="unknown language"
            ) from error
    updated = user.model_copy(update={"language": preference})
    await get_db(request).run(lambda storage: storage.save_user(updated))
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    _, session = user_session
    await get_db(request).run(lambda storage: storage.delete_session(session.token_hash))
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        session_cookie_name(request),
        path="/",
        secure=request.app.state.settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return response


# Password reset (ADR-0032): enumeration-safe, single-use, revoking.

RESET_TTL = timedelta(minutes=30)


def _reset_enabled(request: Request) -> bool:
    return request.app.state.mailer is not None


def _reset_email_body(request: Request, user: User, link: str) -> tuple[str, str]:
    from cms_admin.i18n import translate_for

    subject = translate_for(request, user.language, "Reset your Sardine CMS admin password")
    body = translate_for(
        request,
        user.language,
        "Someone asked to reset the password for %(username)s. If it was "
        "you, open this link within 30 minutes:\n\n%(link)s\n\nIf it was "
        "not you, ignore this message — nothing changed.",
    ) % {"username": user.username, "link": link}
    return subject, body


def _send_in_background(request: Request, to: str, subject: str, body: str) -> None:
    """Fire-and-forget delivery: the response never waits for SMTP and a
    provider failure never becomes a page error (ADR-0032)."""
    import threading

    mailer = request.app.state.mailer

    def run() -> None:
        try:
            mailer.send(to, subject, body)
        except Exception:
            request.app.state.last_mail_error = datetime.now(UTC).isoformat()

    threading.Thread(target=run, daemon=True).start()


@router.get("/reset")
async def reset_request_form(request: Request) -> object:
    if not _reset_enabled(request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    csrf = new_token()
    response = request.app.state.templates.TemplateResponse(
        request, "reset_request.html.j2", {"sent": False, "login_csrf": csrf}
    )
    response.set_cookie(
        login_csrf_cookie_name(request),
        csrf,
        max_age=LOGIN_CSRF_TTL_SECONDS,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.cookie_secure,
        path="/",
    )
    return response


@router.post("/reset")
async def reset_request_submit(
    request: Request,
    username: str = Form(""),
    login_csrf: str = Form(...),
) -> object:
    if not _reset_enabled(request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    login_cookie = request.cookies.get(login_csrf_cookie_name(request))
    if not login_cookie or not secrets.compare_digest(login_cookie, login_csrf):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    now = datetime.now(UTC)
    limiter: LoginRateLimiter = request.app.state.login_limiter
    client_key = _client_key(request)
    if limiter.is_blocked(client_key, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many attempts; try again later",
        )
    # Every request spends one attempt: reset requests share the login
    # budget, so the endpoint cannot be used to probe accounts at volume.
    limiter.record_failure(client_key, now)
    db = get_db(request)
    if len(username) <= 64:
        user = await db.run(lambda storage: storage.load_user(username))
        if user is not None and user.email:
            token = new_token()
            from cms_core import PasswordReset

            reset = PasswordReset(
                token_hash=token_digest(token),
                username=user.username,
                expires_at=now + RESET_TTL,
            )
            await db.run(lambda storage: storage.save_password_reset(reset))
            link = str(request.url_for("reset_form", token=token))
            subject, body = _reset_email_body(request, user, link)
            _send_in_background(request, user.email, subject, body)
    # One response for every outcome: existing or unknown account, with
    # or without an address — nothing to enumerate.
    return request.app.state.templates.TemplateResponse(
        request, "reset_request.html.j2", {"sent": True, "login_csrf": login_csrf}
    )


@router.get("/reset/{token}")
async def reset_form(request: Request, token: str) -> object:
    if not _reset_enabled(request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    csrf = new_token()
    response = request.app.state.templates.TemplateResponse(
        request, "reset_form.html.j2", {"token": token, "error": None, "login_csrf": csrf}
    )
    response.set_cookie(
        login_csrf_cookie_name(request),
        csrf,
        max_age=LOGIN_CSRF_TTL_SECONDS,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.cookie_secure,
        path="/",
    )
    return response


@router.post("/reset/{token}")
async def reset_submit(
    request: Request,
    token: str,
    password: str = Form(""),
    password_repeat: str = Form(""),
    login_csrf: str = Form(...),
) -> object:
    if not _reset_enabled(request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    login_cookie = request.cookies.get(login_csrf_cookie_name(request))
    if not login_cookie or not secrets.compare_digest(login_cookie, login_csrf):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    now = datetime.now(UTC)

    def failed(error: str) -> object:
        return request.app.state.templates.TemplateResponse(
            request,
            "reset_form.html.j2",
            {"token": token, "error": error, "login_csrf": login_csrf},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    from cms_admin.security import MIN_PASSWORD_LENGTH

    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        return failed("The password needs at least 12 characters.")
    if password != password_repeat:
        return failed("The two passwords do not match.")
    db = get_db(request)
    digest = token_digest(token)
    reset = await db.run(lambda storage: storage.pop_password_reset(digest, now))
    if reset is None:
        return failed("This reset link is no longer valid — request a new one.")
    user = await db.run(lambda storage: storage.load_user(reset.username))
    if user is None:
        return failed("This reset link is no longer valid — request a new one.")
    new_hash = await asyncio.to_thread(hash_password, password)
    updated = user.model_copy(update={"password_hash": new_hash})

    def apply(storage: object) -> None:
        storage.save_user(updated)  # type: ignore[attr-defined]
        storage.delete_sessions_for(updated.username)  # type: ignore[attr-defined]
        storage.delete_password_resets_for(updated.username)  # type: ignore[attr-defined]

    await db.run(apply)
    return request.app.state.templates.TemplateResponse(
        request, "reset_done.html.j2", {"login_csrf": login_csrf}
    )


# Two-factor authentication (ADR-0035): self-service, confirmed by code.


@router.get("/profile/2fa")
async def two_factor_page(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    from cms_admin.totp import generate_secret, provisioning_uri

    user, session = user_session
    context: dict[str, object] = {
        "user": user,
        "csrf_token": session.csrf_token,
        "enabled": user.totp_secret is not None,
        "forced": _two_factor_pending(user, request),
        "covered": _policy_covers(user, request),
        "error": None,
    }
    if user.totp_secret is None:
        secret = generate_secret()
        context["secret"] = secret
        context["uri"] = provisioning_uri(secret, user.username)
    return request.app.state.templates.TemplateResponse(request, "two_factor.html.j2", context)


@router.post("/profile/2fa/enable")
async def two_factor_enable(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    secret: str = Form(""),
    code: str = Form(""),
) -> object:
    from cms_admin.totp import provisioning_uri
    from cms_admin.totp import verify as verify_totp

    user, session = user_session
    now = datetime.now(UTC)
    accepted = verify_totp(secret, code.strip(), now, None) if secret and code.strip() else None
    if accepted is None:
        return request.app.state.templates.TemplateResponse(
            request,
            "two_factor.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "enabled": False,
                "error": "Wrong authentication code.",
                "secret": secret,
                "uri": provisioning_uri(secret, user.username) if secret else "",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    updated = user.model_copy(update={"totp_secret": secret, "totp_step": accepted})
    await get_db(request).run(lambda storage: storage.save_user(updated))
    return RedirectResponse("/profile/2fa", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/profile/2fa/disable")
async def two_factor_disable(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    code: str = Form(""),
) -> object:
    from cms_admin.totp import verify as verify_totp

    user, session = user_session
    if _policy_covers(user, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="two-factor authentication is required for this role",
        )
    now = datetime.now(UTC)
    accepted = (
        verify_totp(user.totp_secret, code.strip(), now, user.totp_step)
        if user.totp_secret and code.strip()
        else None
    )
    if accepted is None:
        return request.app.state.templates.TemplateResponse(
            request,
            "two_factor.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "enabled": True,
                "covered": False,
                "error": "Wrong authentication code.",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    updated = user.model_copy(update={"totp_secret": None, "totp_step": None})
    await get_db(request).run(lambda storage: storage.save_user(updated))
    return RedirectResponse("/profile/2fa", status_code=status.HTTP_303_SEE_OTHER)


def _policy_covers(user: User, request: Request) -> bool:
    minimum: Role | None = request.app.state.settings.require_2fa_role
    return minimum is not None and allowed_role(user.role, minimum)
