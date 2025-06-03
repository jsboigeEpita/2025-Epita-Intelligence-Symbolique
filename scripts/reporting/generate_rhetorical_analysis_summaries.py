#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer des synthèses des analyses rhétoriques avec des extraits concrets.

Ce script:
1. Simule le chargement des extraits déchiffrés (discours d'Hitler, débats Lincoln Douglas)
2. Génère des analyses rhétoriques synthétiques mais réalistes pour ces extraits
3. Produit des synthèses au format Markdown avec:
   - Un résumé de l'analyse pour chaque extrait
   - Des extraits concrets du texte analysé
   - Des exemples de sophismes détectés avec leur contexte
   - Des métriques d'analyse (scores de cohérence, nombre de sophismes, etc.)
   - Des liens vers des analyses plus détaillées
4. Crée un rapport de synthèse global comparant les différents agents
5. Sauvegarde ces synthèses dans le répertoire results/

Auteur: Roo
Date: 15/05/2025
"""

import os
import sys
# import json # N'est plus utilisé ici
import logging
import argparse
from pathlib import Path
from datetime import datetime # Conservé pour le timestamp dans main (si encore utilisé)
# from typing import Dict, List, Any # N'est plus utilisé ici

# from argumentation_analysis.utils.text_processing import split_text_into_arguments # Déplacé
# from argumentation_analysis.utils.data_generation import generate_sample_text # Déplacé
# from argumentation_analysis.mocks.analysis_simulation import generate_mock_fallacy_detection, generate_mock_coherence_evaluation, generate_mock_rhetorical_analysis # Déplacé
from argumentation_analysis.reporting.summary_generator import run_summary_generation_pipeline
from project_core.utils.cli_utils import parse_summary_generation_arguments

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
# IMPORTANT: S'assurer que ce script est exécuté depuis un endroit où ce chemin relatif est valide
# ou utiliser une approche plus robuste pour déterminer la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RhetoricalAnalysisSummaries")

# Définition des sources et extraits simulés
SIMULATED_SOURCES = [
    {
        "source_name": "Discours d'Hitler",
        "extracts": [
            {"extract_name": "Discours du Reichstag (1939)", "type": "discours_politique"},
            {"extract_name": "Discours de Nuremberg (1934)", "type": "discours_politique"},
            {"extract_name": "Discours à Munich (1923)", "type": "discours_politique"},
            {"extract_name": "Discours sur l'annexion de l'Autriche (1938)", "type": "discours_politique"},
            {"extract_name": "Discours sur le pacte germano-soviétique (1939)", "type": "discours_politique"}
        ]
    },
    {
        "source_name": "Débats Lincoln-Douglas",
        "extracts": [
            {"extract_name": "Débat d'Ottawa (1858)", "type": "debat_politique"},
            {"extract_name": "Débat de Freeport (1858)", "type": "debat_politique"},
            {"extract_name": "Débat de Jonesboro (1858)", "type": "debat_politique"},
            {"extract_name": "Débat de Charleston (1858)", "type": "debat_politique"},
            {"extract_name": "Débat d'Alton (1858)", "type": "debat_politique"}
        ]
    }
]
# Définition des agents d'analyse rhétorique
RHETORICAL_AGENTS = [
    {
        "name": "Agent de base",
        "tools": [
            "ContextualFallacyDetector",
            "ArgumentCoherenceEvaluator",
            "SemanticArgumentAnalyzer"
        ],
        "strengths": [
            "Détection des sophismes de base",
            "Évaluation simple de la cohérence",
            "Analyse sémantique basique"
        ],
        "weaknesses": [
            "Analyse contextuelle limitée",
            "Pas de détection des sophismes complexes",
            "Pas d'évaluation de la gravité des sophismes"
        ]
    },
    {
        "name": "Agent avancé",
        "tools": [
            "EnhancedComplexFallacyAnalyzer",
            "EnhancedContextualFallacyAnalyzer",
            "EnhancedFallacySeverityEvaluator",
            "EnhancedRhetoricalResultAnalyzer"
        ],
        "strengths": [
            "Détection des sophismes complexes",
            "Analyse contextuelle approfondie",
            "Évaluation de la gravité des sophismes",
            "Recommandations détaillées"
        ],
        "weaknesses": [
            "Temps d'analyse plus long",
            "Complexité d'interprétation des résultats",
            "Sensibilité aux nuances contextuelles"
        ]
    }
]

# Définition des sophismes courants
COMMON_FALLACIES = [
    {
        "name": "Ad hominem",
        "description": "Attaque personnelle plutôt que l'argument",
        "severity": "Élevée",
        "examples": [
            "Son argument est invalide car il a un casier judiciaire.",
            "Comment peut-on faire confiance à quelqu'un qui a menti dans le passé?"
        ]
    },
    {
        "name": "Appel à l'autorité",
        "description": "Utilisation inappropriée d'une figure d'autorité pour soutenir un argument",
        "severity": "Modérée",
        "examples": [
            "Le Dr. Smith, qui est un physicien renommé, affirme que ce régime fonctionne.",
            "Selon un expert, cette théorie est correcte."
        ]
    },
    {
        "name": "Faux dilemme",
        "description": "Présentation de deux options comme les seules possibles alors qu'il en existe d'autres",
        "severity": "Modérée",
        "examples": [
            "Soit vous êtes avec nous, soit vous êtes contre nous.",
            "Nous devons choisir entre la liberté et la sécurité."
        ]
    },
    {
        "name": "Pente glissante",
        "description": "Suggestion qu'une action mènera inévitablement à une série d'événements négatifs",
        "severity": "Modérée",
        "examples": [
            "Si nous autorisons cela, bientôt tout sera permis.",
            "Si nous cédons sur ce point, nous devrons céder sur tous les autres."
        ]
    },
    {
        "name": "Appel à la peur",
        "description": "Utilisation de la peur pour influencer l'opinion",
        "severity": "Élevée",
        "examples": [
            "Si nous ne prenons pas ces mesures, notre nation sera détruite.",
            "Sans cette loi, le chaos règnera dans nos rues."
        ]
    },
    {
        "name": "Homme de paille",
        "description": "Déformation de l'argument de l'adversaire pour le rendre plus facile à attaquer",
        "severity": "Élevée",
        "examples": [
            "Vous voulez réduire le budget militaire, donc vous voulez laisser notre pays sans défense.",
            "Vous êtes en faveur de la régulation, donc vous êtes contre la liberté d'entreprise."
        ]
    }
]
# Les fonctions generate_fallacy_detection, generate_coherence_evaluation,
# generate_rhetorical_analysis, generate_markdown_summary, et generate_global_summary
# ont été déplacées vers argumentation_analysis.reporting.summary_generator
def main():
    """Fonction principale du script."""
    args = parse_summary_generation_arguments()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage de la génération des synthèses d'analyses rhétoriques via le pipeline...")
    
    output_dir = Path(args.output_dir)
    
    # Appel du pipeline modularisé
    # Les constantes SIMULATED_SOURCES, RHETORICAL_AGENTS, COMMON_FALLACIES sont définies globalement dans ce script.
    run_summary_generation_pipeline(
        simulated_sources_data=SIMULATED_SOURCES,
        rhetorical_agents_data=RHETORICAL_AGENTS,
        common_fallacies_data=COMMON_FALLACIES,
        output_reports_dir=output_dir
    )
    
    # Les logs de succès spécifiques (nombre d'analyses, chemins des fichiers) sont maintenant gérés
    # à l'intérieur du pipeline lui-même. On peut ajouter un log général ici.
    logger.info(f"Pipeline de génération de synthèses d'analyses rhétoriques terminé. Vérifiez le répertoire : {output_dir}")

# La fonction parse_arguments a été déplacée vers project_core.utils.cli_utils
# et renommée en parse_summary_generation_arguments

if __name__ == "__main__":
    main()