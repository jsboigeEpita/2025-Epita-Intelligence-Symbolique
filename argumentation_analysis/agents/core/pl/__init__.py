"""
Module pour la logique propositionnelle (PL).

Ce module contient les définitions et les agents spécialisés
dans l'analyse en logique propositionnelle via Tweety/JPype.
"""

try:
    pass

    __all__ = ["PropositionalLogicPlugin", "setup_pl_kernel", "PL_AGENT_INSTRUCTIONS"]
except ImportError as e:
    import logging

    logging.warning(f"Impossible d'importer les définitions PL: {e}")
    __all__ = []
