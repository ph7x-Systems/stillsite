"""Authentication and access control (SECURITY_STRATEGY, admin section).

Server-side sessions in the storage database (revocable, engine-agnostic),
session cookie ``HttpOnly`` + ``SameSite=Strict`` (+ ``Secure`` outside
local development), synchronizer CSRF tokens on authenticated state-changing
requests, a double-submit token on the login form itself, and per-process
rate limiting on failed logins.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from cms_core.accounts import AdminSession, Role, User
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.db import StorageExecutor
from cms_admin.security import new_token, token_digest, verify_password

SESSION_COOKIE = "sardine_session"
LOGIN_CSRF_COOKIE = "sardine_login_csrf"

# Least-privilege ladder (cms_core.accounts.Role docstring).
ROLE_ORDER = (Role.EDITOR, Role.REVIEWER, Role.PUBLISHER, Role.ADMIN)

router = APIRouter()


@dataclass
class LoginRateLimiter:
    """Per-process failed-login limiter, keyed by username and client host."""

    max_failures: int = 5
    window: timedelta = timedelta(minutes=15)
    _failures: dict[str, list[datetime]] = field(default_factory=dict)

    def is_blocked(self, key: str, now: datetime) -> bool:
        recent = [moment for moment in self._failures.get(key, []) if now - moment < self.window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return len(recent) >= self.max_failures

    def record_failure(self, key: str, now: datetime) -> None:
        self._failures.setdefault(key, []).append(now)

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
    token = request.cookies.get(SESSION_COOKIE)
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
    return user, session


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
    if not isinstance(token, str) or token != session.csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    return user_session


def _client_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{username.lower()}|{host}"


@router.get("/login")
async def login_form(request: Request) -> object:
    csrf = new_token()
    response = request.app.state.templates.TemplateResponse(
        request, "login.html.j2", {"error": None, "login_csrf": csrf}
    )
    response.set_cookie(
        LOGIN_CSRF_COOKIE,
        csrf,
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.cookie_secure,
    )
    return response


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    login_csrf: str = Form(...),
) -> object:
    settings = request.app.state.settings
    if request.cookies.get(LOGIN_CSRF_COOKIE) != login_csrf:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    now = datetime.now(UTC)
    limiter: LoginRateLimiter = request.app.state.login_limiter
    key = _client_key(request, username)
    if limiter.is_blocked(key, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many failed attempts; try again later",
        )
    db = get_db(request)
    user = await db.run(lambda storage: storage.load_user(username))
    if user is None or not verify_password(user.password_hash, password):
        limiter.record_failure(key, now)
        response = request.app.state.templates.TemplateResponse(
            request,
            "login.html.j2",
            {"error": "Wrong username or password.", "login_csrf": login_csrf},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        return response
    limiter.reset(key)
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
        SESSION_COOKIE,
        token,
        max_age=int(settings.session_ttl.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )
    response.delete_cookie(LOGIN_CSRF_COOKIE)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    _, session = user_session
    await get_db(request).run(lambda storage: storage.delete_session(session.token_hash))
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response
