#!/usr/bin/env python3
"""
Script de correction automatique F821 - Batch 1 : Imports Courants
Phase 1F : Corrections ciblées des imports les plus communs et sûrs

Basé sur l'analyse de reports/f821_analysis.json, ce script ajoute automatiquement
les imports suivants (triés par fréquence d'occurrence) :
- json (9 occurrences) - module stdlib
- MagicMock (7 occurrences) - unittest.mock
- Optional (2 occurrences) - typing
- datetime (1 occurrence) - module stdlib
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set
import ast

# Mapping des noms undefined vers leurs imports corrects
IMPORT_MAPPING = {
    # Standard library - json
    "json": "import json",
    
    # typing - Optional
    "Optional": "from typing import Optional",
    
    # datetime
    "datetime": "import datetime",
    
    # unittest.mock - MagicMock
    "MagicMock": "from unittest.mock import MagicMock",
}

def read_f821_analysis(report_path: Path) -> Dict:
    """Lit le rapport d'analyse F821"""
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_simple_import_errors(analysis: Dict) -> Dict[str, List[Dict]]:
    """
    Extrait les erreurs F821 qui correspondent à des imports simples et courants
    
    Returns:
        Dict mapping undefined_name -> liste d'erreurs
    """
    simple_imports = {}
    
    for error in analysis.get('by_category', {}).get('missing_imports', {}).get('errors', []):
        undefined_name = error['undefined_name']
        
        # Filtrer uniquement les noms présents dans notre mapping
        if undefined_name in IMPORT_MAPPING:
            if undefined_name not in simple_imports:
                simple_imports[undefined_name] = []
            simple_imports[undefined_name].append(error)
    
    return simple_imports

def get_existing_imports(file_path: Path) -> Set[str]:
    """
    Analyse les imports existants dans un fichier
    
    Returns:
        Set des noms déjà importés
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imported_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.name)
        
        return imported_names
    except Exception as e:
        print(f"⚠️  Erreur analyse imports {file_path}: {e}")
        return set()

def find_import_insertion_line(content: str) -> int:
    """
    Trouve la ligne où insérer un nouvel import
    
    Returns:
        Numéro de ligne (0-indexed) où insérer l'import
    """
    lines = content.splitlines()
    
    # Chercher la dernière ligne d'import
    last_import_line = -1
    docstring_end = -1
    
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Gestion des docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(docstring_char) >= 2:
                    # Docstring sur une seule ligne
                    docstring_end = i
                else:
                    in_docstring = True
        else:
            if docstring_char in stripped:
                in_docstring = False
                docstring_end = i
        
        # Trouver la dernière ligne d'import (ignorer les lignes vides et commentaires après imports)
        if stripped.startswith('import ') or stripped.startswith('from '):
            last_import_line = i
    
    # Insérer après la dernière ligne d'import, ou après le docstring
    insertion_line = max(last_import_line, docstring_end) + 1
    
    # Sauter les lignes vides après la dernière ligne d'import
    while insertion_line < len(lines) and lines[insertion_line].strip() == '':
        insertion_line += 1
    
    # Si aucun import trouvé, insérer après le shebang/encoding si présent
    if insertion_line == 0:
        for i, line in enumerate(lines[:5]):  # Vérifier les 5 premières lignes
            if line.strip().startswith('#'):
                insertion_line = i + 1
            else:
                break
    
    return insertion_line

def add_import_to_file(file_path: Path, import_statement: str, dry_run: bool = False) -> bool:
    """
    Ajoute un import à un fichier si pas déjà présent
    
    Returns:
        True si import ajouté, False sinon
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si l'import existe déjà (exact match)
        if import_statement in content:
            return False
        
        lines = content.splitlines(keepends=True)
        insertion_line = find_import_insertion_line(content)
        
        # Si insertion_line est au milieu d'une ligne vide, ne pas insérer
        # Au lieu de cela, chercher la prochaine ligne non-vide ou la fin du bloc d'imports
        if insertion_line < len(lines):
            # Si on est sur une ligne vide après les imports, ajouter l'import avant cette ligne vide
            while insertion_line > 0 and lines[insertion_line - 1].strip() == '':
                insertion_line -= 1
        
        # Insérer l'import
        new_content_lines = (
            lines[:insertion_line] +
            [import_statement + '\n'] +
            lines[insertion_line:]
        )
        
        new_content = ''.join(new_content_lines)
        
        # Valider syntaxe AST
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            print(f"⚠️  Syntaxe invalide après ajout import dans {file_path}: {e}")
            print(f"   Ligne d'insertion tentée: {insertion_line}")
            print(f"   Contexte (lignes {max(0, insertion_line-2)}-{min(len(lines), insertion_line+2)}):")
            for i in range(max(0, insertion_line-2), min(len(lines), insertion_line+2)):
                print(f"     {i}: {lines[i].rstrip()}")
            return False
        
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur ajout import dans {file_path}: {e}")
        return False

