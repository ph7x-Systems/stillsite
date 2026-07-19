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
    ),
    PT: SectionContent(
        fields={
            "kicker": "Programa espacial · De conserva · Em orbita",
            "heading": "Uma sardinha a caminho de",
            "accent": "Marte.",
            "lead": "Peixe pequeno. Ambicoes enormes. Cheiro discutivel.",
        },
    ),
    ES: SectionContent(
        fields={
            "kicker": "Programa espacial · En conserva · En orbita",
            "heading": "Una sardina camino de",
            "accent": "Marte.",
            "lead": "Pez pequeno. Ambiciones enormes. Olor discutible.",
        },
    ),
    FR: SectionContent(
        fields={
            "kicker": "Programme spatial · En conserve · En orbite",
            "heading": "Une sardine en route vers",
            "accent": "Mars.",
            "lead": "Petit poisson. Ambitions enormes. Odeur discutable.",
        },
    ),
    DE: SectionContent(
        fields={
            "kicker": "Raumfahrtprogramm · In Dosen · Im Orbit",
            "heading": "Eine Sardine auf dem Weg zum",
            "accent": "Mars.",
            "lead": "Kleiner Fisch. Riesige Ambitionen. Fragwuerdiger Geruch.",
        },
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
                "Ours is a tin. Aerodynamic, shiny, and it never complains. The committee "
                "evaluated carbon fibre, titanium and a second-hand submarine. The tin won on "
                "every criterion that matters: it is watertight, it stacks, and we already own "
                "four hundred of them.\n\n"
                "## The selection process\n\n"
                "Every candidate hull faced three questions:\n\n"
                "- Does it keep the ocean in?\n"
                "- Does it keep the vacuum out?\n"
                "- Can the canteen open it in an emergency?\n\n"
                "The submarine failed the third test. The tin passed all three before lunch.\n\n"
                "Critics say a tin is small. So are we. The fit is, frankly, perfect: snug at "
                "launch, roomy in orbit, and the label doubles as a mission patch.\n\n"
                "We choose to go in the tin not because it is easy, but because it is "
                "watertight. Mostly because it is watertight.",
            ),
            (
                "Escolhemos ir na lata",
                "Não porque é fácil, mas porque é estanque.",
                "Toda a grande viagem começa com o veículo certo.\n\n"
                "O nosso é uma lata. Aerodinâmica, brilhante, e nunca se queixa. O comité "
                "avaliou fibra de carbono, titânio e um submarino em segunda mão. A lata venceu "
                "em todos os critérios que importam: é estanque, empilha-se, e já temos "
                "quatrocentas.\n\n"
                "## O processo de seleção\n\n"
                "Cada casco candidato respondeu a três perguntas:\n\n"
                "- Mantém o oceano lá dentro?\n"
                "- Mantém o vácuo lá fora?\n"
                "- A cantina consegue abri-lo numa emergência?\n\n"
                "O submarino chumbou no terceiro teste. A lata passou nos três antes do "
                "almoço.\n\n"
                "Os críticos dizem que uma lata é pequena. Nós também somos. O ajuste é, "
                "francamente, perfeito: justo no lançamento, espaçoso em órbita, e o rótulo "
                "serve de emblema da missão.\n\n"
                "Escolhemos ir na lata não porque é fácil, mas porque é estanque. Sobretudo "
                "porque é estanque.",
                "escolhemos-ir-na-lata",
            ),
            (
                "Elegimos ir en la lata",
                "No porque sea fácil, sino porque es estanca.",
                "Todo gran viaje empieza con el vehículo correcto.\n\n"
                "El nuestro es una lata. Aerodinámica, brillante, y nunca se queja. El comité "
                "evaluó fibra de carbono, titanio y un submarino de segunda mano. La lata ganó "
                "en todos los criterios que importan: es estanca, se apila, y ya tenemos "
                "cuatrocientas.\n\n"
                "## El proceso de selección\n\n"
                "Cada casco candidato respondió a tres preguntas:\n\n"
                "- ¿Mantiene el océano dentro?\n"
                "- ¿Mantiene el vacío fuera?\n"
                "- ¿Puede abrirla la cantina en una emergencia?\n\n"
                "El submarino suspendió la tercera prueba. La lata aprobó las tres antes de "
                "comer.\n\n"
                "Los críticos dicen que una lata es pequeña. Nosotros también. El ajuste es, "
                "francamente, perfecto: ceñido en el lanzamiento, amplio en órbita, y la "
                "etiqueta sirve de parche de misión.\n\n"
                "Elegimos ir en la lata no porque sea fácil, sino porque es estanca. Sobre "
                "todo porque es estanca.",
                "elegimos-ir-en-la-lata",
            ),
            (
                "Nous choisissons la boîte",
                "Non parce que c'est facile, mais parce que c'est étanche.",
                "Tout grand voyage commence par le bon vaisseau.\n\n"
                "Le nôtre est une boîte. Aérodynamique, brillante, et elle ne se plaint "
                "jamais. Le comité a évalué la fibre de carbone, le titane et un sous-marin "
                "d'occasion. La boîte l'a emporté sur tous les critères qui comptent : elle "
                "est étanche, elle s'empile, et nous en possédons déjà quatre cents.\n\n"
                "## Le processus de sélection\n\n"
                "Chaque coque candidate a répondu à trois questions :\n\n"
                "- Garde-t-elle l'océan dedans ?\n"
                "- Garde-t-elle le vide dehors ?\n"
                "- La cantine peut-elle l'ouvrir en urgence ?\n\n"
                "Le sous-marin a échoué au troisième test. La boîte a réussi les trois avant "
                "le déjeuner.\n\n"
                "Les critiques disent qu'une boîte, c'est petit. Nous aussi. L'ajustement est, "
                "franchement, parfait : serré au lancement, spacieux en orbite, et l'étiquette "
                "fait office d'écusson de mission.\n\n"
                "Nous choisissons la boîte non parce que c'est facile, mais parce que c'est "
                "étanche. Surtout parce que c'est étanche.",
                "nous-choisissons-la-boite",
            ),
            (
                "Wir fliegen in der Dose",
                "Nicht weil es leicht ist, sondern weil sie dicht hält.",
                "Jede große Reise beginnt mit dem richtigen Gefährt.\n\n"
                "Unseres ist eine Dose. Aerodynamisch, glänzend, beschwert sich nie. Das "
                "Komitee prüfte Kohlefaser, Titan und ein gebrauchtes U-Boot. Die Dose gewann "
                "in allen Kriterien, die zählen: Sie ist dicht, sie stapelt sich, und wir "
                "besitzen bereits vierhundert.\n\n"
                "## Das Auswahlverfahren\n\n"
                "Jeder Kandidatenrumpf musste drei Fragen bestehen:\n\n"
                "- Hält sie den Ozean drinnen?\n"
                "- Hält sie das Vakuum draußen?\n"
                "- Kann die Kantine sie im Notfall öffnen?\n\n"
                "Das U-Boot fiel beim dritten Test durch. Die Dose bestand alle drei vor dem "
                "Mittagessen.\n\n"
                "Kritiker sagen, eine Dose sei klein. Wir auch. Die Passform ist, offen "
                "gesagt, perfekt: eng beim Start, geräumig im Orbit, und das Etikett dient "
                "als Missionsabzeichen.\n\n"
                "Wir fliegen in der Dose — nicht weil es leicht ist, sondern weil sie dicht "
                "hält. Vor allem, weil sie dicht hält.",
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
                "Our propulsion team spent a quarter comparing fuels the way serious agencies "
                "do: with clipboards, slow-motion cameras and a designated extinguisher "
                "officer named Rui.\n\n"
                "## Findings\n\n"
                "- Extra virgin: 12% more thrust, notes of pepper and rosemary on ignition.\n"
                "- Virgin: stable burn, acceptable aroma, pairs well with re-entry.\n"
                "- Blended: the committee refuses to discuss the blended incident.\n\n"
                "The neighbours now attend every static fire with bread.\n\n"
                "Safety note: the exhaust plume is technically a vinaigrette hazard. Salads "
                "downwind season themselves, which the village considers a feature.\n\n"
                "Conclusion: viable, fragrant, and the propulsion budget is now "
                "indistinguishable from the canteen budget. We call this synergy.",
            ),
            (
                "Azeite como combustível: resultados preliminares",
                "O extra virgem rende 12% mais e cheira a almoço de domingo.",
                "A bancada de testes ardeu duas vezes, deliciosamente.\n\n"
                "A equipa de propulsão passou um trimestre a comparar combustíveis como as "
                "agências sérias: com pranchetas, câmaras de alta velocidade e um responsável "
                "de extintor chamado Rui.\n\n"
                "## Resultados\n\n"
                "- Extra virgem: 12% mais impulso, notas de pimenta e alecrim na ignição.\n"
                "- Virgem: combustão estável, aroma aceitável, combina bem com a reentrada.\n"
                "- Lote: o comité recusa-se a discutir o incidente do lote.\n\n"
                "Os vizinhos já assistem a todos os testes estáticos com pão.\n\n"
                "Nota de segurança: a pluma de escape é tecnicamente um risco de vinagrete. "
                "As saladas a sotavento temperam-se sozinhas, o que a vila considera uma "
                "funcionalidade.\n\n"
                "Conclusão: viável, perfumado, e o orçamento de propulsão é agora "
                "indistinguível do orçamento da cantina. Chamamos-lhe sinergia.",
                "azeite-como-combustivel",
            ),
            (
                "Aceite de oliva como combustible: resultados preliminares",
                "El virgen extra rinde un 12% más y huele a comida de domingo.",
                "El banco de pruebas ardió dos veces, deliciosamente.\n\n"
                "El equipo de propulsión pasó un trimestre comparando combustibles como las "
                "agencias serias: con carpetas, cámaras de alta velocidad y un responsable de "
                "extintor llamado Rui.\n\n"
                "## Resultados\n\n"
                "- Virgen extra: 12% más de empuje, notas de pimienta y romero al encender.\n"
                "- Virgen: combustión estable, aroma aceptable, marida bien con la reentrada.\n"
                "- Mezcla: el comité se niega a hablar del incidente de la mezcla.\n\n"
                "Los vecinos ya asisten a cada prueba estática con pan.\n\n"
                "Nota de seguridad: la pluma de escape es técnicamente un riesgo de "
                "vinagreta. Las ensaladas a sotavento se aliñan solas, lo que el pueblo "
                "considera una ventaja.\n\n"
                "Conclusión: viable, fragante, y el presupuesto de propulsión ya es "
                "indistinguible del presupuesto de la cantina. Lo llamamos sinergia.",
                "aceite-como-combustible",
            ),
            (
                "L'huile d'olive comme carburant : premiers résultats",
                "L'extra vierge rend 12% de plus et sent le déjeuner du dimanche.",
                "Le banc d'essai a pris feu deux fois, délicieusement.\n\n"
                "L'équipe propulsion a passé un trimestre à comparer les carburants comme les "
                "agences sérieuses : avec des blocs-notes, des caméras à haute vitesse et un "
                "responsable extincteur nommé Rui.\n\n"
                "## Résultats\n\n"
                "- Extra vierge : 12% de poussée en plus, notes de poivre et de romarin à "
                "l'allumage.\n"
                "- Vierge : combustion stable, arôme correct, s'accorde bien avec la "
                "rentrée.\n"
                "- Assemblage : le comité refuse d'évoquer l'incident de l'assemblage.\n\n"
                "Les voisins assistent désormais à chaque essai statique avec du pain.\n\n"
                "Note de sécurité : le panache d'échappement constitue techniquement un "
                "risque de vinaigrette. Les salades sous le vent s'assaisonnent seules, ce "
                "que le village considère comme une fonctionnalité.\n\n"
                "Conclusion : viable, parfumé, et le budget propulsion est désormais "
                "indiscernable du budget cantine. Nous appelons cela une synergie.",
                "huile-olive-comme-carburant",
            ),
            (
                "Olivenöl als Raketentreibstoff: erste Ergebnisse",
                "Extra vergine leistet 12% mehr und riecht nach Sonntagsessen.",
                "Der Prüfstand brannte zweimal, köstlich.\n\n"
                "Das Antriebsteam verglich ein Quartal lang Treibstoffe wie die seriösen "
                "Agenturen: mit Klemmbrettern, Zeitlupenkameras und einem "
                "Feuerlöschbeauftragten namens Rui.\n\n"
                "## Ergebnisse\n\n"
                "- Extra vergine: 12% mehr Schub, Noten von Pfeffer und Rosmarin bei der "
                "Zündung.\n"
                "- Vergine: stabile Verbrennung, akzeptables Aroma, passt gut zum "
                "Wiedereintritt.\n"
                "- Verschnitt: Das Komitee weigert sich, den Verschnitt-Vorfall zu "
                "besprechen.\n\n"
                "Die Nachbarn kommen inzwischen mit Brot zu jedem Standtest.\n\n"
                "Sicherheitshinweis: Die Abgasfahne ist technisch gesehen ein "
                "Vinaigrette-Risiko. Salate in Windrichtung würzen sich selbst, was das Dorf "
                "als Funktion betrachtet.\n\n"
                "Fazit: machbar, duftend, und das Antriebsbudget ist vom Kantinenbudget nicht "
                "mehr zu unterscheiden. Wir nennen das Synergie.",
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
                "Three hundred and ninety-nine survived. The other one was lunch.\n\n"
                "## Method\n\n"
                "Zero gravity is expensive, so we simulate it the traditional way: by "
                "throwing things and looking away. Each can was dropped, catalogued, and "
                "interviewed afterwards about the experience.\n\n"
                "Findings:\n\n"
                "- Dents correlate with attitude, not altitude.\n"
                "- A can that survives the roof survives the re-entry paperwork.\n"
                "- Lids stay on. Morale stays in.\n\n"
                "The review board asked whether a roof is a valid analogue for low orbit. We "
                "invited them to the roof. The question was withdrawn.\n\n"
                "Next quarter we move to phase two: the lighthouse.",
            ),
            (
                "Testes de enlatamento em gravidade zero",
                "No espaço, ninguém ouve a lata abrir.",
                "Deixámos cair quatrocentas latas do telhado da conserveira.\n\n"
                "Trezentas e noventa e nove sobreviveram. A outra foi o almoço.\n\n"
                "## Método\n\n"
                "A gravidade zero é cara, por isso simulamo-la à maneira tradicional: a "
                "atirar coisas e a olhar para o lado. Cada lata foi largada, catalogada e "
                "entrevistada depois sobre a experiência.\n\n"
                "Conclusões:\n\n"
                "- As mossas correlacionam com a atitude, não com a altitude.\n"
                "- Uma lata que sobrevive ao telhado sobrevive à papelada da reentrada.\n"
                "- As tampas ficam. A moral também.\n\n"
                "O conselho de revisão perguntou se um telhado é um análogo válido de órbita "
                "baixa. Convidámo-los para o telhado. A pergunta foi retirada.\n\n"
                "No próximo trimestre passamos à fase dois: o farol.",
                "testes-enlatamento-gravidade-zero",
            ),
            (
                "Pruebas de enlatado en gravedad cero",
                "En el espacio, nadie oye abrirse la lata.",
                "Dejamos caer cuatrocientas latas desde el tejado de la conservera.\n\n"
                "Trescientas noventa y nueve sobrevivieron. La otra fue el almuerzo.\n\n"
                "## Método\n\n"
                "La gravedad cero es cara, así que la simulamos a la manera tradicional: "
                "tirando cosas y mirando hacia otro lado. Cada lata fue soltada, catalogada y "
                "entrevistada después sobre la experiencia.\n\n"
                "Conclusiones:\n\n"
                "- Las abolladuras correlacionan con la actitud, no con la altitud.\n"
                "- Una lata que sobrevive al tejado sobrevive al papeleo de la reentrada.\n"
                "- Las tapas se quedan. La moral también.\n\n"
                "La junta de revisión preguntó si un tejado es un análogo válido de órbita "
                "baja. Los invitamos al tejado. La pregunta fue retirada.\n\n"
                "El próximo trimestre pasamos a la fase dos: el faro.",
                "pruebas-enlatado-gravedad-cero",
            ),
            (
                "Essais de mise en boîte en apesanteur",
                "Dans l'espace, personne ne vous entend ouvrir la boîte.",
                "Nous avons lâché quatre cents boîtes du toit de la conserverie.\n\n"
                "Trois cent quatre-vingt-dix-neuf ont survécu. L'autre fut le déjeuner.\n\n"
                "## Méthode\n\n"
                "L'apesanteur coûte cher, alors nous la simulons à l'ancienne : en jetant "
                "des choses et en regardant ailleurs. Chaque boîte a été lâchée, cataloguée, "
                "puis interrogée sur son expérience.\n\n"
                "Constats :\n\n"
                "- Les bosses corrèlent avec l'attitude, pas avec l'altitude.\n"
                "- Une boîte qui survit au toit survit à la paperasse de rentrée.\n"
                "- Les couvercles tiennent. Le moral aussi.\n\n"
                "Le comité de revue a demandé si un toit est un analogue valable de l'orbite "
                "basse. Nous les avons invités sur le toit. La question a été retirée.\n\n"
                "Le trimestre prochain, phase deux : le phare.",
                "essais-mise-en-boite-apesanteur",
            ),
            (
                "Dosen-Tests in Schwerelosigkeit",
                "Im All hört niemand die Dose aufgehen.",
                "Wir haben vierhundert Dosen vom Dach der Konservenfabrik fallen lassen.\n\n"
                "Dreihundertneunundneunzig überlebten. Die andere war das Mittagessen.\n\n"
                "## Methode\n\n"
                "Schwerelosigkeit ist teuer, also simulieren wir sie auf traditionelle Art: "
                "Dinge werfen und weggucken. Jede Dose wurde fallen gelassen, katalogisiert "
                "und anschließend zu ihrer Erfahrung befragt.\n\n"
                "Erkenntnisse:\n\n"
                "- Dellen korrelieren mit der Einstellung, nicht mit der Höhe.\n"
                "- Eine Dose, die das Dach übersteht, übersteht auch den "
                "Wiedereintritts-Papierkram.\n"
                "- Deckel bleiben drauf. Die Moral bleibt drin.\n\n"
                "Der Prüfungsausschuss fragte, ob ein Dach ein gültiges Analogon für den "
                "niedrigen Orbit sei. Wir luden ihn aufs Dach ein. Die Frage wurde "
                "zurückgezogen.\n\n"
                "Nächstes Quartal folgt Phase zwei: der Leuchtturm.",
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
                "Q: Why Mars?\n\n"
                "A: Because the mackerel said it could not be done.\n\n"
                "Q: Most commanders train for years. Your file says you graduated top of "
                "your shoal. What does that involve?\n\n"
                "A: Synchronised turns, cold-water discipline, and never blinking during "
                "safety briefings. I cannot blink anyway. It saves time.\n\n"
                "Q: Mars has no sea.\n\n"
                "A: That is not a question. We are bringing one. It ships in four hundred "
                "parts, each labelled *brine, mission critical*.\n\n"
                "Q: What do you say to people who call the programme a joke?\n\n"
                "A: Laughter is thrust, if you angle it correctly.\n\n"
                "Q: Final words for the crew?\n\n"
                "A: Stay tinned. Stay together. The countdown is a song if you sing it.",
            ),
            (
                "Entrevista com a Comandante Sardinha",
                "Marte não tem mar. Nós levamos um.",
                "P: Porquê Marte?\n\n"
                "R: Porque a cavala disse que era impossível.\n\n"
                "P: A maioria dos comandantes treina durante anos. O seu processo diz que "
                "terminou no topo do cardume. O que é que isso envolve?\n\n"
                "R: Viragens sincronizadas, disciplina de água fria, e nunca pestanejar nos "
                "briefings de segurança. Eu nem consigo pestanejar. Poupa tempo.\n\n"
                "P: Marte não tem mar.\n\n"
                "R: Isso não é uma pergunta. Nós levamos um. Vai em quatrocentas partes, cada "
                "uma rotulada *salmoura, crítica para a missão*.\n\n"
                "P: O que diz a quem chama ao programa uma anedota?\n\n"
                "R: O riso é impulso, se o inclinarmos bem.\n\n"
                "P: Últimas palavras para a tripulação?\n\n"
                "R: Fiquem enlatados. Fiquem juntos. A contagem decrescente é uma canção se a "
                "cantarem.",
                "entrevista-comandante-sardinha",
            ),
            (
                "Entrevista con la Comandante Sardina",
                "Marte no tiene mar. Nosotros llevamos uno.",
                "P: ¿Por qué Marte?\n\n"
                "R: Porque la caballa dijo que era imposible.\n\n"
                "P: La mayoría de los comandantes entrena durante años. Su expediente dice "
                "que terminó la primera de su banco. ¿Qué implica eso?\n\n"
                "R: Giros sincronizados, disciplina de agua fría, y no parpadear jamás en los "
                "briefings de seguridad. Yo ni siquiera puedo parpadear. Ahorra tiempo.\n\n"
                "P: Marte no tiene mar.\n\n"
                "R: Eso no es una pregunta. Nosotros llevamos uno. Viaja en cuatrocientas "
                "partes, cada una etiquetada *salmuera, crítica para la misión*.\n\n"
                "P: ¿Qué le dice a quien llama broma al programa?\n\n"
                "R: La risa es empuje, si se inclina bien.\n\n"
                "P: ¿Últimas palabras para la tripulación?\n\n"
                "R: Seguid enlatados. Seguid juntos. La cuenta atrás es una canción si la "
                "cantáis.",
                "entrevista-comandante-sardina",
            ),
            (
                "Entretien avec la Commandante Sardine",
                "Mars n'a pas de mer. Nous en apportons une.",
                "Q : Pourquoi Mars ?\n\n"
                "R : Parce que le maquereau a dit que c'était impossible.\n\n"
                "Q : La plupart des commandants s'entraînent des années. Votre dossier dit "
                "que vous avez fini première de votre banc. Qu'est-ce que cela implique ?\n\n"
                "R : Des virages synchronisés, la discipline de l'eau froide, et ne jamais "
                "cligner des yeux en briefing de sécurité. Je ne peux pas cligner de toute "
                "façon. Cela fait gagner du temps.\n\n"
                "Q : Mars n'a pas de mer.\n\n"
                "R : Ce n'est pas une question. Nous en apportons une. Elle voyage en quatre "
                "cents pièces, chacune étiquetée *saumure, critique pour la mission*.\n\n"
                "Q : Que répondez-vous à ceux qui traitent le programme de blague ?\n\n"
                "R : Le rire est une poussée, si on l'oriente bien.\n\n"
                "Q : Un dernier mot pour l'équipage ?\n\n"
                "R : Restez en boîte. Restez ensemble. Le compte à rebours est une chanson si "
                "on la chante.",
                "entretien-commandante-sardine",
            ),
            (
                "Interview mit Kommandantin Sardine",
                "Der Mars hat kein Meer. Wir bringen eines mit.",
                "F: Warum der Mars?\n\n"
                "A: Weil die Makrele sagte, es sei unmöglich.\n\n"
                "F: Die meisten Kommandanten trainieren jahrelang. In Ihrer Akte steht, Sie "
                "waren die Beste Ihres Schwarms. Was gehört dazu?\n\n"
                "A: Synchrone Wenden, Kaltwasserdisziplin, und beim Sicherheitsbriefing nie "
                "blinzeln. Ich kann ohnehin nicht blinzeln. Das spart Zeit.\n\n"
                "F: Der Mars hat kein Meer.\n\n"
                "A: Das ist keine Frage. Wir bringen eines mit. Es reist in vierhundert "
                "Teilen, jedes beschriftet mit *Lake, missionskritisch*.\n\n"
                "F: Was sagen Sie Leuten, die das Programm einen Witz nennen?\n\n"
                "A: Lachen ist Schub, wenn man es richtig ausrichtet.\n\n"
                "F: Letzte Worte an die Crew?\n\n"
                "A: Bleibt in der Dose. Bleibt zusammen. Der Countdown ist ein Lied, wenn man "
                "ihn singt.",
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
                "Agenda: everything on the menu is a colleague.\n\n"
                "## Minutes\n\n"
                "The motion *no serving anyone with a personnel file* passed unanimously, "
                "though the tuna abstained, suspiciously.\n\n"
                "Options reviewed:\n\n"
                "- Algae: nutritious, plentiful, terrible at conversation. Approved.\n"
                "- Plankton: approved, pending a headcount that keeps failing.\n"
                "- Bread: contested, as the seagull claims prior ownership of all bread.\n\n"
                "Resolution: the canteen now serves algae, bravely. Morale dipped for a "
                "week, then the chef discovered paprika.\n\n"
                "Meeting forty-three will address the new problem: the algae have "
                "unionised.",
            ),
            (
                "O problema da ementa da cantina",
                "Tudo o que está na ementa é um colega.",
                "Reunião número quarenta e dois do comité de ética.\n\n"
                "Ordem de trabalhos: tudo o que está na ementa é um colega.\n\n"
                "## Ata\n\n"
                "A moção *não servir ninguém com processo individual* passou por "
                "unanimidade, embora o atum se tenha abstido, suspeitosamente.\n\n"
                "Opções analisadas:\n\n"
                "- Algas: nutritivas, abundantes, péssimas à conversa. Aprovadas.\n"
                "- Plâncton: aprovado, pendente de uma contagem que continua a falhar.\n"
                "- Pão: contestado, pois a gaivota reivindica posse anterior de todo o pão.\n\n"
                "Resolução: a cantina passa a servir algas, corajosamente. A moral desceu "
                "uma semana, até o chefe descobrir o pimentão.\n\n"
                "A reunião quarenta e três tratará do novo problema: as algas "
                "sindicalizaram-se.",
                "problema-ementa-cantina",
            ),
            (
                "El problema del menú de la cantina",
                "Todo lo que hay en el menú es un colega.",
                "Reunión número cuarenta y dos del comité de ética.\n\n"
                "Orden del día: todo lo que hay en el menú es un colega.\n\n"
                "## Acta\n\n"
                "La moción *no servir a nadie con expediente de personal* se aprobó por "
                "unanimidad, aunque el atún se abstuvo, sospechosamente.\n\n"
                "Opciones revisadas:\n\n"
                "- Algas: nutritivas, abundantes, pésimas conversadoras. Aprobadas.\n"
                "- Plancton: aprobado, pendiente de un recuento que sigue fallando.\n"
                "- Pan: impugnado, pues la gaviota reclama propiedad previa de todo el pan.\n\n"
                "Resolución: la cantina ahora sirve algas, valientemente. La moral bajó una "
                "semana, hasta que el chef descubrió el pimentón.\n\n"
                "La reunión cuarenta y tres abordará el nuevo problema: las algas se han "
                "sindicado.",
                "problema-menu-cantina",
            ),
            (
                "Le problème du menu de la cantine",
                "Tout ce qui est au menu est un collègue.",
                "Réunion numéro quarante-deux du comité d'éthique.\n\n"
                "Ordre du jour : tout ce qui est au menu est un collègue.\n\n"
                "## Compte rendu\n\n"
                "La motion *ne servir personne ayant un dossier du personnel* a été adoptée "
                "à l'unanimité, quoique le thon se soit abstenu, curieusement.\n\n"
                "Options examinées :\n\n"
                "- Algues : nutritives, abondantes, piètres causeuses. Approuvées.\n"
                "- Plancton : approuvé, en attente d'un recensement qui échoue toujours.\n"
                "- Pain : contesté, la mouette revendiquant la propriété de tout le pain.\n\n"
                "Résolution : la cantine sert désormais des algues, courageusement. Le moral "
                "a baissé une semaine, puis le chef a découvert le paprika.\n\n"
                "La réunion quarante-trois traitera du nouveau problème : les algues se sont "
                "syndiquées.",
                "probleme-menu-cantine",
            ),
            (
                "Das Kantinen-Menü-Problem",
                "Alles auf der Karte ist ein Kollege.",
                "Ethikkommission, Sitzung Nummer zweiundvierzig.\n\n"
                "Tagesordnung: Alles auf der Karte ist ein Kollege.\n\n"
                "## Protokoll\n\n"
                "Der Antrag *niemanden mit Personalakte servieren* wurde einstimmig "
                "angenommen, wobei sich der Thunfisch enthielt — verdächtig.\n\n"
                "Geprüfte Optionen:\n\n"
                "- Algen: nahrhaft, reichlich, miserable Gesprächspartner. Genehmigt.\n"
                "- Plankton: genehmigt, vorbehaltlich einer Zählung, die ständig "
                "fehlschlägt.\n"
                "- Brot: strittig, da die Möwe Alteigentum an sämtlichem Brot geltend "
                "macht.\n\n"
                "Beschluss: Die Kantine serviert jetzt Algen, tapfer. Die Moral sank eine "
                "Woche lang, dann entdeckte der Koch Paprika.\n\n"
                "Sitzung dreiundvierzig widmet sich dem neuen Problem: Die Algen haben sich "
                "gewerkschaftlich organisiert.",
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
                "We were born in the pool. Advantage: Sardine Aerospace.\n\n"
                "## The programme\n\n"
                "Our syllabus is short, because evolution did most of it:\n\n"
                "- Neutral buoyancy: pre-installed.\n"
                "- Life support drills: gills, redundant, twice.\n"
                "- Confined quarters: we sleep four hundred to a tin, voluntarily.\n\n"
                "The hard part is the opposite of the usual: our crew must train for "
                "dryness. Phase one is a damp towel. Phase two is a photograph of a beach. "
                "Phase three, which only the Commander has passed, is standing near a "
                "radiator.\n\n"
                "Graduation is a lap of the harbour in formation, followed by absolutely no "
                "fish jokes at dinner, by order.",
            ),
            (
                "Treinar para o espaço quando já se vive debaixo de água",
                "A flutuabilidade neutra é natural para alguns de nós.",
                "Há agências que treinam astronautas em piscinas.\n\n"
                "Nós nascemos na piscina. Vantagem: Sardine Aerospace.\n\n"
                "## O programa\n\n"
                "O nosso plano de estudos é curto, porque a evolução fez a maior parte:\n\n"
                "- Flutuabilidade neutra: de série.\n"
                "- Exercícios de suporte de vida: guelras, redundantes, em dose dupla.\n"
                "- Espaços confinados: dormimos quatrocentos por lata, voluntariamente.\n\n"
                "A parte difícil é o contrário do costume: a tripulação treina para a "
                "secura. A fase um é uma toalha húmida. A fase dois é uma fotografia de uma "
                "praia. A fase três, que só a Comandante passou, é estar perto de um "
                "aquecedor.\n\n"
                "A graduação é uma volta ao porto em formação, seguida de rigorosamente zero "
                "piadas de peixe ao jantar, por ordem superior.",
                "treinar-espaco-debaixo-de-agua",
            ),
            (
                "Entrenar para el espacio cuando ya vives bajo el agua",
                "La flotabilidad neutra es natural para algunos de nosotros.",
                "Hay agencias que entrenan astronautas en piscinas.\n\n"
                "Nosotros nacimos en la piscina. Ventaja: Sardine Aerospace.\n\n"
                "## El programa\n\n"
                "Nuestro temario es corto, porque la evolución hizo casi todo:\n\n"
                "- Flotabilidad neutra: de serie.\n"
                "- Simulacros de soporte vital: branquias, redundantes, por partida doble.\n"
                "- Espacios confinados: dormimos cuatrocientos por lata, voluntariamente.\n\n"
                "Lo difícil es lo contrario de lo habitual: la tripulación entrena la "
                "sequedad. La fase uno es una toalla húmeda. La fase dos, la foto de una "
                "playa. La fase tres, que solo la Comandante ha superado, es acercarse a un "
                "radiador.\n\n"
                "La graduación es una vuelta al puerto en formación, seguida de "
                "absolutamente ningún chiste de peces en la cena, por orden.",
                "entrenar-espacio-bajo-el-agua",
            ),
            (
                "S'entraîner pour l'espace quand on vit déjà sous l'eau",
                "La flottabilité neutre est naturelle pour certains d'entre nous.",
                "Certaines agences entraînent leurs astronautes en piscine.\n\n"
                "Nous sommes nés dans la piscine. Avantage : Sardine Aerospace.\n\n"
                "## Le programme\n\n"
                "Notre cursus est court, l'évolution ayant fait l'essentiel :\n\n"
                "- Flottabilité neutre : de série.\n"
                "- Exercices de survie : des branchies, redondantes, en double.\n"
                "- Espaces confinés : nous dormons à quatre cents par boîte, "
                "volontairement.\n\n"
                "Le plus dur est l'inverse de l'habitude : l'équipage s'entraîne à la "
                "sécheresse. Phase un : une serviette humide. Phase deux : la photo d'une "
                "plage. Phase trois, que seule la Commandante a réussie : se tenir près "
                "d'un radiateur.\n\n"
                "Le diplôme se passe en un tour du port en formation, suivi de zéro "
                "plaisanterie sur les poissons au dîner, sur ordre.",
                "entrainement-espace-sous-eau",
            ),
            (
                "Fürs All trainieren, wenn man schon unter Wasser lebt",
                "Neutraler Auftrieb liegt manchen von uns im Blut.",
                "Manche Agenturen trainieren Astronauten im Schwimmbecken.\n\n"
                "Wir sind im Becken geboren. Vorteil: Sardine Aerospace.\n\n"
                "## Das Programm\n\n"
                "Unser Lehrplan ist kurz, denn die Evolution hat das meiste erledigt:\n\n"
                "- Neutraler Auftrieb: ab Werk.\n"
                "- Lebenserhaltungsübungen: Kiemen, redundant, doppelt.\n"
                "- Enge Quartiere: Wir schlafen zu vierhundert pro Dose, freiwillig.\n\n"
                "Schwierig ist das Gegenteil des Üblichen: Die Crew trainiert Trockenheit. "
                "Phase eins ist ein feuchtes Handtuch. Phase zwei ein Foto von einem Strand. "
                "Phase drei, die nur die Kommandantin bestanden hat: neben einer Heizung "
                "stehen.\n\n"
                "Der Abschluss ist eine Hafenrunde in Formation, gefolgt von exakt null "
                "Fischwitzen beim Abendessen, auf Befehl.",
                "training-fuers-all-unter-wasser",
            ),
        ),
    ),
    "seagull-air-traffic-control": (
        "missions",
        ("crew", "safety"),
        6,
        _article(
            (
                "Our air traffic controller is a seagull",
                "He accepted the job for bread. He is excellent.",
                "Recruitment for Range Safety Officer was going badly until Gerald "
                "arrived.\n\n"
                "Gerald is a herring gull with nine thousand unassisted landings and a "
                "working knowledge of every thermal in the bay. He accepted the position for "
                "bread, payable weekly, in advance.\n\n"
                "## Performance review\n\n"
                "- Departures cleared this quarter: 61.\n"
                "- Birds warned off the pad: 340, plus one drone he still refuses to "
                "discuss.\n"
                "- Bread consumed: within budget, barely.\n\n"
                "Gerald's only incident report reads *saw chips, investigated*. The board "
                "accepted this, as chips were indeed present.\n\n"
                "His contract renews automatically at dawn, when he lands on the flame "
                "deflector and screams once, which legal has confirmed counts as a "
                "signature.",
            ),
            (
                "O nosso controlador aéreo é uma gaivota",
                "Aceitou o cargo a troco de pão. É excelente.",
                "O recrutamento para Oficial de Segurança de Lançamento corria mal até "
                "chegar o Gerardo.\n\n"
                "O Gerardo é uma gaivota-de-patas-amarelas com nove mil aterragens sem "
                "assistência e conhecimento prático de todas as térmicas da baía. Aceitou o "
                "cargo a troco de pão, pago semanalmente, adiantado.\n\n"
                "## Avaliação de desempenho\n\n"
                "- Partidas autorizadas este trimestre: 61.\n"
                "- Aves afastadas da plataforma: 340, mais um drone de que ainda se recusa a "
                "falar.\n"
                "- Pão consumido: dentro do orçamento, por pouco.\n\n"
                "O único relatório de incidente do Gerardo diz *vi batatas fritas, "
                "investiguei*. O conselho aceitou-o, pois havia de facto batatas fritas.\n\n"
                "O contrato renova-se automaticamente ao amanhecer, quando ele aterra no "
                "defletor de chama e grita uma vez, o que o departamento jurídico confirmou "
                "valer como assinatura.",
                "controlador-aereo-gaivota",
            ),
            (
                "Nuestro controlador aéreo es una gaviota",
                "Aceptó el puesto por pan. Es excelente.",
                "La contratación del Oficial de Seguridad de Lanzamiento iba mal hasta que "
                "llegó Gerardo.\n\n"
                "Gerardo es una gaviota patiamarilla con nueve mil aterrizajes sin "
                "asistencia y conocimiento práctico de todas las térmicas de la bahía. "
                "Aceptó el puesto por pan, pagadero semanalmente, por adelantado.\n\n"
                "## Evaluación de desempeño\n\n"
                "- Salidas autorizadas este trimestre: 61.\n"
                "- Aves alejadas de la plataforma: 340, más un dron del que aún se niega a "
                "hablar.\n"
                "- Pan consumido: dentro del presupuesto, por poco.\n\n"
                "El único informe de incidentes de Gerardo dice *vi patatas fritas, "
                "investigué*. La junta lo aceptó, pues efectivamente había patatas.\n\n"
                "Su contrato se renueva automáticamente al amanecer, cuando aterriza en el "
                "deflector de llama y grita una vez, lo que el departamento legal confirmó "
                "que cuenta como firma.",
                "controlador-aereo-gaviota",
            ),
            (
                "Notre contrôleur aérien est une mouette",
                "Il a accepté le poste contre du pain. Il est excellent.",
                "Le recrutement de l'Officier de Sécurité du Pas de Tir allait mal, jusqu'à "
                "l'arrivée de Gérard.\n\n"
                "Gérard est un goéland argenté fort de neuf mille atterrissages sans "
                "assistance et d'une connaissance pratique de toutes les thermiques de la "
                "baie. Il a accepté le poste contre du pain, payable chaque semaine, "
                "d'avance.\n\n"
                "## Entretien annuel\n\n"
                "- Départs autorisés ce trimestre : 61.\n"
                "- Oiseaux écartés du pas de tir : 340, plus un drone dont il refuse "
                "toujours de parler.\n"
                "- Pain consommé : dans le budget, de justesse.\n\n"
                "Le seul rapport d'incident de Gérard dit *vu des frites, enquêté*. Le "
                "conseil l'a accepté, des frites étant effectivement présentes.\n\n"
                "Son contrat se renouvelle automatiquement à l'aube, quand il se pose sur le "
                "déflecteur de flammes et crie une fois, ce que le service juridique a "
                "confirmé valoir signature.",
                "controleur-aerien-mouette",
            ),
            (
                "Unser Fluglotse ist eine Möwe",
                "Er nahm den Job für Brot an. Er ist hervorragend.",
                "Die Suche nach einem Startsicherheitsoffizier lief schlecht, bis Gerhard "
                "kam.\n\n"
                "Gerhard ist eine Silbermöwe mit neuntausend Landungen ohne Assistenz und "
                "praktischer Kenntnis jeder Thermik der Bucht. Er nahm die Stelle für Brot "
                "an, zahlbar wöchentlich, im Voraus.\n\n"
                "## Leistungsbeurteilung\n\n"
                "- Freigegebene Starts dieses Quartal: 61.\n"
                "- Von der Rampe vertriebene Vögel: 340, plus eine Drohne, über die er "
                "weiterhin schweigt.\n"
                "- Verzehrtes Brot: im Budget, knapp.\n\n"
                "Gerhards einziger Vorfallbericht lautet *Pommes gesehen, ermittelt*. Der "
                "Vorstand akzeptierte ihn, da tatsächlich Pommes vorlagen.\n\n"
                "Sein Vertrag verlängert sich automatisch im Morgengrauen, wenn er auf dem "
                "Flammenabweiser landet und einmal schreit — laut Rechtsabteilung gilt das "
                "als Unterschrift.",
                "fluglotse-moewe",
            ),
        ),
    ),
    "tin-opener-incident-report": (
        "engineering",
        ("safety", "testing"),
        7,
        _article(
            (
                "Incident report: the tin opener",
                "A near miss involving our own hull design. Lessons were learned.",
                "At 09:14 on a Tuesday, an intern brought a tin opener into mission "
                "control.\n\n"
                "Nothing happened. That is the point of a near-miss report: writing down the "
                "nothing, in detail, before it becomes a something.\n\n"
                "## Timeline\n\n"
                "- 09:14 — the opener enters the building, in a lunchbox, labelled *for "
                "beans*.\n"
                "- 09:15 — four hundred crew members feel a chill, simultaneously.\n"
                "- 09:16 — the Commander, without blinking, quarantines the beans.\n"
                "- 09:30 — the opener leaves the premises under escort.\n\n"
                "## Corrective actions\n\n"
                "Openers are now stored with the fireworks, behind two locks and a very "
                "stern poster. The beans were released without charge.\n\n"
                "The intern is fine, and has been promoted to Head of Hazard "
                "Identification, effective immediately, because honestly, nobody else "
                "spotted it.",
            ),
            (
                "Relatório de incidente: o abre-latas",
                "Um quase-acidente com o nosso próprio casco. Aprendemos lições.",
                "Às 09h14 de uma terça-feira, um estagiário entrou no controlo de missão com "
                "um abre-latas.\n\n"
                "Não aconteceu nada. É esse o objetivo de um relatório de quase-acidente: "
                "registar o nada, em detalhe, antes que se torne um alguma-coisa.\n\n"
                "## Cronologia\n\n"
                "- 09h14 — o abre-latas entra no edifício, numa lancheira, rotulado *para o "
                "feijão*.\n"
                "- 09h15 — quatrocentos tripulantes sentem um arrepio, em simultâneo.\n"
                "- 09h16 — a Comandante, sem pestanejar, põe o feijão de quarentena.\n"
                "- 09h30 — o abre-latas sai das instalações sob escolta.\n\n"
                "## Ações corretivas\n\n"
                "Os abre-latas passam a ser guardados com o fogo de artifício, atrás de duas "
                "fechaduras e de um cartaz muito severo. O feijão foi libertado sem "
                "acusações.\n\n"
                "O estagiário está bem e foi promovido a Chefe de Identificação de Perigos, "
                "com efeito imediato, porque sinceramente mais ninguém reparou.",
                "relatorio-incidente-abre-latas",
            ),
            (
                "Informe de incidente: el abrelatas",
                "Un casi accidente con nuestro propio casco. Se aprendieron lecciones.",
                "A las 09:14 de un martes, un becario entró en control de misión con un "
                "abrelatas.\n\n"
                "No pasó nada. Ese es el objetivo de un informe de casi accidente: registrar "
                "la nada, con detalle, antes de que se convierta en un algo.\n\n"
                "## Cronología\n\n"
                "- 09:14 — el abrelatas entra en el edificio, en una fiambrera, etiquetado "
                "*para las alubias*.\n"
                "- 09:15 — cuatrocientos tripulantes sienten un escalofrío, a la vez.\n"
                "- 09:16 — la Comandante, sin parpadear, pone las alubias en cuarentena.\n"
                "- 09:30 — el abrelatas abandona las instalaciones escoltado.\n\n"
                "## Acciones correctivas\n\n"
                "Los abrelatas se guardan ahora con los fuegos artificiales, tras dos "
                "cerraduras y un cartel muy severo. Las alubias quedaron libres sin "
                "cargos.\n\n"
                "El becario está bien y ha sido ascendido a Jefe de Identificación de "
                "Riesgos, con efecto inmediato, porque sinceramente nadie más lo vio.",
                "informe-incidente-abrelatas",
            ),
            (
                "Rapport d'incident : l'ouvre-boîte",
                "Un incident évité impliquant notre propre coque. Des leçons ont été tirées.",
                "À 9h14 un mardi, un stagiaire est entré en salle de contrôle avec un "
                "ouvre-boîte.\n\n"
                "Il ne s'est rien passé. C'est tout l'intérêt d'un rapport d'incident évité "
                ": consigner le rien, en détail, avant qu'il ne devienne un "
                "quelque-chose.\n\n"
                "## Chronologie\n\n"
                "- 9h14 — l'ouvre-boîte entre dans le bâtiment, dans une boîte à déjeuner, "
                "étiqueté *pour les haricots*.\n"
                "- 9h15 — quatre cents membres d'équipage frissonnent, simultanément.\n"
                "- 9h16 — la Commandante, sans ciller, met les haricots en quarantaine.\n"
                "- 9h30 — l'ouvre-boîte quitte les lieux sous escorte.\n\n"
                "## Actions correctives\n\n"
                "Les ouvre-boîtes sont désormais rangés avec les feux d'artifice, derrière "
                "deux serrures et une affiche très sévère. Les haricots ont été relâchés "
                "sans poursuites.\n\n"
                "Le stagiaire va bien et a été promu Chef de l'Identification des Dangers, "
                "avec effet immédiat, car franchement, personne d'autre ne l'avait vu.",
                "rapport-incident-ouvre-boite",
            ),
            (
                "Vorfallbericht: der Dosenöffner",
                "Ein Beinaheunfall mit unserem eigenen Rumpfdesign. Lehren wurden gezogen.",
                "Um 9:14 Uhr an einem Dienstag brachte ein Praktikant einen Dosenöffner in "
                "die Missionskontrolle.\n\n"
                "Nichts geschah. Genau darum geht es bei einem Beinahe-Bericht: das Nichts "
                "im Detail festzuhalten, bevor es ein Etwas wird.\n\n"
                "## Zeitablauf\n\n"
                "- 9:14 — der Öffner betritt das Gebäude, in einer Brotdose, beschriftet "
                "*für die Bohnen*.\n"
                "- 9:15 — vierhundert Crewmitglieder fröstelt es, gleichzeitig.\n"
                "- 9:16 — die Kommandantin stellt, ohne zu blinzeln, die Bohnen unter "
                "Quarantäne.\n"
                "- 9:30 — der Öffner verlässt das Gelände unter Eskorte.\n\n"
                "## Korrekturmaßnahmen\n\n"
                "Dosenöffner lagern jetzt bei den Feuerwerkskörpern, hinter zwei Schlössern "
                "und einem sehr strengen Plakat. Die Bohnen wurden ohne Anklage "
                "freigelassen.\n\n"
                "Dem Praktikanten geht es gut; er wurde mit sofortiger Wirkung zum Leiter "
                "der Gefahrenerkennung befördert, denn ehrlich gesagt hat es sonst niemand "
                "bemerkt.",
                "vorfallbericht-dosenoeffner",
            ),
        ),
    ),
    "ground-crew-swimming-lessons": (
        "missions",
        ("training", "crew"),
        8,
        _article(
            (
                "We are teaching the ground crew to swim",
                "Integration works both ways.",
                "Half our staff live in the water. The other half sink.\n\n"
                "Integration works both ways, so Fridays are now swimming lessons for the "
                "ground crew, taught by the flight crew, who find the whole thing "
                "hilarious.\n\n"
                "## Curriculum\n\n"
                "- Week one: floating, and the theory of not panicking.\n"
                "- Week two: not panicking, applied.\n"
                "- Week three: synchronised turns. Optional, but the flight crew grades "
                "them anyway.\n\n"
                "Progress is measured in biscuits, our most stable currency. The accountant "
                "can now do a full length underwater, which has made audit season genuinely "
                "frightening.\n\n"
                "Next term, the exchange continues: the flight crew learns to use stairs.",
            ),
            (
                "Estamos a ensinar a equipa de terra a nadar",
                "A integração funciona nos dois sentidos.",
                "Metade do pessoal vive dentro de água. A outra metade afunda-se.\n\n"
                "A integração funciona nos dois sentidos, por isso as sextas-feiras passaram "
                "a ser aulas de natação para a equipa de terra, dadas pela tripulação de "
                "voo, que acha tudo isto hilariante.\n\n"
                "## Currículo\n\n"
                "- Semana um: flutuar, e a teoria de não entrar em pânico.\n"
                "- Semana dois: não entrar em pânico, na prática.\n"
                "- Semana três: viragens sincronizadas. Opcional, mas a tripulação de voo "
                "dá nota na mesma.\n\n"
                "O progresso mede-se em bolachas, a nossa moeda mais estável. O contabilista "
                "já faz uma piscina inteira debaixo de água, o que tornou a época de "
                "auditorias genuinamente assustadora.\n\n"
                "No próximo período o intercâmbio continua: a tripulação de voo aprende a "
                "usar escadas.",
                "aulas-natacao-equipa-terra",
            ),
            (
                "Estamos enseñando a nadar al equipo de tierra",
                "La integración funciona en ambos sentidos.",
                "La mitad del personal vive en el agua. La otra mitad se hunde.\n\n"
                "La integración funciona en ambos sentidos, así que los viernes ahora hay "
                "clases de natación para el equipo de tierra, impartidas por la tripulación "
                "de vuelo, que encuentra todo esto graciosísimo.\n\n"
                "## Plan de estudios\n\n"
                "- Semana uno: flotar, y la teoría de no entrar en pánico.\n"
                "- Semana dos: no entrar en pánico, aplicado.\n"
                "- Semana tres: giros sincronizados. Opcional, pero la tripulación de vuelo "
                "puntúa igualmente.\n\n"
                "El progreso se mide en galletas, nuestra moneda más estable. El contable ya "
                "hace un largo entero bajo el agua, lo que ha vuelto la temporada de "
                "auditorías genuinamente aterradora.\n\n"
                "El próximo trimestre el intercambio continúa: la tripulación de vuelo "
                "aprende a usar escaleras.",
                "clases-natacion-equipo-tierra",
            ),
            (
                "Nous apprenons à nager à l'équipe au sol",
                "L'intégration marche dans les deux sens.",
                "La moitié du personnel vit dans l'eau. L'autre moitié coule.\n\n"
                "L'intégration marche dans les deux sens : le vendredi est donc désormais "
                "jour de natation pour l'équipe au sol, sous la direction de l'équipage de "
                "vol, qui trouve tout cela hilarant.\n\n"
                "## Programme\n\n"
                "- Semaine une : flotter, et la théorie du non-affolement.\n"
                "- Semaine deux : le non-affolement, en pratique.\n"
                "- Semaine trois : virages synchronisés. Facultatif, mais l'équipage de vol "
                "note quand même.\n\n"
                "Les progrès se mesurent en biscuits, notre monnaie la plus stable. Le "
                "comptable fait maintenant une longueur entière sous l'eau, ce qui rend la "
                "saison des audits véritablement effrayante.\n\n"
                "Le trimestre prochain, l'échange continue : l'équipage de vol apprend à "
                "utiliser les escaliers.",
                "cours-natation-equipe-sol",
            ),
            (
                "Wir bringen der Bodencrew das Schwimmen bei",
                "Integration funktioniert in beide Richtungen.",
                "Die Hälfte unserer Belegschaft lebt im Wasser. Die andere Hälfte geht "
                "unter.\n\n"
                "Integration funktioniert in beide Richtungen, deshalb ist freitags jetzt "
                "Schwimmunterricht für die Bodencrew — unterrichtet von der Flugcrew, die "
                "das Ganze urkomisch findet.\n\n"
                "## Lehrplan\n\n"
                "- Woche eins: Treiben, und die Theorie des Nicht-in-Panik-Geratens.\n"
                "- Woche zwei: Nicht in Panik geraten, angewandt.\n"
                "- Woche drei: synchrone Wenden. Freiwillig, aber die Flugcrew benotet "
                "trotzdem.\n\n"
                "Fortschritt wird in Keksen gemessen, unserer stabilsten Währung. Der "
                "Buchhalter schafft inzwischen eine ganze Bahn unter Wasser, was die "
                "Prüfungssaison aufrichtig furchteinflößend macht.\n\n"
                "Nächstes Semester geht der Austausch weiter: Die Flugcrew lernt "
                "Treppensteigen.",
                "schwimmunterricht-bodencrew",
            ),
        ),
    ),
    "the-great-olive-oil-audit": (
        "canteen",
        ("food", "fuel"),
        9,
        _article(
            (
                "The great olive oil audit",
                "Propulsion and the canteen share one budget line. It went as expected.",
                "Finance flagged an anomaly: the propulsion budget and the canteen budget "
                "are the same budget.\n\n"
                "The audit lasted three days and produced the following figures:\n\n"
                "- Litres purchased: 1,200.\n"
                "- Litres burned for science: 700.\n"
                "- Litres burned for lunch: 460.\n"
                "- Litres unaccounted for: 40, traced to the chef's *emergency reserve*, "
                "which is a salad.\n\n"
                "## Ruling\n\n"
                "The board ruled that lunch is propulsion, citing morale-per-newton figures "
                "nobody could refute.\n\n"
                "The line item has been renamed *thrust, general*. Finance has stopped "
                "asking questions, which we consider our greatest engineering achievement "
                "to date.",
            ),
            (
                "A grande auditoria ao azeite",
                "Propulsão e cantina partilham uma rubrica. Correu como esperado.",
                "As finanças sinalizaram uma anomalia: o orçamento da propulsão e o "
                "orçamento da cantina são o mesmo orçamento.\n\n"
                "A auditoria durou três dias e produziu os seguintes números:\n\n"
                "- Litros comprados: 1.200.\n"
                "- Litros queimados pela ciência: 700.\n"
                "- Litros queimados ao almoço: 460.\n"
                "- Litros por justificar: 40, rastreados até à *reserva de emergência* do "
                "chefe, que é uma salada.\n\n"
                "## Decisão\n\n"
                "O conselho deliberou que o almoço é propulsão, citando números de moral "
                "por newton que ninguém conseguiu refutar.\n\n"
                "A rubrica foi renomeada *impulso, geral*. As finanças deixaram de fazer "
                "perguntas, o que consideramos o nosso maior feito de engenharia até à "
                "data.",
                "grande-auditoria-azeite",
            ),
            (
                "La gran auditoría del aceite de oliva",
                "Propulsión y cantina comparten una partida. Salió como se esperaba.",
                "Finanzas señaló una anomalía: el presupuesto de propulsión y el de la "
                "cantina son el mismo presupuesto.\n\n"
                "La auditoría duró tres días y arrojó las siguientes cifras:\n\n"
                "- Litros comprados: 1.200.\n"
                "- Litros quemados por la ciencia: 700.\n"
                "- Litros quemados en el almuerzo: 460.\n"
                "- Litros sin justificar: 40, rastreados hasta la *reserva de emergencia* "
                "del chef, que es una ensalada.\n\n"
                "## Fallo\n\n"
                "La junta dictaminó que el almuerzo es propulsión, citando cifras de moral "
                "por newton que nadie pudo rebatir.\n\n"
                "La partida pasa a llamarse *empuje, general*. Finanzas ha dejado de hacer "
                "preguntas, lo que consideramos nuestro mayor logro de ingeniería hasta la "
                "fecha.",
                "gran-auditoria-aceite",
            ),
            (
                "Le grand audit de l'huile d'olive",
                "Propulsion et cantine partagent une ligne budgétaire. Tout s'est passé "
                "comme prévu.",
                "La direction financière a signalé une anomalie : le budget propulsion et "
                "le budget cantine sont le même budget.\n\n"
                "L'audit a duré trois jours et produit les chiffres suivants :\n\n"
                "- Litres achetés : 1 200.\n"
                "- Litres brûlés pour la science : 700.\n"
                "- Litres brûlés au déjeuner : 460.\n"
                "- Litres non justifiés : 40, remontés jusqu'à la *réserve d'urgence* du "
                "chef, qui est une salade.\n\n"
                "## Verdict\n\n"
                "Le conseil a statué que le déjeuner est de la propulsion, en citant des "
                "chiffres de moral par newton que personne n'a pu réfuter.\n\n"
                "La ligne a été renommée *poussée, générale*. Les finances ont cessé de "
                "poser des questions, ce que nous considérons comme notre plus grande "
                "réussite d'ingénierie à ce jour.",
                "grand-audit-huile-olive",
            ),
            (
                "Die große Olivenöl-Prüfung",
                "Antrieb und Kantine teilen sich einen Budgetposten. Es kam wie erwartet.",
                "Die Finanzabteilung meldete eine Anomalie: Das Antriebsbudget und das "
                "Kantinenbudget sind dasselbe Budget.\n\n"
                "Die Prüfung dauerte drei Tage und ergab folgende Zahlen:\n\n"
                "- Gekaufte Liter: 1.200.\n"
                "- Für die Wissenschaft verbrannte Liter: 700.\n"
                "- Fürs Mittagessen verbrannte Liter: 460.\n"
                "- Unbelegte Liter: 40, zurückverfolgt zur *Notreserve* des Kochs, die ein "
                "Salat ist.\n\n"
                "## Entscheidung\n\n"
                "Der Vorstand entschied, dass Mittagessen Antrieb ist, unter Verweis auf "
                "Moral-pro-Newton-Zahlen, die niemand widerlegen konnte.\n\n"
                "Der Posten heißt jetzt *Schub, allgemein*. Die Finanzabteilung stellt "
                "keine Fragen mehr, was wir für unsere bisher größte Ingenieursleistung "
                "halten.",
                "grosse-olivenoel-pruefung",
            ),
        ),
    ),
    "portable-sea-feasibility-study": (
        "engineering",
        ("mars", "testing"),
        10,
        _article(
            (
                "A portable sea: feasibility study",
                "Mars lacks one obvious amenity. Engineering has thoughts.",
                "Mars has mountains, canyons and excellent sunsets. It does not have a "
                "sea. For most agencies this is trivia; for us it is a blocker.\n\n"
                "## Requirements\n\n"
                "The portable sea must be:\n\n"
                "- Salty to specification (Atlantic, house style).\n"
                "- Modular: four hundred parts, each labelled *brine, mission critical*.\n"
                "- Calm on Sundays.\n\n"
                "Phase one prototypes include a very committed paddling pool. It currently "
                "holds 0.0000004% of a sea, which the team insists on calling *a rounding "
                "sea*.\n\n"
                "Wave generation is solved, in the sense that Mars has two moons and we "
                "intend to use whichever behaves.\n\n"
                "Status: feasible, pending tide negotiations.",
            ),
            (
                "Um mar portátil: estudo de viabilidade",
                "Falta a Marte uma comodidade óbvia. A engenharia tem ideias.",
                "Marte tem montanhas, desfiladeiros e pores-do-sol excelentes. Não tem "
                "mar. Para a maioria das agências é uma curiosidade; para nós é um "
                "impedimento.\n\n"
                "## Requisitos\n\n"
                "O mar portátil tem de ser:\n\n"
                "- Salgado conforme a especificação (Atlântico, ao estilo da casa).\n"
                "- Modular: quatrocentas partes, cada uma rotulada *salmoura, crítica para "
                "a missão*.\n"
                "- Calmo aos domingos.\n\n"
                "Os protótipos da fase um incluem uma piscina insuflável muito empenhada. "
                "Contém neste momento 0,0000004% de um mar, a que a equipa insiste em "
                "chamar *um mar de arredondamento*.\n\n"
                "A geração de ondas está resolvida, no sentido em que Marte tem duas luas e "
                "tencionamos usar a que se portar bem.\n\n"
                "Estado: viável, pendente de negociações com a maré.",
                "mar-portatil-estudo-viabilidade",
            ),
            (
                "Un mar portátil: estudio de viabilidad",
                "A Marte le falta una comodidad obvia. Ingeniería tiene ideas.",
                "Marte tiene montañas, cañones y atardeceres excelentes. No tiene mar. "
                "Para la mayoría de las agencias es una curiosidad; para nosotros, un "
                "bloqueo.\n\n"
                "## Requisitos\n\n"
                "El mar portátil debe ser:\n\n"
                "- Salado según especificación (Atlántico, al estilo de la casa).\n"
                "- Modular: cuatrocientas piezas, cada una etiquetada *salmuera, crítica "
                "para la misión*.\n"
                "- Tranquilo los domingos.\n\n"
                "Los prototipos de la fase uno incluyen una piscina hinchable muy "
                "comprometida. Actualmente contiene el 0,0000004% de un mar, que el equipo "
                "insiste en llamar *un mar de redondeo*.\n\n"
                "La generación de olas está resuelta, en el sentido de que Marte tiene dos "
                "lunas y pensamos usar la que se porte bien.\n\n"
                "Estado: viable, pendiente de negociar con la marea.",
                "mar-portatil-estudio-viabilidad",
            ),
            (
                "Une mer portable : étude de faisabilité",
                "Mars manque d'un agrément évident. L'ingénierie a des idées.",
                "Mars a des montagnes, des canyons et d'excellents couchers de soleil. "
                "Elle n'a pas de mer. Pour la plupart des agences, c'est une anecdote ; "
                "pour nous, c'est bloquant.\n\n"
                "## Exigences\n\n"
                "La mer portable doit être :\n\n"
                "- Salée selon la spécification (Atlantique, style maison).\n"
                "- Modulaire : quatre cents pièces, chacune étiquetée *saumure, critique "
                "pour la mission*.\n"
                "- Calme le dimanche.\n\n"
                "Les prototypes de phase un comptent une pataugeoire très investie. Elle "
                "contient actuellement 0,0000004 % d'une mer, que l'équipe tient à appeler "
                "*une mer d'arrondi*.\n\n"
                "La génération de vagues est résolue, en ce sens que Mars a deux lunes et "
                "que nous comptons utiliser celle qui se tient bien.\n\n"
                "Statut : faisable, sous réserve de négociations avec la marée.",
                "mer-portable-etude-faisabilite",
            ),
            (
                "Ein tragbares Meer: Machbarkeitsstudie",
                "Dem Mars fehlt eine offensichtliche Annehmlichkeit. Das Engineering hat Ideen.",
                "Der Mars hat Berge, Schluchten und ausgezeichnete Sonnenuntergänge. Er "
                "hat kein Meer. Für die meisten Agenturen ist das Trivia; für uns ein "
                "Blocker.\n\n"
                "## Anforderungen\n\n"
                "Das tragbare Meer muss sein:\n\n"
                "- Salzig nach Spezifikation (Atlantik, Hausstil).\n"
                "- Modular: vierhundert Teile, jedes beschriftet mit *Lake, "
                "missionskritisch*.\n"
                "- Sonntags ruhig.\n\n"
                "Zu den Phase-eins-Prototypen zählt ein sehr engagiertes Planschbecken. Es "
                "fasst derzeit 0,0000004% eines Meeres, was das Team beharrlich *ein "
                "Rundungsmeer* nennt.\n\n"
                "Die Wellenerzeugung ist gelöst — insofern, als der Mars zwei Monde hat "
                "und wir den benutzen werden, der sich benimmt.\n\n"
                "Status: machbar, vorbehaltlich der Gezeitenverhandlungen.",
                "tragbares-meer-machbarkeitsstudie",
            ),
        ),
    ),
    "mission-patch-committee": (
        "missions",
        ("crew", "launch"),
        11,
        _article(
            (
                "The mission patch committee has opinions",
                "Forty designs, one tin, no survivors.",
                "Designing a mission patch should take an afternoon. We are on week "
                "six.\n\n"
                "## The shortlist\n\n"
                "- A sardine, heroic, looking left: rejected — *looks like the tuna*.\n"
                "- A sardine, heroic, looking right: rejected — the tuna complained "
                "anyway.\n"
                "- The tin, plain, with one star: approved unanimously, then un-approved "
                "when the star was identified as a crumb on the projector.\n\n"
                "The committee has now reviewed forty designs and approved none of them, a "
                "record the previous patch committee held for a single afternoon.\n\n"
                "The Commander ended the deadlock by holding up an actual tin: *the label "
                "is the patch. It has always been the patch.* The minutes record eleven "
                "seconds of silence, then applause.\n\n"
                "The patch now ships on every hull, pre-applied, at zero cost. The "
                "committee remains in session about the font.",
            ),
            (
                "O comité do emblema da missão tem opiniões",
                "Quarenta propostas, uma lata, zero sobreviventes.",
                "Desenhar um emblema de missão devia demorar uma tarde. Vamos na semana "
                "seis.\n\n"
                "## A lista final\n\n"
                "- Uma sardinha, heroica, a olhar para a esquerda: rejeitada — *parece o "
                "atum*.\n"
                "- Uma sardinha, heroica, a olhar para a direita: rejeitada — o atum "
                "queixou-se na mesma.\n"
                "- A lata, simples, com uma estrela: aprovada por unanimidade, e depois "
                "desaprovada quando se percebeu que a estrela era uma migalha no "
                "projetor.\n\n"
                "O comité já analisou quarenta propostas e não aprovou nenhuma, um recorde "
                "que o comité anterior detinha havia uma única tarde.\n\n"
                "A Comandante desbloqueou o impasse erguendo uma lata verdadeira: *o "
                "rótulo é o emblema. Sempre foi o emblema.* A ata regista onze segundos de "
                "silêncio, seguidos de aplausos.\n\n"
                "O emblema segue agora em todos os cascos, pré-aplicado, a custo zero. O "
                "comité continua reunido por causa da fonte.",
                "comite-emblema-missao",
            ),
            (
                "El comité del parche de misión tiene opiniones",
                "Cuarenta diseños, una lata, cero supervivientes.",
                "Diseñar un parche de misión debería llevar una tarde. Vamos por la semana "
                "seis.\n\n"
                "## La lista corta\n\n"
                "- Una sardina, heroica, mirando a la izquierda: rechazada — *se parece al "
                "atún*.\n"
                "- Una sardina, heroica, mirando a la derecha: rechazada — el atún se "
                "quejó igualmente.\n"
                "- La lata, sencilla, con una estrella: aprobada por unanimidad, y luego "
                "desaprobada al identificarse la estrella como una miga en el proyector.\n\n"
                "El comité ha revisado ya cuarenta diseños y no ha aprobado ninguno, un "
                "récord que el comité anterior mantuvo durante una sola tarde.\n\n"
                "La Comandante zanjó el bloqueo levantando una lata de verdad: *la "
                "etiqueta es el parche. Siempre ha sido el parche.* El acta registra once "
                "segundos de silencio, y luego aplausos.\n\n"
                "El parche viaja ahora en todos los cascos, preaplicado, a coste cero. El "
                "comité sigue reunido por la tipografía.",
                "comite-parche-mision",
            ),
            (
                "Le comité de l'écusson de mission a des opinions",
                "Quarante projets, une boîte, aucun survivant.",
                "Dessiner un écusson de mission devrait prendre une après-midi. Nous en "
                "sommes à la semaine six.\n\n"
                "## La liste finale\n\n"
                "- Une sardine, héroïque, regardant à gauche : rejetée — *on dirait le "
                "thon*.\n"
                "- Une sardine, héroïque, regardant à droite : rejetée — le thon s'est "
                "plaint quand même.\n"
                "- La boîte, sobre, avec une étoile : approuvée à l'unanimité, puis "
                "désapprouvée quand l'étoile s'est révélée être une miette sur le "
                "projecteur.\n\n"
                "Le comité a examiné quarante projets et n'en a approuvé aucun, record que "
                "le comité précédent détenait depuis une seule après-midi.\n\n"
                "La Commandante a tranché en brandissant une vraie boîte : *l'étiquette "
                "est l'écusson. Elle a toujours été l'écusson.* Le compte rendu note onze "
                "secondes de silence, puis des applaudissements.\n\n"
                "L'écusson équipe désormais toutes les coques, pré-appliqué, à coût nul. "
                "Le comité reste en séance au sujet de la police.",
                "comite-ecusson-mission",
            ),
            (
                "Das Missionsabzeichen-Komitee hat Meinungen",
                "Vierzig Entwürfe, eine Dose, keine Überlebenden.",
                "Ein Missionsabzeichen zu entwerfen sollte einen Nachmittag dauern. Wir "
                "sind in Woche sechs.\n\n"
                "## Die engere Auswahl\n\n"
                "- Eine Sardine, heroisch, nach links blickend: abgelehnt — *sieht aus wie "
                "der Thunfisch*.\n"
                "- Eine Sardine, heroisch, nach rechts blickend: abgelehnt — der Thunfisch "
                "beschwerte sich trotzdem.\n"
                "- Die Dose, schlicht, mit einem Stern: einstimmig angenommen, dann wieder "
                "abgelehnt, als sich der Stern als Krümel auf dem Projektor entpuppte.\n\n"
                "Das Komitee hat inzwischen vierzig Entwürfe geprüft und keinen "
                "angenommen — ein Rekord, den das vorige Komitee einen einzigen Nachmittag "
                "lang hielt.\n\n"
                "Die Kommandantin beendete die Blockade, indem sie eine echte Dose "
                "hochhielt: *Das Etikett ist das Abzeichen. Es war immer das Abzeichen.* "
                "Das Protokoll verzeichnet elf Sekunden Stille, dann Applaus.\n\n"
                "Das Abzeichen ist jetzt auf jedem Rumpf, vorab angebracht, zum Nulltarif. "
                "Das Komitee tagt weiter — wegen der Schriftart.",
                "missionsabzeichen-komitee",
            ),
        ),
    ),
}

