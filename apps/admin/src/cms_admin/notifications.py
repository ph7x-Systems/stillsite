"""Editorial notifications (ADR-0032 phase 2): two events, explicit.

**Review requested** mails every account of role reviewer or above that
has an address, except the actor. **Published** mails the entry's most
recent editing author (the newest revision not authored by the actor),
if that account has an address. Delivery is fire-and-forget off the
request path; a transport failure is recorded, never surfaced as an
editorial error. No email configured means no notifications — and no
change in behavior anywhere.
"""

import threading
from datetime import UTC, datetime

from cms_core import ContentStatus, Role, User
from fastapi import Request

from cms_admin.auth import get_db
from cms_admin.i18n import translate_for
from cms_admin.security import admin_path
from cms_admin.workflow import allowed


def _deliver_async(request: Request, to: str, subject: str, body: str) -> None:
    mailer = request.app.state.mailer

    def run() -> None:
        try:
            mailer.send(to, subject, body)
        except Exception:
            request.app.state.last_mail_error = datetime.now(UTC).isoformat()

    threading.Thread(target=run, daemon=True).start()


def _entry_link(request: Request, section: str, entity_id: str) -> str:
    return str(request.base_url).rstrip("/") + admin_path(section, entity_id)


async def notify_transition(
    request: Request,
    *,
    section: str,
    entity_id: str,
    title: str,
    target: ContentStatus,
    actor: str,
) -> None:
    """Fan out the two ADR-0032 events after a saved status transition."""
    if request.app.state.mailer is None:
        return
    if target is ContentStatus.REVIEW:
        await _notify_reviewers(request, section, entity_id, title, actor)
    elif target is ContentStatus.PUBLISHED:
        await _notify_author(request, section, entity_id, title, actor)


async def _notify_reviewers(
    request: Request, section: str, entity_id: str, title: str, actor: str
) -> None:
    db = get_db(request)
    usernames = await db.run(lambda storage: storage.list_usernames())
    link = _entry_link(request, section, entity_id)
    async def _load(name: str) -> User | None:
        return await db.run(lambda storage: storage.load_user(name))

    for username in usernames:
        if username == actor:
            continue
        user = await _load(username)
        if user is None or not user.email or not allowed(user.role, Role.REVIEWER):
            continue
        _deliver_async(request, user.email, *_review_message(request, user, title, actor, link))


async def _notify_author(
    request: Request, section: str, entity_id: str, title: str, actor: str
) -> None:
    """The newest revision author other than the actor wrote the content
    that just went live — they are the one to tell."""
    db = get_db(request)
    entity_type = "article" if section == "articles" else "page"
    revisions = await db.run(lambda storage: storage.list_revisions(entity_type, entity_id))
    author = next((entry[2] for entry in revisions if entry[2] != actor), None)
    if author is None:
        return
    user = await db.run(lambda storage: storage.load_user(author))
    if user is None or not user.email:
        return
    link = _entry_link(request, section, entity_id)
    _deliver_async(request, user.email, *_published_message(request, user, title, actor, link))


def _review_message(
    request: Request, user: User, title: str, actor: str, link: str
) -> tuple[str, str]:
    subject = translate_for(request, user.language, "Review requested: %(title)s") % {
        "title": title
    }
    body = translate_for(
        request,
        user.language,
        "%(actor)s sent %(title)s to review. Open it in the panel:\n\n%(link)s",
    ) % {"actor": actor, "title": title, "link": link}
    return subject, body


def _published_message(
    request: Request, user: User, title: str, actor: str, link: str
) -> tuple[str, str]:
    subject = translate_for(request, user.language, "Published: %(title)s") % {"title": title}
    body = translate_for(
        request,
        user.language,
        "%(title)s was published by %(actor)s:\n\n%(link)s",
    ) % {"actor": actor, "title": title, "link": link}
    return subject, body
