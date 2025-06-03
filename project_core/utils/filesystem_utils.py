# -*- coding: utf-8 -*-
"""
Utilitaires pour les opérations sur le système de fichiers.
"""

import logging
import os # Conservé pour os.path.exists si préféré à Path.exists() pour une raison
from pathlib import Path
from typing import List, Tuple, Union, Iterable # Ajout de Union et Iterable

logger = logging.getLogger(__name__)

def ensure_directory_exists(dir_path: Path) -> bool:
    """
    S'assure qu'un répertoire existe, le crée s'il n'existe pas.

    Args:
        dir_path (Path): Chemin du répertoire à vérifier/créer.

    Returns:
        bool: True si le répertoire existe ou a été créé, False en cas d'erreur.
    """
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Répertoire assuré d'exister: {dir_path.resolve()}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création/vérification du répertoire {dir_path.resolve()}: {e}", exc_info=True)
        return False

def create_gitkeep_in_directory(dir_path: Path, overwrite: bool = False) -> bool:
    """
    Crée un fichier .gitkeep dans le répertoire spécifié s'il n'existe pas déjà,
    ou si overwrite est True.

    Args:
        dir_path (Path): Chemin du répertoire où créer le .gitkeep.
        overwrite (bool): Si True, écrase le .gitkeep s'il existe déjà.

    Returns:
        bool: True si le fichier .gitkeep a été créé/vérifié, False en cas d'erreur.
    """
    if not ensure_directory_exists(dir_path):
        return False # Erreur déjà loggée par ensure_directory_exists

    gitkeep_file = dir_path / ".gitkeep"
    try:
        if not gitkeep_file.exists() or overwrite:
            gitkeep_file.touch(exist_ok=overwrite) # exist_ok=True si overwrite est True
            logger.info(f"Fichier .gitkeep {'créé/mis à jour' if overwrite else 'créé'} dans {dir_path.resolve()}")
        else:
            logger.debug(f"Le fichier .gitkeep existe déjà dans {dir_path.resolve()} et overwrite est False.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création du fichier .gitkeep dans {dir_path.resolve()}: {e}", exc_info=True)
        return False

def check_files_existence(
    file_paths: Iterable[Union[str, Path]]
) -> Tuple[List[Path], List[Path]]:
    """
    Vérifie l'existence d'une liste de fichiers.

    Args:
        file_paths (Iterable[Union[str, Path]]): Une collection de chemins de fichiers
                                                 (chaînes ou objets Path).

    Returns:
        Tuple[List[Path], List[Path]]: Un tuple contenant deux listes:
            - La liste des chemins de fichiers qui existent.
            - La liste des chemins de fichiers qui n'existent pas.
    """
    existing_files: List[Path] = []
    missing_files: List[Path] = []

    if not file_paths:
        logger.debug("Aucun chemin de fichier fourni pour la vérification d'existence.")
        return [], []

    for file_path_item in file_paths:
        try:
            p = Path(file_path_item)
            if p.exists() and p.is_file(): # S'assurer que c'est un fichier
                existing_files.append(p)
            elif p.exists() and not p.is_file():
                 logger.warning(f"Le chemin existe mais n'est pas un fichier: {p}")
                 missing_files.append(p) # Le considérer comme manquant si on attend un fichier
            else:
                missing_files.append(p)
        except TypeError:
            logger.warning(f"Chemin invalide ou non convertible en Path: {file_path_item}")
            # On pourrait choisir de l'ajouter à missing_files ou de l'ignorer.
            # Pour l'instant, on le traite comme manquant si non convertible.
            missing_files.append(Path(str(file_path_item))) # Essayer de le convertir en Path pour la liste de retour

    if missing_files:
        logger.warning(f"{len(missing_files)} fichier(s) non trouvé(s) ou invalide(s) sur {len(existing_files) + len(missing_files)} vérifié(s).")
    else:
        logger.info(f"Tous les {len(existing_files)} fichiers vérifiés existent.")
        
    return existing_files, missing_files