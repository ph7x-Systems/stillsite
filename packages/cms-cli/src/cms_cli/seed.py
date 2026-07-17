"""Seed logic: writes the fictional starter content (see seed_data).

Fixed timestamps keep seeded projects building deterministically. When a
project directory is given, the referenced media files are written too, so a
freshly scaffolded project builds with no broken references.
"""

from datetime import timedelta
from pathlib import Path

from cms_core import (
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    Page,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_core.storage import StorageBackend

from cms_cli.seed_data import (
    ABOUT,
    ABOUT_STORY,
    ARTICLES,
    COMPASS_SVG,
    HOME,
    HOME_HERO,
    HOME_LATEST,
    MEDIA_ALT,
    SEED_TIME,
)


def _page(
    page_id: str,
    contents: dict[Language, PageContent],
    sections: list[tuple[str, str, dict[Language, SectionContent]]],
) -> Page:
    page = new_page(page_id, contents[Language.EN], now=SEED_TIME)
    for language, content in contents.items():
        if language is not Language.EN:
            page.set_translation(language, content)
    for key, kind, bodies in sections:
        section = Section(key=key, kind=kind, source=bodies[Language.EN])
        for language, body in bodies.items():
            if language is not Language.EN:
                section.set_translation(language, body)
        page.sections.append(section)
    page.status = ContentStatus.PUBLISHED
    return page


def _article(
    article_id: str,
    category: str,
    tags: tuple[str, ...],
    days: int,
    contents: dict[Language, ArticleContent],
) -> Article:
    article = new_article(article_id, contents[Language.EN], now=SEED_TIME + timedelta(days=days))
    for language, content in contents.items():
        if language is not Language.EN:
            article.set_translation(language, content)
    article.status = ContentStatus.PUBLISHED
    article.category = category
    article.tags = tags
    return article


def seed(storage: StorageBackend, project_dir: Path | None = None) -> tuple[int, int, int]:
    """Write the starter content; returns (pages, articles, media) counts."""
    storage.save_page(
        _page(
            "home",
            HOME,
            [("hero", "hero", HOME_HERO), ("latest", "latest-articles", HOME_LATEST)],
        )
    )
    storage.save_page(_page("about", ABOUT, [("story", "story", ABOUT_STORY)]))

    for article_id, (category, tags, days, contents) in ARTICLES.items():
        storage.save_article(_article(article_id, category, tags, days, contents))

    compass = MediaAsset(
        id="compass",
        path="images/compass.svg",
        mime_type="image/svg+xml",
        width=1200,
        height=675,
        alt=dict(MEDIA_ALT),
    )
    storage.save_media_asset(compass)
    if project_dir is not None:
        target = project_dir / "media" / "images" / "compass.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(COMPASS_SVG, encoding="utf-8")

    return 2, len(ARTICLES), 1
