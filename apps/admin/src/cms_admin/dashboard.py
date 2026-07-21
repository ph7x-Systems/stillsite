"""Dashboard: the editorial state of the site at a glance.

Aggregates what storage holds — content by workflow status, the translation
coverage matrix — and runs the default validation ruleset live, so the
numbers on screen are always derived from the same public APIs the CLI and
the publish gate use (ADR-0006). Build/export records appear once the panel
can trigger builds (phase 8); until then the dashboard shows an empty state.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from cms_core import (
    TARGET_LANGUAGES,
    AdminSession,
    Article,
    ContentStatus,
    Language,
    Page,
    Role,
    StorageBackend,
    TranslationState,
    User,
)
from cms_validation import SiteContent
from fastapi import APIRouter, Depends, Request

from cms_admin.auth import current_session
from cms_admin.publishing import _project, _site_source, _site_targets
from cms_admin.validation_report import report_context
from cms_admin.workflow import allowed

router = APIRouter()


def status_counts(entries: Sequence[Article | Page]) -> dict[ContentStatus, int]:
    counts = dict.fromkeys(ContentStatus, 0)
    for entry in entries:
        counts[entry.status] += 1
    return counts


def translation_matrix(
    entries: Sequence[Article | Page],
    languages: tuple[Language, ...] = TARGET_LANGUAGES,
    source: Language | None = None,
) -> dict[Language, dict[TranslationState, int]]:
    matrix = {language: dict.fromkeys(TranslationState, 0) for language in languages}
    for entry in entries:
        for language, state in entry.translation_states(languages, source=source).items():
            matrix[language][state] += 1
    return matrix


def coverage_percent(cells: dict[TranslationState, int]) -> int:
    total = sum(cells.values())
    if total == 0:
        return 100
    return round(100 * cells[TranslationState.COMPLETE] / total)


def _load_content(storage: StorageBackend) -> SiteContent:
    return SiteContent(
        articles=[a for a in storage.load_all_articles() if a.deleted_at is None],
        pages=[p for p in storage.load_all_pages() if p.deleted_at is None],
        media=storage.load_all_media_assets(),
        menu=storage.load_menu_items(),
    )


@router.get("/")
async def dashboard(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    content: SiteContent = await request.app.state.db.run(_load_content)
    entries: list[Article | Page] = [*content.articles, *content.pages]
    project = _project(request)
    targets = _site_targets(project)
    source = _site_source(project)
    matrix = translation_matrix(entries, targets, source)
    now = datetime.now(tz=UTC)
    week_ahead = now + timedelta(days=7)
    stale_cutoff = now - timedelta(days=30)
    # The needs-attention cards (#135): work, not totals — every number
    # links to where it gets done, and zero renders a real empty state.
    attention = {
        "in_review": sum(1 for entry in entries if entry.status is ContentStatus.REVIEW),
        "can_publish": allowed(user.role, Role.PUBLISHER),
        "pending_translations": sum(
            1
            for entry in entries
            for language in targets
            if entry.translation_state(language, source=source) is not TranslationState.COMPLETE
        ),
        "upcoming": sum(
            1
            for entry in entries
            for moment in (entry.publish_at, entry.unpublish_at)
            if moment is not None and now < moment <= week_ahead
        ),
        "stale_drafts": sum(
            1
            for entry in entries
            if entry.status is ContentStatus.DRAFT and entry.updated_at < stale_cutoff
        ),
    }
    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "dashboard",
            "counts": status_counts(entries),
            "statuses": list(ContentStatus),
            "states": list(TranslationState),
            "matrix": matrix,
            "coverage": {language: coverage_percent(cells) for language, cells in matrix.items()},
            "totals": {
                "articles": len(content.articles),
                "pages": len(content.pages),
                "media": len(content.media),
            },
            **report_context(
                content, _site_targets(project), source_language=_site_source(project)
            ),
            "attention": attention,
            "last_build": getattr(request.app.state, "last_build", None),
        },
    )