def process_batch1_corrections(
    analysis: Dict,
    dry_run: bool = False,
    verbose: bool = True
) -> Dict[str, int]:
    """
    Traite les corrections Batch 1 (imports courants simples)
    
    Returns:
        Dict avec statistiques : {
            'files_modified': int,
            'imports_added': int,
            'errors_fixed': int,
            'by_name': {name: count}
        }
    """
    stats = {
        'files_modified': 0,
        'imports_added': 0,
        'errors_fixed': 0,
        'by_name': {}
    }
    
    simple_imports = extract_simple_import_errors(analysis)
    
    if verbose:
        print(f"\n🔍 Batch 1 : {sum(len(errs) for errs in simple_imports.values())} erreurs F821 pour imports courants")
        print(f"📦 Noms ciblés : {', '.join(simple_imports.keys())}\n")
    
    # Grouper par fichier
    files_to_fix: Dict[Path, Set[str]] = {}
    
    for undefined_name, errors in simple_imports.items():
        for error in errors:
            file_path = Path(error['file'])
            if file_path not in files_to_fix:
                files_to_fix[file_path] = set()
            files_to_fix[file_path].add(undefined_name)
    
    # Traiter chaque fichier
    for file_path, undefined_names in sorted(files_to_fix.items()):
        if not file_path.exists():
            if verbose:
                print(f"⚠️  Fichier introuvable : {file_path}")
            continue
        
        # Vérifier imports existants
        existing_imports = get_existing_imports(file_path)
        
        # Filtrer les imports déjà présents
        names_to_add = [
            name for name in undefined_names
            if name not in existing_imports
        ]
        
        if not names_to_add:
            if verbose:
                print(f"✓ {file_path} - Imports déjà présents")
            continue
        
        file_modified = False
        imports_added_this_file = 0
        
        for undefined_name in names_to_add:
            import_statement = IMPORT_MAPPING[undefined_name]
            
            if add_import_to_file(file_path, import_statement, dry_run=dry_run):
                imports_added_this_file += 1
                stats['imports_added'] += 1
                
                # Compter les erreurs résolues
                errors_fixed = len([
                    e for e in simple_imports[undefined_name]
                    if Path(e['file']) == file_path
                ])
                stats['errors_fixed'] += errors_fixed
                
                # Stats par nom
                if undefined_name not in stats['by_name']:
                    stats['by_name'][undefined_name] = 0
                stats['by_name'][undefined_name] += errors_fixed
                
                file_modified = True
        
        if file_modified:
            stats['files_modified'] += 1
            if verbose:
                mode = "[DRY-RUN] " if dry_run else ""
                print(f"{mode}✅ {file_path}")
                print(f"   → {imports_added_this_file} import(s) ajouté(s) : {', '.join(names_to_add)}")
    
    return stats

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Correction automatique F821 Batch 1 : Imports courants (json, Optional, MagicMock, datetime)"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Mode simulation (aucune modification de fichier)"
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path('reports/f821_analysis.json'),
        help="Chemin vers le rapport d'analyse F821 (défaut: reports/f821_analysis.json)"
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help="Mode silencieux (pas de sortie détaillée)"
    )
    
    args = parser.parse_args()
    
    # Vérifier existence rapport
    if not args.report.exists():
        print(f"❌ Rapport introuvable : {args.report}")
        return 1
    
    # Lire rapport
    analysis = read_f821_analysis(args.report)
    
    # Traiter corrections
    stats = process_batch1_corrections(
        analysis,
        dry_run=args.dry_run,
        verbose=not args.quiet
    )
    
    # Afficher résumé
    print(f"\n{'='*60}")
    print(f"📊 Résumé Batch 1 - Imports Courants")
    print(f"{'='*60}")
    if args.dry_run:
        print("⚠️  MODE DRY-RUN - Aucune modification effectuée")
    print(f"✅ Fichiers modifiés    : {stats['files_modified']}")
    print(f"📦 Imports ajoutés      : {stats['imports_added']}")
    print(f"🐛 Erreurs F821 résolues: {stats['errors_fixed']}")
    print(f"\n📈 Détail par nom :")
    for name, count in sorted(stats['by_name'].items(), key=lambda x: -x[1]):
        print(f"   - {name:15} : {count:2} erreur(s)")
    print(f"{'='*60}\n")
    
    return 0

if __name__ == '__main__':
    exit(main())