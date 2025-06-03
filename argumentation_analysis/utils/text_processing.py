# -*- coding: utf-8 -*-
"""
Utilitaires pour le traitement de texte dans le cadre de l'analyse d'argumentation.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def split_text_into_arguments(text: str) -> List[str]:
    """
    Divise un texte en arguments individuels.

    Utilise des heuristiques simples pour la division, par exemple en se basant
    sur les paragraphes (séquences de deux sauts de ligne ou plus).
    Les arguments vides ou constitués uniquement d'espaces sont ignorés.

    :param text: Le texte à diviser.
    :type text: str
    :return: Une liste de chaînes, chaque chaîne représentant un argument.
             Retourne une liste vide si le texte en entrée est vide ou None.
    :rtype: List[str]
    """
    if not text:
        logger.debug("Texte d'entrée vide ou None pour split_text_into_arguments. Retour d'une liste vide.")
        return []

    # Diviser par paragraphes (deux sauts de ligne ou plus), en conservant les sauts de ligne simples au sein des arguments.
    # Utilisation de re.split avec un groupe de capture pour potentiellement conserver les délimiteurs si besoin futur,
    # mais ici nous ne les utilisons pas directement dans le résultat.
    paragraphs = re.split(r'(\n\s*\n+)', text)
    
    arguments = []
    current_argument = ""
    for part in paragraphs:
        if re.match(r'^\n\s*\n+$', part): # Si c'est un délimiteur de paragraphe
            if current_argument.strip():
                arguments.append(current_argument.strip())
            current_argument = ""
        else:
            current_argument += part
            
    # Ajouter le dernier argument s'il existe
    if current_argument.strip():
        arguments.append(current_argument.strip())

    if not arguments and text.strip():
        # Si aucune division par paragraphe n'a eu lieu mais que le texte n'est pas vide,
        # considérer le texte entier comme un seul argument.
        logger.debug("Aucun séparateur de paragraphe trouvé, le texte entier est considéré comme un argument.")
        arguments.append(text.strip())
    
    # Filtrer les arguments potentiellement vides qui auraient pu passer
    final_arguments = [arg for arg in arguments if arg]

    logger.info(f"{len(final_arguments)} arguments extraits du texte (longueur initiale: {len(text)} caractères).")
    if final_arguments:
        logger.debug(f"Premier argument extrait (aperçu): '{final_arguments[0][:100]}...'")
    return final_arguments