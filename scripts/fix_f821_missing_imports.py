# -*- coding: utf-8 -*-
"""
Script de correction automatique des erreurs F821 - Missing Imports
Mission D-CI-06 Phase 1A.2 - Batch 1

Ce script corrige automatiquement les imports manquants les plus fréquents
détectés dans l'analyse F821.

Corrections appliquées :
- logger → import logging + logger = logging.getLogger(__name__)
- MagicMock, Mock, patch → from unittest.mock import ...
- Path → from pathlib import Path
- json → import json
- datetime → from datetime import datetime

Usage:
    python scripts/fix_f821_missing_imports.py [--dry-run] [--file FILE]

Options:
    --dry-run   : Afficher les changements sans les appliquer
    --file FILE : Corriger un fichier spécifique (sinon traite tous)
"""
import argparse
import json as json_module
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple


# Patterns d'imports à ajouter par nom non défini
IMPORT_FIXES = {
    'logger': {
        'import_line': 'import logging',
        'setup_line': 'logger = logging.getLogger(__name__)',
        'confidence': 'high'
    },
    'MagicMock': {
        'import_line': 'from unittest.mock import MagicMock',
        'setup_line': None,
        'confidence': 'high'
    },
    'Mock': {
        'import_line': 'from unittest.mock import Mock',
        'setup_line': None,
        'confidence': 'high'
    },
    'patch': {
        'import_line': 'from unittest.mock import patch',
        'setup_line': None,
        'confidence': 'high'
    },
    'Path': {
        'import_line': 'from pathlib import Path',
        'setup_line': None,
        'confidence': 'high'
    },
    'json': {
        'import_line': 'import json',
        'setup_line': None,
        'confidence': 'high'
    },
    'datetime': {
        'import_line': 'from datetime import datetime',
        'setup_line': None,
        'confidence': 'medium'
    },
    'isawaitable': {
        'import_line': 'from inspect import isawaitable',
        'setup_line': None,
        'confidence': 'high'
    },
}


def load_f821_analysis(analysis_path: str) -> Dict:
    """Charge l'analyse F821 depuis le fichier JSON."""
    with open(analysis_path, 'r', encoding='utf-8') as f:
        return json_module.load(f)


def get_files_to_fix(analysis_data: Dict, target_file: str = None) -> Dict[str, List[Dict]]:
    """
    Retourne un dictionnaire {file_path: [errors]} pour les erreurs corrigeables.
    
    Args:
        analysis_data: Données d'analyse F821
        target_file: Fichier spécifique à traiter (optionnel)
        
    Returns:
        Dict mapping file paths to list of correctable errors
    """
    files_to_fix = {}
    
    # Extraire les erreurs missing_imports
    missing_imports = analysis_data.get('by_category', {}).get('missing_imports', {}).get('errors', [])
    
    for error in missing_imports:
        file_path = error['file'].replace('.\\', '').replace('\\', '/')
        
        # Si un fichier cible est spécifié, filtrer
        if target_file and file_path != target_file:
            continue
        
        undefined_name = error.get('undefined_name')
        
        # Vérifier si on peut corriger automatiquement
        if undefined_name in IMPORT_FIXES:
            if file_path not in files_to_fix:
                files_to_fix[file_path] = []
            files_to_fix[file_path].append(error)
    
    return files_to_fix


def file_has_import(content: str, import_line: str) -> bool:
    """Vérifie si un import existe déjà dans le fichier."""
    # Normaliser les espaces
    import_normalized = ' '.join(import_line.split())
    
    for line in content.split('\n'):
        line_normalized = ' '.join(line.strip().split())
        if import_normalized in line_normalized:
            return True
    
    return False


def find_import_insertion_point(lines: List[str]) -> int:
    """
    Trouve le point d'insertion optimal pour un nouvel import.
    
    Retourne l'index de ligne où insérer (après les imports existants).
    """
    last_import_idx = -1
    in_docstring = False
    docstring_delimiter = None
    
    for idx, line in enumerate(lines):
        stripped = line.strip()
        
        # Gérer docstrings multi-lignes
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                docstring_delimiter = stripped[:3]
                if stripped.endswith(docstring_delimiter) and len(stripped) > 3:
                    in_docstring = False
            elif stripped.endswith(docstring_delimiter):
                in_docstring = False
            continue
        
        if in_docstring:
            continue
        
        # Ignorer commentaires et lignes vides
        if not stripped or stripped.startswith('#'):
            continue
        
        # Détection d'imports
        if stripped.startswith('import ') or stripped.startswith('from '):
            last_import_idx = idx
    
    # Insérer après le dernier import, ou au début si aucun import
    return last_import_idx + 1 if last_import_idx >= 0 else 0


