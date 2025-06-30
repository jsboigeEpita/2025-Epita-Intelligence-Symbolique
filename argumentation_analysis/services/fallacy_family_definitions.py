# -*- coding: utf-8 -*-
"""
Définitions structurées des familles de sophismes et dictionnaires de classification.

Ce module contient les dictionnaires et définitions utilisés par le système
de classification par familles selon le PRD d'intégration du fact-checking.
"""

from typing import Dict, List, Any, Set
from enum import Enum

from .fallacy_taxonomy_service import FallacyFamily


# Dictionnaire de sévérité par famille de sophismes
FALLACY_FAMILY_SEVERITY = {
    FallacyFamily.AUTHORITY_POPULARITY: {
        "base_severity": 0.7,
        "context_multipliers": {
            "scientific": 0.9,  # Plus grave dans un contexte scientifique
            "medical": 0.9,
            "legal": 0.8,
            "political": 0.6,
            "commercial": 0.5,
            "casual": 0.3
        },
        "keywords_high_severity": ["expert", "docteur", "professeur", "scientifique"],
        "keywords_medium_severity": ["spécialiste", "autorité", "tout le monde"],
        "keywords_low_severity": ["on dit que", "il paraît"]
    },
    
    FallacyFamily.EMOTIONAL_APPEALS: {
        "base_severity": 0.8,
        "context_multipliers": {
            "political": 0.9,  # Très grave en politique
            "legal": 0.9,
            "medical": 0.8,
            "commercial": 0.6,
            "personal": 0.5,
            "artistic": 0.3
        },
        "keywords_high_severity": ["terrorisme", "mort", "catastrophe", "destruction"],
        "keywords_medium_severity": ["peur", "danger", "risque", "menace"],
        "keywords_low_severity": ["inquiétude", "préoccupation"]
    },
    
    FallacyFamily.GENERALIZATION_CAUSALITY: {
        "base_severity": 0.9,  # Très grave car affecte la logique
        "context_multipliers": {
            "scientific": 1.0,  # Critique en science
            "medical": 1.0,
            "research": 0.9,
            "statistical": 0.9,
            "political": 0.7,
            "casual": 0.4
        },
        "keywords_high_severity": ["toujours", "jamais", "tous", "aucun"],
        "keywords_medium_severity": ["généralement", "souvent", "cause"],
        "keywords_low_severity": ["parfois", "peut-être"]
    },
    
    FallacyFamily.DIVERSION_ATTACK: {
        "base_severity": 0.6,
        "context_multipliers": {
            "debate": 0.8,
            "political": 0.7,
            "academic": 0.9,  # Grave dans un contexte académique
            "legal": 0.8,
            "commercial": 0.5,
            "personal": 0.4
        },
        "keywords_high_severity": ["menteur", "idiot", "incompétent"],
        "keywords_medium_severity": ["hypocrite", "contradiction"],
        "keywords_low_severity": ["d'ailleurs", "à propos"]
    },
    
    FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION: {
        "base_severity": 0.7,
        "context_multipliers": {
            "political": 0.8,
            "ethical": 0.9,
            "strategic": 0.8,
            "legal": 0.7,
            "commercial": 0.6,
            "casual": 0.4
        },
        "keywords_high_severity": ["soit... soit", "obligatoirement", "forcément"],
        "keywords_medium_severity": ["seulement", "uniquement", "simple"],
        "keywords_low_severity": ["ou bien", "alternative"]
    },
    
    FallacyFamily.LANGUAGE_AMBIGUITY: {
        "base_severity": 0.5,
        "context_multipliers": {
            "legal": 0.9,  # Très grave en droit
            "scientific": 0.8,
            "philosophical": 0.7,
            "political": 0.6,
            "commercial": 0.6,
            "artistic": 0.3  # Acceptable dans l'art
        },
        "keywords_high_severity": ["clairement", "évidemment", "bien sûr"],
        "keywords_medium_severity": ["peut signifier", "interprétation"],
        "keywords_low_severity": ["ambiguïté", "double sens"]
    },
    
    FallacyFamily.STATISTICAL_PROBABILISTIC: {
        "base_severity": 0.9,  # Très grave car trompe sur les faits
        "context_multipliers": {
            "scientific": 1.0,
            "medical": 1.0,
            "financial": 0.9,
            "research": 0.9,
            "political": 0.8,
            "commercial": 0.7
        },
        "keywords_high_severity": ["prouvé", "certain", "garanti"],
        "keywords_medium_severity": ["probable", "statistique", "étude"],
        "keywords_low_severity": ["chance", "possibilité"]
    },
    
    FallacyFamily.AUDIO_ORAL_CONTEXT: {
        "base_severity": 0.4,
        "context_multipliers": {
            "debate": 0.7,
            "interview": 0.6,
            "academic": 0.8,
            "legal": 0.7,
            "political": 0.6,
            "casual": 0.3
        },
        "keywords_high_severity": ["crier", "hurler", "interrompre"],
        "keywords_medium_severity": ["voix forte", "couper la parole"],
        "keywords_low_severity": ["ton", "intonation"]
    }
}


