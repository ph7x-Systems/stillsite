"""Admin-panel i18n (ADR-0022): gettext catalogs, per-request resolution.

The catalogs are ``.po`` text files in git (``locale/<locale>/LC_MESSAGES/
messages.po``); at startup each is compiled in memory to a
``gettext.GNUTranslations`` — no binary files, no build step. Translations
are injected into every render context (``_``, ``gettext``, ``ngettext``)
by a context processor, never installed globally on the shared Jinja
environment: one process serves users in different languages concurrently.

Resolution order: the signed-in user's stored preference (set on
``request.state`` by the session dependency) → ``Accept-Language`` → EN.
"""

import gettext
from io import BytesIO
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from cms_core import Language
from fastapi import Request

SOURCE = Language.EN

# Admin languages and their catalog directories. The same set as the site's
# languages today, decoupled by design — adding one here (plus its .po)
# is the whole job; the anti-drift test enforces completeness.
LOCALES: dict[Language, str] = {
    Language.PT_PT: "pt_PT",
    Language.ES: "es",
    Language.FR: "fr",
    Language.DE: "de",
}

LOCALE_DIR = Path(__file__).parent / "locale"

# Msgids that reach templates through variables (``{{ _(variable) }}``), so
# the template scan cannot see them. The anti-drift test enforces catalog
# completeness for these exactly like for template literals.
RUNTIME_MSGIDS: tuple[str, ...] = (
    # login route
    "Wrong username or password.",
    # workflow transition labels (cms_admin.workflow.LABELS)
    "Submit for review",
    "Send back to draft",
    "Publish",
    "Archive",
    "Restore to draft",
    # content statuses / translation states / severities
    "draft",
    "review",
    "published",
    "archived",
    "missing",
    "outdated",
    "complete",
    "error",
    "warning",
    # enumerable validation issue messages
    "translation is missing",
    "translation is outdated",
    "missing alt text",
    # scheduling form error (ADR-0024)
    "publish_at: use the picker format (YYYY-MM-DDTHH:MM, UTC)",
    # media upload static errors
    "file: choose a file to upload",
    "file: could not read the image dimensions",
    "file: unsupported type — png, jpeg, gif, webp or svg",
)


def load_catalogs() -> dict[Language, gettext.NullTranslations]:
    """Compile every .po catalog to in-memory translations at startup."""
    catalogs: dict[Language, gettext.NullTranslations] = {SOURCE: gettext.NullTranslations()}
    for language, locale in LOCALES.items():
        po_path = LOCALE_DIR / locale / "LC_MESSAGES" / "messages.po"
        with po_path.open("rb") as handle:
            catalog = read_po(handle, locale=locale)
        buffer = BytesIO()
        write_mo(buffer, catalog)
        buffer.seek(0)
        catalogs[language] = gettext.GNUTranslations(buffer)
    return catalogs


def negotiate(accept_language: str | None) -> Language:
    """Pick the best admin language from an Accept-Language header."""
    if not accept_language:
        return SOURCE
    ranked: list[tuple[float, str]] = []
    for part in accept_language.split(","):
        piece, _, q = part.strip().partition(";q=")
        try:
            quality = float(q) if q else 1.0
        except ValueError:
            quality = 0.0
        ranked.append((-quality, piece.strip().lower()))
    known = {language.value: language for language in (SOURCE, *LOCALES)}
    for _, tag in sorted(ranked):
        if tag in known:
            return known[tag]
        primary = tag.split("-", 1)[0]
        for value, language in known.items():
            if value.split("-", 1)[0] == primary:
                return language
    return SOURCE


def resolve_language(request: Request) -> Language:
    preferred: Language | None = getattr(request.state, "language", None)
    if preferred is not None:
        return preferred
    return negotiate(request.headers.get("accept-language"))


def translations_for(request: Request) -> gettext.NullTranslations:
    catalogs: dict[Language, gettext.NullTranslations] = request.app.state.translations
    return catalogs.get(resolve_language(request), catalogs[SOURCE])


def i18n_context(request: Request) -> dict[str, object]:
    """Jinja context processor: per-request gettext callables."""
    translations = translations_for(request)
    return {
        "_": translations.gettext,
        "gettext": translations.gettext,
        "ngettext": translations.ngettext,
    }


def translate(request: Request, message: str) -> str:
    """Python-side messages (route errors, run records)."""
    return translations_for(request).gettext(message)
