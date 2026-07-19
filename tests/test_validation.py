"""Rule engine and core validation rules."""

from datetime import UTC, datetime

from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_validation import (
    RuleSet,
    Severity,
    SiteContent,
    ValidationContext,
    default_ruleset,
)

NOW = datetime(2026, 1, 15, tzinfo=UTC)
CONTEXT = ValidationContext(required_languages=(Language.PT_PT, Language.ES))


def run(content: SiteContent) -> list[str]:
    report = RuleSet(rules=default_ruleset()).run(content, CONTEXT)
    return [str(issue) for issue in report.issues]


def test_complete_published_content_passes() -> None:
    article = new_article("post", ArticleContent(title="Post"), now=NOW)
    for language in CONTEXT.required_languages:
        article.set_translation(language, ArticleContent(title="Trad"))
    article.status = ContentStatus.PUBLISHED
    report = RuleSet(rules=default_ruleset()).run(SiteContent(articles=[article]), CONTEXT)
    assert report.ok
    assert report.issues == ()


def test_published_missing_translation_is_an_error() -> None:
    article = new_article("post", ArticleContent(title="Post"), now=NOW)
    article.status = ContentStatus.PUBLISHED
    report = RuleSet(rules=default_ruleset()).run(SiteContent(articles=[article]), CONTEXT)
    assert not report.ok
    assert {issue.language for issue in report.errors} == set(CONTEXT.required_languages)


def test_review_content_only_warns() -> None:
    article = new_article("post", ArticleContent(title="Post"), now=NOW)
    article.status = ContentStatus.REVIEW
    report = RuleSet(rules=default_ruleset()).run(SiteContent(articles=[article]), CONTEXT)
    assert report.ok
    assert all(issue.severity is Severity.WARNING for issue in report.issues)


def test_draft_content_is_ignored() -> None:
    article = new_article("post", ArticleContent(title="Post"), now=NOW)
    assert run(SiteContent(articles=[article])) == []


def test_slug_collision_between_page_and_article() -> None:
    article = new_article("about", ArticleContent(title="About post"), now=NOW)
    page = new_page("about-page", PageContent(title="About", slug="about"), now=NOW)
    issues = run(SiteContent(articles=[article], pages=[page]))
    assert any("unique-slugs" in issue for issue in issues)


def test_unknown_media_reference_is_an_error() -> None:
    page = new_page("home", PageContent(title="Home", slug="home"), now=NOW)
    page.sections.append(
        Section(key="hero", kind="hero", source=SectionContent(media=["missing-asset"]))
    )
    issues = run(SiteContent(pages=[page]))
    assert any("media-references" in issue and "missing-asset" in issue for issue in issues)


def test_media_alt_coverage_warns_per_language() -> None:
    asset = MediaAsset(
        id="hero",
        path="images/hero.webp",
        mime_type="image/webp",
        width=100,
        height=100,
        alt={Language.EN: "Hero", Language.PT_PT: "Herói"},
    )
    report = RuleSet(rules=default_ruleset()).run(SiteContent(media=[asset]), CONTEXT)
    assert report.ok
    assert [issue.language for issue in report.warnings] == [Language.ES]


def test_rules_can_be_disabled() -> None:
    article = new_article("post", ArticleContent(title="Post"), now=NOW)
    article.status = ContentStatus.PUBLISHED
    ruleset = RuleSet(rules=default_ruleset(), disabled={"required-translations"})
    report = ruleset.run(SiteContent(articles=[article]), CONTEXT)
    assert report.ok


def test_report_lists_every_rule_result_even_when_all_pass() -> None:
    report = RuleSet(rules=default_ruleset()).run(SiteContent(), CONTEXT)
    assert [result.rule for result in report.results] == [
        "required-translations",
        "unique-slugs",
        "media-references",
        "media-alt-coverage",
        "known-categories",
    ]
    assert all(result.ok for result in report.results)
    assert all(result.description for result in report.results)


def test_rule_results_carry_their_own_issues() -> None:
    article = new_article("post", ArticleContent(title="Post"), now=NOW)
    article.status = ContentStatus.PUBLISHED
    report = RuleSet(rules=default_ruleset()).run(SiteContent(articles=[article]), CONTEXT)
    by_rule = {result.rule: result for result in report.results}
    assert not by_rule["required-translations"].ok
    assert by_rule["unique-slugs"].ok
    assert sum(len(result.issues) for result in report.results) == len(report.issues)


def test_disabled_rules_do_not_appear_in_results() -> None:
    ruleset = RuleSet(rules=default_ruleset(), disabled={"media-alt-coverage"})
    report = ruleset.run(SiteContent(), CONTEXT)
    assert "media-alt-coverage" not in {result.rule for result in report.results}
