# -*- coding: utf-8 -*-
"""
Utilitaires pour la validation de base du contenu et de la lisibilité des fichiers.
"""

import logging
import json
from pathlib import Path # Ajout pour le typage Path
from typing import Tuple # Ajout pour le typage Tuple

logger = logging.getLogger(__name__)

def check_text_file_readable_and_not_empty(file_path: Path) -> Tuple[bool, str]:
    """
    Vérifie qu'un fichier texte est lisible et n'est pas vide (après strip).

    Args:
        file_path (Path): Chemin vers le fichier texte.

    Returns:
        Tuple[bool, str]: (True si valide, message de statut)
    """
    if not isinstance(file_path, Path):
        try:
            file_path = Path(file_path)
        except TypeError:
            return False, f"Chemin de fichier invalide: {file_path}"

    if not file_path.exists() or not file_path.is_file():
        return False, f"Fichier non trouvé ou n'est pas un fichier: {file_path}"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not content.strip():
            return False, f"Le fichier est vide ou ne contient que des espaces: {file_path}"
            
        return True, f"Fichier texte valide et non vide ({len(content)} caractères): {file_path}"
    except Exception as e:
        return False, f"Erreur lors de la lecture du fichier {file_path}: {str(e)}"

def check_json_file_valid(file_path: Path) -> Tuple[bool, str]:
    """
    Vérifie qu'un fichier JSON est valide, peut être parsé et n'est pas vide.

    Args:
        file_path (Path): Chemin vers le fichier JSON.

    Returns:
        Tuple[bool, str]: (True si valide, message de statut)
    """
    if not isinstance(file_path, Path):
        try:
            file_path = Path(file_path)
        except TypeError:
            return False, f"Chemin de fichier invalide: {file_path}"

    if not file_path.exists() or not file_path.is_file():
        return False, f"Fichier non trouvé ou n'est pas un fichier: {file_path}"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Vérifier si les données chargées sont "vides" (ex: {} ou [])
        if not data: # Ceci est True pour un dict vide {} ou une liste vide []
            return False, f"Fichier JSON valide mais structure de données vide: {file_path}"
            
        return True, f"JSON valide et données non vides (longueur str: {len(str(data))}): {file_path}"
    except json.JSONDecodeError as e:
        return False, f"JSON invalide dans {file_path}: {str(e)}"
    except Exception as e: # Autres erreurs de lecture
        return False, f"Erreur lors de la lecture du fichier JSON {file_path}: {str(e)}"

def check_markdown_file_readable_and_basic_structure(file_path: Path) -> Tuple[bool, str]:
    """
    Vérifie qu'un fichier Markdown est lisible, non vide et contient une structure de base (titres).

    Args:
        file_path (Path): Chemin vers le fichier Markdown.

    Returns:
        Tuple[bool, str]: (True si valide, message de statut)
    """
    is_readable, msg_readable = check_text_file_readable_and_not_empty(file_path)
    if not is_readable:
        return False, msg_readable # Le message inclut déjà le nom du fichier

    # Si lisible et non vide, vérifier la structure Markdown
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Vérification basique de la structure Markdown (présence de titres)
        if not any(line.strip().startswith('#') for line in content.splitlines()):
            return False, f"Aucun titre Markdown ('#') détecté dans {file_path}"
            
        return True, f"Fichier Markdown valide avec titres ({len(content)} caractères): {file_path}"
    except Exception as e: # Devrait être déjà attrapé par check_text_file_readable_and_not_empty
        return False, f"Erreur inattendue lors de la vérification de la structure Markdown de {file_path}: {str(e)}"