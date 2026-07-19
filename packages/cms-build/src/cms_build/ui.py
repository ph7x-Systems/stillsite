"""Localized UI chrome labels (never editorial content).

Small strings the theme chrome needs ("Blog", "Search", …). Defaults ship
per language; projects override any of them via ``[site.labels]`` in
configuration — templates and builder code never hardcode UI text.
"""

from cms_core import SOURCE_LANGUAGE, Language

from cms_build.config import SiteConfig

DEFAULT_LABELS: dict[str, dict[Language, str]] = {
    "blog": {
        Language.EN: "Blog",
        Language.PT_PT: "Blog",
        Language.ES: "Blog",
        Language.FR: "Blog",
        Language.DE: "Blog",
    },
    "search": {
        Language.EN: "Search",
        Language.PT_PT: "Pesquisar",
        Language.ES: "Buscar",
        Language.FR: "Rechercher",
        Language.DE: "Suchen",
    },
    "admin": {
        Language.EN: "Admin",
        Language.PT_PT: "Admin",
        Language.ES: "Admin",
        Language.FR: "Admin",
        Language.DE: "Admin",
    },
    "view-cards": {
        Language.EN: "Cards",
        Language.PT_PT: "Cartões",
        Language.ES: "Tarjetas",
        Language.FR: "Cartes",
        Language.DE: "Karten",
    },
    "view-list": {
        Language.EN: "List",
        Language.PT_PT: "Lista",
        Language.ES: "Lista",
        Language.FR: "Liste",
        Language.DE: "Liste",
    },
    "back": {
        Language.EN: "Back to the blog",
        Language.PT_PT: "Voltar ao blog",
        Language.ES: "Volver al blog",
        Language.FR: "Retour au blog",
        Language.DE: "Zurueck zum Blog",
    },
    "blog-title": {
        Language.EN: "Blog",
        Language.PT_PT: "Blog",
        Language.ES: "Blog",
        Language.FR: "Blog",
        Language.DE: "Blog",
    },
    "blog-eyebrow": {
        Language.EN: "Writing",
        Language.PT_PT: "Escrita",
        Language.ES: "Escritura",
        Language.FR: "Écrits",
        Language.DE: "Notizen",
    },
    "blog-sub": {},
    "min-read": {
        Language.EN: "min read",
        Language.PT_PT: "min de leitura",
        Language.ES: "min de lectura",
        Language.FR: "min de lecture",
        Language.DE: "Min. Lesezeit",
    },
    "not-found": {
        Language.EN: "Page not found",
        Language.PT_PT: "Página não encontrada",
        Language.ES: "Página no encontrada",
        Language.FR: "Page introuvable",
        Language.DE: "Seite nicht gefunden",
    },
    "error-unauthorized": {
        Language.EN: "Sign-in required",
        Language.PT_PT: "Autenticação necessária",
        Language.ES: "Se requiere iniciar sesión",
        Language.FR: "Connexion requise",
        Language.DE: "Anmeldung erforderlich",
    },
    "error-forbidden": {
        Language.EN: "Access denied",
        Language.PT_PT: "Acesso negado",
        Language.ES: "Acceso denegado",
        Language.FR: "Accès refusé",
        Language.DE: "Zugriff verweigert",
    },
    "error-server": {
        Language.EN: "Something went wrong",
        Language.PT_PT: "Algo correu mal",
        Language.ES: "Algo salió mal",
        Language.FR: "Une erreur est survenue",
        Language.DE: "Etwas ist schiefgelaufen",
    },
}


MONTHS: dict[Language, tuple[str, ...]] = {
    Language.EN: (
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
    Language.PT_PT: (
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
    Language.ES: (
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
    Language.FR: (
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
    Language.DE: (
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
}


def format_date(day: int, month: int, year: int, language: Language) -> str:
    name = MONTHS.get(language, MONTHS[SOURCE_LANGUAGE])[month - 1]
    if language is Language.EN:
        return f"{day} {name} {year}"
    if language is Language.DE:
        return f"{day}. {name} {year}"
    return f"{day} de {name} de {year}" if language is Language.PT_PT else f"{day} {name} {year}"


def ui_label(config: SiteConfig, key: str, language: Language) -> str:
    overrides = config.labels.get(key, {})
    defaults = DEFAULT_LABELS.get(key, {})
    return (
        overrides.get(language)
        or overrides.get(SOURCE_LANGUAGE)
        or defaults.get(language)
        or defaults.get(SOURCE_LANGUAGE)
        or key
    )
