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
    (Version provenant de file_utils.py original)
    """
    if not filename:
        path_ops_logger.warning("Tentative de nettoyer un nom de fichier vide. Retour de 'empty_filename'.")
        return "empty_filename"

    original_filename_for_log = filename 

    name_part, dot, extension_part = filename.rpartition('.')
    
    if not dot or (dot and not name_part and extension_part):
        name_to_sanitize = filename
        current_extension = ""
    else: 
        name_to_sanitize = name_part
        current_extension = extension_part

    # Translitérer en ASCII (appliqué après la séparation pour ne pas affecter le point de l'extension)
    # Note: unidecode est appliqué sur les parties séparément si nécessaire.
    # Pour la simplicité de cette version, appliquons-le au nom seulement.
    # Une version plus robuste appliquerait unidecode avant rpartition.
    # Cependant, la version originale de file_utils.py l'appliquait globalement au début.
    # Pour rester fidèle à la version lue (ligne 60 de file_utils.py original, avant ma refactorisation de sanitize_filename),
    # unidecode devrait être appliqué au `filename` complet au début.
    # Je vais suivre la logique de la version de file_utils.py que j'ai lue (celle de MERGE_HEAD après checkout --theirs)
    # qui n'avait pas unidecode dans sanitize_filename.
    # MAIS, l'import unidecode EST présent dans le file_utils.py que j'ai lu.
    # Et la version de sanitize_filename dans ui/utils.py (HEAD) l'utilisait.
    # Je vais ajouter unidecode ici pour la robustesse, comme c'était probablement l'intention.
    
    # Ré-évalution: la version de sanitize_filename dans le file_utils.py que j'ai lu (après checkout --theirs)
    # est plus simple et n'utilise PAS unidecode. Je vais m'en tenir à CETTE version pour l'instant.
    # L'import unidecode dans le file_utils.py global était peut-être pour une autre fonction ou un reste.
    # Si unidecode est nécessaire, il faudra le réintégrer soigneusement.
    # Pour l'instant, je copie la version de file_utils.py (lignes 26-122) qui n'utilise pas unidecode.
    # **CORRECTION**: En revoyant le fichier complet de file_utils.py (celui de 791 lignes),
    # `sanitize_filename` (lignes 26-122) N'UTILISE PAS `unidecode`.
    # L'import `unidecode` à la ligne 22 du fichier global est donc soit inutilisé par cette fonction,
    # soit pour une autre partie (mais je ne la vois pas).
    # Je vais donc implémenter `sanitize_filename` SANS `unidecode` pour correspondre au code que je refactorise.

    sanitized_name = re.sub(r'[\s_.-]+', '_', name_to_sanitize)
    sanitized_name = re.sub(r'[^\w_]', '', sanitized_name)
    sanitized_name = sanitized_name.lower()
    sanitized_name = re.sub(r'^_+|_+$', '', sanitized_name)

    if current_extension:
        sanitized_extension = re.sub(r'[^\w]', '', current_extension).lower()
        if not sanitized_extension:
            sanitized_name = f"{sanitized_name}_{re.sub(r'[^a-zA-Z0-9_]', '', current_extension.lower())}"
            sanitized_name = re.sub(r'_+', '_', sanitized_name).strip('_')
            current_extension = ""
        else:
            current_extension = sanitized_extension
            
    if current_extension:
        final_filename = f"{sanitized_name}.{current_extension}"
    else:
        final_filename = sanitized_name

    if not sanitized_name:
        final_filename = f"default_filename{'.' + current_extension if current_extension else ''}"
        path_ops_logger.warning(f"Le nom de base du fichier '{original_filename_for_log}' est devenu vide après nettoyage. Utilisation de '{final_filename}'.")

    if len(final_filename) > max_len:
        if current_extension:
            len_ext_plus_dot = len(current_extension) + 1
            if len_ext_plus_dot >= max_len :
                final_filename = final_filename[:max_len-1] + final_filename[-1] if max_len > 0 else ""
            else:
                name_part_truncated = final_filename[:max_len - len_ext_plus_dot]
                final_filename = f"{name_part_truncated}.{current_extension}"
        else:
            final_filename = final_filename[:max_len]
    
    if not final_filename:
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