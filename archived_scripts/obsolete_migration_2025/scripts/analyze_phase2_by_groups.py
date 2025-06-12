#!/usr/bin/env python3
"""
Script d'analyse Phase 2 - Tests par groupes pour éviter les timeouts
"""
import subprocess
import sys
import os
from pathlib import Path
import json
import time

def run_test_group(test_path, group_name, max_tests=50):
    """Exécute un groupe de tests spécifique"""
    print(f"\n=== GROUPE: {group_name} ===")
    print(f"Chemin: {test_path}")
    
    try:
        # Exécuter avec limite de tests pour éviter les timeouts
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_path,
            "--tb=no", "-q", 
            f"--maxfail={max_tests}",
            "--timeout=5"  # Timeout de 5 secondes par test
        ], capture_output=True, text=True, cwd=Path.cwd(), timeout=25)
        
        print(f"Code retour: {result.returncode}")
        
        # Analyser la sortie
        stdout_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        stderr_lines = result.stderr.strip().split('\n') if result.stderr.strip() else []
        
        print(f"Lignes stdout: {len(stdout_lines)}")
        if stdout_lines:
            print("Dernières lignes stdout:")
            for line in stdout_lines[-3:]:
                print(f"  {line}")
        
        if stderr_lines:
            print(f"Lignes stderr: {len(stderr_lines)}")
            print("Premières lignes stderr:")
            for line in stderr_lines[:3]:
                print(f"  {line}")
        
        return {
            "group": group_name,
            "path": test_path,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT pour le groupe {group_name}")
        return {
            "group": group_name,
            "path": test_path,
            "returncode": -1,
            "stdout": "",
            "stderr": "TIMEOUT",
            "success": False,
            "timeout": True
        }
    except Exception as e:
        print(f"Erreur: {e}")
        return {
            "group": group_name,
            "path": test_path,
            "returncode": -2,
            "stdout": "",
            "stderr": str(e),
            "success": False,
            "error": True
        }

def main():
    print("PHASE 2 - ANALYSE PAR GROUPES")
    print("==============================")
    
    # Groupes de tests prioritaires identifiés
    test_groups = [
        # Groupes de base - configuration
        ("tests/unit/argumentation_analysis/utils", "Utils de base"),
        ("tests/unit/project_core", "Core du projet"),
        ("tests/unit/mocks", "Mocks"),
        
        # Groupes OpenAI/Semantic Kernel
        ("tests/validation_sherlock_watson", "Validation Sherlock-Watson"),
        ("tests/agents", "Agents"),
        
        # Groupes UI/Playwright  
        ("tests/ui", "Tests UI"),
        ("tests/functional", "Tests fonctionnels"),
        
        # Groupes problématiques identifiés
        ("tests/minimal_jpype_tweety_tests", "JPype minimal"),
        ("tests/integration", "Tests d'intégration"),
    ]
    
    results = []
    
    for test_path, group_name in test_groups:
        if Path(test_path).exists():
            print(f"\n{'='*60}")
            result = run_test_group(test_path, group_name)
            results.append(result)
            time.sleep(1)  # Pause entre les groupes
        else:
            print(f"\nGROUPE IGNORÉ: {group_name} (chemin {test_path} inexistant)")
    
    # Résumé final
    print(f"\n{'='*60}")
    print("RÉSUMÉ FINAL PAR GROUPES")
    print(f"{'='*60}")
    
    successes = 0
    failures = 0
    timeouts = 0
    
    for result in results:
        status = "✅ OK" if result["success"] else "❌ ÉCHEC"
        if result.get("timeout"):
            status = "⏰ TIMEOUT"
            timeouts += 1
        elif result["success"]:
            successes += 1
        else:
            failures += 1
            
        print(f"{status} {result['group']}")
    
    print(f"\nSTATISTIQUES:")
    print(f"- Groupes réussis: {successes}")
    print(f"- Groupes échoués: {failures}")  
    print(f"- Groupes timeout: {timeouts}")
    print(f"- Total testé: {len(results)}")
    
    # Sauvegarde des résultats
    os.makedirs("logs", exist_ok=True)
    with open("logs/phase2_groups_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nRésultats détaillés dans logs/phase2_groups_analysis.json")

if __name__ == "__main__":
    main()