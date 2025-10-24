#!/usr/bin/env python3
"""
Fix W293 (blank line whitespace) errors - TARGETED MODE Phase 1E.

Lit flake8_report.txt pour corriger uniquement les 56 erreurs W293 réapparues.
Version optimisée avec logs détaillés et validation AST.

Phase 1E: Quick Wins Auto-Fixables - Option A (0 erreurs)
"""
import ast
import sys
from pathlib import Path
from collections import defaultdict


def parse_flake8_report(report_path: Path) -> dict[Path, list[int]]:
    """
    Parse flake8_report.txt et extrait les erreurs W293.
    
    Returns:
        Dict[filepath, list of line numbers with W293]
    """
    errors_by_file = defaultdict(list)
    
    print(f"📖 Lecture de {report_path}...")
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or 'W293' not in line:
                    continue
                
                # Format: ./path/to/file.py:123:1: W293 blank line contains whitespace
                # Gère aussi le format Windows: .\path\to\file.py:123:1:
                parts = line.split(':')
                if len(parts) < 4:
                    continue
                
                # Nettoyer le chemin (supprimer ./ ou .\ au début)
                filepath_str = parts[0].lstrip('./').lstrip('.\\')
                filepath = Path(filepath_str)
                try:
                    line_num = int(parts[1])
                    errors_by_file[filepath].append(line_num)
                except (ValueError, IndexError):
                    continue
    
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {report_path}", file=sys.stderr)
        return {}
    
    print(f"✅ Trouvé {sum(len(v) for v in errors_by_file.values())} erreurs W293 dans {len(errors_by_file)} fichiers")
    return dict(errors_by_file)


def fix_w293_in_file(filepath: Path, target_lines: list[int]) -> int:
    """
    Fix W293 errors on specific lines in a file.
    
    Args:
        filepath: Path to file
        target_lines: List of 1-based line numbers with W293 errors
    
    Returns:
        Number of lines fixed
    """
    print(f"\n🔧 Traitement de {filepath} ({len(target_lines)} erreurs)...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_content = ''.join(lines)
        fixes_count = 0
        target_lines_set = set(target_lines)
        
        for i, line in enumerate(lines, start=1):
            if i in target_lines_set:
                # W293: blank line contains whitespace
                if line.strip() == '' and line != '\n':
                    lines[i-1] = '\n'
                    fixes_count += 1
                    print(f"  ✓ Ligne {i}: '{repr(line.rstrip())}' → '\\n'")
        
        if fixes_count == 0:
            print(f"  ⚠️ Aucune modification nécessaire (erreurs déjà corrigées?)")
            return 0
        
        # Validation AST
        new_content = ''.join(lines)
        try:
            ast.parse(new_content)
            print(f"  ✅ Validation AST réussie")
        except SyntaxError as e:
            print(f"  ❌ ERREUR AST après modification: {e}", file=sys.stderr)
            print(f"  🔄 Restauration du contenu original", file=sys.stderr)
            return 0
        
        # Écriture du fichier modifié
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ {fixes_count}/{len(target_lines)} corrections appliquées")
        return fixes_count
    
    except Exception as e:
        print(f"  ❌ Erreur lors du traitement: {e}", file=sys.stderr)
        return 0


def main():
    """Process targeted W293 errors from flake8_report.txt."""
    print("=" * 80)
    print("🚀 Fix W293 Whitespace Errors - TARGETED MODE Phase 1E")
    print("=" * 80)
    
    root = Path('.')
    report_path = root / 'flake8_report.txt'
    
    # Parse flake8 report
    errors_by_file = parse_flake8_report(report_path)
    
    if not errors_by_file:
        print("\n❌ Aucune erreur W293 trouvée dans flake8_report.txt")
        return 1
    
    # Process each file
    total_fixed = 0
    files_modified = 0
    
    print(f"\n📋 Plan: {len(errors_by_file)} fichiers à traiter")
    print("-" * 80)
    
    for i, (filepath, target_lines) in enumerate(errors_by_file.items(), start=1):
        print(f"\n[{i}/{len(errors_by_file)}] {filepath}")
        
        if not filepath.exists():
            print(f"  ⚠️ Fichier introuvable, ignoré")
            continue
        
        fixed = fix_w293_in_file(filepath, target_lines)
        if fixed > 0:
            files_modified += 1
            total_fixed += fixed
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"  Fichiers modifiés  : {files_modified}/{len(errors_by_file)}")
    print(f"  Erreurs W293 fixées: {total_fixed}")
    print(f"  Statut             : {'✅ SUCCÈS' if total_fixed > 0 else '⚠️ RIEN À FAIRE'}")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())