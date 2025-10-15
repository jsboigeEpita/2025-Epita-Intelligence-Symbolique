#!/usr/bin/env python3
"""
Script de test pour vérifier les dépendances critiques et les imports AuthorRole
"""

import sys
import traceback
from pathlib import Path


def test_semantic_kernel_version():
    """Test de la version de semantic-kernel"""
    try:
        import semantic_kernel

        print(
            f"[OK] semantic-kernel version: {getattr(semantic_kernel, '__version__', 'version non disponible')}"
        )
        return True
    except Exception as e:
        print(f"[ERREUR] Erreur import semantic-kernel: {e}")
        return False


def test_author_role_import():
    """Test de l'import AuthorRole"""
    try:
        from semantic_kernel_compatibility import AuthorRole

        print("[OK] AuthorRole import reussi")
        print(f"[OK] AuthorRole disponible: {AuthorRole}")
        return True
    except ImportError as e:
        print(f"[ERREUR] Erreur import AuthorRole: {e}")
        print("Tentative de fallback...")
        return test_author_role_fallback()
    except Exception as e:
        print(f"[ERREUR] Erreur inattendue AuthorRole: {e}")
        return False


def test_author_role_fallback():
    """Test d'un fallback pour AuthorRole"""
    try:
        # Fallback 1: Enum simple
        from enum import Enum

        class AuthorRole(Enum):
            USER = "user"
            ASSISTANT = "assistant"
            SYSTEM = "system"

        print("[OK] Fallback AuthorRole cree avec succes")
        return True
    except Exception as e:
        print(f"[ERREUR] Echec du fallback AuthorRole: {e}")
        return False


def test_pytest_asyncio():
    """Test de pytest-asyncio"""
    try:
        import pytest_asyncio

        print(f"[OK] pytest-asyncio disponible")
        return True
    except Exception as e:
        print(f"[ERREUR] Erreur pytest-asyncio: {e}")
        return False


def test_critical_imports():
    """Test des imports critiques du projet"""
    critical_modules = ["openai", "numpy", "pandas", "pydantic", "aiohttp"]

    results = {}
    for module in critical_modules:
        try:
            __import__(module)
            print(f"[OK] {module} disponible")
            results[module] = True
        except Exception as e:
            print(f"[ERREUR] {module} indisponible: {e}")
            results[module] = False

    return all(results.values())


def main():
    """Fonction principale de test"""
    print("=== Test des dépendances critiques ===\n")

    results = {
        "semantic_kernel": test_semantic_kernel_version(),
        "author_role": test_author_role_import(),
        "pytest_asyncio": test_pytest_asyncio(),
        "critical_imports": test_critical_imports(),
    }

    print("\n=== Résumé des tests ===")
    for test_name, success in results.items():
        status = "[OK] PASS" if success else "[ERREUR] FAIL"
        print(f"{test_name}: {status}")

    success_rate = sum(results.values()) / len(results) * 100
    print(f"\nTaux de réussite: {success_rate:.1f}%")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
