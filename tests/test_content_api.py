"""The JSON content target (M6): versioned headless output, same rules
as the HTML build — publication, scheduling, trash and language parity."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from cms_build import build_site
from cms_build.builder import CONTENT_API_VERSION
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
from cms_validation import SiteContent
from test_output_integrity import CONFIG, make_content

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

API_CONFIG = CONFIG.model_copy(update={"content_api": True})


def _api(artifact: Any, path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(artifact.files[path].decode("utf-8"))
    return payload


def test_opt_out_means_no_api_files_at_all() -> None:
    artifact = build_site(CONFIG, make_content(), now=NOW)
    assert not [path for path in artifact.paths() if path.startswith("api/")]


def test_envelope_is_versioned_and_covers_every_language() -> None:
    artifact = build_site(API_CONFIG, make_content(), now=NOW)
    site = _api(artifact, "api/v1/site.json")
    assert site["version"] == CONTENT_API_VERSION
    assert site["name"] == CONFIG.name
    assert site["languages"] == [language.value for language in CONFIG.all_languages]
    assert "field-notes" in site["categories"]
    for language in CONFIG.all_languages:
        payload = _api(artifact, f"api/v1/{language.value}/content.json")
        assert payload["version"] == CONTENT_API_VERSION
        assert payload["language"] == language.value


def test_only_build_eligible_content_appears() -> None:
    content = make_content()
    draft = new_article(
        "draft-one", ArticleContent(title="Draft", summary="S", body_markdown="B"), now=NOW
    )
    scheduled = new_article(
        "later-one", ArticleContent(title="Later", summary="S", body_markdown="B"), now=NOW
    )
    scheduled.status = ContentStatus.PUBLISHED
    scheduled.publish_at = NOW + timedelta(days=9)
    trashed = new_article(
        "gone-one", ArticleContent(title="Gone", summary="S", body_markdown="B"), now=NOW
    )
    trashed.status = ContentStatus.PUBLISHED
    trashed.deleted_at = NOW
    content = SiteContent(
        pages=content.pages,
        articles=[*content.articles, draft, scheduled, trashed],
        media=content.media,
    )
    artifact = build_site(API_CONFIG, content, now=NOW)
    ids = [a["id"] for a in _api(artifact, "api/v1/en/content.json")["articles"]]
    assert "alpha" in ids and "beta" in ids
    assert not {"draft-one", "later-one", "gone-one"} & set(ids)


def test_language_parity_matches_the_html_build() -> None:
    """An article whose DE translation is incomplete stays out of the DE
    file exactly as its DE page stays out of the HTML build."""
    content = make_content()
    partial = new_article(
        "en-only", ArticleContent(title="EN only", summary="S", body_markdown="B"), now=NOW
    )
    partial.status = ContentStatus.PUBLISHED
    content = SiteContent(
        pages=content.pages, articles=[*content.articles, partial], media=content.media
    )
    artifact = build_site(API_CONFIG, content, now=NOW)
    en_ids = [a["id"] for a in _api(artifact, "api/v1/en/content.json")["articles"]]
    de_ids = [a["id"] for a in _api(artifact, "api/v1/de/content.json")["articles"]]
    assert "en-only" in en_ids
    assert "en-only" not in de_ids


def test_articles_carry_slugs_relationships_and_media_metadata() -> None:
    content = make_content()
    cover = MediaAsset(
        id="cover-shot",
        path="images/cover.svg",
        mime_type="image/svg+xml",
        width=1200,
        height=630,
        alt={Language.EN: "A cover", Language.PT_PT: "Uma capa"},
    )
    article = content.articles[0]
    article.cover = "cover-shot"
    article.author = "Crew"
    article.fields = {"mood": "orbital"}
    content = SiteContent(pages=content.pages, articles=content.articles, media=[cover])
    artifact = build_site(API_CONFIG, content, now=NOW)
    entry = next(
        a for a in _api(artifact, "api/v1/en/content.json")["articles"] if a["id"] == article.id
    )
    assert entry["slug"] == article.source.slug
    assert entry["url"].endswith("/")
    assert entry["category"]["label"] == "Field notes"
    assert entry["tags"][0]["slug"] == "maps"
    assert entry["cover"] == {
        "url": "/media/images/cover.svg",
        "alt": "A cover",
        "width": 1200,
        "height": 630,
    }
    assert entry["fields"] == {"mood": "orbital"}
    assert "<p>" in entry["body_html"]
    # translated alt follows the language file
    pt = next(
        a for a in _api(artifact, "api/v1/pt-pt/content.json")["articles"] if a["id"] == article.id
    )
    assert pt["cover"]["alt"] == "Uma capa"


def test_pages_carry_their_typed_sections() -> None:
    page = new_page("about", PageContent(title="About", description="D", slug="about"), now=NOW)
    page.sections.append(
        Section(
            key="story",
            kind="story",
            source=SectionContent(fields={"heading": "Us", "body": "Text"}),
        )
    )
    page.status = ContentStatus.PUBLISHED
    artifact = build_site(API_CONFIG, SiteContent(pages=[page], articles=[], media=[]), now=NOW)
    entry = _api(artifact, "api/v1/en/content.json")["pages"][0]
    assert entry["id"] == "about"
    assert entry["sections"] == [
        {
            "key": "story",
            "kind": "story",
            "fields": {"body": "Text", "heading": "Us"},
            "items": [],
            "images": [],
        }
    ]


def test_the_api_is_deterministic() -> None:
    first = build_site(API_CONFIG, make_content(), now=NOW)
    second = build_site(API_CONFIG, make_content(), now=NOW)
    assert first.digest() == second.digest()
