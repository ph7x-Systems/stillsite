"""The editorial workflow: role-gated status transitions and the publish gate.

`draft → review → published → archived` with each transition owned by a
rung of the role ladder, enforced server-side. Publishing runs the
validation ruleset over the would-be state and blocks on errors for the
entity being published (configurable via the publish-gate setting) — the
same rules the CLI and the builder apply, through the same public API.
"""

from cms_core import Article, ContentStatus, Page, Role
from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from cms_validation import RuleSet, SiteContent, ValidationContext, default_ruleset

from cms_admin.auth import ROLE_ORDER

# (from, to) -> minimum role. The ladder: editor < reviewer < publisher < admin.
TRANSITIONS: dict[tuple[ContentStatus, ContentStatus], Role] = {
    (ContentStatus.DRAFT, ContentStatus.REVIEW): Role.EDITOR,
    (ContentStatus.REVIEW, ContentStatus.DRAFT): Role.REVIEWER,
    (ContentStatus.REVIEW, ContentStatus.PUBLISHED): Role.PUBLISHER,
    (ContentStatus.PUBLISHED, ContentStatus.DRAFT): Role.PUBLISHER,
    (ContentStatus.PUBLISHED, ContentStatus.ARCHIVED): Role.PUBLISHER,
    (ContentStatus.ARCHIVED, ContentStatus.DRAFT): Role.PUBLISHER,
}

LABELS: dict[tuple[ContentStatus, ContentStatus], str] = {
    (ContentStatus.DRAFT, ContentStatus.REVIEW): "Submit for review",
    (ContentStatus.REVIEW, ContentStatus.DRAFT): "Send back to draft",
    (ContentStatus.REVIEW, ContentStatus.PUBLISHED): "Publish",
    (ContentStatus.PUBLISHED, ContentStatus.DRAFT): "Unpublish",
    (ContentStatus.PUBLISHED, ContentStatus.ARCHIVED): "Archive",
    (ContentStatus.ARCHIVED, ContentStatus.DRAFT): "Restore to draft",
}


def allowed(role: Role, minimum: Role) -> bool:
    return ROLE_ORDER.index(role) >= ROLE_ORDER.index(minimum)


def available_transitions(status: ContentStatus, role: Role) -> list[dict[str, str]]:
    """The transitions this role may take from this status, for the UI."""
    return [
        {"to": target.value, "label": LABELS[(source, target)]}
        for (source, target), minimum in TRANSITIONS.items()
        if source is status and allowed(role, minimum)
    ]


def transition_minimum(source: ContentStatus, target: ContentStatus) -> Role | None:
    return TRANSITIONS.get((source, target))


def publish_blockers(
    entity: Article | Page,
    content: SiteContent,
    *,
    required_languages: tuple[Language, ...] = TARGET_LANGUAGES,
    source: Language = SOURCE_LANGUAGE,
) -> list[str]:
    """Validation errors that block publishing this entity, human-readable.

    The entity is validated in its would-be published state alongside the
    rest of the content, then errors are scoped to its subject.
    """
    kind = "article" if isinstance(entity, Article) else "page"
    subject = f"{kind}:{entity.id}"
    would_be = entity.model_copy(update={"status": ContentStatus.PUBLISHED})
    if isinstance(would_be, Article):
        articles = [a for a in content.articles if a.id != entity.id] + [would_be]
        content = SiteContent(articles=articles, pages=content.pages, media=content.media)
    else:
        pages = [p for p in content.pages if p.id != entity.id] + [would_be]
        content = SiteContent(articles=content.articles, pages=pages, media=content.media)
    report = RuleSet(rules=default_ruleset()).run(
        content,
        ValidationContext(required_languages=required_languages, source_language=source),
    )
    return [str(issue) for issue in report.errors if issue.subject == subject]
