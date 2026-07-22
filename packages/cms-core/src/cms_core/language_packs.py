"""Language packs (ADR-0034): everything a locale needs, as data.

A pack carries the locale's identity (tag), its text direction, the
site-facing UI labels, deterministic date formatting and optionally an
admin catalog. Every language is a pack — the bundled six
included (ADR-0034 amendment): their labels, month names, date
patterns and admin catalogs live here and nowhere else.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from cms_core.languages import Language

_LOCALE_DIR = Path(__file__).parent / "locale"


def _bundled_catalog(name: str) -> bytes:
    return (_LOCALE_DIR / f"{name}.po").read_bytes()


@dataclass(frozen=True)
class LanguagePack:
    tag: str
    direction: Literal["ltr", "rtl"] = "ltr"
    native_name: str | None = None
    """The language's name in itself, for language selectors."""
    site_labels: Mapping[str, str] = field(default_factory=dict)
    """UI label key -> text (the keys `cms_build.ui` documents)."""
    month_names: tuple[str, ...] = ()
    """Twelve month names for date formatting; empty falls back to EN."""
    date_pattern: str = "{day} {month} {year}"
    """Deterministic pattern with `{day}`, `{month}`, `{year}`."""
    admin_catalog: bytes | None = None
    """Optional gettext ``.po`` content: the admin-panel chrome in this
    language. A pack without one still works everywhere; the panel just
    stays in its source English for this language."""

    def __post_init__(self) -> None:
        if self.month_names and len(self.month_names) != 12:
            raise ValueError("month_names must have exactly 12 entries")


_PACKS: dict[str, LanguagePack] = {}


def register_language_pack(pack: LanguagePack) -> Language:
    """Register the pack and its tag; idempotent by tag, loud on
    conflicting re-registration."""
    existing = _PACKS.get(pack.tag)
    if existing is not None and existing != pack:
        raise ValueError(f"language pack for {pack.tag!r} is already registered differently")
    language = Language.register(pack.tag)
    _PACKS[pack.tag] = pack
    return language


def language_pack(tag: str) -> LanguagePack | None:
    return _PACKS.get(str(tag))


def direction(tag: str) -> Literal["ltr", "rtl"]:
    pack = language_pack(tag)
    return pack.direction if pack is not None else "ltr"


def registered_language_packs() -> tuple[LanguagePack, ...]:
    """Every registered pack, ordered by tag (deterministic consumers)."""
    return tuple(_PACKS[tag] for tag in sorted(_PACKS))