HOME_ABOUT: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "kicker": "01 · Who we are",
            "menu": "About",
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
        },
        media=["rocket"],
    ),
    PT: SectionContent(
        fields={
            "kicker": "01 · Quem somos",
            "menu": "Quem somos",
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
        },
        media=["rocket"],
    ),
    ES: SectionContent(
        fields={
            "kicker": "01 · Quienes somos",
            "menu": "Quienes somos",
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
        },
        media=["rocket"],
    ),
    FR: SectionContent(
        fields={
            "kicker": "01 · Qui nous sommes",
            "menu": "Qui sommes-nous",
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
        },
        media=["rocket"],
    ),
    DE: SectionContent(
        fields={
            "kicker": "01 · Wer wir sind",
            "menu": "Wer wir sind",
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
        },
        media=["rocket"],
    ),
}

HOME_EXPERTISE: dict[Language, SectionContent] = {
    EN: SectionContent(
        fields={
            "menu": "Capabilities",
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
            "menu": "Capacidades",
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
            "menu": "Capacidades",
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
            "menu": "Capacites",
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
            "menu": "Faehigkeiten",
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
            "menu": "Contact",
            "kicker": "03 · Join the shoal",
            "heading": "Ready to leave the",
            "accent": "ocean?",
            "button": "Meet the crew",
        }
    ),
    PT: SectionContent(
        fields={
            "menu": "Contacto",
            "kicker": "03 · Junta-te ao cardume",
            "heading": "Pronto para sair do",
            "accent": "oceano?",
            "button": "Conhecer a tripulacao",
        }
    ),
    ES: SectionContent(
        fields={
            "menu": "Contacto",
            "kicker": "03 · Unete al banco",
            "heading": "Listo para dejar el",
            "accent": "oceano?",
            "button": "Conocer a la tripulacion",
        }
    ),
    FR: SectionContent(
        fields={
            "menu": "Contact",
            "kicker": "03 · Rejoignez le banc",
            "heading": "Pret a quitter l'",
            "accent": "ocean ?",
            "button": "Rencontrer l'equipage",
        }
    ),
    DE: SectionContent(
        fields={
            "menu": "Kontakt",
            "kicker": "03 · Schliess dich dem Schwarm an",
            "heading": "Bereit, den Ozean zu",
            "accent": "verlassen?",
            "button": "Die Crew treffen",
        }
    ),
}


