"""URL strategy: the one place that maps content to paths.

Mirrors the PoC reference (docs/POC_PLAN.md): the source language lives
at the root, target languages under `/<lang>/`, localized slugs
everywhere. ``source`` defaults to the historical ``en`` so existing
callers and projects behave identically (ADR-0034).
"""

from cms_core import SOURCE_LANGUAGE, Article, Language, Page

from cms_build.config import SiteConfig


def language_prefix(language: Language, source: Language = SOURCE_LANGUAGE) -> str:
    return "" if language == source else f"/{language.value}"


def article_slug(article: Article, language: Language, source: Language = SOURCE_LANGUAGE) -> str:
    if language != source:
        translation = article.translations.get(language)
        if translation is not None and translation.content.slug is not None:
            return translation.content.slug
    return article.source.slug or article.id


def page_slug(page: Page, language: Language, source: Language = SOURCE_LANGUAGE) -> str:
    if language != source:
        translation = page.translations.get(language)
        if translation is not None:
            return translation.content.slug
    return page.source.slug


def article_path(config: SiteConfig, article: Article, language: Language) -> str:
    source = config.source_language
    prefix = language_prefix(language, source)
    return f"{prefix}/{config.blog_path}/{article_slug(article, language, source)}/"


def page_path(
    page: Page,
    language: Language,
    *,
    home_page_id: str = "home",
    source: Language = SOURCE_LANGUAGE,
) -> str:
    prefix = language_prefix(language, source)
    if page.id == home_page_id:
        return f"{prefix}/"
    return f"{prefix}/{page_slug(page, language, source)}/"


def blog_index_path(config: SiteConfig, language: Language) -> str:
    return f"{language_prefix(language, config.source_language)}/{config.blog_path}/"


def blog_page_path(config: SiteConfig, language: Language, number: int) -> str:
    if number <= 1:
        return blog_index_path(config, language)
    prefix = language_prefix(language, config.source_language)
    return f"{prefix}/{config.blog_path}/page/{number}/"


def category_path(config: SiteConfig, slug: str, language: Language) -> str:
    return (
        f"{language_prefix(language, config.source_language)}/{config.blog_path}/category/{slug}/"
    )


def tag_path(config: SiteConfig, slug: str, language: Language) -> str:
    return f"{language_prefix(language, config.source_language)}/{config.blog_path}/tag/{slug}/"


def absolute(config: SiteConfig, path: str) -> str:
    return f"{config.root}{path}"


def output_file(path: str) -> str:
    """Map a URL path to the file inside the artifact (pretty URLs)."""
    return f"{path.lstrip('/')}index.html" if path.endswith("/") else path.lstrip("/")
