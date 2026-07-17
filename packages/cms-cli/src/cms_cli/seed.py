"""Fictional starter content, complete in all five languages.

Everything here is invented (per the repository rules: no real business or
client content). Timestamps are fixed so seeded projects build
deterministically.
"""

from datetime import UTC, datetime

from cms_core import (
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    Page,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_core.storage import StorageBackend

SEED_TIME = datetime(2026, 1, 15, 9, 0, 0, tzinfo=UTC)

_HOME: dict[Language, PageContent] = {
    Language.EN: PageContent(
        title="Aurora Cartography",
        description="Maps and atlases for imaginary places.",
        slug="home",
    ),
    Language.PT_PT: PageContent(
        title="Aurora Cartografia",
        description="Mapas e atlas para lugares imaginários.",
        slug="inicio",
    ),
    Language.ES: PageContent(
        title="Aurora Cartografía",
        description="Mapas y atlas para lugares imaginarios.",
        slug="inicio",
    ),
    Language.FR: PageContent(
        title="Aurora Cartographie",
        description="Cartes et atlas pour des lieux imaginaires.",
        slug="accueil",
    ),
    Language.DE: PageContent(
        title="Aurora Kartographie",
        description="Karten und Atlanten für erdachte Orte.",
        slug="start",
    ),
}

_HERO: dict[Language, SectionContent] = {
    Language.EN: SectionContent(fields={"heading": "Charting places that never were"}),
    Language.PT_PT: SectionContent(fields={"heading": "Cartografar lugares que nunca existiram"}),
    Language.ES: SectionContent(fields={"heading": "Cartografiar lugares que nunca existieron"}),
    Language.FR: SectionContent(
        fields={"heading": "Cartographier des lieux qui n'ont jamais existé"}
    ),
    Language.DE: SectionContent(fields={"heading": "Orte kartieren, die es nie gab"}),
}

_FIRST_POST: dict[Language, ArticleContent] = {
    Language.EN: ArticleContent(
        title="Why every atlas starts with a blank page",
        summary="On the discipline of drawing nothing before drawing anything.",
        body_markdown="A map is a promise.\n\nBefore the first line, decide what to leave out.",
        slug="why-every-atlas-starts-blank",
    ),
    Language.PT_PT: ArticleContent(
        title="Porque todo o atlas começa numa página em branco",
        summary="Sobre a disciplina de desenhar nada antes de desenhar algo.",
        body_markdown="Um mapa é uma promessa.\n\n"
        "Antes da primeira linha, decide o que fica de fora.",
        slug="porque-todo-atlas-comeca-em-branco",
    ),
    Language.ES: ArticleContent(
        title="Por qué todo atlas empieza con una página en blanco",
        summary="Sobre la disciplina de dibujar nada antes de dibujar algo.",
        body_markdown="Un mapa es una promesa.\n\n"
        "Antes de la primera línea, decide qué dejar fuera.",
        slug="por-que-todo-atlas-empieza-en-blanco",
    ),
    Language.FR: ArticleContent(
        title="Pourquoi chaque atlas commence par une page blanche",
        summary="Sur la discipline de ne rien dessiner avant de dessiner quoi que ce soit.",
        body_markdown="Une carte est une promesse.\n\n"
        "Avant le premier trait, décidez de ce qui restera dehors.",
        slug="pourquoi-chaque-atlas-commence-blanc",
    ),
    Language.DE: ArticleContent(
        title="Warum jeder Atlas mit einer leeren Seite beginnt",
        summary="Über die Disziplin, nichts zu zeichnen, bevor man etwas zeichnet.",
        body_markdown="Eine Karte ist ein Versprechen.\n\n"
        "Vor der ersten Linie entscheide, was draußen bleibt.",
        slug="warum-jeder-atlas-leer-beginnt",
    ),
}


def _seed_page(page_id: str, contents: dict[Language, PageContent]) -> Page:
    page = new_page(page_id, contents[Language.EN], now=SEED_TIME)
    for language, content in contents.items():
        if language is not Language.EN:
            page.set_translation(language, content)
    return page


def _seed_article(article_id: str, contents: dict[Language, ArticleContent]) -> Article:
    article = new_article(article_id, contents[Language.EN], now=SEED_TIME)
    for language, content in contents.items():
        if language is not Language.EN:
            article.set_translation(language, content)
    return article


def seed(storage: StorageBackend) -> tuple[int, int]:
    """Write the starter content; returns (pages, articles) counts."""
    home = _seed_page("home", _HOME)
    hero = Section(key="hero", kind="hero", source=_HERO[Language.EN])
    for language, content in _HERO.items():
        if language is not Language.EN:
            hero.set_translation(language, content)
    home.sections.append(hero)
    home.status = ContentStatus.PUBLISHED
    storage.save_page(home)

    article = _seed_article("why-every-atlas-starts-blank", _FIRST_POST)
    article.status = ContentStatus.PUBLISHED
    storage.save_article(article)
    return 1, 1
