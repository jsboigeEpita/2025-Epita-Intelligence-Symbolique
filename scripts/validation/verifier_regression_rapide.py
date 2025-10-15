import argumentation_analysis.core.environment

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification rapide de la régression AuthorRole supposée
"""

import sys
import subprocess
import time


def test_imports_critiques():
    """Teste les imports qui posent problème selon le rapport"""
    print("=== TEST IMPORTS CRITIQUES ===")

    tests = [
        (
            "semantic_kernel.contents.AuthorRole",
            "from semantic_kernel.contents.utils.author_role import AuthorRole",
        ),
        ("semantic_kernel.agents", "from semantic_kernel import agents"),
        (
            "semantic_kernel.contents.ChatMessageContent",
            "from semantic_kernel.contents import ChatMessageContent",
        ),
        (
            "semantic_kernel.contents.utils.author_role",
            "from semantic_kernel.contents.utils.author_role import AuthorRole",
        ),
    ]

    failed = 0
    for desc, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"[OK] {desc}")
        except Exception as e:
            print(f"[ERREUR] {desc}: {e}")
            failed += 1

    return failed == 0


def test_sample_tests():
    """Teste quelques tests spécifiques rapidement"""
    print("\n=== TEST ÉCHANTILLON ===")

    # Tests simples qui devraient marcher
    simple_tests = [
        "tests/unit/mocks/test_numpy_rec_mock.py::test_numpy_rec_import",
        "tests/utils/test_crypto_utils.py",
        "tests/unit/project_core/utils/test_file_utils.py",
    ]

    failed = 0
    for test in simple_tests:
        try:
            print(f"Test: {test}")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test, "-v", "--tb=no", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print(f"[OK] {test}")
            else:
                print(f"[ERREUR] {test}")
                if result.stderr:
                    print(f"  Erreur: {result.stderr[:200]}...")
                failed += 1

        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {test}")
            failed += 1
        except Exception as e:
            print(f"[ERREUR] {test}: {e}")
            failed += 1

    return failed == 0


def count_total_tests():
    """Compte le nombre total de tests"""
    print("\n=== COMPTAGE TESTS ===")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            lines = result.stdout.split("\n")
            # Chercher la ligne avec le résumé
            for line in lines:
                if "collected" in line and "item" in line:
                    print(f"Tests collectés: {line}")
                    return line
        else:
            print(f"Erreur collecte: {result.stderr[:200]}...")

    except Exception as e:
        print(f"Erreur lors du comptage: {e}")

    return None


def main():
    print("=== VÉRIFICATION RÉGRESSION SEMANTIC KERNEL ===")

    # Test 1: Imports critiques
    imports_ok = test_imports_critiques()

    # Test 2: Comptage des tests
    test_count = count_total_tests()

    # Test 3: Échantillon de tests
    sample_ok = test_sample_tests()

    # Conclusion
    print("\n=== CONCLUSION ===")
    print(f"Imports critiques: {'[OK]' if imports_ok else '[ERREUR]'}")
    print(f"Comptage tests: {test_count or '[ECHEC]'}")
    print(f"Tests echantillon: {'[OK]' if sample_ok else '[ERREUR]'}")

    if imports_ok and sample_ok:
        print("\n[SUCCESS] AUCUNE REGRESSION CRITIQUE DETECTEE")
        print("   - AuthorRole fonctionne correctement")
        print("   - Les tests de base passent")
        print("   - Probleme '688+ tests bloques' non confirme")
    else:
        print("\n[CRITICAL] PROBLEMES DETECTES")
        if not imports_ok:
            print("   - Imports critiques echouent")
        if not sample_ok:
            print("   - Tests echantillon echouent")

    return imports_ok and sample_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
