"""
Module core contenant les composants partagés.

Ce module inclut les services LLM, la configuration JVM, la gestion d'état partagé,
et d'autres composants fondamentaux utilisés par le reste du système.
"""

# Importations des sous-modules
try:
    from . import shared_state
    from . import jvm_setup
    from . import llm_service
    from . import state_manager_plugin
    from . import strategies
    from . import communication
except ImportError as e:
    import logging
    logging.warning(f"Certains sous-modules de 'core' n'ont pas pu être importés: {e}")

# Exposer les fonctions et classes importantes
try:
    from .llm_service import create_llm_service
    from .jvm_setup import initialize_jvm, download_tweety_jars
    from .shared_state import SharedState
except ImportError as e:
    import logging
    logging.warning(f"Certaines fonctions/classes de 'core' n'ont pas pu être exposées: {e}")