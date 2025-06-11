#!/usr/bin/env python3
"""
Script de test Phase 2 avec configurations de stabilisation
"""
import subprocess
import sys
import os
from pathlib import Path
import json
import time

def run_stabilized_tests(test_path, group_name):
    """Exécute les tests avec la configuration Phase 2 stabilisée"""
    print(f"\n=== TESTS STABILISÉS: {group_name} ===")
    print(f"Chemin: {test_path}")
    
    # Variables d'environnement pour la stabilisation
    env = os.environ.copy()
    env.update({
        'USE_REAL_JPYPE': 'false',
        'USE_REAL_GPT': 'false', 
        'RUN_OPENAI_TESTS': 'false',
        'RUN_JPYPE_TESTS': 'false',
        'OPENAI_API_KEY': 'sk-fake-phase2-test-key',
        'PYTHONPATH': str(Path.cwd())
    })
    
    try:
        # Utiliser la configuration pytest Phase 2
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            test_path,
            "-c", "pytest_phase2.ini",
            "--tb=line",
            "-q",
            "--maxfail=10"
        ], capture_output=True, text=True, cwd=Path.cwd(), 
           timeout=60, env=env)
        
        print(f"Code retour: {result.returncode}")
        
        # Analyser la sortie
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if stdout:
            print("STDOUT:")
            lines = stdout.split('\n')
            for line in lines[-5:]:  # Dernières 5 lignes
                print(f"  {line}")
        
        if stderr:
            print("STDERR (premières lignes):")
            lines = stderr.split('\n')
            for line in lines[:3]:
                print(f"  {line}")
        
        # Extraction du résumé
        summary_line = ""
        if stdout:
            for line in stdout.split('\n'):
                if any(word in line.lower() for word in ['failed', 'passed', 'error']):
                    summary_line = line
                    break
        
        return {
            "group": group_name,
            "path": test_path,
            "returncode": result.returncode,
            "summary": summary_line,
            "stdout": stdout,
            "stderr": stderr,
            "success": result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT (60s) pour {group_name}")
        return {
            "group": group_name,
            "path": test_path,
            "returncode": -1,
            "summary": "TIMEOUT après 60 secondes",
            "timeout": True,
            "success": False
        }
    except Exception as e:
        print(f"Erreur: {e}")
        return {
            "group": group_name,
            "path": test_path,
            "returncode": -2,
            "summary": f"Erreur: {e}",
            "error": True,
            "success": False
        }

def test_validation_groups():
    """Test des groupes de validation prioritaires"""
    print("PHASE 2 - TESTS STABILISÉS")
    print("===========================")
    
    # Groupes sélectionnés pour validation de la stabilisation
    validation_groups = [
        ("tests/unit/argumentation_analysis/utils/core_utils", "Utils Core"),
        ("tests/unit/project_core/utils", "Project Core Utils"),
        ("tests/unit/mocks", "Mocks"),
        ("tests/unit/argumentation_analysis/test_utils.py", "Utils principal"),
        ("tests/validation_sherlock_watson/test_import.py", "Test import basique"),
        ("tests/validation_sherlock_watson/test_analyse_simple.py", "Analyse simple"),
    ]
    
    results = []
    
    for test_path, group_name in validation_groups:
        if Path(test_path).exists():
            result = run_stabilized_tests(test_path, group_name)
            results.append(result)
            time.sleep(2)  # Pause entre groupes
        else:
            print(f"\nGROUPE IGNORÉ: {group_name} (chemin inexistant)")
    
    # Résumé
    print(f"\n{'='*60}")
    print("RÉSUMÉ DE VALIDATION")
    print(f"{'='*60}")
    
    successes = sum(1 for r in results if r["success"])
    total = len(results)
    
    for result in results:
        status = "OK" if result["success"] else "ECHEC"
        print(f"{status} {result['group']}: {result.get('summary', 'N/A')}")
    
    success_rate = (successes / total * 100) if total > 0 else 0
    print(f"\nTaux de réussite validation: {success_rate:.1f}% ({successes}/{total})")
    
    # Sauvegarde
    os.makedirs("logs", exist_ok=True)
    with open("logs/phase2_stabilized_validation.json", "w", encoding="utf-8") as f:
        json.dump({
            "results": results,
            "summary": {
                "success_rate": success_rate,
                "successes": successes,
                "total": total
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nDétails dans logs/phase2_stabilized_validation.json")
    
    return success_rate >= 70  # Seuil de validation

def main():
    # Vérifier la configuration
    if not Path("pytest_phase2.ini").exists():
        print("ERREUR - Configuration pytest_phase2.ini manquante")
        return False
    
    if not Path("tests/conftest_phase2_stabilization.py").exists():
        print("ERREUR - Configuration conftest Phase 2 manquante")
        return False
        
    print("OK - Configurations Phase 2 detectees")
    
    # Lancer les tests de validation
    validation_success = test_validation_groups()
    
    if validation_success:
        print("\nVALIDATION REUSSIE - Configuration Phase 2 stabilisee")
        print("Prêt pour tests étendus sur l'ensemble des 1850 tests")
    else:
        print("\nVALIDATION PARTIELLE - Ajustements necessaires")
    
    return validation_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)