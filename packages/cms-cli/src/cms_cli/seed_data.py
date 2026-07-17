"""Starter content data for `cms seed` — fictional in every language.

"Sardine Aerospace" is an invented space programme led by a sardine — playful
demo content made for presentations. All names, texts and images are fictional
(repository rule: no real business or client content). Slugs are ASCII-only.
"""

from datetime import UTC, datetime

from cms_core import ArticleContent, Language, PageContent, SectionContent

SEED_TIME = datetime(2026, 1, 15, 9, 0, 0, tzinfo=UTC)

EN = Language.EN
PT = Language.PT_PT
ES = Language.ES
FR = Language.FR
DE = Language.DE

ROCKET_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675"
    width="1200" height="675" role="img">
  <rect width="1200" height="675" fill="#080809"/>
  <g transform="translate(600 340) rotate(-45)">
    <ellipse rx="210" ry="72" fill="none" stroke="#d8cfc0" stroke-width="5"/>
    <ellipse rx="150" ry="48" fill="none" stroke="#d8cfc0" stroke-width="2" stroke-dasharray="5 8"/>
    <path fill="#d8cfc0"
      d="M-210 0 Q-252 -36 -284 -55 Q-264 -19 -264 0 Q-264 19 -284 55 Q-252 36 -210 0Z"/>
    <circle cx="158" cy="-17" r="9" fill="#080809" stroke="#d8cfc0" stroke-width="4"/>
    <path d="M208 8 Q274 30 338 18 Q276 48 220 38Z" fill="#7ec8a2" opacity="0.85"/>
  </g>
  <text x="600" y="620" text-anchor="middle" font-family="serif" font-size="34"
    fill="#d8cfc0">Sardine Aerospace</text>
