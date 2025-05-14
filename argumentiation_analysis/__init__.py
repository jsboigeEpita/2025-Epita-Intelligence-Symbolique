"""
Package principal pour l'analyse d'argumentation.

Ce package contient tous les modules nécessaires pour l'analyse d'argumentation,
y compris les modèles de données, les services, les agents et les utilitaires.
"""

# Version du package
__version__ = '1.0.0'

# Importations pour faciliter l'accès aux modules principaux
import argumentiation_analysis.core
import argumentiation_analysis.agents
import argumentiation_analysis.orchestration
import argumentiation_analysis.ui
import argumentiation_analysis.utils
from . import paths

# Exposer certaines fonctions couramment utilisées
try:
    from .core.llm_service import create_llm_service
    from .core.jvm_setup import initialize_jvm
except ImportError:
    # En cas d'erreur d'importation, ne pas échouer complètement
    # Cela permet d'importer d'autres parties du package même si certains modules sont manquants
    import logging
    logging.warning("Certaines importations ont échoué dans __init__.py. Certaines fonctionnalités peuvent être indisponibles.")