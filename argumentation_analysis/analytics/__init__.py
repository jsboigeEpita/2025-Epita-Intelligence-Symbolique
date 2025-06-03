# -*- coding: utf-8 -*-
"""
Package `analytics` pour l'analyse quantitative et statistique des arguments.

Ce package regroupe les modules dédiés à l'analyse quantitative des données
textuelles et des résultats d'argumentation. Il fournit des outils pour :
    - Calculer des statistiques descriptives sur les textes et les arguments.
    - Effectuer des analyses de complexité textuelle.
    - Potentiellement, intégrer des métriques d'évaluation de la qualité
      ou de la force des arguments.

Modules clés :
    - `stats_calculator`: Fonctions pour calculer diverses statistiques.
    - `text_analyzer`: Outils pour l'analyse de caractéristiques textuelles.
"""

# Initializer for the argumentation_analysis.analytics module

# Exposer les classes ou fonctions importantes si nécessaire
# from .stats_calculator import StatsCalculator # Exemple
# from .text_analyzer import TextAnalyzer       # Exemple

__all__ = [
    # "StatsCalculator",
    # "TextAnalyzer",
]

import logging
logger = logging.getLogger(__name__)
logger.info("Package 'argumentation_analysis.analytics' chargé.")
