#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigation systématique des tests unitaires - Diagnostic approfondi
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_pydantic_compatibility():
    """Vérifie la compatibilité Pydantic / Semantic Kernel"""
    print("=== DIAGNOSTIC PYDANTIC / SEMANTIC KERNEL ===")
    
    try:
        import pydantic
        print(f"[OK] Pydantic version: {pydantic.__version__}")
        
        # Test spécifique de l'import problématique
        try:
            from pydantic.networks import Url
            print("[OK] pydantic.networks.Url: Disponible")
        except ImportError as e:
            print(f"[CRITICAL] pydantic.networks.Url: ÉCHEC - {e}")
            
        try:
            import semantic_kernel
            print(f"[OK] Semantic Kernel version: {semantic_kernel.__version__}")
        except ImportError as e:
            print(f"[CRITICAL] Semantic Kernel: ÉCHEC - {e}")
            
    except Exception as e:
        print(f"[ERROR] Erreur lors du diagnostic Pydantic: {e}")

def test_jpype_availability():
    """Test de JPype et JVM"""
    print("\n=== DIAGNOSTIC JPYPE / JVM ===")
    
    try:
        import jpype
        print(f"[OK] JPype disponible")
        
        if jpype.isJVMStarted():
            print("[INFO] JVM déjà démarrée")
        else:
            print("[INFO] JVM non démarrée")
            
    except ImportError:
        print("[EXPECTED] JPype non installé (mode mock attendu)")
    except Exception as e:
        print(f"[ERROR] Erreur JPype: {e}")

def run_limited_pytest():
    """Exécute pytest sur des modules limités pour isoler les problèmes"""
    print("\n=== TEST PYTEST LIMITÉ ===")
    
    test_dirs = [
        "tests/utils/",
        "tests/unit/utils/",
        "tests/unit/mocks/",
    ]
    
    results = {}
    
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            print(f"\n--- Test de {test_dir} ---")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", test_dir, 
                    "-v", "--tb=short", "--maxfail=3", "--disable-warnings"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"[OK] {test_dir}: SUCCÈS")
                    results[test_dir] = "SUCCESS"
                else:
                    print(f"[FAIL] {test_dir}: ÉCHEC")
                    results[test_dir] = "FAIL"
                    print(f"Erreur: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"[TIMEOUT] {test_dir}: Timeout")
                results[test_dir] = "TIMEOUT"
            except Exception as e:
                print(f"[ERROR] {test_dir}: Erreur - {e}")
                results[test_dir] = "ERROR"
        else:
            print(f"[SKIP] {test_dir}: Répertoire non trouvé")
            results[test_dir] = "SKIP"
    
    return results

def main():
    """Fonction principale de diagnostic"""
    print("INVESTIGATION SYSTEMATIQUE DES TESTS UNITAIRES")
    print("=" * 60)
    
    # 1. Diagnostic des dépendances critiques
    check_pydantic_compatibility()
    
    # 2. Test JPype
    test_jpype_availability()
    
    # 3. Tests limités
    test_results = run_limited_pytest()
    
    # 4. Résumé
    print("\n=== RÉSUMÉ DU DIAGNOSTIC ===")
    working_tests = sum(1 for result in test_results.values() if result == "SUCCESS")
    total_tests = len(test_results)
    
    print(f"Tests réussis: {working_tests}/{total_tests}")
    
    for test_dir, result in test_results.items():
        status_icon = {
            "SUCCESS": "[OK]",
            "FAIL": "[FAIL]",
            "TIMEOUT": "[TIMEOUT]",
            "ERROR": "[ERROR]",
            "SKIP": "[SKIP]"
        }.get(result, "[UNKNOWN]")
        print(f"  {status_icon} {test_dir}: {result}")
    
    print("\n=== PROBLÈMES IDENTIFIÉS ===")
    print("1. Incompatibilité Pydantic/Semantic Kernel (pydantic.networks.Url)")
    print("2. JPype manquant (normal en mode développement)")
    print("3. Nécessité d'isoler les tests par dépendances")
    
    return working_tests > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)