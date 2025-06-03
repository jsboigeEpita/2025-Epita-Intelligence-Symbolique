# -*- coding: utf-8 -*-
"""
Utilitaires pour des opérations de refactorisation de code à grande échelle,
comme la mise à jour d'importations ou de références de chemins.
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any # Ajout de Any

logger = logging.getLogger(__name__)

# Les motifs d'importation pourraient être passés en argument ou chargés d'une config
# Pour l'instant, on les garde ici comme dans le script original.
DEFAULT_IMPORT_PATTERNS: List[Tuple[str, str]] = [
    (r'from\s+core\s+import\s+([^\n]+)', r'from argumentation_analysis.core import \1'),
    (r'import\s+core(?!\s*\.)', r'import argumentation_analysis.core'),
    (r'from\s+core\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentation_analysis.core.\1 import \2'),
    (r'from\s+agents\s+import\s+([^\n]+)', r'from argumentation_analysis.agents import \1'),
    (r'import\s+agents(?!\s*\.)', r'import argumentation_analysis.agents'),
    (r'from\s+agents\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentation_analysis.agents.\1 import \2'),
    (r'from\s+orchestration\s+import\s+([^\n]+)', r'from argumentation_analysis.orchestration import \1'),
    (r'import\s+orchestration(?!\s*\.)', r'import argumentation_analysis.orchestration'),
    (r'from\s+orchestration\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentation_analysis.orchestration.\1 import \2'),
    (r'from\s+ui\s+import\s+([^\n]+)', r'from argumentation_analysis.ui import \1'),
    (r'import\s+ui(?!\s*\.)', r'import argumentation_analysis.ui'),
    (r'from\s+ui\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentation_analysis.ui.\1 import \2'),
    (r'from\s+utils\s+import\s+([^\n]+)', r'from argumentation_analysis.utils import \1'), # Attention, peut être trop générique
    (r'import\s+utils(?!\s*\.)', r'import argumentation_analysis.utils'), # Idem
    (r'from\s+utils\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentation_analysis.utils.\1 import \2'), # Idem
    (r'from\s+agents\.extract\s+import\s+([^\n]+)', r'from argumentation_analysis.agents.extract import \1'),
]

def update_imports_in_file_content(
    content: str,
    import_patterns: List[Tuple[str, str]] = DEFAULT_IMPORT_PATTERNS
) -> Tuple[str, int]:
    """
    Met à jour les importations dans une chaîne de contenu de fichier.

    Args:
        content (str): Le contenu du fichier à analyser.
        import_patterns (List[Tuple[str, str]]): Liste de tuples (motif_regex, remplacement_str).

    Returns:
        Tuple[str, int]: Le contenu mis à jour et le nombre total de remplacements.
    """
    updated_content = content
    total_replacements = 0
    for pattern, replacement in import_patterns:
        try:
            updated_content, count = re.subn(pattern, replacement, updated_content)
            total_replacements += count
        except re.error as e_re:
            logger.error(f"Erreur de regex avec le motif '{pattern}': {e_re}")
    return updated_content, total_replacements

def update_imports_in_file(
    file_path: Path,
    dry_run: bool = True,
    import_patterns: List[Tuple[str, str]] = DEFAULT_IMPORT_PATTERNS
) -> Tuple[int, Optional[str]]:
    """
    Met à jour les importations dans un fichier spécifique.

    Args:
        file_path (Path): Chemin du fichier à mettre à jour.
        dry_run (bool): Si True, n'effectue pas les modifications sur le disque.
        import_patterns (List[Tuple[str, str]]): Liste de motifs d'importation.

    Returns:
        Tuple[int, Optional[str]]: (nombre de modifications, contenu mis à jour si dry_run ou succès).
                                   Retourne (0, None) en cas d'erreur de lecture/écriture.
    """
    logger.debug(f"Analyse des importations pour le fichier: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated_content, total_replacements = update_imports_in_file_content(content, import_patterns)
        
        if total_replacements > 0:
            logger.info(f"Fichier {file_path}: {total_replacements} importation(s) potentiellement à mettre à jour.")
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                logger.info(f"Fichier {file_path} mis à jour sur le disque.")
            return total_replacements, updated_content
        else:
            logger.debug(f"Aucune importation à mettre à jour dans {file_path}.")
            return 0, content # Retourner le contenu original si pas de modif
            
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return 0, None
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du fichier {file_path}: {e}", exc_info=True)
        return 0, None

def update_imports_in_directory(
    directory: Path,
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    dry_run: bool = True,
    import_patterns: List[Tuple[str, str]] = DEFAULT_IMPORT_PATTERNS
) -> Dict[str, Any]:
    """
    Met à jour les importations dans tous les fichiers d'un répertoire correspondant
    aux extensions données, en excluant certains sous-répertoires.

    Args:
        directory (Path): Répertoire à analyser.
        extensions (Optional[List[str]]): Extensions de fichiers à analyser (ex: ['.py']).
                                          Si None, utilise ['.py'].
        exclude_dirs (Optional[List[str]]): Répertoires à exclure (ex: ['__pycache__', '.git']).
                                           Si None, utilise une liste par défaut.
        dry_run (bool): Si True, n'effectue pas les modifications sur le disque.
        import_patterns (List[Tuple[str, str]]): Liste de motifs d'importation.

    Returns:
        Dict[str, Any]: Statistiques sur les modifications effectuées.
    """
    if extensions is None:
        extensions = ['.py']
    
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', 'venv', 'env', 'htmlcov', 'node_modules', '.vscode', '.idea']
    
    stats: Dict[str, Any] = {
        'total_files_scanned': 0,
        'files_with_potential_changes': 0,
        'total_potential_replacements': 0,
        'modified_files_list_details': [] # Liste de dicts avec path et count
    }
    
    logger.info(f"Mise à jour des importations dans le répertoire: {directory} (dry_run: {dry_run})")
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            # Vérifier si le fichier est dans un répertoire exclu
            is_excluded = False
            for excluded_part in exclude_dirs:
                if excluded_part in file_path.parts:
                    is_excluded = True
                    break
            if is_excluded:
                logger.debug(f"Fichier ignoré (répertoire exclu): {file_path}")
                continue
            
            # Vérifier si l'extension du fichier est dans la liste des extensions
            if file_path.suffix not in extensions:
                logger.debug(f"Fichier ignoré (extension non correspondante): {file_path}")
                continue
            
            stats['total_files_scanned'] += 1
            
            replacements, _ = update_imports_in_file(file_path, dry_run, import_patterns)
            
            if replacements > 0:
                stats['files_with_potential_changes'] += 1
                stats['total_potential_replacements'] += replacements
                stats['modified_files_list_details'].append({"path": str(file_path), "replacements": replacements})
                # Le logging détaillé est déjà fait par update_imports_in_file
    
    logger.info(f"Scan terminé. {stats['total_potential_replacements']} remplacement(s) potentiel(s) dans {stats['files_with_potential_changes']} fichier(s) sur {stats['total_files_scanned']} scanné(s).")
    return stats

# --- Path Refactoring Utilities ---

DEFAULT_PATH_PATTERNS: List[Tuple[str, str]] = [
    (r'"config/([^"]+)"', r'CONFIG_DIR / "\1"'),
    (r"'config/([^']+)'", r"CONFIG_DIR / '\1'"),
    (r'"data/([^"]+)"', r'DATA_DIR / "\1"'),
    (r"'data/([^']+)'", r"DATA_DIR / '\1'"),
    (r'"libs/([^"]+)"', r'LIBS_DIR / "\1"'),
    (r"'libs/([^']+)'", r"LIBS_DIR / '\1'"),
    (r'"results/([^"]+)"', r'RESULTS_DIR / "\1"'),
    (r"'results/([^']+)'", r"RESULTS_DIR / '\1'"),
    (r'"config/"', r'CONFIG_DIR'),
    (r"'config/'", r"CONFIG_DIR"),
    (r'"data/"', r'DATA_DIR'),
    (r"'data/'", r"DATA_DIR"),
    (r'"libs/"', r'LIBS_DIR'),
    (r"'libs/'", r"LIBS_DIR"),
    (r'"results/"', r'RESULTS_DIR'),
    (r"'results/'", r"RESULTS_DIR"),
    # Les remplacements plus généraux comme "config" -> CONFIG_DIR sont plus risqués
    # et pourraient être activés/désactivés ou affinés.
    # (r'"config"', r'CONFIG_DIR'),
    # (r"'config'", r"CONFIG_DIR"),
    # (r'"data"', r'DATA_DIR'),
    # (r"'data'", r"DATA_DIR"),
    # (r'"libs"', r'LIBS_DIR'),
    # (r"'libs'", r"LIBS_DIR"),
    # (r'"results"', r'RESULTS_DIR'),
    # (r"'results'", r"RESULTS_DIR"),
]

# Motif pour détecter l'importation du module paths
# Assumer que le module paths est dans argumentation_analysis.paths
# Si ce n'est pas le cas, ce motif doit être adapté ou rendu configurable.
DEFAULT_PATHS_MODULE_IMPORT_PATTERN: str = r'from\s+argumentation_analysis\.paths\s+import\s+([A-Z_0-9,\s]+)'


def update_paths_in_file_content(
    content: str,
    path_patterns: List[Tuple[str, str]] = DEFAULT_PATH_PATTERNS,
    paths_module_import_pattern: str = DEFAULT_PATHS_MODULE_IMPORT_PATTERN,
    paths_module_qualifier: str = "argumentation_analysis.paths" # Module où les constantes de chemin sont définies
) -> Tuple[str, int, bool]:
    """
    Met à jour les références de chemin codées en dur dans une chaîne de contenu de fichier
    et s'assure que les constantes de chemin nécessaires sont importées.

    Args:
        content (str): Le contenu du fichier à analyser.
        path_patterns (List[Tuple[str, str]]): Liste de (motif_regex, remplacement_str)
                                               pour les chemins.
        paths_module_import_pattern (str): Regex pour trouver l'importation du module de chemins.
        paths_module_qualifier (str): Nom qualifié du module de chemins (ex: "my_project.paths").

    Returns:
        Tuple[str, int, bool]: (contenu mis à jour, nombre de remplacements de chemin, bool indiquant si un import a été ajouté/modifié).
    """
    updated_content = content
    total_path_replacements = 0
    import_modified_or_added = False

    # Déterminer quels chemins sont référencés et donc à importer
    referenced_path_constants = set()
    temp_content_for_scan = content # Scanner le contenu original pour les motifs
    for pattern, replacement_str_format in path_patterns:
        # Extraire le nom de la constante de chemin (ex: CONFIG_DIR) du remplacement
        # Ceci est une heuristique basée sur le format r'CONST_NAME / "..."'
        match_const = re.search(r'([A-Z_]+(?:_DIR|_FILE))\s*(?:/)?', replacement_str_format)
        if match_const:
            path_const_name = match_const.group(1)
            # Vérifier si le motif est présent avant d'ajouter la constante
            if re.search(pattern, temp_content_for_scan):
                 referenced_path_constants.add(path_const_name)
        else: # Cas où le remplacement est juste la constante (ex: "CONFIG_DIR")
            if replacement_str_format.isupper() and ("_DIR" in replacement_str_format or "_FILE" in replacement_str_format):
                if re.search(pattern, temp_content_for_scan):
                    referenced_path_constants.add(replacement_str_format)


    # Mettre à jour les chemins
    for pattern, replacement in path_patterns:
        try:
            updated_content, count = re.subn(pattern, replacement, updated_content)
            total_path_replacements += count
        except re.error as e_re:
            logger.error(f"Erreur de regex avec le motif de chemin '{pattern}': {e_re}")

    # Gérer l'importation des constantes de chemin si des remplacements ont eu lieu
    if total_path_replacements > 0 and referenced_path_constants:
        paths_to_import_list = sorted(list(referenced_path_constants))
        new_import_statement_str = f"from {paths_module_qualifier} import {', '.join(paths_to_import_list)}"

        import_pattern_re = re.compile(paths_module_import_pattern)
        match_import = import_pattern_re.search(updated_content)

        if match_import:
            # L'import existe, vérifier si toutes les constantes nécessaires y sont
            existing_imported_constants_str = match_import.group(1).strip()
            existing_constants = set(c.strip() for c in existing_imported_constants_str.split(','))
            
            missing_constants = referenced_path_constants - existing_constants
            if missing_constants:
                all_needed_constants = sorted(list(existing_constants | referenced_path_constants))
                updated_import_line = f"from {paths_module_qualifier} import {', '.join(all_needed_constants)}"
                updated_content = import_pattern_re.sub(updated_import_line, updated_content, count=1)
                import_modified_or_added = True
                logger.debug(f"Importation de chemins mise à jour : {updated_import_line}")
        else:
            # Ajouter la nouvelle déclaration d'importation
            # Essayer de l'ajouter après les autres imports ou au début du fichier
            import_insertion_point = 0
            last_import_match = None
            for m in re.finditer(r"^(?:from\s+[.\w]+\s+)?import\s+[\w,\s]+$", updated_content, re.MULTILINE):
                last_import_match = m
            if last_import_match:
                import_insertion_point = last_import_match.end() + 1 # Après le saut de ligne
                updated_content = updated_content[:import_insertion_point] + new_import_statement_str + "\n" + updated_content[import_insertion_point:]
            else: # Pas d'autres imports, ajouter au début
                updated_content = new_import_statement_str + "\n\n" + updated_content
            import_modified_or_added = True
            logger.debug(f"Importation de chemins ajoutée : {new_import_statement_str}")
            
    return updated_content, total_path_replacements, import_modified_or_added


def update_paths_in_file(
    file_path: Path,
    dry_run: bool = True,
    path_patterns: List[Tuple[str, str]] = DEFAULT_PATH_PATTERNS,
    paths_module_import_pattern: str = DEFAULT_PATHS_MODULE_IMPORT_PATTERN,
    paths_module_qualifier: str = "argumentation_analysis.paths"
) -> Tuple[int, bool, Optional[str]]:
    """
    Met à jour les références aux chemins dans un fichier spécifique.

    Args:
        file_path (Path): Chemin du fichier à mettre à jour.
        dry_run (bool): Si True, n'effectue pas les modifications sur le disque.
        path_patterns, paths_module_import_pattern, paths_module_qualifier: voir update_paths_in_file_content.

    Returns:
        Tuple[int, bool, Optional[str]]: (nombre de remplacements de chemin,
                                          bool indiquant si un import a été ajouté/modifié,
                                          contenu mis à jour si dry_run ou succès).
                                          Retourne (0, False, None) en cas d'erreur.
    """
    logger.debug(f"Analyse des chemins pour le fichier: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated_content, total_replacements, import_changed = update_paths_in_file_content(
            content, path_patterns, paths_module_import_pattern, paths_module_qualifier
        )
        
        if total_replacements > 0 or import_changed:
            logger.info(f"Fichier {file_path}: {total_replacements} référence(s) de chemin potentiellement à mettre à jour. Import modifié/ajouté: {import_changed}.")
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                logger.info(f"Fichier {file_path} mis à jour sur le disque.")
            return total_replacements, import_changed, updated_content
        else:
            logger.debug(f"Aucune référence de chemin à mettre à jour ou import à modifier dans {file_path}.")
            return 0, False, content # Retourner le contenu original si pas de modif

    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        return 0, False, None
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des chemins dans le fichier {file_path}: {e}", exc_info=True)
        return 0, False, None

def update_paths_in_directory(
    directory: Path,
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    dry_run: bool = True,
    path_patterns: List[Tuple[str, str]] = DEFAULT_PATH_PATTERNS,
    paths_module_import_pattern: str = DEFAULT_PATHS_MODULE_IMPORT_PATTERN,
    paths_module_qualifier: str = "argumentation_analysis.paths"
) -> Dict[str, Any]:
    """
    Met à jour les références aux chemins dans tous les fichiers d'un répertoire.
    """
    if extensions is None:
        extensions = ['.py']
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', 'venv', 'env', 'htmlcov', 'node_modules', '.vscode', '.idea', 'docs', '_archives']

    stats: Dict[str, Any] = {
        'total_files_scanned': 0,
        'files_with_path_changes': 0,
        'total_path_replacements': 0,
        'files_with_import_changes': 0,
        'changed_files_details': [] # Liste de dicts avec path, replacements, import_changed
    }
    logger.info(f"Mise à jour des chemins dans le répertoire: {directory} (dry_run: {dry_run})")

    for file_path in directory.rglob('*'):
        if file_path.is_file():
            is_excluded = False
            for excluded_part in exclude_dirs:
                if excluded_part in file_path.parts:
                    is_excluded = True
                    break
            if is_excluded:
                continue
            
            if file_path.suffix not in extensions:
                continue
            
            stats['total_files_scanned'] += 1
            
            replacements, import_changed, _ = update_paths_in_file(
                file_path, dry_run, path_patterns, paths_module_import_pattern, paths_module_qualifier
            )
            
            if replacements > 0 or import_changed:
                stats['files_with_path_changes'] += 1 if replacements > 0 else 0
                stats['total_path_replacements'] += replacements
                stats['files_with_import_changes'] += 1 if import_changed else 0
                stats['changed_files_details'].append({
                    "path": str(file_path),
                    "path_replacements": replacements,
                    "import_changed": import_changed
                })
    
    logger.info(f"Scan des chemins terminé. {stats['total_path_replacements']} remplacement(s) de chemin dans {stats['files_with_path_changes']} fichier(s).")
    logger.info(f"{stats['files_with_import_changes']} fichier(s) avec importations de chemin modifiées/ajoutées sur {stats['total_files_scanned']} scanné(s).")
    return stats
