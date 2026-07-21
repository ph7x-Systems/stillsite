"""Core validation rules.

Each rule is small, pure and independently testable. Rules never read global
state — everything comes from the content set and the context.
"""

from collections.abc import Iterable, Iterator

from cms_core import Article, ContentStatus, Language, Page, TranslationState

from cms_validation.engine import Issue, Rule, Severity, SiteContent, ValidationContext


def _publishable(status: ContentStatus) -> bool:
    return status in (ContentStatus.REVIEW, ContentStatus.PUBLISHED)


class RequiredTranslationsRule:
    """Published/review content must be complete in every required language."""

    name = "required-translations"
    description = (
        "Content in review or published carries every required language; "
        "incomplete translations warn in review and block once published"
    )

    def check(self, content: SiteContent, context: ValidationContext) -> Iterator[Issue]:
        entries: Iterable[tuple[str, Article | Page]] = [
            *((f"article:{article.id}", article) for article in content.articles),
            *((f"page:{page.id}", page) for page in content.pages),
        ]
        for subject, entry in entries:
            if not _publishable(entry.status):
                continue
            severity = (
                Severity.ERROR if entry.status is ContentStatus.PUBLISHED else Severity.WARNING
            )
            for language in context.required_languages:
                state = entry.translation_state(language, source=context.source_language)
                if state is not TranslationState.COMPLETE:
                    yield Issue(
                        code=self.name,
                        severity=severity,
                        message=f"translation is {state.value}",
                        subject=subject,
                        language=language,
                    )


class UniqueSlugsRule:
    """Within each language, generated URLs must not collide."""

    name = "unique-slugs"
    description = "Generated URLs never collide within a language, across articles and pages"

    def check(self, content: SiteContent, context: ValidationContext) -> Iterator[Issue]:
        for language in (context.source_language, *context.required_languages):
            seen: dict[str, str] = {}
            for article in content.articles:
                slug = _article_slug(article, language)
                subject = f"article:{article.id}"
                if slug in seen:
                    yield self._collision(subject, seen[slug], slug, language)
                else:
                    seen[slug] = subject
            for page in content.pages:
                slug = _page_slug(page, language)
                subject = f"page:{page.id}"
                if slug in seen:
                    yield self._collision(subject, seen[slug], slug, language)
                else:
                    seen[slug] = subject

    def _collision(self, subject: str, other: str, slug: str, language: Language) -> Issue:
        return Issue(
            code=self.name,
            severity=Severity.ERROR,
            message=f"slug {slug!r} collides with {other}",
            subject=subject,
            language=language,
        )


class MediaReferencesRule:
    """Sections may only reference media assets that exist."""

    name = "media-references"
    description = "Page sections only reference media assets that actually exist"

    def check(self, content: SiteContent, context: ValidationContext) -> Iterator[Issue]:
        known = {asset.id for asset in content.media}
        for page in content.pages:
            for section in page.sections:
                for media_id in section.source.media:
                    if media_id not in known:
                        yield Issue(
                            code=self.name,
                            severity=Severity.ERROR,
                            message=f"unknown media asset {media_id!r}",
                            subject=f"page:{page.id}/section:{section.key}",
                        )


class MediaAltCoverageRule:
    """Media used by publishable content must have alt text in required languages."""

    name = "media-alt-coverage"
    description = "Every media asset has alt text in each required language"

    def check(self, content: SiteContent, context: ValidationContext) -> Iterator[Issue]:
        for asset in content.media:
            missing = [
                language
                for language in context.required_languages
                if not asset.alt.get(language, "").strip()
            ]
            for language in missing:
                yield Issue(
                    code=self.name,
                    severity=Severity.WARNING,
                    message="missing alt text",
                    subject=f"media:{asset.id}",
                    language=language,
                )


def _article_slug(article: Article, language: Language) -> str:
    if language is Language.EN:
        return article.source.slug or article.id
    translation = article.translations.get(language)
    if translation is None or translation.content.slug is None:
        return article.source.slug or article.id
    return translation.content.slug


def _page_slug(page: Page, language: Language) -> str:
    if language is Language.EN:
        return page.source.slug
    translation = page.translations.get(language)
    return translation.content.slug if translation else page.source.slug


class KnownCategoriesRule:
    """When the project declares categories, articles may only use those."""

    name = "known-categories"
    description = (
        "Articles only use categories the project declares (skipped when none are declared)"
    )

    def check(self, content: SiteContent, context: ValidationContext) -> Iterator[Issue]:
        if context.known_categories is None:
            return
        known = set(context.known_categories)
        for article in content.articles:
            if article.category is not None and article.category not in known:
                yield Issue(
                    code=self.name,
                    severity=Severity.ERROR,
                    message=f"unknown category {article.category!r}",
                    subject=f"article:{article.id}",
                )


def default_ruleset() -> list[Rule]:
    return [
        RequiredTranslationsRule(),
        UniqueSlugsRule(),
        MediaReferencesRule(),
        MediaAltCoverageRule(),
        KnownCategoriesRule(),
    ]
