# -*- coding: utf-8 -*-
"""
Utilitaires pour la gestion des arguments de ligne de commande (CLI).
"""

import argparse

# from pathlib import Path # Pas nécessaire pour cette fonction spécifique, mais souvent utile avec argparse


def parse_advanced_analysis_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande spécifiques au script d'analyse rhétorique avancée.

    Returns:
        argparse.Namespace: Les arguments parsés.
    """
    parser = argparse.ArgumentParser(
        description="Analyse rhétorique avancée des extraits déchiffrés"
    )

    parser.add_argument(
        "--extracts",
        "-e",
        type=str,  # Garder en str, la conversion en Path se fait dans le script appelant
        help="Chemin du fichier contenant les extraits déchiffrés",
        default=None,
    )

    parser.add_argument(
        "--base-results",
        "-b",
        type=str,
        help="Chemin du fichier contenant les résultats de l'analyse de base",
        default=None,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Chemin du fichier de sortie pour les résultats de l'analyse avancée",
        default=None,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires",
    )

    return parser.parse_args()


# On pourrait ajouter d'autres fonctions de parsing d'arguments ici pour d'autres scripts.
# Par exemple:
# def parse_data_processing_arguments() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(description="Script de traitement de données")
#     parser.add_argument("--input-file", required=True)
#     # ... autres arguments
#     return parser.parse_args()
def parse_summary_generation_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande spécifiques au script de génération de synthèses.

    Returns:
        argparse.Namespace: Les arguments parsés.
    """
    parser = argparse.ArgumentParser(
        description="Génération de synthèses d'analyses rhétoriques"
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,  # Garder en str, la conversion en Path se fait dans le script appelant
        help="Répertoire de sortie pour les synthèses",
        default="results",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires",
    )

    return parser.parse_args()


def parse_extract_verification_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande spécifiques au script de vérification des extraits.

    Returns:
        argparse.Namespace: Les arguments parsés.
    """
    parser = argparse.ArgumentParser(description="Vérification des extraits")
    parser.add_argument(
        "--output",
        "-o",
        default="verify_report.html",
        help="Fichier de sortie pour le rapport HTML",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Activer le mode verbeux"
    )
    parser.add_argument(
        "--input", "-i", default=None, help="Fichier d'entrée personnalisé"
    )
    parser.add_argument(
        "--hitler-only",
        action="store_true",
        help="Traiter uniquement le corpus de discours d'Hitler",
    )
    return parser.parse_args()


def parse_extract_repair_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande spécifiques au script de réparation des extraits.

    Returns:
        argparse.Namespace: Les arguments parsés.
    """
    parser = argparse.ArgumentParser(
        description="Réparation des bornes défectueuses dans les extraits"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="repair_report.html",
        help="Fichier de sortie pour le rapport HTML",
    )
    parser.add_argument(
        "--save", "-s", action="store_true", help="Sauvegarder les modifications"
    )
    parser.add_argument(
        "--hitler-only",
        action="store_true",
        help="Traiter uniquement le corpus de discours d'Hitler",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Activer le mode verbeux"
    )
    parser.add_argument(
        "--input", "-i", default=None, help="Fichier d'entrée personnalisé"
    )
    parser.add_argument(
        "--output-json",
        default="extract_sources_updated.json",
        help="Fichier de sortie JSON pour vérification",
    )
    return parser.parse_args()
