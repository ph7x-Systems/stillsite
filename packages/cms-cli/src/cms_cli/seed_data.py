"""Starter content data for `cms seed` — fictional in every language.

"Aurora Cartography" is an invented studio that draws maps of places that do
not exist. All names, texts and images are fictional (repository rule: no
real business or client content). Slugs are ASCII-only by design.
"""

from datetime import UTC, datetime

from cms_core import ArticleContent, Language, PageContent, SectionContent

SEED_TIME = datetime(2026, 1, 15, 9, 0, 0, tzinfo=UTC)

EN = Language.EN
PT = Language.PT_PT
ES = Language.ES
FR = Language.FR
DE = Language.DE

COMPASS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675"
    width="1200" height="675" role="img">
  <rect width="1200" height="675" fill="#101623"/>
  <g transform="translate(600 337)" stroke="#e8e4da" fill="none" stroke-width="4">
    <circle r="220"/>
    <circle r="180" stroke-dasharray="6 10"/>
    <path d="M0-260 20-20 0 260 -20-20Z" fill="#e8e4da" stroke="none"/>
    <path d="M-260 0 -20 20 260 0 -20-20Z" fill="#7a8db0" stroke="none"/>
  </g>
  <text x="600" y="640" text-anchor="middle" font-family="serif" font-size="34"
    fill="#e8e4da">Aurora Cartography</text>