</svg>
"""

HOME: dict[Language, PageContent] = {
    EN: PageContent(
        title="Sardine Aerospace",
        description="The first space programme led by a sardine.",
        slug="home",
    ),
    PT: PageContent(
        title="Sardine Aerospace",
        description="O primeiro programa espacial liderado por uma sardinha.",
        slug="inicio",
    ),
    ES: PageContent(
        title="Sardine Aerospace",
        description="El primer programa espacial dirigido por una sardina.",
        slug="inicio",
    ),
    FR: PageContent(
        title="Sardine Aerospace",
        description="Le premier programme spatial dirige par une sardine.",
        slug="accueil",
    ),
    DE: PageContent(
        title="Sardine Aerospace",
        description="Das erste Raumfahrtprogramm unter Leitung einer Sardine.",
        slug="start",
    ),
}

HOME_HERO: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "kicker": "Space programme · Tinned · In orbit",
            "heading": "A sardine on its way to",
            "accent": "Mars.",
            "lead": "Small fish. Enormous ambitions. Questionable smell.",
        },
        media=["rocket"],
    ),
    PT: SectionContent(
        fields={
            "kicker": "Programa espacial · De conserva · Em orbita",
            "heading": "Uma sardinha a caminho de",
            "accent": "Marte.",
            "lead": "Peixe pequeno. Ambicoes enormes. Cheiro discutivel.",
        },
        media=["rocket"],
    ),
    ES: SectionContent(
        fields={
            "kicker": "Programa espacial · En conserva · En orbita",
            "heading": "Una sardina camino de",
            "accent": "Marte.",
            "lead": "Pez pequeno. Ambiciones enormes. Olor discutible.",
        },
        media=["rocket"],
    ),
    FR: SectionContent(
        fields={
            "kicker": "Programme spatial · En conserve · En orbite",
            "heading": "Une sardine en route vers",
            "accent": "Mars.",
            "lead": "Petit poisson. Ambitions enormes. Odeur discutable.",
        },
        media=["rocket"],
    ),
    DE: SectionContent(
        fields={
            "kicker": "Raumfahrtprogramm · In Dosen · Im Orbit",
            "heading": "Eine Sardine auf dem Weg zum",
            "accent": "Mars.",
            "lead": "Kleiner Fisch. Riesige Ambitionen. Fragwuerdiger Geruch.",
        },
        media=["rocket"],
    ),
}

HOME_LATEST: dict[Language, SectionContent] = {
    EN: SectionContent(fields={"kicker": "Mission log", "heading": "Latest from the launch pad"}),
    PT: SectionContent(
        fields={"kicker": "Diario de missao", "heading": "O mais recente da plataforma"}
    ),
    ES: SectionContent(
        fields={"kicker": "Diario de mision", "heading": "Lo ultimo de la plataforma"}
    ),
    FR: SectionContent(
        fields={"kicker": "Journal de mission", "heading": "Les dernieres du pas de tir"}
    ),
    DE: SectionContent(
        fields={"kicker": "Missionslog", "heading": "Das Neueste von der Startrampe"}
    ),
}

ABOUT: dict[Language, PageContent] = {
    EN: PageContent(
        title="The crew",
        description="One sardine, three engineers, unlimited olive oil.",
        slug="crew",
    ),
    PT: PageContent(
        title="A tripulacao",
        description="Uma sardinha, tres engenheiros, azeite ilimitado.",
        slug="tripulacao",
    ),
    ES: PageContent(
        title="La tripulacion",
        description="Una sardina, tres ingenieros, aceite de oliva ilimitado.",
        slug="tripulacion",
    ),
    FR: PageContent(
        title="L'equipage",
        description="Une sardine, trois ingenieurs, huile d'olive illimitee.",
        slug="equipage",
    ),
    DE: PageContent(
        title="Die Crew",
        description="Eine Sardine, drei Ingenieure, unbegrenztes Olivenoel.",
        slug="crew-de",
    ),
}

ABOUT_STORY: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "kicker": "01 · Who we are",
            "heading": "Built in a cannery, aimed at the stars",
            "body": "Commander Sardinha graduated top of her shoal. The engineering team "
            "joined for the challenge and stayed for the snacks. Mission control fits "
            "in a fish crate, and the countdown is sung.",
        }
    ),
    PT: SectionContent(
        fields={
            "kicker": "01 · Quem somos",
            "heading": "Nascidos numa conserveira, apontados as estrelas",
            "body": "A Comandante Sardinha formou-se no topo do cardume. A equipa de "
            "engenharia veio pelo desafio e ficou pelos petiscos. O controlo de missao "
            "cabe numa caixa de peixe, e a contagem decrescente e cantada.",
        }
    ),
    ES: SectionContent(
        fields={
            "kicker": "01 · Quienes somos",
            "heading": "Nacidos en una conservera, apuntando a las estrellas",
            "body": "La Comandante Sardina se graduo la primera de su banco. El equipo de "
            "ingenieria vino por el reto y se quedo por las tapas. El control de mision "
            "cabe en una caja de pescado, y la cuenta atras se canta.",
        }
    ),
    FR: SectionContent(
        fields={
            "kicker": "01 · Qui nous sommes",
            "heading": "Nes dans une conserverie, vises vers les etoiles",
            "body": "La Commandante Sardine a fini premiere de son banc. L'equipe "
            "d'ingenierie est venue pour le defi et restee pour les encas. Le controle de "
            "mission tient dans une caisse a poisson, et le compte a rebours est chante.",
        }
    ),
    DE: SectionContent(
        fields={
            "kicker": "01 · Wer wir sind",
            "heading": "In einer Konservenfabrik geboren, auf die Sterne gerichtet",
            "body": "Kommandantin Sardine schloss als Beste ihres Schwarms ab. Das "
            "Ingenieursteam kam wegen der Herausforderung und blieb wegen der Snacks. Die "
            "Missionskontrolle passt in eine Fischkiste, der Countdown wird gesungen.",
        }
    ),
}

CATEGORIES: dict[str, dict[Language, str]] = {
    "missions": {
        EN: "Missions",
        PT: "Missoes",
        ES: "Misiones",
        FR: "Missions",
        DE: "Missionen",
    },
    "engineering": {
        EN: "Engineering",
        PT: "Engenharia",
        ES: "Ingenieria",
        FR: "Ingenierie",
        DE: "Technik",
    },
    "canteen": {
        EN: "Canteen",
        PT: "Cantina",
        ES: "Cantina",
        FR: "Cantine",
        DE: "Kantine",
    },
}

MEDIA_ALT: dict[Language, str] = {
    EN: "A tin-can rocket with a sardine at the controls",
    PT: "Um foguetao-lata com uma sardinha aos comandos",
    ES: "Un cohete-lata con una sardina a los mandos",
    FR: "Une fusee-boite avec une sardine aux commandes",
    DE: "Eine Dosenrakete mit einer Sardine am Steuer",
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
    "we-choose-the-tin": (
        "missions",
        ("launch", "mars"),
        0,
        _article(
            (
                "We choose to go in the tin",
                "Not because it is easy, but because it is watertight.",
                "Every great voyage starts with the right vessel.\n\n"
                "Ours is a tin. Aerodynamic, shiny, and it never complains.",
            ),
            (
                "Escolhemos ir na lata",
                "Nao porque e facil, mas porque e estanque.",
                "Toda a grande viagem comeca com o veiculo certo.\n\n"
                "O nosso e uma lata. Aerodinamica, brilhante, e nunca se queixa.",
                "escolhemos-ir-na-lata",
            ),
            (
                "Elegimos ir en la lata",
                "No porque sea facil, sino porque es estanca.",
                "Todo gran viaje empieza con el vehiculo correcto.\n\n"
                "El nuestro es una lata. Aerodinamica, brillante, y nunca se queja.",
                "elegimos-ir-en-la-lata",
            ),
            (
                "Nous choisissons la boite",
                "Non parce que c'est facile, mais parce que c'est etanche.",
                "Tout grand voyage commence par le bon vaisseau.\n\n"
                "Le notre est une boite. Aerodynamique, brillante, sans jamais se plaindre.",
                "nous-choisissons-la-boite",
            ),
            (
                "Wir fliegen in der Dose",
                "Nicht weil es leicht ist, sondern weil sie dicht haelt.",
                "Jede grosse Reise beginnt mit dem richtigen Gefaehrt.\n\n"
                "Unseres ist eine Dose. Aerodynamisch, glaenzend, beschwert sich nie.",
                "wir-fliegen-in-der-dose",
            ),
        ),
    ),
    "olive-oil-as-rocket-fuel": (
        "engineering",
        ("fuel", "testing"),
        1,
        _article(
            (
                "Olive oil as rocket fuel: preliminary findings",
                "Extra virgin performs 12% better and smells like Sunday lunch.",
                "The test bench caught fire twice, deliciously.\n\n"
                "Conclusion: viable, fragrant, and the neighbours now attend every ignition.",
            ),
            (
                "Azeite como combustivel: resultados preliminares",
                "O extra virgem rende 12% mais e cheira a almoco de domingo.",
                "A bancada de testes ardeu duas vezes, deliciosamente.\n\n"
                "Conclusao: viavel, perfumado, e os vizinhos ja nao perdem uma ignicao.",
                "azeite-como-combustivel",
            ),
            (
                "Aceite de oliva como combustible: resultados preliminares",
                "El virgen extra rinde un 12% mas y huele a comida de domingo.",
                "El banco de pruebas ardio dos veces, deliciosamente.\n\n"
                "Conclusion: viable, fragante, y los vecinos ya no se pierden una ignicion.",
                "aceite-como-combustible",
            ),
            (
                "L'huile d'olive comme carburant : premiers resultats",
                "L'extra vierge rend 12% de plus et sent le dejeuner du dimanche.",
                "Le banc d'essai a pris feu deux fois, delicieusement.\n\n"
                "Conclusion : viable, parfume, et les voisins assistent a chaque allumage.",
                "huile-olive-comme-carburant",
            ),
            (
                "Olivenoel als Raketentreibstoff: erste Ergebnisse",
                "Extra vergine leistet 12% mehr und riecht nach Sonntagsessen.",
                "Der Pruefstand brannte zweimal, koestlich.\n\n"
                "Fazit: machbar, duftend, und die Nachbarn verpassen keine Zuendung mehr.",
                "olivenoel-als-treibstoff",
            ),
        ),
    ),
    "zero-g-canning-tests": (
        "engineering",
        ("testing", "cans"),
        2,
        _article(
            (
                "Zero-G canning tests",
                "In space, no one can hear the tin open.",
                "We dropped four hundred cans from the cannery roof.\n\n"
                "Three hundred and ninety-nine survived. The other one was lunch.",
            ),
            (
                "Testes de enlatamento em gravidade zero",
                "No espaco, ninguem ouve a lata abrir.",
                "Deixamos cair quatrocentas latas do telhado da conserveira.\n\n"
                "Trezentas e noventa e nove sobreviveram. A outra foi o almoco.",
                "testes-enlatamento-gravidade-zero",
            ),
            (
                "Pruebas de enlatado en gravedad cero",
                "En el espacio, nadie oye abrirse la lata.",
                "Dejamos caer cuatrocientas latas del tejado de la conservera.\n\n"
                "Trescientas noventa y nueve sobrevivieron. La otra fue el almuerzo.",
                "pruebas-enlatado-gravedad-cero",
            ),
            (
                "Essais de mise en boite en apesanteur",
                "Dans l'espace, personne n'entend la boite s'ouvrir.",
                "Nous avons lache quatre cents boites du toit de la conserverie.\n\n"
                "Trois cent quatre-vingt-dix-neuf ont survecu. L'autre fut le dejeuner.",
                "essais-boite-apesanteur",
            ),
            (
                "Dosen-Tests in Schwerelosigkeit",
                "Im All hoert niemand die Dose aufgehen.",
                "Wir warfen vierhundert Dosen vom Dach der Konservenfabrik.\n\n"
                "Dreihundertneunundneunzig ueberlebten. Die andere war das Mittagessen.",
                "dosen-tests-schwerelosigkeit",
            ),
        ),
    ),
    "commander-sardinha-interview": (
        "missions",
        ("crew", "mars"),
        3,
        _article(
            (
                "An interview with Commander Sardinha",
                "Mars has no sea. We are bringing one.",
                "Q: Why Mars?\n\nA: Because the mackerel said it could not be done.",
            ),
            (
                "Entrevista com a Comandante Sardinha",
                "Marte nao tem mar. Nos levamos um.",
                "P: Porque Marte?\n\nR: Porque a cavala disse que era impossivel.",
                "entrevista-comandante-sardinha",
            ),
            (
                "Entrevista con la Comandante Sardina",
                "Marte no tiene mar. Nosotros llevamos uno.",
                "P: Por que Marte?\n\nR: Porque la caballa dijo que era imposible.",
                "entrevista-comandante-sardina",
            ),
            (
                "Entretien avec la Commandante Sardine",
                "Mars n'a pas de mer. Nous en apportons une.",
                "Q : Pourquoi Mars ?\n\nR : Parce que le maquereau a dit que c'etait impossible.",
                "entretien-commandante-sardine",
            ),
            (
                "Interview mit Kommandantin Sardine",
                "Der Mars hat kein Meer. Wir bringen eines mit.",
                "F: Warum der Mars?\n\nA: Weil die Makrele sagte, es sei unmoeglich.",
                "interview-kommandantin-sardine",
            ),
        ),
    ),
    "the-canteen-menu-problem": (
        "canteen",
        ("food", "crew"),
        4,
        _article(
            (
                "The canteen menu problem",
                "Everything on the menu is a colleague.",
                "Ethics committee meeting number forty-two.\n\n"
                "Resolution: the canteen now serves algae, bravely.",
            ),
            (
                "O problema da ementa da cantina",
                "Tudo o que esta na ementa e um colega.",
                "Reuniao numero quarenta e dois do comite de etica.\n\n"
                "Resolucao: a cantina passa a servir algas, corajosamente.",
                "problema-ementa-cantina",
            ),
            (
                "El problema del menu de la cantina",
                "Todo lo que hay en el menu es un colega.",
                "Reunion numero cuarenta y dos del comite de etica.\n\n"
                "Resolucion: la cantina ahora sirve algas, valientemente.",
                "problema-menu-cantina",
            ),
            (
                "Le probleme du menu de la cantine",
                "Tout ce qui est au menu est un collegue.",
                "Reunion numero quarante-deux du comite d'ethique.\n\n"
                "Resolution : la cantine sert desormais des algues, courageusement.",
                "probleme-menu-cantine",
            ),
            (
                "Das Kantinen-Menue-Problem",
                "Alles auf der Karte ist ein Kollege.",
                "Ethikkommission, Sitzung Nummer zweiundvierzig.\n\n"
                "Beschluss: Die Kantine serviert jetzt Algen, tapfer.",
                "kantinen-menue-problem",
            ),
        ),
    ),
    "train-for-space-underwater": (
        "missions",
        ("training", "crew"),
        5,
        _article(
            (
                "How to train for space when you already live underwater",
                "Neutral buoyancy comes naturally to some of us.",
                "NASA trains astronauts in swimming pools.\n\n"
                "We were born in the pool. Advantage: Sardine Aerospace.",
            ),
            (
                "Treinar para o espaco quando ja se vive debaixo de agua",
                "A flutuabilidade neutra e natural para alguns de nos.",
                "Ha agencias que treinam astronautas em piscinas.\n\n"
                "Nos nascemos na piscina. Vantagem: Sardine Aerospace.",
                "treinar-espaco-debaixo-de-agua",
            ),
            (
                "Entrenar para el espacio cuando ya vives bajo el agua",
                "La flotabilidad neutra es natural para algunos de nosotros.",
                "Hay agencias que entrenan astronautas en piscinas.\n\n"
                "Nosotros nacimos en la piscina. Ventaja: Sardine Aerospace.",
                "entrenar-espacio-bajo-el-agua",
            ),
            (
                "S'entrainer pour l'espace quand on vit deja sous l'eau",
                "La flottabilite neutre est naturelle pour certains d'entre nous.",
                "Certaines agences entrainent leurs astronautes en piscine.\n\n"
                "Nous sommes nes dans la piscine. Avantage : Sardine Aerospace.",
                "entrainement-espace-sous-eau",
            ),
            (
                "Fuers All trainieren, wenn man schon unter Wasser lebt",
                "Neutraler Auftrieb liegt manchen von uns im Blut.",
                "Manche Agenturen trainieren Astronauten im Schwimmbecken.\n\n"
                "Wir sind im Becken geboren. Vorteil: Sardine Aerospace.",
                "training-fuers-all-unter-wasser",
            ),
        ),
    ),
}


HOME_ABOUT: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "kicker": "01 · Who we are",
            "heading": "A space programme born in a cannery",
            "body": "Commander Sardinha graduated top of her shoal and now leads the only "
            "space agency with a fish at the helm. Mission control fits in a fish crate, "
            "the countdown is sung, and every launch smells faintly of the Atlantic.",
            "meta1k": "1 sardine",
            "meta1v": "at the controls",
            "meta2k": "400 tins",
            "meta2v": "drop-tested",
            "meta3k": "12% more thrust",
            "meta3v": "on extra virgin",
            "meta4k": "0 crew eaten",
            "meta4v": "this month",
        }
    ),
    PT: SectionContent(
        fields={
            "kicker": "01 · Quem somos",
            "heading": "Um programa espacial nascido numa conserveira",
            "body": "A Comandante Sardinha formou-se no topo do cardume e lidera a unica "
            "agencia espacial com um peixe ao leme. O controlo de missao cabe numa caixa "
            "de peixe, a contagem e cantada, e cada lancamento cheira ao Atlantico.",
            "meta1k": "1 sardinha",
            "meta1v": "aos comandos",
            "meta2k": "400 latas",
            "meta2v": "testadas em queda",
            "meta3k": "12% mais impulso",
            "meta3v": "com extra virgem",
            "meta4k": "0 tripulantes comidos",
            "meta4v": "este mes",
        }
    ),
    ES: SectionContent(
        fields={
            "kicker": "01 · Quienes somos",
            "heading": "Un programa espacial nacido en una conservera",
            "body": "La Comandante Sardina se graduo la primera de su banco y dirige la "
            "unica agencia espacial con un pez al timon. El control de mision cabe en una "
            "caja de pescado, la cuenta atras se canta y cada lanzamiento huele al Atlantico.",
            "meta1k": "1 sardina",
            "meta1v": "a los mandos",
            "meta2k": "400 latas",
            "meta2v": "probadas en caida",
            "meta3k": "12% mas empuje",
            "meta3v": "con virgen extra",
            "meta4k": "0 tripulantes comidos",
            "meta4v": "este mes",
        }
    ),
    FR: SectionContent(
        fields={
            "kicker": "01 · Qui nous sommes",
            "heading": "Un programme spatial ne dans une conserverie",
            "body": "La Commandante Sardine a fini premiere de son banc et dirige la seule "
            "agence spatiale avec un poisson a la barre. Le controle de mission tient dans "
            "une caisse, le compte a rebours est chante, chaque lancement sent l'Atlantique.",
            "meta1k": "1 sardine",
            "meta1v": "aux commandes",
            "meta2k": "400 boites",
            "meta2v": "testees en chute",
            "meta3k": "12% de poussee en plus",
            "meta3v": "a l'extra vierge",
            "meta4k": "0 membre d'equipage mange",
            "meta4v": "ce mois-ci",
        }
    ),
    DE: SectionContent(
        fields={
            "kicker": "01 · Wer wir sind",
            "heading": "Ein Raumfahrtprogramm aus der Konservenfabrik",
            "body": "Kommandantin Sardine schloss als Beste ihres Schwarms ab und fuehrt "
            "die einzige Raumfahrtagentur mit einem Fisch am Ruder. Die Missionskontrolle "
            "passt in eine Fischkiste, der Countdown wird gesungen, jeder Start riecht "
            "nach Atlantik.",
            "meta1k": "1 Sardine",
            "meta1v": "am Steuer",
            "meta2k": "400 Dosen",
            "meta2v": "im Falltest",
            "meta3k": "12% mehr Schub",
            "meta3v": "mit extra vergine",
            "meta4k": "0 Crewmitglieder gegessen",
            "meta4v": "diesen Monat",
        }
    ),
}

HOME_EXPERTISE: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "kicker": "02 · What we do",
            "heading": "Capabilities",
            "row1no": "01",
            "row1t": "Tinned launches",
            "row1d": "Vessels sealed to survive vacuum, rain and curious seagulls.",
            "row2no": "02",
            "row2t": "Olive-oil propulsion",
            "row2d": "Renewable, fragrant, and the neighbours applaud every ignition.",
            "row3no": "03",
            "row3t": "Echo communications",
            "row3d": "If you shout into a tin, Mars hears you eventually.",
            "row4no": "04",
            "row4t": "Stylish re-entry",
            "row4d": "Any fish can fall. Ours falls with intention.",
        }
    ),
    PT: SectionContent(
        fields={
            "kicker": "02 · O que fazemos",
            "heading": "Capacidades",
            "row1no": "01",
            "row1t": "Lancamentos em lata",
            "row1d": "Veiculos selados para sobreviver ao vacuo, a chuva e a gaivotas curiosas.",
            "row2no": "02",
            "row2t": "Propulsao a azeite",
            "row2d": "Renovavel, perfumada, e os vizinhos aplaudem cada ignicao.",
            "row3no": "03",
            "row3t": "Comunicacoes por eco",
            "row3d": "Se gritares para uma lata, Marte acaba por ouvir.",
            "row4no": "04",
            "row4t": "Reentrada com estilo",
            "row4d": "Qualquer peixe cai. O nosso cai com intencao.",
        }
    ),
    ES: SectionContent(
        fields={
            "kicker": "02 · Que hacemos",
            "heading": "Capacidades",
            "row1no": "01",
            "row1t": "Lanzamientos en lata",
            "row1d": "Vehiculos sellados para sobrevivir al vacio, la lluvia y gaviotas curiosas.",
            "row2no": "02",
            "row2t": "Propulsion de aceite de oliva",
            "row2d": "Renovable, fragante, y los vecinos aplauden cada ignicion.",
            "row3no": "03",
            "row3t": "Comunicaciones por eco",
            "row3d": "Si gritas a una lata, Marte acaba oyendote.",
            "row4no": "04",
            "row4t": "Reentrada con estilo",
            "row4d": "Cualquier pez cae. El nuestro cae con intencion.",
        }
    ),
    FR: SectionContent(
        fields={
            "kicker": "02 · Ce que nous faisons",
            "heading": "Capacites",
            "row1no": "01",
            "row1t": "Lancements en boite",
            "row1d": "Des vaisseaux scelles pour survivre au vide, a la pluie et aux mouettes "
            "curieuses.",
            "row2no": "02",
            "row2t": "Propulsion a l'huile d'olive",
            "row2d": "Renouvelable, parfumee, et les voisins applaudissent chaque allumage.",
            "row3no": "03",
            "row3t": "Communications par echo",
            "row3d": "Criez dans une boite : Mars finit par entendre.",
            "row4no": "04",
            "row4t": "Rentree avec style",
            "row4d": "N'importe quel poisson tombe. Le notre tombe avec intention.",
        }
    ),
    DE: SectionContent(
        fields={
            "kicker": "02 · Was wir tun",
            "heading": "Faehigkeiten",
            "row1no": "01",
            "row1t": "Dosenstarts",
            "row1d": "Versiegelte Gefaehrte fuer Vakuum, Regen und neugierige Moewen.",
            "row2no": "02",
            "row2t": "Olivenoel-Antrieb",
            "row2d": "Erneuerbar, duftend, und die Nachbarn applaudieren jeder Zuendung.",
            "row3no": "03",
            "row3t": "Echo-Kommunikation",
            "row3d": "Ruf in eine Dose, und der Mars hoert dich irgendwann.",
            "row4no": "04",
            "row4t": "Wiedereintritt mit Stil",
            "row4d": "Jeder Fisch faellt. Unserer faellt mit Absicht.",
        }
    ),
}

HOME_CTA: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "kicker": "03 · Join the shoal",
            "heading": "Ready to leave the",
            "accent": "ocean?",
            "button": "Meet the crew",
        }
    ),
    PT: SectionContent(
        fields={
            "kicker": "03 · Junta-te ao cardume",
            "heading": "Pronto para sair do",
            "accent": "oceano?",
            "button": "Conhecer a tripulacao",
        }
    ),
    ES: SectionContent(
        fields={
            "kicker": "03 · Unete al banco",
            "heading": "Listo para dejar el",
            "accent": "oceano?",
            "button": "Conocer a la tripulacion",
        }
    ),
    FR: SectionContent(
        fields={
            "kicker": "03 · Rejoignez le banc",
            "heading": "Pret a quitter l'",
            "accent": "ocean ?",
            "button": "Rencontrer l'equipage",
        }
    ),
    DE: SectionContent(
        fields={
            "kicker": "03 · Schliess dich dem Schwarm an",
            "heading": "Bereit, den Ozean zu",
            "accent": "verlassen?",
            "button": "Die Crew treffen",
        }
    ),
}
