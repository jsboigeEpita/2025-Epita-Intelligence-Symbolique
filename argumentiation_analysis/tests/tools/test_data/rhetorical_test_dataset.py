#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Jeu de données de test pour les outils d'analyse rhétorique.

Ce module contient un jeu de données de test comprenant divers textes argumentatifs
avec différents types de sophismes dans différents contextes.
"""

# Jeu de données de test pour les outils d'analyse rhétorique
RHETORICAL_TEST_DATASET = {
    # Textes politiques
    "politique": {
        "simple": [
            """
            Notre parti a toujours défendu les intérêts des travailleurs. Nous continuerons à lutter
            pour des salaires équitables et de meilleures conditions de travail. Notre programme
            économique créera des emplois et stimulera la croissance. Votez pour nous lors des
            prochaines élections.
            """
        ],
        "sophismes_simples": [
            """
            Mon adversaire n'a aucune expérience en matière de gouvernance. Comment pourrait-il
            diriger notre pays? Il a échoué dans ses entreprises précédentes, il échouera également
            en tant que dirigeant. Votez pour moi, car j'ai l'expérience nécessaire pour réussir.
            """,
            """
            Si nous adoptons cette politique fiscale, ce sera le début de la fin pour notre économie.
            Les entreprises fermeront, le chômage explosera, et nous entrerons dans une récession
            sans précédent. Voulez-vous vraiment être responsables de cette catastrophe?
            """,
            """
            Tous les experts économiques sérieux soutiennent notre plan de relance. Seuls quelques
            économistes marginaux s'y opposent. La science économique est claire sur ce point.
            """
        ],
        "sophismes_complexes": [
            """
            Mon adversaire prétend défendre les travailleurs, mais il est soutenu par les grandes
            entreprises. Comment peut-il prétendre représenter vos intérêts alors qu'il est financé
            par ceux qui vous exploitent? De plus, son plan économique est similaire à celui qui a
            conduit à la crise de 2008. Voulez-vous revivre cette période difficile? Si nous suivons
            sa politique, nous verrons une augmentation du chômage, une baisse des salaires, et une
            détérioration des services publics. Est-ce vraiment ce que vous souhaitez pour votre
            famille? Votez pour moi, car je suis le seul candidat qui défend réellement vos intérêts.
            """
        ]
    },
    
    # Textes scientifiques
    "scientifique": {
        "simple": [
            """
            Notre étude a démontré une corrélation significative entre la consommation de sucre et
            l'incidence du diabète de type 2. Les données collectées sur 10 ans auprès de 5000
            participants montrent que ceux qui consomment plus de 50g de sucre par jour ont un risque
            accru de 30% de développer cette maladie. Ces résultats suggèrent l'importance de limiter
            la consommation de sucre dans le cadre d'une alimentation équilibrée.
            """
        ],
        "sophismes_simples": [
            """
            Notre nouvelle théorie sur le changement climatique remet en question le consensus
            scientifique actuel. Bien que minoritaire, notre approche offre une explication plus
            élégante des phénomènes observés. Le fait que la communauté scientifique résiste à
            nos idées montre simplement qu'ils sont attachés à leurs paradigmes dépassés.
            """,
            """
            Les températures ont baissé dans certaines régions l'année dernière, ce qui prouve
            que le réchauffement climatique n'est pas un phénomène global comme on le prétend.
            """,
            """
            Cette théorie est soutenue par le Professeur Johnson de l'Université de Cambridge,
            l'une des institutions les plus prestigieuses au monde. Son soutien suffit à
            démontrer la validité de nos conclusions.
            """
        ],
        "sophismes_complexes": [
            """
            Notre étude remet en question l'efficacité des vaccins contre la grippe. Nous avons
            observé que plusieurs patients vaccinés ont quand même contracté la maladie. De plus,
            certains patients ont rapporté des effets secondaires après la vaccination. Le Dr. Smith,
            qui a travaillé dans l'industrie pharmaceutique pendant 20 ans, soutient nos conclusions.
            Si les vaccins étaient vraiment efficaces, personne ne tomberait malade après avoir été
            vacciné. L'industrie pharmaceutique ne veut pas que ces informations soient connues car
            elle fait des milliards grâce aux vaccins. Nous devons remettre en question le consensus
            médical sur ce sujet pour protéger la santé publique.
            """
        ]
    },
    
    # Textes commerciaux
    "commercial": {
        "simple": [
            """
            Notre nouveau smartphone offre une batterie longue durée, un appareil photo haute
            résolution et un processeur rapide. Il est disponible en trois couleurs et deux
            capacités de stockage. Commandez maintenant et bénéficiez d'une remise de 15%.
            """
        ],
        "sophismes_simples": [
            """
            Notre produit est utilisé par des millions de personnes dans le monde entier.
            Rejoignez cette communauté et transformez votre vie dès aujourd'hui!
            """,
            """
            Ce supplément nutritionnel révolutionnaire a été développé par des scientifiques
            de pointe. Sa formule brevetée vous garantit des résultats exceptionnels.
            """,
            """
            Si vous n'achetez pas notre système de sécurité, vous mettez votre famille en danger.
            Pouvez-vous vraiment vous permettre de prendre ce risque?
            """
        ],
        "sophismes_complexes": [
            """
            Notre crème anti-âge est une révolution dans le domaine de la cosmétique. Développée
            par des chercheurs de renommée mondiale, elle utilise une technologie brevetée qui
            agit directement sur les cellules de la peau. Des célébrités comme Emma Johnson
            l'utilisent quotidiennement et en vantent les mérites. Dans une étude récente, 95%
            des utilisateurs ont constaté une amélioration visible de leur peau. Ne ratez pas
            cette opportunité de paraître 10 ans plus jeune! Si vous n'essayez pas notre produit,
            vous continuerez à subir les effets visibles du vieillissement. Commandez maintenant
            et rejoignez les millions de clients satisfaits dans le monde entier!
            """
        ]
    },
    
    # Textes juridiques
    "juridique": {
        "simple": [
            """
            Conformément à l'article 1134 du Code civil, les contrats légalement formés tiennent
            lieu de loi à ceux qui les ont faits. En l'espèce, le contrat signé entre les parties
            le 15 mars 2024 stipule clairement les obligations de chacune des parties. Par conséquent,
            le défendeur est tenu d'exécuter ses obligations contractuelles.
            """
        ],
        "sophismes_simples": [
            """
            Mon client ne peut pas être coupable de ce crime. C'est un père de famille respecté
            dans sa communauté, qui fait régulièrement des dons à des œuvres caritatives.
            """,
            """
            Si nous acceptons d'assouplir cette loi, ce sera le début d'une pente glissante.
            Bientôt, toutes nos lois seront remises en question et nous vivrons dans l'anarchie.
            """,
            """
            La partie adverse n'a présenté que des preuves circonstancielles. En l'absence de
            preuve directe, vous devez acquitter mon client.
            """
        ],
        "sophismes_complexes": [
            """
            Mesdames et messieurs les jurés, l'accusation veut vous faire croire que mon client
            est coupable de fraude. Mais regardez-le: c'est un homme d'affaires respecté, père
            de trois enfants, et bénévole dans sa communauté. Comment un tel homme pourrait-il
            commettre un crime? L'expert comptable de l'accusation a certes relevé des irrégularités,
            mais cet expert travaille régulièrement pour le procureur et a intérêt à trouver des
            problèmes. Si vous condamnez mon client aujourd'hui, vous détruirez non seulement sa
            vie, mais aussi celle de sa famille et de ses employés qui dépendent de lui. Est-ce
            vraiment ce que vous voulez? De plus, si nous commençons à criminaliser de simples
            erreurs comptables, aucun entrepreneur ne sera à l'abri. C'est l'avenir de notre
            économie qui est en jeu.
            """
        ]
    },
    
    # Textes académiques
    "académique": {
        "simple": [
            """
            Cette thèse examine l'impact des réseaux sociaux sur les comportements électoraux
            des jeunes adultes. À travers une analyse quantitative de données collectées auprès
            de 2000 participants âgés de 18 à 25 ans, nous démontrons une corrélation significative
            entre l'exposition à certains contenus politiques sur les réseaux sociaux et les
            intentions de vote. Ces résultats contribuent à la littérature existante sur l'influence
            des médias numériques dans les processus démocratiques.
            """
        ],
        "sophismes_simples": [
            """
            La théorie X n'a jamais été réfutée de manière concluante, ce qui prouve sa validité
            dans le domaine des sciences sociales.
            """,
            """
            Les travaux du Professeur Johnson sont largement cités dans la littérature. Par
            conséquent, ses conclusions sur ce sujet doivent être acceptées.
            """,
            """
            Cette méthodologie est utilisée depuis des décennies dans notre discipline. Il n'y a
            donc aucune raison de la remettre en question ou d'adopter de nouvelles approches.
            """
        ],
        "sophismes_complexes": [
            """
            Notre étude remet en question le paradigme dominant dans le domaine de la psychologie
            cognitive. Bien que nos résultats contredisent ceux de Johnson et al. (2022), il faut
            noter que leur étude a été financée par une institution qui a intérêt à maintenir le
            statu quo théorique. Notre approche, bien que minoritaire, offre une explication plus
            élégante des phénomènes observés. Le fait que nos conclusions n'aient pas été publiées
            dans les revues traditionnelles montre simplement la résistance de l'establishment
            académique aux idées novatrices. Si l'on rejette notre théorie aujourd'hui, on risque
            de retarder des avancées significatives dans notre compréhension de la cognition humaine.
            Après tout, toutes les grandes théories scientifiques ont d'abord été rejetées avant
            d'être acceptées.
            """
        ]
    }
}

# Jeu de données de test pour l'évaluation de la performance
PERFORMANCE_TEST_DATASET = {
    "simple": [
        "Le réchauffement climatique est un problème mondial urgent.",
        "Les émissions de gaz à effet de serre contribuent significativement au réchauffement climatique.",
        "Nous devons réduire nos émissions de carbone pour lutter contre le réchauffement climatique.",
        "Les énergies renouvelables sont une alternative viable aux combustibles fossiles."
    ],
    "complex": [
        "Le réchauffement climatique est un mythe créé par les scientifiques pour obtenir des financements.",
        "Regardez, il a neigé l'hiver dernier, ce qui prouve que le climat ne se réchauffe pas.",
        "De plus, des milliers de scientifiques ont signé une pétition contre cette théorie.",
        "Si nous réduisons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.",
        "Voulez-vous être responsable de la misère de tant de familles?",
        "Les écologistes sont des extrémistes qui veulent nous ramener à l'âge de pierre."
    ],
    "mixed": [
        "Le réchauffement climatique est un problème sérieux, mais certains scientifiques exagèrent ses effets.",
        "Les données montrent une augmentation de la température mondiale, mais les modèles climatiques ne sont pas parfaits.",
        "Nous devons réduire nos émissions de carbone, mais pas au détriment de l'économie.",
        "Les énergies renouvelables sont prometteuses, mais elles ne sont pas encore assez développées pour remplacer complètement les combustibles fossiles.",
        "Les politiques environnementales doivent être équilibrées et tenir compte des réalités économiques et sociales."
    ]
}

# Mapping des sophismes pour l'évaluation
FALLACY_MAPPING = {
    "Appel à l'autorité": {
        "description": "Utilisation d'une figure d'autorité pour soutenir un argument sans fournir de preuves substantielles",
        "exemples": [
            "Cette théorie est soutenue par le Professeur Johnson de l'Université de Cambridge.",
            "Tous les experts économiques sérieux soutiennent notre plan de relance."
        ]
    },
    "Appel à la popularité": {
        "description": "Argument basé sur le fait qu'une idée est largement acceptée ou populaire",
        "exemples": [
            "Notre produit est utilisé par des millions de personnes dans le monde entier.",
            "Des milliers de scientifiques ont signé une pétition contre cette théorie."
        ]
    },
    "Appel à l'émotion": {
        "description": "Tentative de manipuler les émotions plutôt que de présenter des arguments logiques",
        "exemples": [
            "Voulez-vous vraiment être responsables de cette catastrophe?",
            "Pouvez-vous vraiment vous permettre de prendre ce risque?"
        ]
    },
    "Appel à la peur": {
        "description": "Utilisation de la peur pour persuader plutôt que de présenter des arguments logiques",
        "exemples": [
            "Si nous adoptons cette politique fiscale, ce sera le début de la fin pour notre économie.",
            "Si vous n'achetez pas notre système de sécurité, vous mettez votre famille en danger."
        ]
    },
    "Ad hominem": {
        "description": "Attaque de la personne plutôt que de ses arguments",
        "exemples": [
            "Mon adversaire n'a aucune expérience en matière de gouvernance.",
            "Il a échoué dans ses entreprises précédentes, il échouera également en tant que dirigeant."
        ]
    },
    "Faux dilemme": {
        "description": "Présentation de seulement deux options alors qu'il en existe d'autres",
        "exemples": [
            "Soit nous adoptons cette politique, soit nous acceptons le déclin économique.",
            "Vous êtes soit avec nous, soit contre nous."
        ]
    },
    "Généralisation hâtive": {
        "description": "Conclusion basée sur un échantillon trop petit ou non représentatif",
        "exemples": [
            "J'ai rencontré deux personnes qui ont eu des effets secondaires après la vaccination, donc les vaccins sont dangereux.",
            "Les températures ont baissé dans certaines régions l'année dernière, ce qui prouve que le réchauffement climatique n'est pas réel."
        ]
    },
    "Pente glissante": {
        "description": "Argument suggérant qu'une action mènera inévitablement à une série d'événements négatifs",
        "exemples": [
            "Si nous assouplissons cette loi, bientôt toutes nos lois seront remises en question.",
            "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie."
        ]
    },
    "Homme de paille": {
        "description": "Déformation de l'argument de l'adversaire pour le rendre plus facile à attaquer",
        "exemples": [
            "Les écologistes veulent nous ramener à l'âge de pierre.",
            "Les défenseurs de la régulation veulent un contrôle total du gouvernement sur l'économie."
        ]
    },
    "Post hoc ergo propter hoc": {
        "description": "Conclusion qu'un événement a causé un autre simplement parce qu'il l'a précédé",
        "exemples": [
            "J'ai pris ce médicament et je me suis senti mieux le lendemain, donc le médicament m'a guéri.",
            "L'économie s'est améliorée après l'élection du président, donc ses politiques sont efficaces."
        ]
    }
}

# Contextes pour l'évaluation
CONTEXT_MAPPING = {
    "politique": {
        "description": "Discours, débats ou textes liés à la politique et aux affaires publiques",
        "audience_typique": "Électeurs, citoyens, autres politiciens",
        "sophismes_courants": ["Appel à l'émotion", "Ad hominem", "Homme de paille", "Faux dilemme", "Pente glissante"]
    },
    "scientifique": {
        "description": "Publications, présentations ou discussions dans un contexte scientifique ou académique",
        "audience_typique": "Chercheurs, étudiants, communauté scientifique",
        "sophismes_courants": ["Appel à l'autorité", "Post hoc ergo propter hoc", "Généralisation hâtive"]
    },
    "commercial": {
        "description": "Publicités, présentations de produits ou communications marketing",
        "audience_typique": "Consommateurs, clients potentiels",
        "sophismes_courants": ["Appel à la popularité", "Appel à la nouveauté", "Appel à la peur", "Faux dilemme"]
    },
    "juridique": {
        "description": "Plaidoiries, arguments juridiques ou textes légaux",
        "audience_typique": "Juges, jurés, autres avocats",
        "sophismes_courants": ["Ad hominem", "Pente glissante", "Appel à l'émotion", "Faux dilemme"]
    },
    "académique": {
        "description": "Publications académiques, thèses ou présentations dans un contexte éducatif",
        "audience_typique": "Chercheurs, étudiants, pairs académiques",
        "sophismes_courants": ["Appel à l'autorité", "Appel à la tradition", "Appel à l'ignorance"]
    },
    "général": {
        "description": "Contexte général ou non spécifique",
        "audience_typique": "Public général",
        "sophismes_courants": ["Appel à l'émotion", "Appel à la popularité", "Généralisation hâtive", "Ad hominem"]
    }
}


def get_test_text(context_type, complexity_level):
    """
    Récupère un texte de test en fonction du contexte et du niveau de complexité.
    
    Args:
        context_type: Type de contexte (politique, scientifique, commercial, juridique, académique)
        complexity_level: Niveau de complexité (simple, sophismes_simples, sophismes_complexes)
        
    Returns:
        Un texte de test correspondant aux critères
    """
    if context_type in RHETORICAL_TEST_DATASET and complexity_level in RHETORICAL_TEST_DATASET[context_type]:
        texts = RHETORICAL_TEST_DATASET[context_type][complexity_level]
        if texts:
            return texts[0]
    
    return "Texte de test non disponible pour ce contexte et ce niveau de complexité."


def get_performance_test_data(complexity_level):
    """
    Récupère des données de test pour l'évaluation de la performance.
    
    Args:
        complexity_level: Niveau de complexité (simple, complex, mixed)
        
    Returns:
        Une liste d'arguments pour les tests de performance
    """
    if complexity_level in PERFORMANCE_TEST_DATASET:
        return PERFORMANCE_TEST_DATASET[complexity_level]
    
    return []


def get_fallacy_info(fallacy_type):
    """
    Récupère des informations sur un type de sophisme.
    
    Args:
        fallacy_type: Type de sophisme
        
    Returns:
        Un dictionnaire contenant des informations sur le sophisme
    """
    if fallacy_type in FALLACY_MAPPING:
        return FALLACY_MAPPING[fallacy_type]
    
    return {
        "description": "Information non disponible pour ce type de sophisme.",
        "exemples": []
    }


def get_context_info(context_type):
    """
    Récupère des informations sur un type de contexte.
    
    Args:
        context_type: Type de contexte
        
    Returns:
        Un dictionnaire contenant des informations sur le contexte
    """
    if context_type in CONTEXT_MAPPING:
        return CONTEXT_MAPPING[context_type]
    
    return {
        "description": "Information non disponible pour ce type de contexte.",
        "audience_typique": "Non spécifié",
        "sophismes_courants": []
    }


if __name__ == "__main__":
    # Exemple d'utilisation
    print("Exemple de texte politique avec sophismes complexes:")
    print(get_test_text("politique", "sophismes_complexes"))
    print("\nExemple de données de test pour l'évaluation de la performance (niveau complexe):")
    print(get_performance_test_data("complex"))
    print("\nInformations sur le sophisme 'Appel à l'autorité':")
    print(get_fallacy_info("Appel à l'autorité"))
    print("\nInformations sur le contexte 'scientifique':")
    print(get_context_info("scientifique"))