</svg>
"""

HOME: dict[Language, PageContent] = {
    EN: PageContent(
        title="Aurora Cartography",
        description="Maps and atlases for imaginary places.",
        slug="home",
    ),
    PT: PageContent(
        title="Aurora Cartografia",
        description="Mapas e atlas para lugares imaginários.",
        slug="inicio",
    ),
    ES: PageContent(
        title="Aurora Cartografía",
        description="Mapas y atlas para lugares imaginarios.",
        slug="inicio",
    ),
    FR: PageContent(
        title="Aurora Cartographie",
        description="Cartes et atlas pour des lieux imaginaires.",
        slug="accueil",
    ),
    DE: PageContent(
        title="Aurora Kartographie",
        description="Karten und Atlanten für erdachte Orte.",
        slug="start",
    ),
}

HOME_HERO: dict[Language, SectionContent] = {
    EN: SectionContent(fields={"heading": "Charting places that never were"}, media=["compass"]),
    PT: SectionContent(
        fields={"heading": "Cartografar lugares que nunca existiram"}, media=["compass"]
    ),
    ES: SectionContent(
        fields={"heading": "Cartografiar lugares que nunca existieron"}, media=["compass"]
    ),
    FR: SectionContent(
        fields={"heading": "Cartographier des lieux qui n'ont jamais existé"}, media=["compass"]
    ),
    DE: SectionContent(fields={"heading": "Orte kartieren, die es nie gab"}, media=["compass"]),
}

ABOUT: dict[Language, PageContent] = {
    EN: PageContent(
        title="About the studio",
        description="Who draws the maps, and why.",
        slug="about",
    ),
    PT: PageContent(
        title="Sobre o estudio",
        description="Quem desenha os mapas, e porque.",
        slug="sobre",
    ),
    ES: PageContent(
        title="Sobre el estudio",
        description="Quien dibuja los mapas, y por que.",
        slug="sobre",
    ),
    FR: PageContent(
        title="A propos de l'atelier",
        description="Qui dessine les cartes, et pourquoi.",
        slug="a-propos",
    ),
    DE: PageContent(
        title="Uber das Studio",
        description="Wer die Karten zeichnet, und warum.",
        slug="ueber-uns",
    ),
}

ABOUT_STORY: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "heading": "A workshop for invented geography",
            "body": "Three cartographers, one drafting table, and a rule: every map must be "
            "believable enough to get lost in.",
        }
    ),
    PT: SectionContent(
        fields={
            "heading": "Uma oficina de geografia inventada",
            "body": "Tres cartografos, uma mesa de desenho e uma regra: todos os mapas devem "
            "ser criveis ao ponto de nos perdermos neles.",
        }
    ),
    ES: SectionContent(
        fields={
            "heading": "Un taller de geografia inventada",
            "body": "Tres cartografos, una mesa de dibujo y una regla: todo mapa debe ser tan "
            "creible que uno pueda perderse en el.",
        }
    ),
    FR: SectionContent(
        fields={
            "heading": "Un atelier de geographie inventee",
            "body": "Trois cartographes, une table a dessin et une regle : chaque carte doit "
            "etre assez credible pour qu'on s'y perde.",
        }
    ),
    DE: SectionContent(
        fields={
            "heading": "Eine Werkstatt fur erfundene Geographie",
            "body": "Drei Kartographen, ein Zeichentisch und eine Regel: Jede Karte muss so "
            "glaubwurdig sein, dass man sich darin verlieren kann.",
        }
    ),
}

CATEGORIES: dict[str, dict[Language, str]] = {
    "field-notes": {
        EN: "Field notes",
        PT: "Notas de campo",
        ES: "Notas de campo",
        FR: "Notes de terrain",
        DE: "Feldnotizen",
    },
    "atlas-craft": {
        EN: "Atlas craft",
        PT: "Oficio do atlas",
        ES: "Oficio del atlas",
        FR: "Metier de l'atlas",
        DE: "Atlas-Handwerk",
    },
    "studio": {
        EN: "Studio",
        PT: "Estudio",
        ES: "Estudio",
        FR: "Atelier",
        DE: "Studio",
    },
}

MEDIA_ALT: dict[Language, str] = {
    EN: "A compass rose over a night-blue chart",
    PT: "Uma rosa dos ventos sobre uma carta azul-noite",
    ES: "Una rosa de los vientos sobre una carta azul noche",
    FR: "Une rose des vents sur une carte bleu nuit",
    DE: "Eine Windrose auf einer nachtblauen Karte",
}


def _article(
    en: tuple[str, str, str],
    pt: tuple[str, str, str, str],
    es: tuple[str, str, str, str],
    fr: tuple[str, str, str, str],
    de: tuple[str, str, str, str],
) -> dict[Language, ArticleContent]:
    title, summary, body = en
    return {
        EN: ArticleContent(title=title, summary=summary, body_markdown=body),
        PT: ArticleContent(title=pt[0], summary=pt[1], body_markdown=pt[2], slug=pt[3]),
        ES: ArticleContent(title=es[0], summary=es[1], body_markdown=es[2], slug=es[3]),
        FR: ArticleContent(title=fr[0], summary=fr[1], body_markdown=fr[2], slug=fr[3]),
        DE: ArticleContent(title=de[0], summary=de[1], body_markdown=de[2], slug=de[3]),
    }


# id -> (category, tags, days offset, contents)
ARTICLES: dict[str, tuple[str, tuple[str, ...], int, dict[Language, ArticleContent]]] = {
    "why-every-atlas-starts-blank": (
        "field-notes",
        ("craft", "maps"),
        0,
        _article(
            (
                "Why every atlas starts with a blank page",
                "On the discipline of drawing nothing before drawing anything.",
                "A map is a promise.\n\nBefore the first line, decide what to leave out.",
            ),
            (
                "Porque todo o atlas comeca numa pagina em branco",
                "Sobre a disciplina de desenhar nada antes de desenhar algo.",
                "Um mapa e uma promessa.\n\nAntes da primeira linha, decide o que fica de fora.",
                "porque-todo-atlas-comeca-em-branco",
            ),
            (
                "Por que todo atlas empieza con una pagina en blanco",
                "Sobre la disciplina de dibujar nada antes de dibujar algo.",
                "Un mapa es una promesa.\n\nAntes de la primera linea, decide que dejar fuera.",
                "por-que-todo-atlas-empieza-en-blanco",
            ),
            (
                "Pourquoi chaque atlas commence par une page blanche",
                "Sur la discipline de ne rien dessiner avant de dessiner quoi que ce soit.",
                "Une carte est une promesse.\n\n"
                "Avant le premier trait, decidez de ce qui restera dehors.",
                "pourquoi-chaque-atlas-commence-blanc",
            ),
            (
                "Warum jeder Atlas mit einer leeren Seite beginnt",
                "Uber die Disziplin, nichts zu zeichnen, bevor man etwas zeichnet.",
                "Eine Karte ist ein Versprechen.\n\n"
                "Vor der ersten Linie entscheide, was draussen bleibt.",
                "warum-jeder-atlas-leer-beginnt",
            ),
        ),
    ),
    "the-legend-is-the-map": (
        "atlas-craft",
        ("craft", "design"),
        1,
        _article(
            (
                "The legend is the map",
                "Symbols carry more territory than lines do.",
                "Readers trust the legend before they trust the coastline.\n\n"
                "Design the symbols first and the terrain will follow.",
            ),
            (
                "A legenda e o mapa",
                "Os simbolos carregam mais territorio do que as linhas.",
                "O leitor confia na legenda antes de confiar na costa.\n\n"
                "Desenha primeiro os simbolos e o terreno segue.",
                "a-legenda-e-o-mapa",
            ),
            (
                "La leyenda es el mapa",
                "Los simbolos cargan mas territorio que las lineas.",
                "El lector confia en la leyenda antes que en la costa.\n\n"
                "Disena primero los simbolos y el terreno seguira.",
                "la-leyenda-es-el-mapa",
            ),
            (
                "La legende est la carte",
                "Les symboles portent plus de territoire que les traits.",
                "Le lecteur croit la legende avant de croire la cote.\n\n"
                "Dessinez d'abord les symboles, le terrain suivra.",
                "la-legende-est-la-carte",
            ),
            (
                "Die Legende ist die Karte",
                "Symbole tragen mehr Gelande als Linien.",
                "Leser vertrauen der Legende, bevor sie der Kuste vertrauen.\n\n"
                "Entwirf zuerst die Symbole, das Gelande folgt.",
                "die-legende-ist-die-karte",
            ),
        ),
    ),
    "drawing-coastlines-that-never-were": (
        "field-notes",
        ("maps", "imagination"),
        2,
        _article(
            (
                "Drawing coastlines that never were",
                "Believable shores obey rules the sea never wrote down.",
                "Real coasts are fractal, patient, indifferent.\n\n"
                "Invented ones must fake all three at once.",
            ),
            (
                "Desenhar costas que nunca existiram",
                "Uma costa crivel obedece a regras que o mar nunca escreveu.",
                "As costas reais sao fractais, pacientes, indiferentes.\n\n"
                "As inventadas tem de fingir as tres coisas ao mesmo tempo.",
                "desenhar-costas-que-nunca-existiram",
            ),
            (
                "Dibujar costas que nunca existieron",
                "Una costa creible obedece reglas que el mar nunca escribio.",
                "Las costas reales son fractales, pacientes, indiferentes.\n\n"
                "Las inventadas deben fingir las tres cosas a la vez.",
                "dibujar-costas-que-nunca-existieron",
            ),
            (
                "Dessiner des cotes qui n'ont jamais existe",
                "Une cote credible obeit a des regles que la mer n'a jamais ecrites.",
                "Les cotes reelles sont fractales, patientes, indifferentes.\n\n"
                "Les cotes inventees doivent feindre les trois a la fois.",
                "dessiner-des-cotes-jamais-existees",
            ),
            (
                "Kustenlinien zeichnen, die es nie gab",
                "Eine glaubwurdige Kuste folgt Regeln, die das Meer nie aufschrieb.",
                "Echte Kusten sind fraktal, geduldig, gleichgultig.\n\n"
                "Erfundene mussen alle drei Dinge zugleich vortauschen.",
                "kuestenlinien-die-es-nie-gab",
            ),
        ),
    ),
    "inks-that-age-like-places": (
        "atlas-craft",
        ("craft", "materials"),
        3,
        _article(
            (
                "Inks that age like places",
                "Choosing pigments for maps that should feel found, not printed.",
                "A new map of an old place should not look new.\n\n"
                "We mix inks that will yellow on schedule.",
            ),
            (
                "Tintas que envelhecem como lugares",
                "Escolher pigmentos para mapas que parecem achados, nao impressos.",
                "Um mapa novo de um lugar antigo nao deve parecer novo.\n\n"
                "Misturamos tintas que amarelecem com hora marcada.",
                "tintas-que-envelhecem-como-lugares",
            ),
            (
                "Tintas que envejecen como lugares",
                "Elegir pigmentos para mapas que parezcan hallados, no impresos.",
                "Un mapa nuevo de un lugar antiguo no debe parecer nuevo.\n\n"
                "Mezclamos tintas que amarillean puntualmente.",
                "tintas-que-envejecen-como-lugares",
            ),
            (
                "Des encres qui vieillissent comme des lieux",
                "Choisir des pigments pour des cartes trouvees, pas imprimees.",
                "Une carte neuve d'un lieu ancien ne doit pas sembler neuve.\n\n"
                "Nous melangeons des encres qui jaunissent a l'heure dite.",
                "encres-qui-vieillissent-comme-des-lieux",
            ),
            (
                "Tinten, die wie Orte altern",
                "Pigmente fur Karten, die gefunden wirken sollen, nicht gedruckt.",
                "Eine neue Karte eines alten Ortes darf nicht neu aussehen.\n\n"
                "Wir mischen Tinten, die punktlich vergilben.",
                "tinten-die-wie-orte-altern",
            ),
        ),
    ),
    "a-studio-between-two-rivers": (
        "studio",
        ("studio",),
        4,
        _article(
            (
                "A studio between two rivers",
                "Where Aurora Cartography draws, and why the light matters.",
                "The drafting room faces north, over water that is real.\n\n"
                "Everything drawn inside it is not.",
            ),
            (
                "Um estudio entre dois rios",
                "Onde a Aurora Cartografia desenha, e porque a luz importa.",
                "A sala de desenho vira a norte, sobre agua verdadeira.\n\n"
                "Tudo o que la se desenha nao e.",
                "um-estudio-entre-dois-rios",
            ),
            (
                "Un estudio entre dos rios",
                "Donde dibuja Aurora Cartografia, y por que importa la luz.",
                "La sala de dibujo mira al norte, sobre agua verdadera.\n\n"
                "Todo lo que alli se dibuja no lo es.",
                "un-estudio-entre-dos-rios",
            ),
            (
                "Un atelier entre deux rivieres",
                "Ou dessine Aurora Cartographie, et pourquoi la lumiere compte.",
                "La salle de dessin regarde le nord, au-dessus d'une eau reelle.\n\n"
                "Tout ce qui s'y dessine ne l'est pas.",
                "un-atelier-entre-deux-rivieres",
            ),
            (
                "Ein Studio zwischen zwei Flussen",
                "Wo Aurora Kartographie zeichnet, und warum das Licht zahlt.",
                "Der Zeichensaal blickt nach Norden, uber echtes Wasser.\n\n"
                "Alles, was darin gezeichnet wird, ist es nicht.",
                "ein-studio-zwischen-zwei-fluessen",
            ),
        ),
    ),
    "naming-places-with-care": (
        "studio",
        ("language", "naming"),
        5,
        _article(
            (
                "Naming places with care",
                "A place name is a one-word story; invent it responsibly.",
                "Names outlive coastlines and empires.\n\n"
                "We test every invented name in five languages before it enters an atlas.",
            ),
            (
                "Nomear lugares com cuidado",
                "Um toponimo e uma historia numa palavra; inventa-o com responsabilidade.",
                "Os nomes sobrevivem a costas e a imperios.\n\n"
                "Testamos cada nome inventado em cinco linguas antes de entrar num atlas.",
                "nomear-lugares-com-cuidado",
            ),
            (
                "Nombrar lugares con cuidado",
                "Un toponimo es una historia en una palabra; inventalo con responsabilidad.",
                "Los nombres sobreviven a costas e imperios.\n\n"
                "Probamos cada nombre inventado en cinco lenguas antes de entrar en un atlas.",
                "nombrar-lugares-con-cuidado",
            ),
            (
                "Nommer les lieux avec soin",
                "Un toponyme est une histoire en un mot ; inventez-le avec soin.",
                "Les noms survivent aux cotes et aux empires.\n\n"
                "Nous testons chaque nom invente en cinq langues avant l'atlas.",
                "nommer-les-lieux-avec-soin",
            ),
            (
                "Orte mit Sorgfalt benennen",
                "Ein Ortsname ist eine Geschichte in einem Wort; erfinde ihn mit Sorgfalt.",
                "Namen uberdauern Kusten und Reiche.\n\n"
                "Wir prufen jeden erfundenen Namen in funf Sprachen, bevor er in den Atlas kommt.",
                "orte-mit-sorgfalt-benennen",
            ),
        ),
    ),
}
