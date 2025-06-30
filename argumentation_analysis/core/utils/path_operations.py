# -*- coding: utf-8 -*-
"""
Utilitaires pour les opérations sur les chemins de fichiers, la sanitization
des noms de fichiers, et l'archivage.
"""
from pathlib import Path
import logging
import re
import shutil
import sys
from unidecode import unidecode # Utilisé par sanitize_filename
from typing import List, Dict, Any, Optional, Union # Ajouté pour la complétude, même si pas directement utilisé par les fonctions ici

# Logger spécifique pour ce module
path_ops_logger = logging.getLogger("App.ProjectCore.PathOperations")
if not path_ops_logger.handlers and not path_ops_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    path_ops_logger.addHandler(handler)
    path_ops_logger.setLevel(logging.INFO)

# Constantes pour les types de chemins (utilisées par check_path_exists)
PATH_TYPE_FILE = "file"
PATH_TYPE_DIRECTORY = "directory"
PATH_TYPE_ANY = "any" # Bien que non utilisé par check_path_exists actuel, gardé pour extension future

def sanitize_filename(filename: str, max_len: int = 255) -> str:
    """
    Nettoie une chaîne de caractères pour la transformer en un nom de fichier valide et sûr.
    """
    if not filename:
        path_ops_logger.warning("Tentative de nettoyer un nom de fichier vide. Retour de 'empty_filename'.")
        return "empty_filename"

    original_filename_for_log = filename

    # Gestion spécifique pour "." et ".." qui doivent retourner une valeur fixe.
    if filename == "." or filename == "..":
        path_ops_logger.warning(f"Nom de fichier caché invalide '{original_filename_for_log}'. Utilisation de '_hidden_default'.")
        return "_hidden_default"

    # Translitérer d'abord le nom complet pour une meilleure gestion des accents dans les extensions
    filename_ascii = unidecode(filename)
    
    # Séparer le nom de base et l'extension APRÈS la translittération
    is_hidden_file_original = filename.startswith('.') # Basé sur le nom original pour la logique des fichiers cachés
    
    # Logique de séparation du nom et de l'extension
    if is_hidden_file_original:
        # Pour les fichiers cachés, on partitionne ce qui suit le premier '.'
        base_for_partition = filename_ascii[1:]
        name_part_temp, dot_temp, ext_part_temp = base_for_partition.rpartition('.')
        if dot_temp: # Une extension a été trouvée après le premier point
            name_to_sanitize = "." + name_part_temp # Reconstituer le nom caché avec le point initial
            current_extension = ext_part_temp
        else: # Pas d'extension trouvée après le premier point
            name_to_sanitize = "." + base_for_partition # Tout est considéré comme nom (avec le point initial)
            current_extension = ""
    else: # Fichier non caché
        name_part_temp, dot_temp, ext_part_temp = filename_ascii.rpartition('.')
        if dot_temp:
            name_to_sanitize = name_part_temp
            current_extension = ext_part_temp
        else:
            name_to_sanitize = filename_ascii # Pas d'extension, tout est nom
            current_extension = ""

    # Nettoyage du nom de base (name_to_sanitize peut déjà inclure un "." au début s'il est caché)
    base_name_part_to_clean = name_to_sanitize[1:] if name_to_sanitize.startswith('.') and is_hidden_file_original else name_to_sanitize
    
    cleaned_base_name_part = re.sub(r'[\s_.-]+', '_', base_name_part_to_clean)
    cleaned_base_name_part = re.sub(r'[^\w_]', '', cleaned_base_name_part) # Garde les underscores
    cleaned_base_name_part = cleaned_base_name_part.lower()
    cleaned_base_name_part = re.sub(r'^_+|_+$', '', cleaned_base_name_part) # Supprime underscores en début/fin

    # Reconstituer sanitized_name avec le point initial si c'était un fichier caché
    if is_hidden_file_original:
        sanitized_name = "." + cleaned_base_name_part
    else:
        sanitized_name = cleaned_base_name_part
        
    # Gestion des noms vides après nettoyage
    if is_hidden_file_original and not cleaned_base_name_part: # Ex: "...", "._-.", ". "
        sanitized_name = ".default_name" 
        path_ops_logger.warning(f"Le nom de base du fichier caché '{original_filename_for_log}' est devenu vide après nettoyage. Utilisation de '{sanitized_name}'.")
    elif not is_hidden_file_original and not cleaned_base_name_part: # Ex: "!@#$", "   "
        sanitized_name = "default_filename"
        path_ops_logger.warning(f"Le nom de base du fichier '{original_filename_for_log}' est devenu vide après nettoyage. Utilisation de '{sanitized_name}'.")
    # Si le nom original était juste des points (ex: "...") et n'était pas caché initialement,
    # mais que filename_ascii est devenu vide ou que des symboles, il sera traité par la ligne ci-dessus.
    # Le cas spécifique de `all(c == '.' for c in filename.strip())` est géré par la logique ci-dessus
    # car `cleaned_base_name_part` deviendra vide.

    # Nettoyage de l'extension (si elle existe)
    if current_extension:
        sanitized_cleaned_extension = re.sub(r'[^\w]', '', current_extension).lower()
        current_extension = sanitized_cleaned_extension if sanitized_cleaned_extension else ""

    # Recomposition finale
    if current_extension:
        final_filename = f"{sanitized_name}.{current_extension}"
    else:
        final_filename = sanitized_name
            
    # Troncature à max_len
    if len(final_filename) > max_len:
        if current_extension: # Si une extension est présente
            len_ext_plus_dot = len(current_extension) + 1
            if len_ext_plus_dot >= max_len : 
                # Si l'extension + point est trop long, on tronque brutalement le nom complet
                final_filename = final_filename[:max_len] 
                path_ops_logger.debug(f"Extension trop longue pour max_len={max_len}. Troncature brutale de '{original_filename_for_log}' en '{final_filename}'.")
            else:
                # Assez de place pour l'extension, tronquer la partie nom (sanitized_name)
                name_part_to_truncate = sanitized_name
                allowed_len_for_name = max_len - len_ext_plus_dot
                truncated_name_part = name_part_to_truncate[:allowed_len_for_name]
                final_filename = f"{truncated_name_part}.{current_extension}"
        else: # Pas d'extension, juste tronquer
            final_filename = final_filename[:max_len]
    
    # Ultime fallback si, pour une raison quelconque, final_filename est vide
    # Cela peut arriver si max_len est 0, ou si le nom après troncature est vide.
    if not final_filename:
        # Si c'était un fichier caché à l'origine et que tout est devenu vide
        if is_hidden_file_original:
            path_ops_logger.error(f"La sanitization du nom de fichier caché '{original_filename_for_log}' a résulté en une chaîne vide. Retour de '.error_empty_filename'.")
            return ".error_empty_filename"
        else:
            path_ops_logger.error(f"La sanitization du nom de fichier '{original_filename_for_log}' a résulté en une chaîne vide. Retour de 'error_empty_filename'.")
            return "error_empty_filename"

    path_ops_logger.debug(f"Nom de fichier original: '{original_filename_for_log}', nettoyé: '{final_filename}'")
    return final_filename

