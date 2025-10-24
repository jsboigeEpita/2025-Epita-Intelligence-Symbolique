#!/usr/bin/env python3
"""
Fix F541 (f-string sans placeholder) errors de manière ciblée.
Lit le rapport flake8 et corrige uniquement les fichiers concernés.
"""
import re
import ast
import sys
from pathlib import Path
from typing import Set

def extract_f541_files(report_path: str) -> Set[str]:
    """Extrait la liste des fichiers avec erreurs F541 du rapport."""
    files = set()
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Le rapport peut avoir des \n comme texte ou de vraies nouvelles lignes
        lines = content.replace('\\n', '\n').split('\n')
        for line in lines:
            if 'F541' in line and ':' in line:
                file_path = line.split(':')[0].strip('.\\').strip('./').strip()
                if file_path:
                    files.add(file_path)
    return files

def has_fstring_placeholder(content: str) -> bool:
    """Détecte si un f-string contient des placeholders réels."""
    pattern = r'(?<!\\)\{[^}]+(?<!\\)\}'
    return bool(re.search(pattern, content))

def fix_f541_in_file(filepath: Path, dry_run: bool = True) -> tuple:
    """Fix F541 errors in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Pattern : f-strings (f"..." ou f'...')
        pattern = r'f(["\'])([^\1]*?)\1'

        fixes_count = 0
        modified_content = original_content

        def replacer(match):
            nonlocal fixes_count
            quote = match.group(1)
            content = match.group(2)

            if has_fstring_placeholder(content):
                return match.group(0)
            else:
                fixes_count += 1
                return f'{quote}{content}{quote}'

        modified_content = re.sub(pattern, replacer, original_content)

        if fixes_count == 0:
            return (0, True, "no_changes")

        # VALIDATION AST CRITIQUE
        try:
            ast.parse(modified_content)
        except SyntaxError as e:
            print(f"❌ {filepath}: AST validation failed - {e}", file=sys.stderr)
            return (0, False, "ast_error")

        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"✅ {filepath}: {fixes_count} f-strings corrigés")
        else:
            print(f"📝 {filepath}: {fixes_count} f-strings à corriger")

        return (fixes_count, True, "success")

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
        return (0, False, "exception")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix F541 errors from flake8 report')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Preview changes without modifying files')
    parser.add_argument('--report', default='flake8_report.txt',
                        help='Path to flake8 report')
    args = parser.parse_args()

    print(f"🔍 Extraction des fichiers avec F541 depuis {args.report}...")
    f541_files = extract_f541_files(args.report)

    if not f541_files:
        print("❌ Aucun fichier avec F541 trouvé dans le rapport")
        return

    print(f"📋 {len(f541_files)} fichiers avec erreurs F541 détectés")

    total_fixes = 0
    files_fixed = 0
    files_failed = 0
    files_skipped = 0

    mode = "DRY RUN" if args.dry_run else "FIXING"
    print(f"\n🔧 {mode}: Traitement des fichiers...")

    for file_path in sorted(f541_files):
        filepath = Path(file_path)
        if not filepath.exists():
            print(f"⚠️ {filepath}: Fichier introuvable", file=sys.stderr)
            files_skipped += 1
            continue

        fixes, success, status = fix_f541_in_file(filepath, args.dry_run)

        if status == "success":
            files_fixed += 1
            total_fixes += fixes
        elif status == "ast_error" or status == "exception":
            files_failed += 1
        # no_changes ne compte pas comme échec

    print(f"\n📊 Summary:")
    print(f"  Fichiers {'à modifier' if args.dry_run else 'modifiés'}: {files_fixed}")
    print(f"  F541 {'détectés' if args.dry_run else 'corrigés'}: {total_fixes}")
    print(f"  Échecs: {files_failed}")
    print(f"  Ignorés (introuvables): {files_skipped}")

    if args.dry_run:
        print(f"\n💡 Exécuter sans --dry-run pour appliquer les corrections")

if __name__ == '__main__':
    main()