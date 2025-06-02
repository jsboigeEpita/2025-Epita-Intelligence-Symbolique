#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour les références aux chemins dans les fichiers existants.

Ce script recherche les références aux chemins codés en dur et les remplace par
des références au module paths.py, ce qui centralise la gestion des chemins.
"""

import re
import sys
from pathlib import Path
import logging
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Définir les motifs de recherche et de remplacement
PATH_PATTERNS = [
    # "config/X" -> CONFIG_DIR / "X"
    (r'"config/([^"]+)"', r'CONFIG_DIR / "\1"'),
    (r"'config/([^']+)'", r"CONFIG_DIR / '\1'"),
    
    # "data/X" -> DATA_DIR / "X"
    (r'"data/([^"]+)"', r'DATA_DIR / "\1"'),
    (r"'data/([^']+)'", r"DATA_DIR / '\1'"),
    
    # "libs/X" -> LIBS_DIR / "X"
    (r'"libs/([^"]+)"', r'LIBS_DIR / "\1"'),
    (r"'libs/([^']+)'", r"LIBS_DIR / '\1'"),
    
    # "results/X" -> RESULTS_DIR / "X"
    (r'"results/([^"]+)"', r'RESULTS_DIR / "\1"'),
    (r"'results/([^']+)'", r"RESULTS_DIR / '\1'"),
    
    # "config/" -> CONFIG_DIR
    (r'"config/"', r'CONFIG_DIR'),
    (r"'config/'", r"CONFIG_DIR"),
    
    # "data/" -> DATA_DIR
    (r'"data/"', r'DATA_DIR'),
    (r"'data/'", r"DATA_DIR"),
    
    # "libs/" -> LIBS_DIR
    (r'"libs/"', r'LIBS_DIR'),
    (r"'libs/'", r"LIBS_DIR"),
    
    # "results/" -> RESULTS_DIR
    (r'"results/"', r'RESULTS_DIR'),
    (r"'results/'", r"RESULTS_DIR"),
    
    # "config" -> CONFIG_DIR
    (r'"config"', r'CONFIG_DIR'),
    (r"'config'", r"CONFIG_DIR"),
    
    # "data" -> DATA_DIR
    (r'"data"', r'DATA_DIR'),
    (r"'data'", r"DATA_DIR"),
    
    # "libs" -> LIBS_DIR
    (r'"libs"', r'LIBS_DIR'),
    (r"'libs'", r"LIBS_DIR"),
    
    # "results" -> RESULTS_DIR
    (r'"results"', r'RESULTS_DIR'),
    (r"'results'", r"RESULTS_DIR"),
]

# Motif pour détecter l'importation du module paths
IMPORT_PATHS_PATTERN = r'from\s+argumentiation_analysis\.paths\s+import\s+([^\n]+)'

def update_paths_in_file(file_path, dry_run=True):
    """
    Met à jour les références aux chemins dans un fichier.
    
    Args:
        file_path (Path): Chemin du fichier à mettre à jour
        dry_run (bool): Si True, n'effectue pas les modifications
    
    Returns:
        tuple: (nombre de modifications, contenu mis à jour, importation ajoutée)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si le fichier contient des références aux chemins
        has_path_references = False
        for pattern, _ in PATH_PATTERNS:
            if re.search(pattern, content):
                has_path_references = True
                break
        
        if not has_path_references:
            return 0, content, False
        
        # Vérifier si le module paths est déjà importé
        paths_import_match = re.search(IMPORT_PATHS_PATTERN, content)
        paths_already_imported = paths_import_match is not None
        
        # Déterminer quels chemins sont référencés
        referenced_paths = set()
        for pattern, replacement in PATH_PATTERNS:
            if re.search(pattern, content):
                path_name = re.search(r'([A-Z_]+)_DIR', replacement)
                if path_name:
                    referenced_paths.add(path_name.group(1))
        
        # Construire la liste des chemins à importer
        paths_to_import = [f"{path}_DIR" for path in referenced_paths]
        
        # Mettre à jour l'importation si nécessaire
        import_added = False
        if paths_to_import and not paths_already_imported:
            import_statement = f"from argumentiation_analysis.paths import {', '.join(paths_to_import)}\n\n"
            
            # Trouver un bon endroit pour ajouter l'importation
            import_section_end = 0
            for match in re.finditer(r'import\s+[^\n]+\n', content):
                import_section_end = max(import_section_end, match.end())
            
            if import_section_end > 0:
                content = content[:import_section_end] + "\n" + import_statement + content[import_section_end:]
            else:
                content = import_statement + content
            
            import_added = True
        
        # Appliquer les motifs de recherche et de remplacement
        updated_content = content
        total_replacements = 0
        
        for pattern, replacement in PATH_PATTERNS:
            updated_content, count = re.subn(pattern, replacement, updated_content)
            total_replacements += count
        
        # Écrire le contenu mis à jour si des modifications ont été effectuées
        if (total_replacements > 0 or import_added) and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        
        return total_replacements, updated_content, import_added
    
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du fichier {file_path}: {e}")
        return 0, None, False

