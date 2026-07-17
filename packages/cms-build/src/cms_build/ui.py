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
    "back": {
        Language.EN: "Back to the blog",
        Language.PT_PT: "Voltar ao blog",
        Language.ES: "Volver al blog",
        Language.FR: "Retour au blog",
        Language.DE: "Zurueck zum Blog",
    },
    "not-found": {
        Language.EN: "Page not found",
        Language.PT_PT: "Página não encontrada",
        Language.ES: "Página no encontrada",
        Language.FR: "Page introuvable",
        Language.DE: "Seite nicht gefunden",
    },
}


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
