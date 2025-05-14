"""
Module orchestration contenant la logique d'exécution de la conversation.

Ce module gère l'orchestration des différents agents et services pour
l'analyse argumentative, y compris l'exécution des conversations et
la coordination des agents.
"""

# Importations des sous-modules
try:
    from . import analysis_runner
    from . import hierarchical
except ImportError as e:
    import logging
    logging.warning(f"Certains sous-modules de 'orchestration' n'ont pas pu être importés: {e}")

# Exposer les fonctions importantes
try:
    from .analysis_runner import run_analysis_conversation
except ImportError as e:
    import logging
    logging.warning(f"La fonction 'run_analysis_conversation' n'a pas pu être exposée: {e}")