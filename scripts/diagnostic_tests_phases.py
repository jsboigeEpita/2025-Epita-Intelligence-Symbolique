#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic des tests par phases selon les configurations pytest
"""

import sys
import subprocess
from pathlib import Path

def test_with_config(config_file, test_path, max_failures=5):
    """Test avec une configuration pytest spécifique"""
    print(f"\n--- Test avec {config_file} sur {test_path} ---")
    
    if not Path(config_file).exists():
        print(f"[SKIP] Configuration {config_file} non trouvée")
        return "SKIP"
    
    if not Path(test_path).exists():
        print(f"[SKIP] Chemin de test {test_path} non trouvé")
        return "SKIP"
    
    try:
        cmd = [
            sys.executable, "-m", "pytest", 
            "-c", config_file,
            test_path,
            "-v", "--tb=short", 
            f"--maxfail={max_failures}",
            "--disable-warnings"
        ]
        
        print(f"Commande: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            print(f"[OK] SUCCÈS - tous les tests passent")
            return "SUCCESS"
        else:
            print(f"[FAIL] ÉCHEC - code de retour: {result.returncode}")
            # Afficher un résumé des erreurs
            lines = result.stdout.split('\n')
            for line in lines[-20:]:  # Dernières 20 lignes
                if 'ERROR' in line or 'FAILED' in line or 'collected' in line:
                    print(f"  {line}")
            return "FAIL"
            
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Dépassement de temps (120s)")
        return "TIMEOUT"
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'exécution: {e}")
        return "ERROR"

def test_specific_directories():
    """Test de répertoires spécifiques sans configurations"""
    print("\n=== TESTS DIRECTS SANS CONFIGURATION ===")
    
    test_dirs = [
        "tests/unit/argumentation_analysis/utils/",
        "tests/unit/config/",
        "tests/unit/project_core/",
        "tests/unit/orchestration/",
        "tests/validation_sherlock_watson/test_import.py",
        "tests/validation_sherlock_watson/test_analyse_simple.py"
    ]
    
    results = {}
    
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            print(f"\n--- Test direct de {test_dir} ---")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", test_dir,
                    "-v", "--tb=short", "--maxfail=2", "--disable-warnings"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"[OK] {test_dir}: SUCCÈS")
                    results[test_dir] = "SUCCESS"
                else:
                    print(f"[FAIL] {test_dir}: ÉCHEC")
                    results[test_dir] = "FAIL"
                    # Montrer l'erreur principale
                    if "ImportError" in result.stdout:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if "ImportError" in line:
                                print(f"  -> {line}")
                                break
                    
            except subprocess.TimeoutExpired:
                print(f"[TIMEOUT] {test_dir}")
                results[test_dir] = "TIMEOUT"
            except Exception as e:
                print(f"[ERROR] {test_dir}: {e}")
                results[test_dir] = "ERROR"
        else:
            print(f"[SKIP] {test_dir}: Non trouvé")
            results[test_dir] = "SKIP"
    
    return results

def main():
    """Fonction principale"""
    print("DIAGNOSTIC DES TESTS PAR PHASES")
    print("=" * 50)
    
    # Tests par configuration
    phase_configs = [
        ("pytest_phase2.ini", "tests/unit/"),
        ("pytest_phase3.ini", "tests/unit/"),
        ("pytest_phase4_final.ini", "tests/unit/")
    ]
    
    config_results = {}
    for config, test_path in phase_configs:
        result = test_with_config(config, test_path, max_failures=3)
        config_results[f"{config}:{test_path}"] = result
    
    # Tests directs
    direct_results = test_specific_directories()
    
    # Résumé global
    print("\n=== RÉSUMÉ GLOBAL ===")
    print("\nTests avec configurations:")
    for test_config, result in config_results.items():
        print(f"  [{result}] {test_config}")
    
    print("\nTests directs:")
    for test_dir, result in direct_results.items():
        print(f"  [{result}] {test_dir}")
    
    # Calcul du taux de succès
    all_results = list(config_results.values()) + list(direct_results.values())
    success_count = sum(1 for r in all_results if r == "SUCCESS")
    total_count = len(all_results)
    
    print(f"\nTaux de succès global: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    print("\n=== PROBLÈMES IDENTIFIÉS ===")
    print("- Conflits entre semantic_kernel.agents et pydantic lors de l'import")
    print("- Tests dépendants des agents Sherlock/Watson bloqués")
    print("- JPype nécessaire pour certains tests avancés")
    
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)