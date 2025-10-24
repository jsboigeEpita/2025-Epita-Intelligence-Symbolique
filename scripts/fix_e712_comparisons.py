#!/usr/bin/env python3
"""
Fix E712 (comparison to True/False) errors.
Replaces ' is True' with 'is True' and ' is False' with 'is False'.
"""
import re
import sys
from pathlib import Path
from typing import Tuple

def fix_e712_in_file(filepath: Path, dry_run: bool = False) -> Tuple[int, int]:
    """
    Fix E712 errors in a single file.
    Returns: (true_fixes, false_fixes)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        true_fixes = 0
        false_fixes = 0

        # Pattern 1: is True (avec espaces variables)
        pattern_true = r'\s*==\s*True\b'
        matches_true = re.findall(pattern_true, content)
        true_fixes = len(matches_true)
        content = re.sub(pattern_true, ' is True', content)

        # Pattern 2: is False (avec espaces variables)
        pattern_false = r'\s*==\s*False\b'
        matches_false = re.findall(pattern_false, content)
        false_fixes = len(matches_false)
        content = re.sub(pattern_false, ' is False', content)

        # Pattern 3: is not True → is not True
        pattern_not_true = r'\s*!=\s*True\b'
        matches_not_true = re.findall(pattern_not_true, content)
        true_fixes += len(matches_not_true)
        content = re.sub(pattern_not_true, ' is not True', content)

        # Pattern 4: is not False → is not False
        pattern_not_false = r'\s*!=\s*False\b'
        matches_not_false = re.findall(pattern_not_false, content)
        false_fixes += len(matches_not_false)
        content = re.sub(pattern_not_false, ' is not False', content)

        if content != original_content and not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        return (true_fixes, false_fixes)
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
        return (0, 0)

def main():
    """Process all Python files in project."""
    import argparse
    parser = argparse.ArgumentParser(description='Fix E712 comparison errors')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be changed without modifying files')
    args = parser.parse_args()

    root = Path('.')
    python_files = list(root.rglob('*.py'))

    # Exclusions (respecter .flake8) - normaliser les chemins pour Windows
    excludes = ['libs/portable_octave', 'node_modules', '.git', '__pycache__',
                '.venv', 'venv', 'env', '.eggs', 'dist', 'build', '.tox',
                '.roo', '.temp', '.pytest_cache', '.benchmarks', 'migration_output',
                '.github', 'logs']

    def should_exclude(filepath):
        """Check if file should be excluded (works with Windows paths)."""
        path_str = str(filepath).replace('\\', '/')
        return any(excl in path_str for excl in excludes)

    python_files = [f for f in python_files if not should_exclude(f)]

    total_true = 0
    total_false = 0
    files_modified = 0

    mode = "DRY RUN" if args.dry_run else "FIXING"
    print(f"🔍 {mode}: Processing {len(python_files)} Python files...")

    for filepath in python_files:
        true_fixes, false_fixes = fix_e712_in_file(filepath, args.dry_run)
        if true_fixes > 0 or false_fixes > 0:
            files_modified += 1
            total_true += true_fixes
            total_false += false_fixes
            symbol = "  📝" if args.dry_run else "  ✅"
            print(f"{symbol} {filepath}: True={true_fixes}, False={false_fixes}")

    print("\n📊 Summary:")
    print(f"  Files {'would be modified' if args.dry_run else 'modified'}: {files_modified}")
    print(f"  ' is True' → 'is True': {total_true}")
    print(f"  ' is False' → 'is False': {total_false}")
    print(f"  Total fixed: {total_true + total_false}")

    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")

if __name__ == '__main__':
    main()