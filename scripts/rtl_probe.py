"""Build a minimal RTL site for the accessibility gate (ADR-0034).

Registers a fictional full RTL language pack, builds a deterministic
two-entry site with that language as the source, and writes the artifact
to the given directory. The CI accessibility job then runs axe over it —
the mirrored layout passes WCAG permanently, not once.

Usage:
    python scripts/rtl_probe.py <output_dir>
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

from cms_build import SiteConfig, build_site
from cms_core import ArticleContent, ContentStatus, Language, new_article
from cms_core.language_packs import LanguagePack, register_language_pack
from cms_core.pages import PageContent, Section, SectionContent, new_page
from cms_validation import SiteContent

RTL_PACK = LanguagePack(
    tag="mir",
    direction="rtl",
    native_name="Mirrorish",
    site_labels={
        "blog": "golB",
        "search": "hcraeS",
        "back": "golb eht ot kcaB",
        "blog-title": "golB",
        "blog-eyebrow": "gnitirW",
        "min-read": "daer nim",
        "not-found": "dnuof ton egaP",
    },
    month_names=tuple(f"htnom{i}" for i in range(1, 13)),
    date_pattern="{year}/{month}/{day}",
)

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


def main() -> int:
    output = Path(sys.argv[1])
    register_language_pack(RTL_PACK)
    config = SiteConfig(
        name="Mirror probe",
        base_url="https://mirror.example",
        source_language=Language("mir"),
        languages=(),
    )
    page = new_page("home", PageContent(title="emoH", description="D", slug="home"), now=NOW)
    page.sections.append(
        Section(
            key="hero",
            kind="hero",
            source=SectionContent(fields={"heading": "tcejorp rorrim ehT"}),
        )
    )
    page.status = ContentStatus.PUBLISHED
    article = new_article(
        "first-post",
        ArticleContent(
            title="tsop tsrif ehT",
            summary="yrammus trohs A",
            body_markdown="ydob elcitra ehT.",
        ),
        now=NOW,
    )
    article.status = ContentStatus.PUBLISHED
    artifact = build_site(config, SiteContent(articles=[article], pages=[page]), now=NOW)
    for path, data in artifact.files.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    index = (output / "index.html").read_text(encoding="utf-8")
    assert 'dir="rtl"' in index, "the probe did not render RTL"
    print(f"OK: RTL probe written to {output} ({len(artifact.files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
