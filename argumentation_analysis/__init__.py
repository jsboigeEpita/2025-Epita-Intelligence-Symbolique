"""
Package principal pour l'analyse d'argumentation.

Ce package contient tous les modules nécessaires pour l'analyse d'argumentation,
y compris les modèles de données, les services, les agents et les utilitaires.
"""

# Version du package
__version__ = '1.0.0'

# Importations pour faciliter l'accès aux modules principaux
from . import paths
from . import core

# Remplacement du lazy import par des imports directs pour débogage des tests
from . import agents
from . import orchestration
# from . import ui # Re-commenté pour éviter le blocage
from . import utils
from . import examples
from . import services
from . import scripts
print("INFO [ARG_ANALYSIS_INIT]: Import de 'ui' re-commenté dans argumentation_analysis/__init__.py.")

# Exposer certaines fonctions couramment utilisées
try:
    from .core.llm_service import create_llm_service
    from .core.jvm_setup import initialize_jvm
except ImportError:
    # En cas d'erreur d'importation, ne pas échouer complètement
    # Cela permet d'importer d'autres parties du package même si certains modules sont manquants
    import logging
    logging.warning("Certaines importations ont échoué dans __init__.py. Certaines fonctionnalités peuvent être indisponibles.")