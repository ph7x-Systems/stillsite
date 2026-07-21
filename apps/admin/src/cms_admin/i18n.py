"""Admin-panel i18n (ADR-0022 + ADR-0034): pack catalogs, per-request
resolution.

The catalogs are gettext ``.po`` text carried by language packs
(``LanguagePack.admin_catalog``) — the bundled five's live in cms-core,
an extension pack brings its own, and activating a pack is the whole
job of adding a panel language. At startup every registered pack's
catalog is compiled in memory to a ``gettext.GNUTranslations`` — no
binary files, no build step. Translations are injected into every
render context (``_``, ``gettext``, ``ngettext``) by a context
processor, never installed globally on the shared Jinja environment:
one process serves users in different languages concurrently.

Resolution order: the signed-in user's stored preference (set on
``request.state`` by the session dependency) → ``Accept-Language`` → EN.
"""

import gettext
from io import BytesIO

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from cms_core import Language
from cms_core.language_packs import direction, registered_language_packs
from fastapi import Request

SOURCE = Language.EN

# Msgids that reach templates through variables (``{{ _(variable) }}``), so
# the template scan cannot see them. The anti-drift test enforces catalog
# completeness for these exactly like for template literals.
RUNTIME_MSGIDS: tuple[str, ...] = (
    # login route
    "Wrong username or password.",
    # two-factor authentication (ADR-0035)
    "Two-factor authentication is required for your role. Enrol to continue.",
    "Two-factor authentication is required for your role and cannot be disabled.",
    "Two-factor authentication",
    "Two-factor authentication is enabled.",
    "Enter this key in your authenticator app, then confirm with a code:",
    "Manual key",
    "Setup link",
    "Authentication code",
    "Authentication code required.",
    "Wrong authentication code.",
    "Verify and enable",
    "Disable two-factor authentication",
    # notifications (ADR-0032 phase 2)
    "Review requested: %(title)s",
    "%(actor)s sent %(title)s to review. Open it in the panel:\n\n%(link)s",
    "Published: %(title)s",
    "%(title)s was published by %(actor)s:\n\n%(link)s",
    # password reset (ADR-0032)
    "Email",
    "optional — password reset and notifications",
    "Forgot your password?",
    "Reset your password",
    "Send the reset link",
    "If that account has an address, a message is on its way.",
    "Back to sign in",
    "New password",
    "Repeat the new password",
    "Set the new password",
    "The password needs at least 12 characters.",
    "The two passwords do not match.",
    "This reset link is no longer valid — request a new one.",
    "Your password was changed. Sign in with the new one.",
    "Reset your Sardine CMS admin password",
    "Someone asked to reset the password for %(username)s. If it was "
    "you, open this link within 30 minutes:\n\n%(link)s\n\nIf it was "
    "not you, ignore this message — nothing changed.",
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
    # users screen route errors
    "username: lowercase letters, digits and dashes only",
    "password: between 12 and 1024 characters",
    "role: unknown role",
    "language: unknown language",
    "username: already taken",
    "role: the last admin cannot be demoted",
    "delete: you cannot delete your own account",
    "delete: the last admin cannot be deleted",
    # menu manager route error
    "menu: id is lowercase-with-dashes, url and position are required",
    # media upload static errors
    "file: choose a file to upload",
    "file: could not read the image dimensions",
    "file: unsupported type — png, jpeg, gif or webp",
    "file: image dimensions exceed the pixel limit",
    "file: a file already exists at the generated path",
)


def load_catalogs() -> dict[Language, gettext.NullTranslations]:
    """Compile every registered pack's catalog to in-memory translations.

    Runs after the project's extensions register their packs, so an
    activated pack's panel language is simply there. The source (EN)
    needs no catalog: the msgids are its text.
    """
    catalogs: dict[Language, gettext.NullTranslations] = {SOURCE: gettext.NullTranslations()}
    for pack in registered_language_packs():
        if pack.admin_catalog is None:
            continue
        catalog = read_po(BytesIO(pack.admin_catalog))
        buffer = BytesIO()
        write_mo(buffer, catalog)
        buffer.seek(0)
        catalogs[Language(pack.tag)] = gettext.GNUTranslations(buffer)
    return catalogs


def panel_languages() -> tuple[tuple[Language, str], ...]:
    """The panel-language choices: the source plus every registered pack
    carrying an admin catalog, labeled by the pack's own native name."""
    choices: dict[Language, str] = {SOURCE: "English"}
    for pack in registered_language_packs():
        language = Language(pack.tag)
        if language is SOURCE:
            choices[language] = pack.native_name or "English"
        elif pack.admin_catalog is not None:
            choices[language] = pack.native_name or pack.tag
    return tuple(sorted(choices.items(), key=lambda item: str(item[0])))


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
    known = {str(language): language for language, _name in panel_languages()}
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
    """Jinja context processor: per-request gettext callables, plus the
    resolved panel language and its text direction (ADR-0034: the panel
    mirrors for RTL packs like any page)."""
    translations = translations_for(request)
    language = resolve_language(request)
    return {
        "_": translations.gettext,
        "gettext": translations.gettext,
        "ngettext": translations.ngettext,
        "panel_language": language,
        "panel_dir": direction(language),
        "panel_language_choices": panel_languages(),
    }


def translate(request: Request, message: str) -> str:
    """Python-side messages (route errors, run records)."""
    return translations_for(request).gettext(message)


def translate_for(request: Request, language: Language | None, message: str) -> str:
    """A message in a specific user's language (ADR-0032 emails): the
    stored preference wins; None falls back to the request's resolution."""
    catalogs: dict[Language, gettext.NullTranslations] = request.app.state.translations
    if language is not None:
        return catalogs.get(language, catalogs[SOURCE]).gettext(message)
    return translations_for(request).gettext(message)
