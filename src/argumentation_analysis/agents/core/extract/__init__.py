"""
Module extract contenant l'agent d'extraction et ses composants.

Ce module fournit les fonctionnalités pour extraire des informations
à partir de textes, y compris la définition de l'agent d'extraction,
les définitions des extraits, et les prompts utilisés.
"""

# Exposer les classes et fonctions importantes
try:
    from .extract_agent import ExtractAgent # setup_extract_agent a été supprimé
    from .extract_definitions import ExtractDefinition, ExtractResult
    from .prompts import EXTRACT_PROMPT_TEMPLATE
except ImportError as e:
    import logging
    logging.warning(f"Certaines classes/fonctions de 'agents.core.extract' n'ont pas pu être exposées: {e}")