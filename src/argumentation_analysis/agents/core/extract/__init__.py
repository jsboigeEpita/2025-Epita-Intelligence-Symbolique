"""
Package `extract` pour les agents d'extraction d'informations.

Ce package fournit les composants nécessaires à l'extraction structurée
d'informations à partir de textes. Il comprend :
    - `ExtractAgent`: L'agent principal responsable de l'orchestration de l'extraction.
    - `ExtractDefinition`: Modèle Pydantic pour définir la structure des informations à extraire.
    - `ExtractResult`: Modèle Pydantic pour encapsuler les résultats de l'extraction.
    - `prompts`: Contient les templates de prompts utilisés par `ExtractAgent`.

Les composants principaux sont exposés pour faciliter leur utilisation par d'autres
parties du système d'analyse argumentative.
"""

# Exposer les classes et fonctions importantes
try:
    from .extract_agent import ExtractAgent
    from .extract_definitions import ExtractDefinition, ExtractResult
    from .prompts import EXTRACT_PROMPT_TEMPLATE

    __all__ = [
        "ExtractAgent",
        "ExtractDefinition",
        "ExtractResult",
        "EXTRACT_PROMPT_TEMPLATE",
    ]
except ImportError as e:
    import logging
    logging.warning(f"Certaines classes/fonctions de 'agents.core.extract' n'ont pas pu être exposées: {e}")
    __all__ = []