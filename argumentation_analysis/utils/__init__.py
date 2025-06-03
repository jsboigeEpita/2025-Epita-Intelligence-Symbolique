# -*- coding: utf-8 -*-
"""
Ce module initialise le package argumentation_analysis.utils.

Il rend accessibles les utilitaires pour l'analyse d'argumentation,
tels que le traitement de texte, le chargement de données spécifiques,
la comparaison d'analyses, etc.
"""

# Importations sélectives pour exposer les fonctionnalités clés
# Exemple (à adapter lorsque les modules seront créés) :
# from .text_processing import split_text_into_arguments
# from .data_loaders import load_specific_format_data
# from .analysis_comparison import compare_analyses

# Définir __all__ si vous voulez contrôler ce qui est importé avec 'from .utils import *'
# __all__ = ['split_text_into_arguments', 'load_specific_format_data', 'compare_analyses']

# Log d'initialisation du package (optionnel)
import logging
logger = logging.getLogger(__name__)
logger.debug("Package 'argumentation_analysis.utils' initialisé.")