def update_paths_in_directory(directory, extensions=None, exclude_dirs=None, dry_run=True):
    """
    Met à jour les références aux chemins dans tous les fichiers d'un répertoire.
    
    Args:
        directory (str): Répertoire à analyser
        extensions (list): Extensions de fichiers à analyser
        exclude_dirs (list): Répertoires à exclure
        dry_run (bool): Si True, n'effectue pas les modifications
    
    Returns:
        dict: Statistiques sur les modifications effectuées
    """
    if extensions is None:
        extensions = ['.py']
    
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', 'venv', 'env', 'htmlcov']
    
    stats = {
        'total_files': 0,
        'modified_files': 0,
        'total_replacements': 0,
        'imports_added': 0,
        'modified_files_list': []
    }
    
    for file_path in Path(directory).rglob('*'):
        # Vérifier si le fichier est dans un répertoire exclu
        if any(exclude_dir in file_path.parts for exclude_dir in exclude_dirs):
            continue
        
        # Vérifier si l'extension du fichier est dans la liste des extensions
        if file_path.suffix not in extensions:
            continue
        
        stats['total_files'] += 1
        
        # Mettre à jour les références aux chemins dans le fichier
        replacements, _, import_added = update_paths_in_file(file_path, dry_run)
        
        if replacements > 0 or import_added:
            stats['modified_files'] += 1
            stats['total_replacements'] += replacements
            if import_added:
                stats['imports_added'] += 1
            stats['modified_files_list'].append(str(file_path))
            
            logging.info(f"Fichier {file_path}: {replacements} références aux chemins mises à jour, importation ajoutée: {import_added}.")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Met à jour les références aux chemins dans les fichiers Python")
    parser.add_argument('--dir', type=str, default='argumentiation_analysis', help="Répertoire à analyser")
    parser.add_argument('--dry-run', action='store_true', help="Ne pas effectuer les modifications")
    args = parser.parse_args()
    
    logging.info(f"Analyse des références aux chemins dans {args.dir}...")
    
    stats = update_paths_in_directory(args.dir, dry_run=args.dry_run)
    
    logging.info(f"\nRésultat: {stats['total_replacements']} références aux chemins mises à jour dans {stats['modified_files']}/{stats['total_files']} fichiers.")
    logging.info(f"Importations ajoutées: {stats['imports_added']}")
    
    if args.dry_run:
        logging.info("Mode dry-run: aucune modification n'a été effectuée.")
        logging.info("Exécutez à nouveau sans l'option --dry-run pour appliquer les modifications.")
    
    if stats['modified_files'] > 0:
        logging.info("\nFichiers modifiés:")
        for file_path in stats['modified_files_list']:
            logging.info(f"  {file_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())