"""Section-kind specs (ADR-0037): what a kind consumes, as data.

Lives in cms-core so ``Extension.section_kinds`` can carry full specs;
the build layer's gallery (``cms_build.themes``) re-exports it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionKindSpec:
    """What a section kind consumes.

    ``fields`` are the flat field names; names listed in ``markdown``
    render through the safe Markdown renderer (raw HTML off) and reach
    templates as HTML; ``items`` names the columns of the section's
    unbounded repeating group (ADR-0037)."""

    fields: tuple[str, ...] = ()
    markdown: tuple[str, ...] = ()
    items: tuple[str, ...] = ()
