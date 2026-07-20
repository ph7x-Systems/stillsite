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
    ABOUT_QUOTE,
    ABOUT_STORY,
    ARTICLES,
    COVER_ALT,
    COVER_SVGS,
    HOME,
    HOME_ABOUT,
    HOME_CTA,
    HOME_EXPERTISE,
    HOME_FAQ,
    HOME_HERO,
    HOME_LATEST,
    MEDIA_ALT,
    REVIEW_ARTICLE,
    REVIEW_ARTICLE_ID,
    ROCKET_SVG,
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
            [
                ("hero", "hero", HOME_HERO),
                ("about", "story", HOME_ABOUT),
                ("expertise", "expertise", HOME_EXPERTISE),
                ("latest", "latest-articles", HOME_LATEST),
                ("questions", "faq", HOME_FAQ),
                ("join", "contact", HOME_CTA),
            ],
        )
    )
    storage.save_page(
        _page("about", ABOUT, [("story", "story", ABOUT_STORY), ("voices", "quote", ABOUT_QUOTE)])
    )

    for article_id, (category, tags, days, contents) in ARTICLES.items():
        entry = _article(article_id, category, tags, days, contents)
        entry.cover = f"cover-{category}"
        storage.save_article(entry)

    # Still in review, DE translation deliberately missing: the seeded
    # project shows the publish gate holding a real warning instead of an
    # empty all-green report. Never exported (not published).
    pending = new_article(
        REVIEW_ARTICLE_ID, REVIEW_ARTICLE[Language.EN], now=SEED_TIME + timedelta(days=1)
    )
    for language, content in REVIEW_ARTICLE.items():
        if language is not Language.EN:
            pending.set_translation(language, content)
    pending.status = ContentStatus.REVIEW
    pending.category = "missions"
    pending.tags = ("training", "parking")
    pending.cover = "cover-missions"
    storage.save_article(pending)

    rocket = MediaAsset(
        id="rocket",
        path="images/rocket.svg",
        mime_type="image/svg+xml",
        width=1200,
        height=675,
        alt=dict(MEDIA_ALT),
    )
    storage.save_media_asset(rocket)
    for cover_id, svg in COVER_SVGS.items():
        storage.save_media_asset(
            MediaAsset(
                id=cover_id,
                path=f"images/{cover_id}.svg",
                mime_type="image/svg+xml",
                width=1200,
                height=630,
                alt=dict(COVER_ALT[cover_id]),
            )
        )
        if project_dir is not None:
            cover_target = project_dir / "media" / "images" / f"{cover_id}.svg"
            cover_target.parent.mkdir(parents=True, exist_ok=True)
            if not cover_target.exists():
                cover_target.write_text(svg, encoding="utf-8")
    if project_dir is not None:
        target = project_dir / "media" / "images" / "rocket.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(ROCKET_SVG, encoding="utf-8")

    return 2, len(ARTICLES) + 1, 1 + len(COVER_SVGS)
