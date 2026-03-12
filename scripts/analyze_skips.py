#!/usr/bin/env python3
"""
Script pour analyser les marqueurs de skip dans les tests.

Identifie tous les tests qui sont potentiellement skippés et catégorise
les raisons selon le protocole de la Mission 1 (#94).
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"


def find_test_files(directory: Path) -> list[Path]:
    """Trouve tous les fichiers de test Python."""
    test_files = []
    for root, dirs, files in os.walk(directory):
        # Ignorer certains répertoires
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.pytest_cache', 'node_modules']]

        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                test_files.append(Path(root) / file)
            elif file == 'conftest.py':
                test_files.append(Path(root) / file)

    return sorted(test_files)


def extract_skip_markers(file_path: Path) -> list[dict]:
    """Extrait les marqueurs de skip d'un fichier de test."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return []

    skips = []

    # Patterns pour différents types de skip
    patterns = [
        # @pytest.mark.skipif avec condition
        (r'@pytest\.mark\.skipif\((.*?)\s*,\s*reason\s*=\s*["\']([^"\']+)["\']\)', 'skipif'),
        # @pytest.mark.skip avec raison
        (r'@pytest\.mark\.skip\((?:reason\s*=\s*)?["\']([^"\']+)["\']?\)', 'skip'),
        # pytest.skip() dans le code
        (r'pytest\.skip\(["\']([^"\']+)["\']\)', 'runtime_skip'),
        # @pytest.mark.jpype_tweety
        (r'@pytest\.mark\.jpype_tweety\b', 'jpype_tweety'),
        # @pytest.mark.tweety
        (r'@pytest\.mark\.tweety\b', 'tweety'),
        # @pytest.mark.jpype
        (r'@pytest\.mark\.jpype\b', 'jpype'),
        # @pytest.mark.requires_api
        (r'@pytest\.mark\.requires_api\b', 'requires_api'),
        # @pytest.mark.slow
        (r'@pytest\.mark\.slow\b', 'slow'),
    ]

    for pattern, marker_type in patterns:
        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            if marker_type in ['skip', 'skipif']:
                reason = match.group(2) if marker_type == 'skipif' else match.group(1)
                condition = match.group(1) if marker_type == 'skipif' else None
                skips.append({
                    'type': marker_type,
                    'reason': reason,
                    'condition': condition,
                    'line': content[:match.start()].count('\n') + 1
                })
            elif marker_type == 'runtime_skip':
                skips.append({
                    'type': 'runtime_skip',
                    'reason': match.group(1),
                    'line': content[:match.start()].count('\n') + 1
                })
            else:
                skips.append({
                    'type': marker_type,
                    'reason': f'Marker: @{marker_type}',
                    'line': content[:match.start()].count('\n') + 1
                })

    return skips


def categorize_skip(skip_info: dict, file_path: Path) -> str:
    """
    Catégorise un skip selon le protocole Mission 1:
    - INTENTIONNEL: marker légitime (jpype, tweety, requires_api, slow)
    - ENV_DELTA: dû à un delta d'environnement (package manquant, version)
    - BUG: skip par erreur d'import ou condition cassée
    """
    reason_lower = skip_info['reason'].lower()
    marker_type = skip_info['type']
    rel_path = file_path.relative_to(PROJECT_ROOT)

    # INTENTIONNEL - marqueurs connus
    if marker_type in ['jpype_tweety', 'tweety', 'jpype', 'requires_api', 'slow']:
        return 'INTENTIONNEL'

    # INTENTIONNEL - raisons connues
    intentional_keywords = [
        'jvm non disponible', 'jvm non démarrée', 'jpype',
        'oracle non disponible', 'gpt réel', 'openai_api_key',
        'démo', 'setup', 'désactivé',
    ]
    if any(kw in reason_lower for kw in intentional_keywords):
        return 'INTENTIONNEL'

    # ENV_DELTA - package manquant ou version
    env_keywords = [
        'module', 'package', 'import', 'version',
        'installé', 'disponible', 'dependencies',
    ]
    if any(kw in reason_lower for kw in env_keywords):
        return 'ENV_DELTA'

    # BUG - conditions cassées ou erreurs d'import
    bug_keywords = [
        'error', 'exception', 'failed', 'crash',
        'timeout', 'hang', 'freeze',
    ]
    if any(kw in reason_lower for kw in bug_keywords):
        return 'BUG'

    # Par défaut, classer comme ENV_DELTA pour investigation
    return 'ENV_DELTA'


def main():
    print("🔍 Analyse des marqueurs de skip dans les tests...\n")
    print(f"📁 Répertoire: {TESTS_DIR}\n")

    test_files = find_test_files(TESTS_DIR)
    print(f"📝 {len(test_files)} fichiers de test trouvés\n")

    all_skips = []
    category_counts = defaultdict(int)
    file_skips = defaultdict(list)

    for file_path in test_files:
        skips = extract_skip_markers(file_path)
        if skips:
            rel_path = file_path.relative_to(PROJECT_ROOT)
            for skip in skips:
                skip['file'] = str(rel_path)
                category = categorize_skip(skip, file_path)
                skip['category'] = category
                all_skips.append(skip)
                category_counts[category] += 1
                file_skips[str(rel_path)].append(skip)

    # Afficher le résumé par catégorie
    print("=" * 70)
    print("📊 RÉSUMÉ PAR CATÉGORIE")
    print("=" * 70)

    for category in ['INTENTIONNEL', 'ENV_DELTA', 'BUG']:
        count = category_counts[category]
        print(f"\n{category}: {count} skips")

    print(f"\n{'TOTAL':<20} {len(all_skips)} skips identifiés")

    # Afficher les détails par fichier
    print("\n" + "=" * 70)
    print("📋 DÉTAILS PAR FICHIER")
    print("=" * 70)

    for file_path, skips in sorted(file_skips.items()):
        print(f"\n📄 {file_path} ({len(skips)} skip(s))")
        for skip in skips:
            print(f"   Line {skip['line']}: [{skip['category']}] {skip['type']}")
            if skip.get('reason'):
                print(f"      Reason: {skip['reason']}")

    # Générer le tableau pour la Mission 1
    print("\n" + "=" * 70)
    print("📋 TABLEAU POUR MISSION 1 (#94)")
    print("=" * 70)

    print("\n| Test | Catégorie | Raison | Marker |")
    print("|------|-----------|---------|--------|")

    for skip in sorted(all_skips, key=lambda s: (s['file'], s['line'])):
        test_name = f"{skip['file']}:{skip['line']}"
        category = skip['category']
        reason = skip['reason'][:50] + '...' if len(skip.get('reason', '')) > 50 else skip.get('reason', '')
        marker = skip['type']
        print(f"| {test_name:<50} | {category:<10} | {reason:<30} | {marker:<15} |")

    print(f"\n📈 Total: {len(all_skips)} skips analysés")
    print(f"   - INTENTIONNEL: {category_counts['INTENTIONNEL']}")
    print(f"   - ENV_DELTA: {category_counts['ENV_DELTA']}")
    print(f"   - BUG: {category_counts['BUG']}")


if __name__ == '__main__':
    main()