# Mots-clés de détection par famille
FALLACY_FAMILY_KEYWORDS = {
    FallacyFamily.AUTHORITY_POPULARITY: {
        "primary": [
            "expert", "spécialiste", "autorité", "professeur", "docteur",
            "tout le monde", "chacun sait", "il est évident", "tradition",
            "toujours fait", "nouveau", "moderne", "récent", "innovant"
        ],
        "secondary": [
            "compétent", "qualifié", "reconnu", "célèbre", "populaire",
            "majorité", "consensus", "admis", "établi", "conventionnel"
        ],
        "patterns": [
            r"\b(?:le|un|des?)\s+(?:expert|spécialiste)s?\b",
            r"\btout\s+(?:le\s+)?monde\s+(?:sait|dit|pense)\b",
            r"\btoujours\s+(?:fait|été)\b",
            r"\bça\s+se\s+fait\s+(?:pas|plus)\b"
        ]
    },
    
    FallacyFamily.EMOTIONAL_APPEALS: {
        "primary": [
            "peur", "terreur", "angoisse", "crainte", "effroi",
            "pitié", "compassion", "émouvant", "touchant",
            "honte", "embarrassant", "humiliant", "gênant",
            "colère", "révolte", "indignation", "scandale"
        ],
        "secondary": [
            "danger", "risque", "menace", "catastrophe", "drame",
            "pauvre", "malheureux", "victime", "souffrance",
            "fierté", "honneur", "dignité", "respect"
        ],
        "patterns": [
            r"\bimaginez\s+(?:si|que)\b",
            r"\bavez-vous\s+pensé\s+à\b",
            r"\bque\s+(?:dira|diront)\b",
            r"\bn'est-ce\s+pas\s+(?:émouvant|touchant|triste)\b"
        ]
    },
    
    FallacyFamily.GENERALIZATION_CAUSALITY: {
        "primary": [
            "tous", "toutes", "toujours", "jamais", "aucun", "aucune",
            "cause", "conséquence", "provoque", "entraîne", "résulte",
            "corrélation", "lien", "relation", "suite", "donc"
        ],
        "secondary": [
            "généralement", "habituellement", "systématiquement",
            "à cause de", "grâce à", "par conséquent", "ainsi",
            "preuve", "démontré", "établi", "confirmé"
        ],
        "patterns": [
            r"\btous\s+(?:les|ces)\s+\w+\s+(?:sont|font)\b",
            r"\btoujours\s+(?:le|la|les)\s+même\b",
            r"\bjamais\s+(?:de|d')\w+\b",
            r"\bpuisque\s+\w+,?\s+alors\b"
        ]
    },
    
    FallacyFamily.DIVERSION_ATTACK: {
        "primary": [
            "personnellement", "hypocrite", "menteur", "incompétent",
            "d'ailleurs", "à propos", "parlons plutôt", "changeons",
            "mais vous", "et vous", "tu fais pareil", "toi aussi"
        ],
        "secondary": [
            "attaque", "critique", "accusation", "reproche",
            "hors sujet", "pas le problème", "question différente",
            "contradiction", "incohérence", "illogique"
        ],
        "patterns": [
            r"\bmais\s+(?:vous|tu|toi)\b",
            r"\bet\s+(?:vous|tu|toi)\s+alors\b",
            r"\bfaites\s+(?:pas|plutôt)\s+pareil\b",
            r"\bd'ailleurs\s+(?:parlons|voyons)\b"
        ]
    },
    
    FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION: {
        "primary": [
            "soit", "ou bien", "seulement", "uniquement", "obligé",
            "forcé", "pas le choix", "deux solutions", "alternative",
            "simple", "compliqué", "complexe", "évident"
        ],
        "secondary": [
            "binaire", "noir ou blanc", "tout ou rien",
            "pour ou contre", "ami ou ennemi",
            "réduire", "simplifier", "schématiser"
        ],
        "patterns": [
            r"\bsoit\s+\w+\s+soit\s+\w+\b",
            r"\bou\s+bien\s+\w+\s+ou\s+bien\s+\w+\b",
            r"\bpas\s+(?:le|d'autre)\s+choix\b",
            r"\bc'est\s+(?:simple|évident|clair)\b"
        ]
    },
    
    FallacyFamily.LANGUAGE_AMBIGUITY: {
        "primary": [
            "équivoque", "ambiguïté", "double sens", "malentendu",
            "interprétation", "dépend", "selon", "peut signifier",
            "jeu de mots", "calembour", "sous-entendu"
        ],
        "secondary": [
            "comprendre", "entendre", "vouloir dire",
            "sens", "signification", "définition",
            "précision", "clarté", "flou", "vague"
        ],
        "patterns": [
            r"\bça\s+dépend\s+(?:de|du|des?)\b",
            r"\bselon\s+(?:le|la|les)\s+\w+\b",
            r"\bpeut\s+(?:vouloir\s+)?dire\b",
            r"\bdans\s+(?:le|un)\s+sens\b"
        ]
    },
    
    FallacyFamily.STATISTICAL_PROBABILISTIC: {
        "primary": [
            "statistique", "pourcentage", "probabilité", "chance",
            "échantillon", "sondage", "étude", "recherche",
            "corrélation", "moyenne", "médiane", "écart"
        ],
        "secondary": [
            "données", "chiffres", "résultats", "mesure",
            "probable", "possible", "certain", "sûr",
            "tendance", "évolution", "progression"
        ],
        "patterns": [
            r"\b\d+%\s+(?:des?|de\s+(?:la|les))\b",
            r"\b(?:une|l')\s+étude\s+(?:montre|prouve|dit)\b",
            r"\bstatistiquement\s+(?:parlant|significatif)\b",
            r"\bchances?\s+sur\s+\d+\b"
        ]
    },
    
    FallacyFamily.AUDIO_ORAL_CONTEXT: {
        "primary": [
            "interrompre", "couper", "crier", "hurler", "voix forte",
            "ton", "intonation", "accent", "débit", "volume",
            "parler fort", "hausser le ton", "élever la voix"
        ],
        "secondary": [
            "écouter", "entendre", "silence", "parole",
            "expression", "articulation", "prononciation",
            "rythme", "pause", "respiration"
        ],
        "patterns": [
            r"\bne\s+me\s+(?:coupez|interrompez)\s+pas\b",
            r"\blaissez-moi\s+(?:parler|finir)\b",
            r"\bbaissez\s+(?:le\s+)?(?:ton|voix)\b",
            r"\bpourquoi\s+(?:criez|hurlez)-vous\b"
        ]
    }
}


