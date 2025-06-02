# -*- coding: utf-8 -*-
"""Utilitaires pour la génération de données d'exemple ou de test."""

import logging

logger = logging.getLogger(__name__)

def generate_sample_text(extract_name: str, source_name: str) -> str:
    """
    Génère un texte d'exemple pour un extrait donné.

    Cette fonction est utilisée lorsque le contenu réel de l'extrait n'est pas
    disponible, par exemple pour des tests ou des démonstrations. Le texte généré
    dépend de mots-clés présents dans `extract_name` ou `source_name`.

    :param extract_name: Nom de l'extrait (peut contenir des mots-clés comme
                         "Lincoln", "Débat", "hitler", "churchill").
    :type extract_name: str
    :param source_name: Nom de la source (peut aussi contenir des mots-clés).
    :type source_name: str
    :return: Un texte d'exemple généré.
    :rtype: str
    """
    logger.debug(f"Génération de texte d'exemple pour extract_name='{extract_name}', source_name='{source_name}'")
    
    # Logique de génération de texte d'exemple
    # (Identique à la fonction originale, avec une petite adaptation pour couvrir plus de cas)
    if "Lincoln" in extract_name or "Lincoln" in source_name:
        return """
        Nous sommes engagés dans une grande guerre civile, mettant à l'épreuve si cette nation, ou toute nation ainsi conçue et ainsi dédiée, peut perdurer.
        Nous sommes réunis sur un grand champ de bataille de cette guerre. Nous sommes venus dédier une portion de ce champ comme lieu de dernier repos pour ceux qui ont donné leur vie pour que cette nation puisse vivre.
        Il est tout à fait approprié et juste que nous le fassions. Mais, dans un sens plus large, nous ne pouvons pas dédier, nous ne pouvons pas consacrer, nous ne pouvons pas sanctifier ce sol.
        Les braves hommes, vivants et morts, qui ont lutté ici, l'ont consacré, bien au-delà de notre pauvre pouvoir d'ajouter ou de retrancher.
        """
    elif "Débat" in extract_name or "Discours" in extract_name or \
         "Hitler" in source_name or "hitler" in extract_name.lower() or \
         "Churchill" in source_name or "churchill" in extract_name.lower(): # Étendre pour couvrir plus de cas des scripts
        return """
        Mesdames et messieurs, je me présente devant vous aujourd'hui pour discuter d'une question d'importance nationale.
        Premièrement, nous devons considérer les principes fondamentaux qui guident notre nation.
        Deuxièmement, nous devons examiner les conséquences pratiques de ces principes dans notre vie quotidienne.
        Enfin, nous devons réfléchir à la manière dont nous pouvons avancer ensemble, en tant que nation unie, malgré nos différences.
        Je crois fermement que c'est par le dialogue et la compréhension mutuelle que nous pourrons surmonter nos défis.
        """
    else:
        return """
        L'argumentation est l'art de convaincre par le raisonnement logique et la présentation d'évidences.
        Un bon argument repose sur des prémisses solides et des inférences valides.
        Cependant, il faut être vigilant face aux sophismes qui peuvent miner la qualité d'un raisonnement.
        La cohérence argumentative est essentielle pour maintenir la crédibilité d'un discours.
        En conclusion, l'analyse rhétorique nous permet d'évaluer la qualité et l'efficacité des arguments présentés.
        """