#!/usr/bin/env python3
"""
Analyse par lots pour évaluer l'état actuel des 1850 tests
"""
import subprocess
import sys
import os
from pathlib import Path
import json
import time
import re

def discover_test_files(base_path="tests"):
    """Découvre tous les fichiers de test"""
    test_files = []
    base = Path(base_path)
    
    for file_path in base.rglob("test_*.py"):
        # Ignorer les fichiers temporaires et __pycache__
        if "__pycache__" not in str(file_path) and file_path.stat().st_size > 0:
            test_files.append(str(file_path))
    
    return sorted(test_files)

def run_test_batch(test_files, batch_name, batch_size=5):
    """Exécute un lot de tests limité"""
    print(f"\n=== BATCH: {batch_name} ===")
    print(f"Fichiers: {len(test_files)} (max {batch_size})")
    
    # Limiter la taille du lot
    files_to_test = test_files[:batch_size]
    
    # Environnement optimisé
    env = os.environ.copy()
    env.update({
        'USE_REAL_JPYPE': 'false',
        'USE_REAL_GPT': 'false',
        'RUN_OPENAI_TESTS': 'false',
        'RUN_JPYPE_TESTS': 'false',
        'PYTHONPATH': str(Path.cwd())
    })
    
    try:
        # Exécution avec limites strictes
        result = subprocess.run([
            sys.executable, "-m", "pytest"
        ] + files_to_test + [
            "--tb=no", "-q",
            "--maxfail=5",
            "--timeout=30"
        ], capture_output=True, text=True, timeout=45, env=env)
        
        # Analyse des résultats
        stdout = result.stdout.strip()
        summary_match = re.search(r'(\d+) passed.*?(\d+) failed|(\d+) passed|(\d+) failed', stdout)
        
        passed = 0
        failed = 0
        
        if summary_match:
            groups = summary_match.groups()
            if groups[0] and groups[1]:  # Format "X passed, Y failed"
                passed = int(groups[0])
                failed = int(groups[1])
            elif groups[2]:  # Format "X passed"
                passed = int(groups[2])
            elif groups[3]:  # Format "X failed"
                failed = int(groups[3])
        
        total_tested = passed + failed
        success_rate = (passed / total_tested * 100) if total_tested > 0 else 0
        
        print(f"  Résultats: {passed} réussis, {failed} échoués ({success_rate:.1f}%)")
        
        return {
            "batch": batch_name,
            "files_tested": len(files_to_test),
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "returncode": result.returncode,
            "files": files_to_test
        }
        
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT pour le batch {batch_name}")
        return {
            "batch": batch_name,
            "files_tested": len(files_to_test),
            "passed": 0,
            "failed": len(files_to_test),
            "success_rate": 0,
            "timeout": True,
            "files": files_to_test
        }
    except Exception as e:
        print(f"  Erreur: {e}")
        return {
            "batch": batch_name,
            "files_tested": len(files_to_test),
            "passed": 0,
            "failed": len(files_to_test),
            "success_rate": 0,
            "error": str(e),
            "files": files_to_test
        }

def categorize_tests(test_files):
    """Catégorise les tests par type"""
    categories = {
        "utils_core": [],
        "mocks": [],
        "unit_basic": [],
        "validation_sherlock": [],
        "agents": [],
        "logic_jpype": [],
        "openai_semantic": [],
        "integration": [],
        "ui_playwright": [],
        "other": []
    }
    
    for test_file in test_files:
        file_str = test_file.lower()
        
        if "utils/core" in file_str or "utils\\core" in file_str:
            categories["utils_core"].append(test_file)
        elif "mock" in file_str:
            categories["mocks"].append(test_file)
        elif "unit" in file_str and "basic" in file_str:
            categories["unit_basic"].append(test_file)
        elif "validation_sherlock_watson" in file_str:
            categories["validation_sherlock"].append(test_file)
        elif "agents" in file_str:
            categories["agents"].append(test_file)
        elif any(word in file_str for word in ["logic", "jpype", "tweety"]):
            categories["logic_jpype"].append(test_file)
        elif any(word in file_str for word in ["openai", "semantic", "gpt"]):
            categories["openai_semantic"].append(test_file)
        elif "integration" in file_str:
            categories["integration"].append(test_file)
        elif "ui" in file_str or "playwright" in file_str:
            categories["ui_playwright"].append(test_file)
        else:
            categories["other"].append(test_file)
    
    return categories

def main():
    print("ANALYSE PAR LOTS - PHASE 2")
    print("==========================")
    
    # Découverte des tests
    print("Découverte des fichiers de test...")
    test_files = discover_test_files()
    print(f"Total découvert: {len(test_files)} fichiers")
    
    # Catégorisation
    categories = categorize_tests(test_files)
    
    print("\nCatégories identifiées:")
    for cat_name, files in categories.items():
        if files:
            print(f"  {cat_name}: {len(files)} fichiers")
    
    # Test par catégorie (échantillonnage)
    results = []
    total_passed = 0
    total_failed = 0
    
    for cat_name, files in categories.items():
        if files:
            result = run_test_batch(files, cat_name, batch_size=3)
            results.append(result)
            total_passed += result["passed"]
            total_failed += result["failed"]
            time.sleep(2)  # Pause entre lots
    
    # Résumé global
    total_tests = total_passed + total_failed
    global_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{'='*50}")
    print("RÉSUMÉ GLOBAL - ÉCHANTILLONNAGE")
    print(f"{'='*50}")
    print(f"Tests exécutés: {total_tests}")
    print(f"Réussis: {total_passed}")
    print(f"Échoués: {total_failed}")
    print(f"Taux de réussite: {global_success_rate:.1f}%")
    
    # Estimation pour les 1850 tests
    estimated_success_rate = global_success_rate  # Approximation basée sur l'échantillon
    estimated_passed = int(1850 * estimated_success_rate / 100)
    
    print(f"\nESTIMATION POUR LES 1850 TESTS:")
    print(f"Taux estimé: {estimated_success_rate:.1f}%")
    print(f"Tests réussis estimés: {estimated_passed}/1850")
    
    # Évaluation par rapport à l'objectif
    target_rate = 87.0
    if estimated_success_rate >= target_rate:
        print(f"OBJECTIF ATTEINT: {estimated_success_rate:.1f}% >= {target_rate}%")
    else:
        deficit = target_rate - estimated_success_rate
        print(f"OBJECTIF MANQUÉ: {deficit:.1f} points de pourcentage à gagner")
    
    # Sauvegarde
    os.makedirs("logs", exist_ok=True)
    with open("logs/phase2_batch_analysis.json", "w", encoding="utf-8") as f:
        json.dump({
            "results": results,
            "summary": {
                "total_tested": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "success_rate": global_success_rate,
                "estimated_1850_success_rate": estimated_success_rate,
                "estimated_1850_passed": estimated_passed
            },
            "categories": {k: len(v) for k, v in categories.items()}
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nDétails dans logs/phase2_batch_analysis.json")

if __name__ == "__main__":
    main()