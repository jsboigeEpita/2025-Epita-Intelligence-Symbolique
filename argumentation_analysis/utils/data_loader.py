#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire pour le chargement des données d'analyse.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime # Ajouté car utilisé dans le code original pour les noms d'extraits inconnus

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def load_results_from_json(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les résultats d'analyse à partir d'un fichier JSON spécifié.

    Cette fonction s'attend à ce que le fichier JSON contienne une liste de
    dictionnaires, chaque dictionnaire représentant un ensemble de résultats d'analyse.
    Elle gère les erreurs de fichier non trouvé, de format JSON incorrect,
    et d'autres exceptions potentielles lors de la lecture.

    :param file_path: Le chemin (objet `Path`) vers le fichier JSON contenant les résultats.
    :type file_path: Path
    :return: Une liste de dictionnaires représentant les résultats d'analyse.
             Retourne une liste vide si le fichier n'existe pas, n'est pas un fichier,
             si le JSON est malformé, ou si une autre erreur de lecture survient.
    :rtype: List[Dict[str, Any]]
    """
    logger.info(f"Chargement des résultats depuis {file_path}")
    
    if not file_path.exists():
        logger.error(f"Le fichier {file_path} n'existe pas.")
        return []
    if not file_path.is_file():
        logger.error(f"Le chemin {file_path} n'est pas un fichier.")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        if not isinstance(results, list):
            logger.warning(f"Les données dans {file_path} ne sont pas une liste JSON. Type trouvé: {type(results)}. Retourne une liste vide.")
            return []
            
        logger.info(f"[OK] {len(results)} résultats chargés avec succès depuis {file_path}")
        return results
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON dans {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erreur inattendue lors du chargement de {file_path}: {e}")
        return []