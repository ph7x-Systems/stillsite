"""Pages composed of typed sections; both are independently translatable.

A section's ``kind`` names the theme template that renders it — cms-build
never hardcodes HTML, per the extensibility contracts in docs/PLAN.md. A
page's translation state aggregates its own content and every section: the
least-complete state wins, so one missing section translation blocks the
whole page from publishing.
"""

from datetime import UTC, datetime

from pydantic import Field

from cms_core.languages import Language
from cms_core.models import SLUG_PATTERN
from cms_core.states import ContentStatus, TranslationState
from cms_core.translatable import ChecksummedContent, TranslatableModel, worst_state


class PageContent(ChecksummedContent):
    title: str = Field(min_length=1)
    description: str = ""
    slug: str = Field(pattern=SLUG_PATTERN)
    body_markdown: str = ""
    """Long-form prose (ADR-0037): a page can be a document, a zone
    composition, or both — rendered between the header and sections."""

    def checksum_payload(self) -> tuple[str, ...]:
        base = (self.title, self.description, self.slug)
        # Empty body keeps the pre-ADR-0037 checksum: adding the field
        # must not flip existing translations to outdated.
        return (*base, self.body_markdown) if self.body_markdown else base


class SectionContent(ChecksummedContent):
    fields: dict[str, str] = Field(default_factory=dict)
    media: list[str] = Field(default_factory=list)
    items: list[dict[str, str]] = Field(default_factory=list)
    """The section's ordered repeating group (ADR-0037): unbounded,
    translated with the section, counted into the checksum. An FAQ's
    question/answer pairs, an expertise list's rows."""

    def checksum_payload(self) -> tuple[str, ...]:
        field_parts = tuple(f"{name}\x1e{self.fields[name]}" for name in sorted(self.fields))
        base = (*field_parts, "\x1d", *self.media)
        if not self.items:
            # Pre-ADR-0037 checksum preserved: adding the field must not
            # flip existing translations to outdated.
            return base
        item_parts = tuple(
            "\x1e".join(f"{name}\x1c{item[name]}" for name in sorted(item)) for item in self.items
        )
        return (*base, "\x1d", *item_parts)


class Section(TranslatableModel[SectionContent]):
    key: str = Field(pattern=SLUG_PATTERN)
    kind: str = Field(pattern=SLUG_PATTERN)
    hidden: bool = False
    """Kept but not rendered (#127): the builder skips hidden sections
    entirely; the editor toggles them without losing content."""


class Page(TranslatableModel[PageContent]):
    id: str = Field(pattern=SLUG_PATTERN)
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    publish_at: datetime | None = None
    """UTC moment before which a published page stays out of builds
    (ADR-0024); None publishes immediately once published."""
    deleted_at: datetime | None = None
    """Set = in the trash (ADR-0026): invisible to builds, validation,
    export and the admin lists until restored or purged."""
    sections: list[Section] = Field(default_factory=list)

    def translation_state(
        self, language: Language, *, source: Language | None = None
    ) -> TranslationState:
        own = super().translation_state(language, source=source)
        # Hidden sections are not rendered, so they never block parity
        # (#127); their states return with them when unhidden.
        return worst_state(
            (
                own,
                *(
                    section.translation_state(language, source=source)
                    for section in self.sections
                    if not section.hidden
                ),
            )
        )

    def section(self, key: str) -> Section | None:
        for section in self.sections:
            if section.key == key:
                return section
        return None


def new_page(page_id: str, source: PageContent, *, now: datetime | None = None) -> Page:
    timestamp = now or datetime.now(tz=UTC)
    return Page(id=page_id, created_at=timestamp, updated_at=timestamp, source=source)
