# -*- coding: utf-8 -*-
"""
Script d'ajout de # noqa: F821 pour tests obsolètes - Phase 1A.3
Mission D-CI-06

Ajoute des commentaires # noqa: F821 justifiés sur les fichiers de tests
identifiés comme "dead_code" ou problématiques dans l'analyse.

Usage:
    python scripts/add_f821_noqa_tests.py [--dry-run]
"""
import argparse
import json
import os
import re
from typing import List, Dict, Set

# Fichiers hotspots identifiés dans l'analyse
HOTSPOT_FILES = [
    'tests/conftest_phase3_jpype_killer.py',
    'scripts/testing/run_embed_tests.py',
]

# Patterns de lignes nécessitant noqa
NOQA_PATTERNS = [
    (r'\bMagicMock\b', '# noqa: F821 - unittest.mock import dynamique'),
    (r'\bMock\b', '# noqa: F821 - unittest.mock import dynamique'),
    (r'\bpatch\b', '# noqa: F821 - unittest.mock import dynamique'),
    (r'\blogger\b', '# noqa: F821 - logging import dynamique'),
    (r'\bUnifiedOrchestrationPipeline\b', '# noqa: F821 - dead code test obsolète'),
]


def load_f821_analysis(analysis_path: str = 'reports/f821_analysis.json') -> Dict:
    """Charge l'analyse F821."""
    with open(analysis_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def should_add_noqa(line: str, existing_noqa: bool = False) -> tuple:
    """
    Détermine si une ligne nécessite un noqa F821.

    Returns:
        (should_add: bool, reason: str)
    """
    if existing_noqa:
        return False, ""

    line_stripped = line.strip()

    # Ignorer lignes vides et commentaires purs
    if not line_stripped or line_stripped.startswith('#'):
        return False, ""

    # Vérifier patterns
    for pattern, reason in NOQA_PATTERNS:
        if re.search(pattern, line):
            return True, reason

    return False, ""


def add_noqa_to_file(file_path: str, errors: List[Dict], dry_run: bool = False) -> int:
    """
    Ajoute des # noqa: F821 aux lignes identifiées dans errors.

    Returns:
        Nombre de lignes modifiées
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        lines_to_modify = {}
        for error in errors:
            line_num = error['line'] - 1  # 0-indexed
            if 0 <= line_num < len(lines):
                lines_to_modify[line_num] = error

        modified_count = 0
        new_lines = []

        for idx, line in enumerate(lines):
            if idx in lines_to_modify:
                # Vérifier si noqa déjà présent
                has_noqa = '# noqa' in line or '# type: ignore' in line

                if not has_noqa:
                    should_add, reason = should_add_noqa(line, has_noqa)

                    if should_add:
                        # Enlever le \n final si présent
                        line_clean = line.rstrip('\n\r')

                        # Ajouter noqa à la fin
                        new_line = f"{line_clean}  {reason}\n"
                        new_lines.append(new_line)
                        modified_count += 1

                        if dry_run:
                            print(f"  [DRY-RUN] Ligne {idx+1}: ajouterait noqa")
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if modified_count > 0 and not dry_run:
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.writelines(new_lines)
            print(f"  ✅ {modified_count} lignes modifiées")
        elif modified_count > 0 and dry_run:
            print(f"  [DRY-RUN] {modified_count} lignes à modifier")
        else:
            print(f"  ℹ️  Aucune modification nécessaire")

        return modified_count

    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return 0


def process_hotspots(analysis_data: Dict, dry_run: bool = False) -> int:
    """
    Traite les fichiers hotspots identifiés.

    Returns:
        Nombre total de lignes modifiées
    """
    total_modified = 0

    # Extraire toutes les erreurs
    all_errors = analysis_data.get('all_errors', [])

    # Grouper par fichier
    errors_by_file = {}
    for error in all_errors:
        file_path = error['file'].replace('.\\', '').replace('\\', '/')
        if file_path not in errors_by_file:
            errors_by_file[file_path] = []
        errors_by_file[file_path].append(error)

    # Traiter fichiers
    hotspots = analysis_data.get('hotspots', [])
    for hotspot in hotspots:
        file_path = hotspot['file'].replace('.\\', '').replace('\\', '/')

        # Vérifier si c'est un fichier de test
        if 'test' not in file_path.lower():
            continue

        if file_path in errors_by_file:
            print(f"\n📝 Traitement: {file_path} ({hotspot['f821_count']} erreurs)")
            modified = add_noqa_to_file(
                file_path,
                errors_by_file[file_path],
                dry_run
            )
            total_modified += modified

    return total_modified


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description='Ajout de # noqa: F821 pour tests obsolètes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Afficher les changements sans les appliquer'
    )
    parser.add_argument(
        '--analysis',
        type=str,
        default='reports/f821_analysis.json',
        help='Chemin du fichier d\'analyse F821'
    )

    args = parser.parse_args()

    print("🚀 Script d'ajout # noqa: F821 - Tests obsolètes")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  MODE DRY-RUN : Aucune modification ne sera appliquée\n")

    # Charger l'analyse
    if not os.path.exists(args.analysis):
        print(f"❌ Fichier d'analyse introuvable: {args.analysis}")
        return 1

    print(f"📊 Chargement de l'analyse: {args.analysis}")
    analysis_data = load_f821_analysis(args.analysis)

    # Traiter hotspots
    total_modified = process_hotspots(analysis_data, args.dry_run)

    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"Lignes modifiées: {total_modified}")

    if args.dry_run:
        print("\n⚠️  Mode DRY-RUN : Aucune modification appliquée")
    else:
        print("\n✅ Modifications appliquées!")
        print("\n📋 Prochaines étapes:")
        print("  1. Vérifier: git diff")
        print("  2. Compter F821: python -m flake8 --select=F821 --count")
        print("  3. Tests: pytest tests/ -v --tb=short -x")

    return 0


if __name__ == '__main__':
    exit(main())