# Contextes typiques pour chaque famille
FALLACY_FAMILY_CONTEXTS = {
    FallacyFamily.AUTHORITY_POPULARITY: [
        "politique", "publicité", "marketing", "débat public",
        "réseaux sociaux", "médias", "communication commerciale"
    ],
    
    FallacyFamily.EMOTIONAL_APPEALS: [
        "politique", "publicité", "plaidoyer", "campagne",
        "sensibilisation", "mobilisation", "persuasion"
    ],
    
    FallacyFamily.GENERALIZATION_CAUSALITY: [
        "scientifique", "recherche", "analyse", "rapport",
        "étude", "article académique", "démonstration"
    ],
    
    FallacyFamily.DIVERSION_ATTACK: [
        "débat", "controverse", "polémique", "discussion",
        "argumentation", "confrontation", "négociation"
    ],
    
    FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION: [
        "politique", "éthique", "stratégie", "choix",
        "décision", "alternative", "problématique"
    ],
    
    FallacyFamily.LANGUAGE_AMBIGUITY: [
        "rhétorique", "juridique", "littéraire", "philosophique",
        "négociation", "contrat", "communication subtile"
    ],
    
    FallacyFamily.STATISTICAL_PROBABILISTIC: [
        "scientifique", "médical", "économique", "financier",
        "recherche", "analyse quantitative", "rapport technique"
    ],
    
    FallacyFamily.AUDIO_ORAL_CONTEXT: [
        "débat oral", "interview", "présentation", "discours",
        "conférence", "discussion en direct", "émission"
    ]
}


