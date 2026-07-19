"""Shared validation-report context for the dashboard and publishing pages.

The report is rendered by ``templates/_validation_report.html.j2``: the gate
callout, one row per rule (passing rules included — the report must show what
ran, not only what failed) and the issue list with subjects linked to their
edit screens.
"""

from cms_core import TARGET_LANGUAGES, Language
from cms_validation import Report, RuleSet, SiteContent, ValidationContext, default_ruleset


def run_report(content: SiteContent, languages: tuple[Language, ...]) -> Report:
    return RuleSet(rules=default_ruleset()).run(
        content, ValidationContext(required_languages=languages)
    )


def report_context(
    content: SiteContent, languages: tuple[Language, ...] | None = None
) -> dict[str, object]:
    required = languages or TARGET_LANGUAGES
    report = run_report(content, tuple(required))
    scope = {
        "articles": len(content.articles),
        "pages": len(content.pages),
        "media": len(content.media),
        # +1: EN is the source language on top of the required translations.
        "languages": len(required) + 1,
    }
    subject_links: dict[str, str] = {}
    for issue in report.issues:
        kind, _, rest = issue.subject.partition(":")
        ident = rest.split("/", 1)[0]
        if kind == "article":
            subject_links[issue.subject] = f"/articles/{ident}"
        elif kind == "page":
            subject_links[issue.subject] = f"/pages/{ident}"
        elif kind == "media":
            subject_links[issue.subject] = "/media"
    return {"report": report, "scope": scope, "subject_links": subject_links}
