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
    
    # 1. Gérer les fichiers cachés (commençant par un point) et translittérer
    is_hidden_file_prefix = ""
    if filename.startswith('.'):
        if filename == "." or filename == ".." or not filename[1:].strip():
             path_ops_logger.warning(f"Nom de fichier caché invalide ou vide '{original_filename_for_log}'. Utilisation de '_hidden_default'.")
             return "_hidden_default"
        is_hidden_file_prefix = "."
        name_to_process = unidecode(filename[1:]) # Translitérer la partie après le '.'
    else:
        name_to_process = unidecode(filename) # Translitérer tout le nom

    # 2. Séparer nom et extension de la partie traitée
    name_part, dot, extension_part = name_to_process.rpartition('.')

    if not dot: # Pas d'extension trouvée
        base_name_to_sanitize = name_to_process
        current_extension = ""
    else: # Extension trouvée
        base_name_to_sanitize = name_part
        current_extension = extension_part
        
    # 3. Nettoyer la partie nom de base
    sanitized_base_name = re.sub(r'[\s_.-]+', '_', base_name_to_sanitize)
    sanitized_base_name = re.sub(r'[^\w_]', '', sanitized_base_name)
    sanitized_base_name = sanitized_base_name.lower()
    sanitized_base_name = re.sub(r'^_+|_+$', '', sanitized_base_name)

    # 4. Nettoyer l'extension
    sanitized_extension = ""
    if current_extension:
        cleaned_ext = re.sub(r'[^\w]', '', current_extension).lower()
        if cleaned_ext:
            sanitized_extension = cleaned_ext

    # 5. Gérer nom de base vide après nettoyage
    if not sanitized_base_name:
        if not is_hidden_file_prefix:
            sanitized_base_name = "default_filename"
            path_ops_logger.warning(
                f"Le nom de base du fichier '{original_filename_for_log}' (après unidecode: '{name_to_process}') est devenu vide après nettoyage. "
                f"Utilisation de '{sanitized_base_name}'.")
        # Si c'est un fichier caché et que la base est vide (ex: ".config" -> name_part="", ext="config"),
        # sanitized_base_name reste vide, le préfixe "." sera la seule partie "nom".

    # 6. Recomposer le nom final avant troncature
    # Le préfixe "." est ajouté ici s'il était présent
    final_name_base_with_prefix = is_hidden_file_prefix + sanitized_base_name
    
    if sanitized_extension:
        final_filename = f"{final_name_base_with_prefix}.{sanitized_extension}"
    else:
        final_filename = final_name_base_with_prefix
    
    # Cas spécial: si le résultat est juste "." (ex: ".<seulement_symboles_non_alpha>" devient ".")
    if final_filename == ".":
        default_prefix_for_log = is_hidden_file_prefix or ""
        path_ops_logger.warning(f"Sanitization de '{original_filename_for_log}' a résulté en '.'. Utilisation de '{default_prefix_for_log}default_name'.")
        final_filename = f"{is_hidden_file_prefix or ''}default_name" # Ex: ".default_name" ou "default_name"

    # 7. Tronquer si nécessaire
    if len(final_filename) > max_len:
        path_ops_logger.debug(f"Nom '{final_filename}' (longueur {len(final_filename)}) dépasse max_len {max_len}. Tronquage...")
        if sanitized_extension:
            ext_with_dot = f".{sanitized_extension}"
            len_ext_plus_dot = len(ext_with_dot)

            # Si l'extension seule (avec le point) est trop longue ou ne laisse pas de place pour le nom + préfixe
            if len_ext_plus_dot >= max_len: # Ne laisse pas de place pour le nom
                 # Troncature brutale de l'ensemble, en essayant de garder le début
                final_filename = final_filename[:max_len]
                # Alternative: tronquer l'extension elle-même si elle est trop longue
                # final_filename = final_name_base_with_prefix + "." + sanitized_extension[:max_len - len(final_name_base_with_prefix) -1]

            elif len(final_name_base_with_prefix) + len_ext_plus_dot > max_len:
                # Assez de place pour l'extension complète, tronquer la partie nom
                allowed_len_for_base = max_len - len_ext_plus_dot
                truncated_base = final_name_base_with_prefix[:allowed_len_for_base]
                final_filename = f"{truncated_base}{ext_with_dot}"
            # else: le nom complet avec extension est déjà <= max_len
        else: # Pas d'extension
            final_filename = final_filename[:max_len]
        path_ops_logger.debug(f"Nom tronqué: '{final_filename}'")

    # 8. Vérification finale si vide (ne devrait plus arriver avec les defaults)
    if not final_filename:
        path_ops_logger.error(f"La sanitization du nom de fichier '{original_filename_for_log}' a résulté en une chaîne vide après troncature. Retour de 'error_empty_filename'.")
        return "error_empty_filename" # Fallback ultime

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
        path_ops_logger.info(f"✅ Le fichier {path} existe et est un fichier.")
    elif path_type == PATH_TYPE_DIRECTORY: # Utilisation de la constante
        if not path.is_dir():
            path_ops_logger.critical(f"❌ ERREUR CRITIQUE: Le chemin {path} existe mais n'est pas un répertoire (attendu: répertoire).")
            sys.exit(1)
        path_ops_logger.info(f"✅ Le répertoire {path} existe et est un répertoire.")
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
        num_available_parents = len(source_file_path.parents)
        levels_to_take = min(preserve_levels, num_available_parents)
        
        for i in range(levels_to_take):
            parent_names_to_preserve.append(source_file_path.parents[i].name)
        parent_names_to_preserve.reverse()

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
        path_ops_logger.info(f"✅ Fichier {source_path} archivé avec succès vers {archive_path}")
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