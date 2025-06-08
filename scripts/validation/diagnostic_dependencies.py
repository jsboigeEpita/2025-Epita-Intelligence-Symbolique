#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic des dépendances critiques
"""

import sys
import importlib

def check_dependency(module_name, extra_info=None):
    """Vérifie si un module peut être importé"""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'Version inconnue')
        print(f"[OK] {module_name}: {version}")
        if extra_info:
            extra_info(module)
        return True
    except ImportError as e:
        print(f"[FAIL] {module_name}: ECHEC - {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {module_name}: ERREUR - {e}")
        return False

def check_semantic_kernel_agents(sk_module):
    """Vérifie les agents semantic kernel"""
    try:
        from semantic_kernel.agents import AuthorRole
        print("  - AuthorRole: [OK] Disponible")
    except ImportError:
        print("  - AuthorRole: [FAIL] Non disponible")

def check_pydantic_url(pydantic_module):
    """Vérifie l'import Url depuis pydantic"""
    try:
        from pydantic.networks import Url
        print("  - pydantic.networks.Url: [OK] Disponible")
    except ImportError as e:
        print(f"  - pydantic.networks.Url: [FAIL] ECHEC - {e}")

def main():
    print("=== DIAGNOSTIC DES DÉPENDANCES CRITIQUES ===")
    print(f"Python: {sys.version}")
    print()
    
    # Dépendances critiques
    dependencies = [
        ("semantic_kernel", check_semantic_kernel_agents),
        ("pydantic", check_pydantic_url),
        ("jpype1", None),
        ("pytest", None),
        ("pytest_asyncio", None),
        ("numpy", None),
        ("pandas", None),
    ]
    
    print("--- Vérification des modules ---")
    working = 0
    total = len(dependencies)
    
    for module_name, extra_check in dependencies:
        if check_dependency(module_name, extra_check):
            working += 1
    
    print()
    print("--- Résumé ---")
    print(f"Modules fonctionnels: {working}/{total}")
    print(f"Taux de réussite: {working/total*100:.1f}%")
    
    if working == total:
        print("[SUCCESS] Toutes les dependances sont operationnelles!")
    else:
        print("[WARNING] Certaines dependances necessitent une attention.")

if __name__ == "__main__":
    main()