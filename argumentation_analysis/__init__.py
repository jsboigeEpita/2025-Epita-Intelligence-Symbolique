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

# Utilisation d'importations conditionnelles pour éviter les importations circulaires
def _lazy_import():
    """Importe les modules de manière paresseuse pour éviter les importations circulaires."""
    global agents, orchestration, ui, utils, examples, services, scripts
    
    import argumentation_analysis.agents as agents
    import argumentation_analysis.orchestration as orchestration
    import argumentation_analysis.ui as ui
    import argumentation_analysis.utils as utils
    import argumentation_analysis.examples as examples
    import argumentation_analysis.services as services
    import argumentation_analysis.scripts as scripts

# Appeler la fonction d'importation paresseuse
_lazy_import()

# Exposer certaines fonctions couramment utilisées
try:
    from .core.llm_service import create_llm_service
    from .core.jvm_setup import initialize_jvm
except ImportError:
    # En cas d'erreur d'importation, ne pas échouer complètement
    # Cela permet d'importer d'autres parties du package même si certains modules sont manquants
    import logging
    logging.warning("Certaines importations ont échoué dans __init__.py. Certaines fonctionnalités peuvent être indisponibles.")