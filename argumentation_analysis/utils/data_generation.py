# -*- coding: utf-8 -*-
"""
Utilitaires pour la génération de données d'exemple ou de test
pour l'analyse d'argumentation.
"""

import logging
from typing import Dict, Any # Ajouté pour type hinting si besoin futur

logger = logging.getLogger(__name__)

def generate_sample_text(extract_name: str, source_name: str) -> str:
    """
    Génère un texte d'exemple simple pour un extrait donné.

    Le texte généré est destiné à être utilisé pour des tests ou des démonstrations
    et contient des phrases de base pour simuler un contenu analysable.

    :param extract_name: Le nom de l'extrait pour lequel générer le texte.
    :type extract_name: str
    :param source_name: Le nom de la source de l'extrait.
    :type source_name: str
    :return: Une chaîne de caractères représentant le texte d'exemple.
    :rtype: str
    """
    if not extract_name:
        extract_name = "Inconnu"
        logger.debug("Nom d'extrait non fourni, utilisation de 'Inconnu'.")
    if not source_name:
        source_name = "Inconnue"
        logger.debug("Nom de source non fourni, utilisation de 'Inconnue'.")

    sample_text = (
        f"Ceci est un texte d'exemple généré pour l'extrait intitulé '{extract_name}' "
        f"provenant de la source '{source_name}'.\n\n"
        "Ce texte a pour objectif de simuler un contenu qui pourrait être sujet à une analyse rhétorique. "
        "Il contient plusieurs phrases et est structuré en paragraphes pour permettre une évaluation basique des outils d'analyse.\n"
        "Par exemple, on pourrait y chercher des sophismes, évaluer la cohérence, ou identifier les figures de style. "
        "La complexité de ce texte est volontairement limitée pour faciliter les tests initiaux."
    )
    logger.info(f"Texte d'exemple généré pour extract='{extract_name}', source='{source_name}'.")
    return sample_text

# Potentiellement d'autres fonctions de génération de données ici à l'avenir.
# Par exemple, générer des structures de résultats d'analyse simulées, etc.