# Métriques d'évaluation par famille
FALLACY_FAMILY_METRICS = {
    FallacyFamily.AUTHORITY_POPULARITY: {
        "authority_relevance": {
            "description": "Pertinence de l'autorité dans le domaine (0-1)",
            "weight": 0.4
        },
        "source_credibility": {
            "description": "Crédibilité de la source (0-1)",
            "weight": 0.3
        },
        "popularity_representativeness": {
            "description": "Représentativité de l'opinion populaire citée (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.EMOTIONAL_APPEALS: {
        "emotional_intensity": {
            "description": "Intensité émotionnelle (0-1)",
            "weight": 0.4
        },
        "emotion_relevance": {
            "description": "Pertinence de l'émotion dans le contexte (0-1)",
            "weight": 0.3
        },
        "manipulation_intentionality": {
            "description": "Manipulation intentionnelle (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.GENERALIZATION_CAUSALITY: {
        "sample_representativeness": {
            "description": "Représentativité de l'échantillon (0-1)",
            "weight": 0.4
        },
        "causal_strength": {
            "description": "Force de la relation causale (0-1)",
            "weight": 0.3
        },
        "confounding_variables": {
            "description": "Présence de variables confondantes (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.DIVERSION_ATTACK: {
        "attack_relevance": {
            "description": "Pertinence de l'attaque (0-1)",
            "weight": 0.4
        },
        "diversion_degree": {
            "description": "Degré de diversion (0-1)",
            "weight": 0.3
        },
        "discussion_impact": {
            "description": "Impact sur la discussion principale (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.FALSE_DILEMMA_SIMPLIFICATION: {
        "alternatives_omitted": {
            "description": "Nombre d'alternatives omises",
            "weight": 0.4
        },
        "complexity_ratio": {
            "description": "Complexité réelle vs. présentée (0-1)",
            "weight": 0.3
        },
        "simplification_degree": {
            "description": "Degré de simplification (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.LANGUAGE_AMBIGUITY: {
        "ambiguity_degree": {
            "description": "Degré d'ambiguïté (0-1)",
            "weight": 0.4
        },
        "ambiguity_intentionality": {
            "description": "Intentionnalité de l'ambiguïté (0-1)",
            "weight": 0.3
        },
        "comprehension_impact": {
            "description": "Impact sur la compréhension (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.STATISTICAL_PROBABILISTIC: {
        "statistical_accuracy": {
            "description": "Exactitude des statistiques (0-1)",
            "weight": 0.4
        },
        "sample_representativeness": {
            "description": "Représentativité de l'échantillon (0-1)",
            "weight": 0.3
        },
        "statistical_relevance": {
            "description": "Pertinence des statistiques dans le contexte (0-1)",
            "weight": 0.3
        }
    },
    
    FallacyFamily.AUDIO_ORAL_CONTEXT: {
        "interruption_frequency": {
            "description": "Fréquence des interruptions",
            "weight": 0.3
        },
        "volume_variations": {
            "description": "Variations de volume (dB)",
            "weight": 0.3
        },
        "speech_rate": {
            "description": "Débit de parole (mots/minute)",
            "weight": 0.4
        }
    }
}


def get_family_severity_info(family: FallacyFamily) -> Dict[str, Any]:
    """Retourne les informations de sévérité pour une famille."""
    return FALLACY_FAMILY_SEVERITY.get(family, {})


def get_family_keywords(family: FallacyFamily) -> Dict[str, List[str]]:
    """Retourne les mots-clés de détection pour une famille."""
    return FALLACY_FAMILY_KEYWORDS.get(family, {})


def get_family_contexts(family: FallacyFamily) -> List[str]:
    """Retourne les contextes typiques pour une famille."""
    return FALLACY_FAMILY_CONTEXTS.get(family, [])


def get_family_metrics(family: FallacyFamily) -> Dict[str, Dict[str, Any]]:
    """Retourne les métriques d'évaluation pour une famille."""
    return FALLACY_FAMILY_METRICS.get(family, {})