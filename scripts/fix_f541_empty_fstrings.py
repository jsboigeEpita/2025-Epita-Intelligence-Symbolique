#!/usr/bin/env python3
"""
Fix F541 (f-string sans placeholder) errors.
Remplace f"text" → "text" si aucun placeholder détecté.
Validation AST obligatoire pour éviter casser code.
"""
import re
import ast
import sys
from pathlib import Path
from typing import Tuple

def has_fstring_placeholder(content: str) -> bool:
    """
    Détecte si un f-string contient des placeholders réels.
    Retourne True si placeholders détectés, False sinon.
    """
    # Pattern placeholders : {var}, {expr}, {func()}, etc.
    # Mais PAS \{ ou \} (échappés)
    pattern = r'(?<!\\)\{[^}]+(?<!\\)\}'
    return bool(re.search(pattern, content))

def fix_f541_in_file(filepath: Path, dry_run: bool = True) -> Tuple[int, bool]:
    """
    Fix F541 errors in a single file.
    Returns: (fixes_count, success)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Pattern : f-strings (f"..." ou f'...')
        # Capture quote type et contenu
        pattern = r'f(["\'])([^\1]*?)\1'
        
        fixes_count = 0
        modified_content = original_content
        
        def replacer(match):
            nonlocal fixes_count
            quote = match.group(1)
            content = match.group(2)
            
            # Vérifier si contient placeholders
            if has_fstring_placeholder(content):
                # Garder f-string (placeholders détectés)
                return match.group(0)
            else:
                # Supprimer préfixe f
                fixes_count += 1
                return f'{quote}{content}{quote}'
        
        modified_content = re.sub(pattern, replacer, original_content)
        
        if fixes_count == 0:
            return (0, True)
        
        # VALIDATION AST CRITIQUE
        try:
            ast.parse(modified_content)
        except SyntaxError as e:
            print(f"❌ {filepath}: AST validation failed - {e}", file=sys.stderr)
            print(f"   Correction annulée pour sécurité", file=sys.stderr)
            return (0, False)
        
        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"✅ {filepath}: {fixes_count} f-strings corrigés")
        else:
            print(f"📝 {filepath}: {fixes_count} f-strings à corriger")
        
        return (fixes_count, True)
        
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
        return (0, False)

def main():
    """Process Python files with F541 errors."""
    import argparse
    parser = argparse.ArgumentParser(description='Fix F541 empty f-string errors')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without modifying files')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of files to process per batch')
    parser.add_argument('--interactive', action='store_true',
                       help='Ask confirmation for each batch')
    args = parser.parse_args()
    
    root = Path('.')
    python_files = list(root.rglob('*.py'))
    
    # Exclusions (respecter .flake8)
    excludes = ['.git', '__pycache__', 'build', 'dist', '.roo', '.temp',
                'node_modules', 'venv', '.venv', 'env', '.env', '.pytest_cache',
                '.benchmarks', '*.egg-info', 'migration_output', '.github',
                'libs/portable_octave', 'logs']
    python_files = [f for f in python_files 
                   if not any(excl in str(f) for excl in excludes)]
    
    print(f"🔍 {'DRY RUN' if args.dry_run else 'FIXING'}: {len(python_files)} fichiers Python...")
    
    total_fixes = 0
    files_fixed = 0
    files_failed = 0
    
    # Traitement par batch
    for i in range(0, len(python_files), args.batch_size):
        batch = python_files[i:i+args.batch_size]
        batch_num = i // args.batch_size + 1
        total_batches = (len(python_files) + args.batch_size - 1) // args.batch_size
        
        if args.interactive and not args.dry_run:
            response = input(f"\n🤔 Batch {batch_num}/{total_batches} ({len(batch)} fichiers). Continuer? (y/n): ")
            if response.lower() != 'y':
                print("❌ Arrêt utilisateur")
                break
        
        print(f"\n--- Batch {batch_num}/{total_batches} ---")
        
        for filepath in batch:
            fixes, success = fix_f541_in_file(filepath, args.dry_run)
            if fixes > 0:
                files_fixed += 1
                total_fixes += fixes
            if not success:
                files_failed += 1
    
    print(f"\n📊 Summary:")
    print(f"  Fichiers {'à modifier' if args.dry_run else 'modifiés'}: {files_fixed}")
    print(f"  F541 {'détectés' if args.dry_run else 'corrigés'}: {total_fixes}")
    print(f"  Échecs: {files_failed}")
    
    if args.dry_run:
        print(f"\n💡 Exécuter sans --dry-run pour appliquer les corrections")

if __name__ == '__main__':
    main()