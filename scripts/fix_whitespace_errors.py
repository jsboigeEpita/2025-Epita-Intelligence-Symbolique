#!/usr/bin/env python3
"""
Fix W293 (blank line whitespace) and W291 (trailing whitespace) errors.
100% safe, cosmetic changes only.

Phase 1B: Quick Wins Whitespace - Corrections Automatiques
Target: 684 W293 + 269 W291 = 953 errors
"""
import os
import sys
from pathlib import Path


def should_exclude(filepath: Path, exclusions: list[str]) -> bool:
    """Check if file should be excluded based on .flake8 exclusions."""
    filepath_str = str(filepath).replace('\\', '/')

    for exclusion in exclusions:
        exclusion = exclusion.strip()
        if not exclusion or exclusion.startswith('#'):
            continue

        # Handle wildcards
        if '*' in exclusion:
            if exclusion.endswith('*'):
                # Pattern like "*.egg-info"
                if filepath_str.endswith(exclusion.replace('*', '')):
                    return True
        else:
            # Direct path match
            if exclusion in filepath_str:
                return True

    return False


def fix_whitespace_in_file(filepath: Path) -> tuple[int, int]:
    """
    Fix whitespace errors in a single file.
    Returns: (w293_fixed, w291_fixed)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        w293_count = 0
        w291_count = 0
        modified_lines = []

        for line in lines:
            original = line
            # Fix W293: Remove whitespace from blank lines
            if line.strip() == '' and line != '\n':
                line = '\n'
                w293_count += 1
            # Fix W291: Remove trailing whitespace
            elif line.rstrip() != line.rstrip('\n'):
                line = line.rstrip() + '\n' if line.endswith('\n') else line.rstrip()
                w291_count += 1
            modified_lines.append(line)

        if w293_count > 0 or w291_count > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

        return (w293_count, w291_count)
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
        return (0, 0)


def main():
    """Process all Python files in project."""
    # Read exclusions from .flake8
    exclusions = [
        '.git', '__pycache__', 'build', 'dist', '.roo', '.temp',
        'node_modules', 'venv', '.venv', 'env', '.env',
        '.pytest_cache', '.benchmarks', '*.egg-info',
        'migration_output', '.github', 'libs/portable_octave', 'logs'
    ]

    root = Path('.')
    python_files = list(root.rglob('*.py'))

    # Filter files based on exclusions
    filtered_files = [f for f in python_files if not should_exclude(f, exclusions)]

    total_w293 = 0
    total_w291 = 0
    files_modified = 0

    print(f"🔍 Processing {len(filtered_files)} Python files (excluded {len(python_files) - len(filtered_files)})...")

    for filepath in filtered_files:
        w293, w291 = fix_whitespace_in_file(filepath)
        if w293 > 0 or w291 > 0:
            files_modified += 1
            total_w293 += w293
            total_w291 += w291
            print(f"  ✅ {filepath}: W293={w293}, W291={w291}")

    print(f"\n📊 Summary:")
    print(f"  Files modified: {files_modified}")
    print(f"  W293 fixed: {total_w293}")
    print(f"  W291 fixed: {total_w291}")
    print(f"  Total fixed: {total_w293 + total_w291}")


if __name__ == '__main__':
    main()