#!/usr/bin/env python3
"""
Script pour exécuter les tests de la Phase 2 et analyser les résultats
"""
import subprocess
import sys
import os
from pathlib import Path
import json
import re

def run_pytest_summary():
    """Exécute pytest avec un résumé compact"""
    print("=== EXÉCUTION PYTEST - RÉSUMÉ COMPACT ===")
    
    try:
        # Exécuter pytest avec résumé minimal
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--tb=no", "-q", "--maxfail=50"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nCode de retour: {result.returncode}")
        
        return result
        
    except Exception as e:
        print(f"Erreur lors de l'exécution de pytest: {e}")
        return None

def analyze_test_counts(output):
    """Analyse la sortie pour extraire les compteurs de tests"""
    print("\n=== ANALYSE DES COMPTEURS ===")
    
    # Recherche des patterns de résultats
    patterns = [
        r"(\d+) failed",
        r"(\d+) passed", 
        r"(\d+) error",
        r"(\d+) skipped",
        r"(\d+) warnings",
    ]
    
    results = {}
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            count = int(match.group(1))
            test_type = pattern.replace(r"(\d+) ", "").replace("failed", "échecs").replace("passed", "réussis").replace("error", "erreurs").replace("skipped", "ignorés").replace("warnings", "avertissements")
            results[test_type] = count
            print(f"- {test_type}: {count}")
    
    return results

def run_focused_test_discovery():
    """Découvre le nombre total de tests"""
    print("\n=== DÉCOUVERTE DES TESTS ===")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--collect-only", "-q"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        lines = result.stdout.split('\n')
        test_count = 0
        for line in lines:
            if "test session starts" in line.lower():
                continue
            if line.strip() and not line.startswith('=') and not line.startswith('<'):
                test_count += 1
        
        print(f"Nombre total de tests découverts: {test_count}")
        return test_count
        
    except Exception as e:
        print(f"Erreur lors de la découverte: {e}")
        return 0

def main():
    print("PHASE 2 - STABILISATION MOYENNE")
    print("================================")
    
    # Vérifier l'environnement
    print(f"Répertoire de travail: {Path.cwd()}")
    print(f"Python: {sys.executable}")
    
    # Découverte des tests
    total_tests = run_focused_test_discovery()
    
    # Exécution avec résumé
    result = run_pytest_summary()
    
    if result:
        # Analyse des résultats
        output = result.stdout + result.stderr
        counts = analyze_test_counts(output)
        
        # Calcul du pourcentage de réussite
        if "réussis" in counts and total_tests > 0:
            success_rate = (counts["réussis"] / total_tests) * 100
            print(f"\n=== RÉSUMÉ FINAL ===")
            print(f"Tests découverts: {total_tests}")
            print(f"Tests réussis: {counts.get('réussis', 0)}")
            print(f"Tests échoués: {counts.get('échecs', 0)}")
            print(f"Taux de réussite: {success_rate:.1f}%")
        
        # Sauvegarde des résultats
        results_data = {
            "total_tests": total_tests,
            "counts": counts,
            "success_rate": success_rate if "réussis" in counts else 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        
        os.makedirs("logs", exist_ok=True)
        with open("logs/phase2_initial_results.json", "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nRésultats sauvegardés dans logs/phase2_initial_results.json")

if __name__ == "__main__":
    main()