# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de chaînes de caractères.
"""

import logging
from typing import Tuple, Optional # Ajout pour le typage

logger = logging.getLogger(__name__)

def get_significant_substrings(marker_text: str, length: int = 30) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrait des sous-chaînes significatives (préfixe et suffixe) d'un texte de marqueur.
    
    Retire les espaces de début/fin du texte, puis prend les `length` premiers
    et `length` derniers caractères. Si le texte nettoyé est plus court que `length`,
    le préfixe sera le texte entier et le suffixe également (ou une partie si `length` est très petit).
    Si le texte nettoyé est plus court que `2 * length`, les sous-chaînes peuvent se chevaucher.

    Args:
        marker_text (str): Le texte du marqueur à traiter.
        length (int, optional): La longueur souhaitée pour le préfixe et le suffixe.
                                Par défaut à 30.

    Returns:
        Tuple[Optional[str], Optional[str]]: Un tuple contenant le préfixe et le suffixe.
                                             Retourne (None, None) si marker_text est None,
                                             vide, ou ne contient que des espaces.
    """
    if not marker_text or not isinstance(marker_text, str):
        logger.debug("Texte de marqueur non valide ou non fourni.")
        return None, None
    
    cleaned_marker = marker_text.strip()
    if not cleaned_marker:
        logger.debug("Texte de marqueur vide après nettoyage.")
        return None, None

    # Si le texte nettoyé est très court, le préfixe et le suffixe peuvent être identiques ou se chevaucher.
    prefix = cleaned_marker[:length]
    suffix = cleaned_marker[-length:]
    
    logger.debug(f"Pour le marqueur (nettoyé, aperçu): '{cleaned_marker[:50]}...', préfixe: '{prefix}', suffixe: '{suffix}'")
    return prefix, suffix