#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour mettre à jour les importations dans les fichiers existants.

Ce script recherche les importations problématiques et les remplace par
les importations correctes, en utilisant le nom complet du package.
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
IMPORT_PATTERNS = [
    # from core import X -> from argumentiation_analysis.core import X
    (r'from\s+core\s+import\s+([^\n]+)', r'from argumentiation_analysis.core import \1'),
    
    # import core -> import argumentiation_analysis.core
    (r'import\s+core(?!\s*\.)', r'import argumentiation_analysis.core'),
    
    # from core.X import Y -> from argumentiation_analysis.core.X import Y
    (r'from\s+core\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentiation_analysis.core.\1 import \2'),
    
    # from agents import X -> from argumentiation_analysis.agents import X
    (r'from\s+agents\s+import\s+([^\n]+)', r'from argumentiation_analysis.agents import \1'),
    
    # import agents -> import argumentiation_analysis.agents
    (r'import\s+agents(?!\s*\.)', r'import argumentiation_analysis.agents'),
    
    # from agents.X import Y -> from argumentiation_analysis.agents.X import Y
    (r'from\s+agents\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentiation_analysis.agents.\1 import \2'),
    
    # from orchestration import X -> from argumentiation_analysis.orchestration import X
    (r'from\s+orchestration\s+import\s+([^\n]+)', r'from argumentiation_analysis.orchestration import \1'),
    
    # import orchestration -> import argumentiation_analysis.orchestration
    (r'import\s+orchestration(?!\s*\.)', r'import argumentiation_analysis.orchestration'),
    
    # from orchestration.X import Y -> from argumentiation_analysis.orchestration.X import Y
    (r'from\s+orchestration\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentiation_analysis.orchestration.\1 import \2'),
    
    # from ui import X -> from argumentiation_analysis.ui import X
    (r'from\s+ui\s+import\s+([^\n]+)', r'from argumentiation_analysis.ui import \1'),
    
    # import ui -> import argumentiation_analysis.ui
    (r'import\s+ui(?!\s*\.)', r'import argumentiation_analysis.ui'),
    
    # from ui.X import Y -> from argumentiation_analysis.ui.X import Y
    (r'from\s+ui\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentiation_analysis.ui.\1 import \2'),
    
    # from utils import X -> from argumentiation_analysis.utils import X
    (r'from\s+utils\s+import\s+([^\n]+)', r'from argumentiation_analysis.utils import \1'),
    
    # import utils -> import argumentiation_analysis.utils
    (r'import\s+utils(?!\s*\.)', r'import argumentiation_analysis.utils'),
    
    # from utils.X import Y -> from argumentiation_analysis.utils.X import Y
    (r'from\s+utils\.([^\s]+)\s+import\s+([^\n]+)', r'from argumentiation_analysis.utils.\1 import \2'),
    
    # from agents.extract import X -> from argumentiation_analysis.agents.extract import X
    (r'from\s+agents\.extract\s+import\s+([^\n]+)', r'from argumentiation_analysis.agents.extract import \1'),
]

def update_imports_in_file(file_path, dry_run=True):
    """
    Met à jour les importations dans un fichier.
    
    Args:
        file_path (Path): Chemin du fichier à mettre à jour
        dry_run (bool): Si True, n'effectue pas les modifications
    
    Returns:
        tuple: (nombre de modifications, contenu mis à jour)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Appliquer les motifs de recherche et de remplacement
        updated_content = content
        total_replacements = 0
        
        for pattern, replacement in IMPORT_PATTERNS:
            updated_content, count = re.subn(pattern, replacement, updated_content)
            total_replacements += count
        
        # Écrire le contenu mis à jour si des modifications ont été effectuées
        if total_replacements > 0 and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        
        return total_replacements, updated_content
    
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du fichier {file_path}: {e}")
        return 0, None

def update_imports_in_directory(directory, extensions=None, exclude_dirs=None, dry_run=True):
    """
    Met à jour les importations dans tous les fichiers d'un répertoire.
    
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
        
        # Mettre à jour les importations dans le fichier
        replacements, _ = update_imports_in_file(file_path, dry_run)
        
        if replacements > 0:
            stats['modified_files'] += 1
            stats['total_replacements'] += replacements
            stats['modified_files_list'].append(str(file_path))
            
            logging.info(f"Fichier {file_path}: {replacements} importations mises à jour.")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Met à jour les importations dans les fichiers Python")
    parser.add_argument('--dir', type=str, default='argumentiation_analysis', help="Répertoire à analyser")
    parser.add_argument('--dry-run', action='store_true', help="Ne pas effectuer les modifications")
    args = parser.parse_args()
    
    logging.info(f"Analyse des importations dans {args.dir}...")
    
    stats = update_imports_in_directory(args.dir, dry_run=args.dry_run)
    
    logging.info(f"\nRésultat: {stats['total_replacements']} importations mises à jour dans {stats['modified_files']}/{stats['total_files']} fichiers.")
    
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