def add_import_to_file(file_path: str, import_line: str, setup_line: str = None, dry_run: bool = False) -> bool:
    """
    Ajoute un import à un fichier Python.
    
    Args:
        file_path: Chemin du fichier
        import_line: Ligne d'import à ajouter
        setup_line: Ligne de setup optionnelle (ex: logger = ...)
        dry_run: Si True, n'applique pas les changements
        
    Returns:
        True si modification effectuée, False sinon
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Vérifier si l'import existe déjà
        if file_has_import(content, import_line):
            print(f"  ⏭️  Import déjà présent: {import_line}")
            return False
        
        # Trouver point d'insertion
        insert_idx = find_import_insertion_point(lines)
        
        # Insérer l'import
        lines.insert(insert_idx, import_line)
        
        # Si setup_line fourni, l'insérer après les imports
        if setup_line:
            # Trouver la fin de la section imports après insertion
            new_insert_idx = find_import_insertion_point(lines)
            # Ajouter ligne vide puis setup
            lines.insert(new_insert_idx, '')
            lines.insert(new_insert_idx + 1, setup_line)
        
        if dry_run:
            print(f"  [DRY-RUN] Ajouterait: {import_line}")
            if setup_line:
                print(f"  [DRY-RUN] Ajouterait: {setup_line}")
            return True
        
        # Écrire le fichier modifié
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
        
        print(f"  ✅ Ajouté: {import_line}")
        if setup_line:
            print(f"  ✅ Ajouté: {setup_line}")
        return True
    
    except Exception as e:
        print(f"  ❌ Erreur lors de la modification de {file_path}: {e}")
        return False


def fix_file_imports(file_path: str, errors: List[Dict], dry_run: bool = False) -> int:
    """
    Corrige les imports manquants dans un fichier.
    
    Returns:
        Nombre de corrections appliquées
    """
    print(f"\n📝 Traitement: {file_path}")
    
    # Collecter les imports uniques nécessaires
    needed_imports = {}
    for error in errors:
        undefined_name = error.get('undefined_name')
        if undefined_name in IMPORT_FIXES and undefined_name not in needed_imports:
            needed_imports[undefined_name] = IMPORT_FIXES[undefined_name]
    
    if not needed_imports:
        print(f"  ⚠️  Aucun import automatique disponible")
        return 0
    
    # Appliquer les corrections
    fixes_applied = 0
    for name, fix_info in needed_imports.items():
        if add_import_to_file(
            file_path,
            fix_info['import_line'],
            fix_info.get('setup_line'),
            dry_run
        ):
            fixes_applied += 1
    
    return fixes_applied


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description='Correction automatique des imports manquants (F821)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Afficher les changements sans les appliquer'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Fichier spécifique à corriger (chemin relatif)'
    )
    parser.add_argument(
        '--analysis',
        type=str,
        default='reports/f821_analysis.json',
        help='Chemin du fichier d\'analyse F821'
    )
    
    args = parser.parse_args()
    
    print("🚀 Script de correction F821 - Missing Imports")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  MODE DRY-RUN : Aucune modification ne sera appliquée\n")
    
    # Charger l'analyse
    if not os.path.exists(args.analysis):
        print(f"❌ Fichier d'analyse introuvable: {args.analysis}")
        return 1
    
    print(f"📊 Chargement de l'analyse: {args.analysis}")
    analysis_data = load_f821_analysis(args.analysis)
    
    # Obtenir les fichiers à corriger
    files_to_fix = get_files_to_fix(analysis_data, args.file)
    
    if not files_to_fix:
        print("ℹ️  Aucun fichier nécessitant des corrections automatiques")
        return 0
    
    print(f"\n📦 Fichiers à traiter: {len(files_to_fix)}")
    print("=" * 60)
    
    # Statistiques
    total_fixes = 0
    files_modified = 0
    
    # Traiter chaque fichier
    for file_path, errors in files_to_fix.items():
        fixes = fix_file_imports(file_path, errors, args.dry_run)
        if fixes > 0:
            total_fixes += fixes
            files_modified += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"Fichiers traités:  {len(files_to_fix)}")
    print(f"Fichiers modifiés: {files_modified}")
    print(f"Imports ajoutés:   {total_fixes}")
    
    if args.dry_run:
        print("\n⚠️  Mode DRY-RUN : Aucune modification appliquée")
        print("Relancez sans --dry-run pour appliquer les changements")
    else:
        print("\n✅ Corrections appliquées avec succès!")
        print("\n📋 Prochaines étapes:")
        print("  1. Vérifier les modifications: git diff")
        print("  2. Tester: pytest tests/ -v --tb=short -x")
        print("  3. Vérifier F821: flake8 --select=F821 --count")
        print("  4. Commit: git add . && git commit -m 'fix(linting): Add missing imports - Phase 1A Batch 1'")
    
    return 0


if __name__ == '__main__':
    exit(main())