#!/usr/bin/env python3
"""
Script de correction ciblée des erreurs E128 (continuation line under-indented).
Phase 1E - Mission D-CI-06

Utilise autopep8 pour corriger automatiquement les problèmes d'indentation
sur les lignes de continuation identifiées dans flake8_report.txt.

Fonctionnalités :
- Parsing du rapport flake8 pour identifier les fichiers avec E128
- Application ciblée d'autopep8 --select=E128 sur ces fichiers
- Validation AST après chaque correction
- Logs détaillés des opérations
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Dict, Set


def parse_flake8_report(report_path: Path) -> Set[Path]:
    """
    Parse flake8_report.txt et extrait les fichiers contenant des erreurs E128.

    Args:
        report_path: Chemin vers flake8_report.txt

    Returns:
        Set des chemins de fichiers uniques contenant E128
    """
    files_with_e128: Set[Path] = set()

    if not report_path.exists():
        print(f"❌ ERREUR: {report_path} introuvable", file=sys.stderr)
        return files_with_e128

    print(f"📖 Lecture du rapport: {report_path}")

    with open(report_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or not ':' in line:
                continue

            # Format: ./path/to/file.py:123:1: E128 message
            parts = line.split(':')
            if len(parts) < 4:
                continue

            # Vérifier si c'est une erreur E128
            code_msg = ':'.join(parts[3:]).strip()
            if not code_msg.startswith('E128'):
                continue

            # Extraire et nettoyer le chemin
            filepath_str = parts[0].lstrip('./').lstrip('.\\')
            filepath = Path(filepath_str)

            if filepath.exists():
                files_with_e128.add(filepath)

    return files_with_e128


def validate_ast(filepath: Path) -> bool:
    """
    Valide la syntaxe Python d'un fichier via ast.parse().

    Args:
        filepath: Chemin du fichier à valider

    Returns:
        True si la syntaxe est valide, False sinon
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"  ❌ ERREUR AST: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  ❌ ERREUR lecture: {e}", file=sys.stderr)
        return False


def fix_e128_with_autopep8(filepath: Path) -> bool:
    """
    Applique autopep8 --select=E128 sur un fichier.

    Args:
        filepath: Chemin du fichier à corriger

    Returns:
        True si la correction a réussi, False sinon
    """
    try:
        # Commande autopep8 ciblée sur E128
        cmd = [
            'autopep8',
            '--in-place',           # Modification directe du fichier
            '--select=E128',        # Cibler uniquement E128
            '--aggressive',         # Mode agressif pour corrections complexes
            str(filepath)
        ]

        print(f"  🔧 Exécution: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout:
            print(f"  📝 stdout: {result.stdout}")
        if result.stderr:
            print(f"  ⚠️  stderr: {result.stderr}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"  ❌ ERREUR autopep8: {e}", file=sys.stderr)
        print(f"  stdout: {e.stdout}", file=sys.stderr)
        print(f"  stderr: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("  ❌ ERREUR: autopep8 non installé", file=sys.stderr)
        print("  💡 Installer avec: pip install autopep8", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  ❌ ERREUR inattendue: {e}", file=sys.stderr)
        return False


def main():
    """Point d'entrée principal du script."""
    print("🚀 Fix E128 Indentation Errors - TARGETED MODE Phase 1E")
    print("=" * 70)

    # Chemins
    report_path = Path('flake8_report.txt')

    # Phase 1: Parsing du rapport
    print("\n📊 Phase 1: Analyse du rapport flake8")
    files_with_e128 = parse_flake8_report(report_path)

    if not files_with_e128:
        print("✅ Aucune erreur E128 trouvée dans le rapport")
        return 0

    print(f"🎯 {len(files_with_e128)} fichiers avec erreurs E128:")
    for filepath in sorted(files_with_e128):
        print(f"   - {filepath}")

    # Phase 2: Correction des fichiers
    print("\n🔧 Phase 2: Correction via autopep8")

    fixed_count = 0
    failed_count = 0

    for i, filepath in enumerate(sorted(files_with_e128), 1):
        print(f"\n[{i}/{len(files_with_e128)}] Traitement: {filepath}")

        # Validation AST avant correction
        print("  🔍 Validation AST pré-correction...")
        if not validate_ast(filepath):
            print("  ⚠️  ATTENTION: Syntaxe invalide AVANT correction")
            failed_count += 1
            continue
        print("  ✅ Syntaxe valide avant correction")

        # Application autopep8
        if not fix_e128_with_autopep8(filepath):
            print("  ❌ Échec correction autopep8")
            failed_count += 1
            continue

        # Validation AST après correction
        print("  🔍 Validation AST post-correction...")
        if not validate_ast(filepath):
            print("  ❌ ERREUR: Syntaxe invalide APRÈS correction!")
            failed_count += 1
            continue

        print("  ✅ Correction réussie + validation AST OK")
        fixed_count += 1

    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES CORRECTIONS E128")
    print("=" * 70)
    print(f"✅ Fichiers corrigés avec succès: {fixed_count}")
    print(f"❌ Échecs de correction: {failed_count}")
    print(f"📁 Total traité: {len(files_with_e128)}")

    if fixed_count > 0:
        print("\n✅ Corrections E128 appliquées avec succès!")
        print("💡 Prochaines étapes:")
        print("   1. Vérifier git diff pour valider les changements")
        print("   2. Exécuter: python generate_flake8_report.py")
        print("   3. Commit: git commit -m 'fix(linting): Phase 1E - Fix E128 indentation -X errors'")

    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())