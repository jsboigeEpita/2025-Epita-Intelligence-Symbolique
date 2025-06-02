"""
Package `nlp` pour les fonctionnalités de Traitement du Langage Naturel (NLP).

Ce package regroupe les modules et utilitaires spécifiquement dédiés au
traitement et à l'analyse du langage naturel dans le contexte de l'analyse
d'argumentation. Cela peut inclure :
    - La génération et la gestion de plongements lexicaux (embeddings).
    - Des outils pour l'analyse syntaxique ou sémantique de bas niveau.
    - La reconnaissance d'entités nommées (NER).
    - D'autres techniques de NLP pertinentes pour comprendre et structurer
      le contenu textuel des arguments.

Modules clés :
    - `embedding_utils`: Fonctions pour la création et la manipulation d'embeddings.
"""

# Exposer les fonctions ou classes importantes si nécessaire
# from .embedding_utils import generate_embeddings

__all__ = [
    # "generate_embeddings",
]

import logging
logger = logging.getLogger(__name__)
logger.info("Package 'argumentation_analysis.nlp' chargé.")