def check_path_exists(path: Path, path_type: str = "file") -> bool:
    """
    Vérifie si un chemin existe et correspond au type spécifié (fichier ou répertoire).
    Arrête le script en cas d'échec.
    """
    path_ops_logger.debug(f"Vérification de l'existence et du type pour le chemin : {path} (attendu: {path_type})")
    if not path.exists():
        path_ops_logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} n'existe pas.")
        sys.exit(1)

    if path_type == PATH_TYPE_FILE: # Utilisation de la constante
        if not path.is_file():
            path_ops_logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} existe mais n'est pas un fichier (attendu: fichier).")
            sys.exit(1)
        path_ops_logger.info(f"[OK] Le fichier {path} existe et est un fichier.")
    elif path_type == PATH_TYPE_DIRECTORY: # Utilisation de la constante
        if not path.is_dir():
            path_ops_logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} existe mais n'est pas un répertoire (attendu: répertoire).")
            sys.exit(1)
        path_ops_logger.info(f"[OK] Le répertoire {path} existe et est un répertoire.")
    else:
        path_ops_logger.critical(f"❌ ERREUR CRITIQUE: Type de chemin non supporté '{path_type}'. Utilisez '{PATH_TYPE_FILE}' ou '{PATH_TYPE_DIRECTORY}'.")
        sys.exit(1)
    return True