def _cover(seed_color: str, label: str) -> str:
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 630'
    width='1200' height='630' role='img'>
  <rect width='1200' height='630' fill='#0a0c12'/>
  <g stroke='{seed_color}' stroke-width='1' opacity='0.55'>
    <path d='M80 520 L340 300 L620 420 L900 180 L1140 320' fill='none'/>
    <circle cx='340' cy='300' r='4' fill='{seed_color}'/>
    <circle cx='620' cy='420' r='4' fill='{seed_color}'/>
    <circle cx='900' cy='180' r='4' fill='{seed_color}'/>
  </g>
  <g transform='translate(600 300) rotate(-38)'>
    <ellipse rx='120' ry='42' fill='none' stroke='#d8cfc0' stroke-width='4'/>
    <path fill='#d8cfc0'
      d='M-120 0 Q-146 -21 -165 -32 Q-153 -11 -153 0 Q-153 11 -165 32 Q-146 21 -120 0Z'/>
    <circle cx='90' cy='-10' r='6' fill='#0a0c12' stroke='#d8cfc0' stroke-width='3'/>
  </g>
  <text x='600' y='580' text-anchor='middle' font-family='serif' font-size='26'
    fill='#7b7e88'>{label}</text>
</svg>
"""


COVER_SVGS: dict[str, str] = {
    "cover-missions": _cover("#7fb4ff", "Mission log"),
    "cover-engineering": _cover("#7ec8a2", "Engineering"),
    "cover-canteen": _cover("#d8cfc0", "Canteen"),
}

COVER_ALT: dict[str, dict[Language, str]] = {
    "cover-missions": {
        EN: "A tin rocket crossing a constellation chart",
        PT: "Um foguetao-lata a cruzar uma carta de constelacoes",
        ES: "Un cohete-lata cruzando una carta de constelaciones",
        FR: "Une fusee-boite traversant une carte de constellations",
        DE: "Eine Dosenrakete auf einer Sternkarte",
    },
    "cover-engineering": {
        EN: "Engineering plots behind a tin rocket",
        PT: "Tracados de engenharia atras de um foguetao-lata",
        ES: "Trazados de ingenieria tras un cohete-lata",
        FR: "Traces d'ingenierie derriere une fusee-boite",
        DE: "Ingenieurkurven hinter einer Dosenrakete",
    },
    "cover-canteen": {
        EN: "The canteen chart nobody follows",
        PT: "A carta da cantina que ninguem segue",
        ES: "La carta de la cantina que nadie sigue",
        FR: "La carte de la cantine que personne ne suit",
        DE: "Die Kantinenkarte, der niemand folgt",
    },
}


# One article deliberately left in review with the DE translation missing:
# the seeded project must exercise the publish gate, not only pass it. The
# entry never reaches the public site (only published content is exported),
# but the dashboard and publishing report show the live warning.
REVIEW_ARTICLE_ID = "parallel-parking-the-rocket"
REVIEW_ARTICLE: dict[Language, ArticleContent] = {
    EN: ArticleContent(
        title="Parallel parking the rocket",
        summary="A launch pad is easy. The spot between two comets is not.",
        body_markdown=(
            "Nobody warns you about parking.\n\n"
            "Launching is loud and glorious and the brochure covers it in "
            "detail. What the brochure does not cover is arriving at a busy "
            "orbit at rush hour and finding one free spot between two comets, "
            "both of which parked diagonally.\n\n"
            "The committee has therefore opened a training programme: forty "
            "hours of simulator time, a traffic cone borrowed from the "
            "canteen, and an instructor who keeps saying *mirror, signal, "
            "retro-burn*. Certification is mandatory before anyone is allowed "
            "to dock the tin anywhere with witnesses.\n\n"
            "The German translation of this report is still with the review "
            "board, which is exactly the kind of thing our own publish gate "
            "is for."
        ),
    ),
    PT: ArticleContent(
        title="Estacionar o foguetao em paralelo",
        summary="Uma plataforma de lancamento é fácil. A vaga entre dois cometas não.",
        body_markdown=(
            "Ninguém nos avisa sobre o estacionamento.\n\n"
            "Lançar é barulhento e glorioso e a brochura cobre isso ao "
            "detalhe. O que a brochura não cobre é chegar a uma órbita "
            "movimentada à hora de ponta e encontrar uma única vaga entre "
            "dois cometas, ambos estacionados na diagonal.\n\n"
            "O comité abriu por isso um programa de treino: quarenta horas de "
            "simulador, um cone de trânsito emprestado pela cantina e um "
            "instrutor que repete *espelho, pisca, retro-propulsão*. A "
            "certificação é obrigatória antes de alguém poder atracar a lata "
            "num sítio com testemunhas."
        ),
        slug="estacionar-o-foguetao-em-paralelo",
    ),
    ES: ArticleContent(
        title="Aparcar el cohete en paralelo",
        summary="Una plataforma de lanzamiento es fácil. El hueco entre dos cometas no.",
        body_markdown=(
            "Nadie te avisa sobre el aparcamiento.\n\n"
            "Lanzar es ruidoso y glorioso y el folleto lo cubre con detalle. "
            "Lo que el folleto no cubre es llegar a una órbita concurrida en "
            "hora punta y encontrar un único hueco entre dos cometas, los dos "
            "aparcados en diagonal.\n\n"
            "El comité ha abierto por ello un programa de entrenamiento: "
            "cuarenta horas de simulador, un cono de tráfico prestado por la "
            "cantina y un instructor que repite *espejo, intermitente, "
            "retropropulsión*. La certificación es obligatoria antes de que "
            "nadie pueda atracar la lata donde haya testigos."
        ),
        slug="aparcar-el-cohete-en-paralelo",
    ),
    FR: ArticleContent(
        title="Garer la fusée en créneau",
        summary="Un pas de tir, c'est facile. La place entre deux comètes, non.",
        body_markdown=(
            "Personne ne vous prévient pour le stationnement.\n\n"
            "Décoller est bruyant et glorieux et la brochure couvre le sujet "
            "en détail. Ce que la brochure ne couvre pas, c'est l'arrivée sur "
            "une orbite chargée à l'heure de pointe, avec une seule place "
            "libre entre deux comètes garées en diagonale.\n\n"
            "Le comité a donc ouvert un programme d'entraînement : quarante "
            "heures de simulateur, un cône de chantier prêté par la cantine "
            "et un instructeur qui répète *rétroviseur, clignotant, "
            "rétro-poussée*. La certification est obligatoire avant d'amarrer "
            "la boîte devant témoins."
        ),
        slug="garer-la-fusee-en-creneau",
    ),
}