# The bundled six, as full packs (ADR-0034 amendment: no privileged
# languages) — every label, month name, date pattern and admin catalog
# lives here, nowhere else. English carries no catalog: the panel's
# msgids are the English source text itself. Italian ships without an
# admin catalog; the panel stays English for it until one is added.
register_language_pack(
    LanguagePack(
        tag="en",
        direction="ltr",
        native_name="English",
        site_labels={
            "blog": "Blog",
            "search": "Search",
            "admin": "Admin",
            "comments": "Join the discussion",
            "view-cards": "Cards",
            "view-list": "List",
            "back": "Back to the blog",
            "blog-title": "Blog",
            "blog-eyebrow": "Writing",
            "min-read": "min read",
            "not-found": "Page not found",
            "error-unauthorized": "Sign-in required",
            "error-forbidden": "Access denied",
            "error-server": "Something went wrong",
            "form-received": "Message received",
            "form-thanks": "Thank you — your message has been sent.",
            "form-error": "The form could not be sent",
            "form-field-required": "The field “{label}” is required.",
            "form-field-email": "“{label}” must be a valid e-mail address.",
            "form-back": "Back to the page",
            "form-rate-limited": "Too many submissions — please try again in a moment.",
            "preview-banner": "Draft preview — not published",
        },
        month_names=(
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        date_pattern="{day} {month} {year}",
    )
)
register_language_pack(
    LanguagePack(
        tag="pt-pt",
        direction="ltr",
        native_name="Português",
        admin_catalog=_bundled_catalog("pt_PT"),
        site_labels={
            "blog": "Blog",
            "search": "Pesquisar",
            "admin": "Admin",
            "comments": "Participar na discussão",
            "view-cards": "Cartões",
            "view-list": "Lista",
            "back": "Voltar ao blog",
            "blog-title": "Blog",
            "blog-eyebrow": "Escrita",
            "min-read": "min de leitura",
            "not-found": "Página não encontrada",
            "error-unauthorized": "Autenticação necessária",
            "error-forbidden": "Acesso negado",
            "error-server": "Algo correu mal",
            "form-received": "Mensagem recebida",
            "form-thanks": "Obrigado — a sua mensagem foi enviada.",
            "form-error": "Não foi possível enviar o formulário",
            "form-field-required": "O campo “{label}” é obrigatório.",
            "form-field-email": "“{label}” tem de ser um endereço de e-mail válido.",
            "form-back": "Voltar à página",
            "form-rate-limited": "Demasiados envios — tente novamente dentro de momentos.",
            "preview-banner": "Pré-visualização de rascunho — não publicado",
        },
        month_names=(
            "janeiro",
            "fevereiro",
            "março",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ),
        date_pattern="{day} de {month} de {year}",
    )
)
register_language_pack(
    LanguagePack(
        tag="es",
        direction="ltr",
        native_name="Español",
        admin_catalog=_bundled_catalog("es"),
        site_labels={
            "blog": "Blog",
            "search": "Buscar",
            "admin": "Admin",
            "comments": "Únete a la conversación",
            "view-cards": "Tarjetas",
            "view-list": "Lista",
            "back": "Volver al blog",
            "blog-title": "Blog",
            "blog-eyebrow": "Escritura",
            "min-read": "min de lectura",
            "not-found": "Página no encontrada",
            "error-unauthorized": "Se requiere iniciar sesión",
            "error-forbidden": "Acceso denegado",
            "error-server": "Algo salió mal",
            "form-received": "Mensaje recibido",
            "form-thanks": "Gracias — su mensaje ha sido enviado.",
            "form-error": "No se pudo enviar el formulario",
            "form-field-required": "El campo “{label}” es obligatorio.",
            "form-field-email": "“{label}” debe ser una dirección de correo válida.",
            "form-back": "Volver a la página",
            "form-rate-limited": "Demasiados envíos — inténtelo de nuevo en un momento.",
            "preview-banner": "Vista previa de borrador — no publicado",
        },
        month_names=(
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ),
        date_pattern="{day} {month} {year}",
    )
)
register_language_pack(
    LanguagePack(
        tag="fr",
        direction="ltr",
        native_name="Français",
        admin_catalog=_bundled_catalog("fr"),
        site_labels={
            "blog": "Blog",
            "search": "Rechercher",
            "admin": "Admin",
            "comments": "Rejoindre la discussion",
            "view-cards": "Cartes",
            "view-list": "Liste",
            "back": "Retour au blog",
            "blog-title": "Blog",
            "blog-eyebrow": "Écrits",
            "min-read": "min de lecture",
            "not-found": "Page introuvable",
            "error-unauthorized": "Connexion requise",
            "error-forbidden": "Accès refusé",
            "error-server": "Une erreur est survenue",
            "form-received": "Message reçu",
            "form-thanks": "Merci — votre message a été envoyé.",
            "form-error": "Le formulaire n'a pas pu être envoyé",
            "form-field-required": "Le champ “{label}” est obligatoire.",
            "form-field-email": "“{label}” doit être une adresse e-mail valide.",
            "form-back": "Retour à la page",
            "form-rate-limited": "Trop d'envois — veuillez réessayer dans un instant.",
            "preview-banner": "Aperçu de brouillon — non publié",
        },
        month_names=(
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ),
        date_pattern="{day} {month} {year}",
    )
)
register_language_pack(
    LanguagePack(
        tag="de",
        direction="ltr",
        native_name="Deutsch",
        admin_catalog=_bundled_catalog("de"),
        site_labels={
            "blog": "Blog",
            "search": "Suchen",
            "admin": "Admin",
            "comments": "An der Diskussion teilnehmen",
            "view-cards": "Karten",
            "view-list": "Liste",
            "back": "Zurueck zum Blog",
            "blog-title": "Blog",
            "blog-eyebrow": "Notizen",
            "min-read": "Min. Lesezeit",
            "not-found": "Seite nicht gefunden",
            "error-unauthorized": "Anmeldung erforderlich",
            "error-forbidden": "Zugriff verweigert",
            "error-server": "Etwas ist schiefgelaufen",
            "form-received": "Nachricht erhalten",
            "form-thanks": "Danke — Ihre Nachricht wurde gesendet.",
            "form-error": "Das Formular konnte nicht gesendet werden",
            "form-field-required": "Das Feld „{label}“ ist erforderlich.",
            "form-field-email": "„{label}“ muss eine gültige E-Mail-Adresse sein.",
            "form-back": "Zurück zur Seite",
            "form-rate-limited": "Zu viele Einsendungen — bitte versuchen Sie es gleich erneut.",
            "preview-banner": "Entwurfsvorschau — nicht veröffentlicht",
        },
        month_names=(
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ),
        date_pattern="{day}. {month} {year}",
    )
)
register_language_pack(
    LanguagePack(
        tag="it",
        direction="ltr",
        native_name="Italiano",
        admin_catalog=_bundled_catalog("it"),
        site_labels={
            "blog": "Blog",
            "search": "Cerca",
            "admin": "Admin",
            "comments": "Partecipa alla discussione",
            "view-cards": "Schede",
            "view-list": "Lista",
            "back": "Torna al blog",
            "blog-title": "Blog",
            "blog-eyebrow": "Scritti",
            "min-read": "min di lettura",
            "not-found": "Pagina non trovata",
            "error-unauthorized": "Accesso richiesto",
            "error-forbidden": "Accesso negato",
            "error-server": "Si è verificato un errore",
            "form-received": "Messaggio ricevuto",
            "form-thanks": "Grazie — il tuo messaggio è stato inviato.",
            "form-error": "Non è stato possibile inviare il modulo",
            "form-field-required": "Il campo “{label}” è obbligatorio.",
            "form-field-email": "“{label}” deve essere un indirizzo e-mail valido.",
            "form-back": "Torna alla pagina",
            "form-rate-limited": "Troppi invii — riprova tra un momento.",
            "preview-banner": "Anteprima bozza — non pubblicato",
        },
        month_names=(
            "gennaio",
            "febbraio",
            "marzo",
            "aprile",
            "maggio",
            "giugno",
            "luglio",
            "agosto",
            "settembre",
            "ottobre",
            "novembre",
            "dicembre",
        ),
        date_pattern="{day} {month} {year}",
    )
)