def create_archive_path(base_archive_dir: Path, source_file_path: Path, preserve_levels: int = 2) -> Path:
    """
    Génère un chemin de destination complet pour archiver un fichier source.
    (Version provenant de file_utils.py original - lignes 538-635)
    """
    path_ops_logger.debug(
        f"Création du chemin d'archive pour {source_file_path} dans {base_archive_dir} "
        f"en préservant {preserve_levels} niveaux."
    )

    if preserve_levels < 0:
        path_ops_logger.warning("preserve_levels ne peut pas être négatif. Utilisation de 0 à la place.")
        preserve_levels = 0

    file_name = source_file_path.name
    
    parent_names_to_preserve = []
    if preserve_levels > 0 and source_file_path.parents:
        # source_file_path.parents n'inclut pas le fichier lui-même, ni '.'
        # Si source_file_path est "a/b/c.txt", parents est (Path('a/b'), Path('a'), Path('.'))
        # Si source_file_path est "c.txt", parents est (Path('.'),)
        # On veut les noms des répertoires parents, en excluant le '.' final s'il est le seul parent.
        
        actual_parents = [p for p in source_file_path.parents if p.name] # Exclut Path('.') qui a un nom vide
        num_available_parents = len(actual_parents)
        levels_to_take = min(preserve_levels, num_available_parents)
        
        for i in range(levels_to_take):
            parent_names_to_preserve.append(actual_parents[i].name)
        parent_names_to_preserve.reverse() # Les parents sont listés du plus proche au plus éloigné

    if parent_names_to_preserve:
        archive_sub_path = Path(*parent_names_to_preserve) / file_name
    else:
        archive_sub_path = Path(file_name)

    destination_path = base_archive_dir / archive_sub_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    path_ops_logger.info(f"Chemin d'archive généré : {destination_path}")
    return destination_path

def archive_file(source_path: Path, archive_path: Path) -> bool:
    """
    Archive un fichier en le déplaçant de `source_path` vers `archive_path`.
    (Version provenant de file_utils.py original - lignes 638-680)
    """
    path_ops_logger.info(f"Tentative d'archivage du fichier {source_path} vers {archive_path}")

    if not source_path.exists() or not source_path.is_file():
        path_ops_logger.error(f"❌ Le fichier source {source_path} n'existe pas ou n'est pas un fichier.")
        return False

    try:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        path_ops_logger.debug(f"Répertoire parent {archive_path.parent} pour l'archive vérifié/créé.")
        shutil.move(str(source_path), str(archive_path))
        path_ops_logger.info(f"[OK] Fichier {source_path} archivé avec succès vers {archive_path}")
        return True
    except FileNotFoundError:
        path_ops_logger.error(f"❌ Erreur (FileNotFoundError) lors de la tentative d'archivage : {source_path} non trouvé.")
        return False
    except PermissionError:
        path_ops_logger.error(f"❌ Erreur de permission lors de la tentative d'archivage de {source_path} vers {archive_path}.")
        return False
    except Exception as e:
        path_ops_logger.error(f"❌ Erreur inattendue lors de l'archivage du fichier {source_path} vers {archive_path}: {e}", exc_info=True)
        return False

path_ops_logger.info("Utilitaires d'opérations sur les chemins (PathOperations) définis.")