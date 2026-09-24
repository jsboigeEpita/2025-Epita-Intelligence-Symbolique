#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire pour le chargement des données d'analyse.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import (
    datetime,
)  # Ajouté car utilisé dans le code original pour les noms d'extraits inconnus

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def load_results_from_json(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les résultats d'analyse à partir d'un fichier JSON spécifié.

    Le fichier doit contenir une liste JSON de dictionnaires, chacun représentant
    un ensemble de résultats d'analyse. Une liste vide est un résultat légitime
    et revient telle quelle. Un fichier absent, illisible, mal formé ou qui ne
    contient pas une liste lève (#2344) : renvoyer ``[]`` dans ces cas rendait
    « aucun résultat » indiscernable d'un chargement en échec.

    :param file_path: Le chemin (objet `Path`) vers le fichier JSON contenant les résultats.
    :type file_path: Path
    :return: Une liste de dictionnaires représentant les résultats d'analyse.
    :rtype: List[Dict[str, Any]]
    :raises FileNotFoundError: le chemin n'existe pas ou n'est pas un fichier.
    :raises json.JSONDecodeError: le contenu n'est pas du JSON valide.
    :raises ValueError: le JSON n'est pas une liste.
    :raises OSError: le fichier ne peut pas être lu.
    """
    logger.info(f"Chargement des résultats depuis {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"Le fichier {file_path} n'existe pas.")
    if not file_path.is_file():
        raise FileNotFoundError(f"Le chemin {file_path} n'est pas un fichier.")

    with open(file_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    if not isinstance(results, list):
        raise ValueError(
            f"Les données dans {file_path} ne sont pas une liste JSON "
            f"(type trouvé : {type(results).__name__})."
        )

    logger.info(f"[OK] {len(results)} résultats chargés avec succès depuis {file_path}")
    return results
