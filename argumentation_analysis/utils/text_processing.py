# -*- coding: utf-8 -*-
"""
Utilitaires pour le traitement de texte dans le cadre de l'analyse d'argumentation.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def split_text_into_arguments(text: str, min_arg_length: int = 10) -> List[str]:
    """
    Divise un texte en arguments individuels.

    Cette fonction utilise des heuristiques simples pour diviser un texte
    en arguments individuels, en se basant sur la ponctuation.
    Une version plus avancée pourrait utiliser NLTK ou spaCy pour une segmentation de phrases plus robuste.

    Args:
        text (str): Texte à diviser en arguments.
        min_arg_length (int): Longueur minimale pour qu'un segment soit considéré comme un argument.

    Returns:
        List[str]: Liste des arguments extraits.
    """
    if not text or not isinstance(text, str):
        logger.warning("split_text_into_arguments a reçu une entrée non valide (None ou pas une chaîne).")
        return []

    # Liste des délimiteurs d'arguments.
    # Le motif regex recherche les fins de phrases typiques.
    # Une amélioration future pourrait utiliser re.split() avec un motif plus complexe.
    delimiters = [
        ". \n", "! \n", "? \n", # Fin de phrase suivie d'un espace puis nouvelle ligne
        ".\n", "!\n", "?\n",   # Fin de phrase suivie d'une nouvelle ligne
        ". ", "! ", "? ",       # Fin de phrase suivie d'un espace
        # On pourrait ajouter des délimiteurs plus simples comme "." s'ils ne sont pas suivis d'un espace ou d'une nouvelle ligne,
        # mais cela risque de couper au milieu des phrases (ex: "Mr. Smith").
        # Pour l'instant, on se limite aux délimiteurs qui indiquent plus clairement une fin de segment.
    ]
    
    # Utiliser un marqueur de split unique qui a peu de chances d'être dans le texte
    split_marker = "<ARG_SPLIT_MARKER_XYZ>" # Rendu plus unique
    
    processed_text = text
    for delimiter in delimiters:
        # Remplacer le délimiteur par lui-même (sans l'espace s'il y en avait un après le point) + le marqueur.
        # Cela permet de conserver la ponctuation originale à la fin de l'argument.
        # Exemple: "Phrase 1. Phrase 2." -> "Phrase 1.<ARG_SPLIT_MARKER_XYZ>Phrase 2.<ARG_SPLIT_MARKER_XYZ>"
        # Si le délimiteur est ". \n", on remplace par ".\n<ARG_SPLIT_MARKER_XYZ>"
        # Si le délimiteur est ". ", on remplace par ".<ARG_SPLIT_MARKER_XYZ>"
        # Si le délimiteur est ".\n", on remplace par ".\n<ARG_SPLIT_MARKER_XYZ>"
        
        # Conserver la ponctuation et le saut de ligne si présent dans le délimiteur
        replacement = delimiter.rstrip(' ') # Enlève l'espace de fin s'il y en a un ("! " -> "!")
        processed_text = processed_text.replace(delimiter, replacement + split_marker)

    raw_arguments = processed_text.split(split_marker)
    
    arguments = []
    for arg in raw_arguments:
        cleaned_arg = arg.strip() # Nettoyer les espaces au début/fin de chaque segment potentiel
        # Vérifier si l'argument nettoyé n'est pas vide et respecte la longueur minimale
        if cleaned_arg and len(cleaned_arg) >= min_arg_length:
            arguments.append(cleaned_arg)
    
    if not arguments and text.strip() and len(text.strip()) >= min_arg_length:
        # Si aucun argument n'a été trouvé par les délimiteurs mais que le texte original est valide,
        # considérer le texte entier comme un seul argument.
        logger.debug(f"Aucun délimiteur standard n'a permis de scinder le texte. Texte original considéré comme un seul argument: '{text[:70]}...'")
        arguments.append(text.strip())
        
    logger.debug(f"Texte divisé en {len(arguments)} arguments.")
    return arguments

# D'autres fonctions de traitement de texte pourraient être ajoutées ici.
# Par exemple, normalisation, suppression de stop-words, lemmatisation, etc.
