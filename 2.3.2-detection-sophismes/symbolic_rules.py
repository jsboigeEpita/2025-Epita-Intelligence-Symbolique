"""
Symbolic Rules for French Fallacy Detection.

This file contains rule patterns for the symbolic matching engine.
These rules are designed to be used with a token-based matching engine like spaCy's Matcher.
Each pattern identifies a linguistic structure commonly associated with a specific fallacy.
"""

fallacy_rules = {
    "AD_HOMINEM_DIRECT": [
        # "Vous avez tort parce que vous êtes [ADJECTIF NÉGATIF]"
        # Example: "Tu es un idiot, donc ton argument est invalide."
        {
            "PATTERN": [
                {"LOWER": {"IN": ["tu", "vous", "il", "elle"]}}, 
                {"LEMMA": "être"}, 
                {"POS": "DET", "OP": "*"}, 
                {"POS": "ADJ"}, 
                {"LOWER": {"IN": ["donc", "alors", "parce que", "car"]}}, 
                {"TEXT": {"REGEX": ".*"}}
            ],
            "FALLACY_TYPE": "Attaque personnelle (Ad Hominem)"
        },
        # New pattern for general discredit: "On ne peut pas faire confiance à [GROUPE]"
        {"PATTERN": [
            {"LOWER": "on"},
            {"LOWER": "ne"},
            {"LEMMA": "pouvoir"},
            {"LOWER": "pas"},
            {"LEMMA": "faire"},
            {"LOWER": "confiance"},
            {"LEMMA": "à"},
            {"POS": "DET", "OP": "?"},
            {"POS": "NOUN"}
        ],
        "FALLACY_TYPE": "Attaque personnelle (Ad Hominem)"
        },
        # Attacking character/motive: "[Nom] est [adjectif négatif], donc son argument est faux."
        {"PATTERN": [
            {"POS": "PROPN"},
            {"LEMMA": "être"},
            {"POS": "ADJ"},
            {"LOWER": {"IN": ["donc", "alors"]}},
            {"POS": "DET"},
            {"POS": "NOUN"},
            {"LEMMA": "être"},
            {"LOWER": "faux"}
        ],
        "FALLACY_TYPE": "Attaque personnelle (Ad Hominem)"
        }
    ],
    "PENTE_GLISSANTE": [
        # "Si nous autorisons A, alors B, C, et D (négatifs) se produiront inévitablement."
        # Example: "Si on autorise le mariage pour tous, bientôt on autorisera la polygamie."
        {
            "PATTERN": [
                {"LOWER": "si"},
                {"LOWER": "on"},
                {"LEMMA": "autoriser"},
                {"POS": "NOUN"},
                {"LOWER": "alors"},
                {"TEXT": {"REGEX": ".*"}}
            ],
            "FALLACY_TYPE": "Pente glissante (Slippery Slope)"
        },
        # Chain of negative consequences: "Cela mènera inévitablement à..."
        {"PATTERN": [
            {"LOWER": "cela"},
            {"LEMMA": "mener"},
            {"LOWER": "inévitablement"},
            {"LEMMA": "à"},
            {"TEXT": {"REGEX": ".*"}}
        ],
        "FALLACY_TYPE": "Pente glissante (Slippery Slope)"
        },
        # "Le premier pas vers..."
        {"PATTERN": [
            {"LOWER": "le"},
            {"LOWER": "premier"},
            {"LOWER": "pas"},
            {"LOWER": "vers"},
            {"TEXT": {"REGEX": ".*"}}
        ],
        "FALLACY_TYPE": "Pente glissante (Slippery Slope)"
        }
    ],
    "GÉNÉRALISATION_HÂTIVE": [
        # "[QUANTIFICATEUR] [GROUPE] sont [ADJECTIF]."
        # Example: "J'ai vu deux touristes malpolis. Tous les touristes sont désagréables."
        {
            "PATTERN": [
                {"LOWER": {"IN": ["tous", "toutes", "chaque", "personne"]}},
                {"POS": "NOUN", "OP": "+"},
                {"LEMMA": "être"},
                {"POS": "ADJ"}
            ],
            "FALLACY_TYPE": "Généralisation hâtive (Hasty Generalization)"
        },
        # "Sur la base de [petit nombre] exemples..."
        {"PATTERN": [
            {"LOWER": "sur"},
            {"LOWER": "la"},
            {"LOWER": "base"},
            {"LOWER": "de"},
            {"POS": "NUM"},
            {"POS": "NOUN"},
            {"LOWER": "exemples"}
        ],
        "FALLACY_TYPE": "Généralisation hâtive (Hasty Generalization)"
        }
    ],
    "APPEL_À_LA_TRADITION": [
        # "Nous avons toujours fait comme ça."
        # Example: "On a toujours célébré cette fête de cette manière, il ne faut rien changer."
        {
            "PATTERN": [
                {"LOWER": "on"},
                {"LOWER": "a"},
                {"LOWER": "toujours"},
                {"LEMMA": "faire"},
                {"LOWER": "comme"},
                {"LOWER": "ça"}
            ],
            "FALLACY_TYPE": "Appel à la tradition (Appeal to Tradition)"
        },
        # "C'est la tradition."
        {"PATTERN": [
            {"LOWER": "c'"},
            {"LEMMA": "être"},
            {"LOWER": "la"},
            {"LOWER": "tradition"}
        ],
        "FALLACY_TYPE": "Appel à la tradition (Appeal to Tradition)"
        },
        # "Depuis toujours..."
        {"PATTERN": [
            {"LOWER": "depuis"},
            {"LOWER": "toujours"}
        ],
        "FALLACY_TYPE": "Appel à la tradition (Appeal to Tradition)"
        }
    ],
    "ARGUMENT_D_AUTORITÉ_SIMPLE": [
        # "[EXPERT/SOURCE] a dit que [PROPOSITION], donc c'est vrai."
        # Example: "Un scientifique célèbre a dit que le chocolat est bon pour la santé."
        {
            "PATTERN": [
                {"POS": "NOUN", "OP": "+"}, # e.g., "Un expert"
                {"LEMMA": "dire"},
                {"LOWER": "que"},
                {"TEXT": {"REGEX": ".*"}},
                {"LOWER": {"IN": ["donc", "alors"]}},
                {"TEXT": {"REGEX": ".*"}}
            ],
            "FALLACY_TYPE": "Argument d'autorité (Appeal to Authority)"
        }
    ],
    "ARGUMENT_D_AUTORITÉ_GÉNÉRAL": [
        # "[GROUPE] disent que [PROPOSITION]"
        # Example: "Les experts le disent."
        {
            "PATTERN": [
                {"POS": "NOUN", "OP": "+"}, # e.g., "Les experts"
                {"LEMMA": "le", "OP": "?"},
                {"LEMMA": "dire"}
            ],
            "FALLACY_TYPE": "Argument d'autorité (Appeal to Authority)"
        },
        # "Selon [source non qualifiée]..."
        {"PATTERN": [
            {"LOWER": "selon"},
            {"POS": "DET"},
            {"POS": "NOUN"},
            {"TEXT": {"REGEX": ".*"}}
        ],
        "FALLACY_TYPE": "Argument d'autorité (Appeal to Authority)"
        },
        # "[Personne célèbre] a dit..."
        {"PATTERN": [
            {"POS": "PROPN"},
            {"LEMMA": "dire"}
        ],
        "FALLACY_TYPE": "Argument d'autorité (Appeal to Authority)"
        }
    ]
}