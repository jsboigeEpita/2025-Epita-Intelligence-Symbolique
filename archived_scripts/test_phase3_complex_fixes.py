#!/usr/bin/env python3
"""
PHASE 3 - Test des corrections complexes
Validation que les problèmes JPype/Oracle/Cluedo/Agents sont résolus
"""
import subprocess
import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime

def setup_phase3_environment():
    """Configuration environnement Phase 3"""
    env = os.environ.copy()
    env.update({
        'PYTHONPATH': str(Path.cwd()),
        'USE_REAL_JPYPE': 'false',
        'USE_REAL_GPT': 'false',
        'JPYPE_JVM': 'false',
        'DISABLE_JVM': 'true',
        'RUN_OPENAI_TESTS': 'false',
        'RUN_JPYPE_TESTS': 'true',  # Activer avec mocks forcés
        'OPENAI_API_KEY': 'sk-fake-phase3-key',
        'PHASE3_COMPLEX_MODE': 'true'
    })
    return env

def test_complex_targets_phase3():
    """Test les cibles complexes identifiées en Phase 3"""
    
    # Tests représentatifs par domaine problématique
    complex_test_targets = {
        'jpype_jvm': [
            'tests/unit/argumentation_analysis/utils/dev_tools/test_mock_utils.py',
        ],
        'oracle_cluedo': [
            'tests/unit/argumentation_analysis/core/test_cluedo_oracle_state.py',
        ],
        'agents_sherlock': [
            'tests/validation_sherlock_watson/test_analyse_simple.py',
        ],
        'orchestration': [
            'tests/unit/orchestration/hierarchical/tactical/test_tactical_resolver.py',
        ]
    }
    
    env = setup_phase3_environment()
    results = {}
    
    print("PHASE 3 - VALIDATION CORRECTIONS COMPLEXES")
    print("=" * 50)
    
    total_passed = 0
    total_failed = 0
    
    for domain, test_files in complex_test_targets.items():
        print(f"\n[TEST] Domaine: {domain}")
        print("-" * 30)
        
        domain_passed = 0
        domain_failed = 0
        
        for test_file in test_files:
            test_path = Path(test_file)
            if test_path.exists():
                print(f"  Testing: {test_file}")
                
                try:
                    # Exécution avec configuration Phase 3
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", test_file,
                        "-c", "pytest_phase3.ini",  # Configuration Phase 3
                        "--confcutdir=tests",  # Utiliser conftest_phase3_complex.py
                        "-v", "--tb=no", "--no-header",
                        "--timeout=5",  # Timeout agressif
                        "-x"  # Arrêter au premier échec
                    ], capture_output=True, text=True, timeout=15, env=env)
                    
                    success = result.returncode == 0
                    if success:
                        domain_passed += 1
                        print("    [PASS] Corrections Phase 3 efficaces")
                    else:
                        domain_failed += 1
                        print("    [FAIL] Problème subsiste")
                        
                        # Analyse rapide de l'erreur
                        output = f"{result.stdout}\n{result.stderr}"
                        if 'jpype' in output.lower() or 'jvm' in output.lower():
                            print("      Issue: JPype/JVM non résolu")
                        elif 'timeout' in output.lower():
                            print("      Issue: Timeout persistant")
                        elif 'import' in output.lower():
                            print("      Issue: Import/Mock")
                        else:
                            print("      Issue: Autre")
                            
                except subprocess.TimeoutExpired:
                    domain_failed += 1
                    print("    [TIMEOUT] Configuration Phase 3 insuffisante")
                except Exception as e:
                    domain_failed += 1
                    print(f"    [ERROR] {e}")
                
                time.sleep(1)
            else:
                print(f"  [SKIP] Fichier manquant: {test_file}")
        
        total_passed += domain_passed
        total_failed += domain_failed
        
        domain_total = domain_passed + domain_failed
        domain_rate = (domain_passed / domain_total * 100) if domain_total > 0 else 0
        
        results[domain] = {
            'passed': domain_passed,
            'failed': domain_failed,
            'total': domain_total,
            'success_rate': domain_rate
        }
        
        status = "[OK]" if domain_rate >= 80 else "[WARN]" if domain_rate >= 50 else "[FAIL]"
        print(f"  {status} {domain}: {domain_rate:.1f}% ({domain_passed}/{domain_total})")
    
    # Résumé global
    total_tests = total_passed + total_failed
    global_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{'='*50}")
    print("RÉSUMÉ CORRECTIONS PHASE 3")
    print(f"{'='*50}")
    print(f"Tests complexes validés: {total_tests}")
    print(f"Réussis: {total_passed}")
    print(f"Échoués: {total_failed}")
    print(f"Taux de réussite: {global_success_rate:.1f}%")
    
    # Estimation d'amélioration
    baseline_rate = 85.0  # Taux Phase 2
    if global_success_rate >= 80:
        improvement_estimate = (global_success_rate - baseline_rate) * 0.1  # 10% des tests sont complexes
        new_estimate = baseline_rate + improvement_estimate
        print(f"\nEstimation nouvelle performance globale: {new_estimate:.1f}%")
        
        if new_estimate >= 92:
            print("[SUCCESS] Objectif Phase 3 ATTEINT (92%)")
        else:
            remaining = 92 - new_estimate
            print(f"[PROGRESS] Progression vers 92%, reste {remaining:.1f} points")
    else:
        print(f"\n[ISSUE] Corrections Phase 3 insuffisantes")
        print("Actions requises:")
        for domain, result in results.items():
            if result['success_rate'] < 80:
                print(f"  - Approfondir corrections {domain}")
    
    return {
        'timestamp': datetime.now().isoformat(),
        'phase': 'Phase 3 Complex Fixes Validation',
        'total_tests': total_tests,
        'total_passed': total_passed,
        'total_failed': total_failed,
        'success_rate': global_success_rate,
        'domain_results': results
    }

def validate_phase3_infrastructure():
    """Valide que l'infrastructure Phase 3 est opérationnelle"""
    
    print("\n[VALIDATION] Infrastructure Phase 3")
    print("-" * 40)
    
    # Vérifier les fichiers clés
    key_files = [
        'tests/conftest_phase3_complex.py',
        'pytest_phase3.ini'
    ]
    
    for file_path in key_files:
        if Path(file_path).exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [MISS] {file_path}")
            return False
    
    # Test de l'isolation JPype
    env = setup_phase3_environment()
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; sys.path.insert(0, '.'); "
            "from tests.conftest_phase3_complex import phase3_jpype_advanced_isolation; "
            "print('JPype isolation OK')"
        ], capture_output=True, text=True, timeout=10, env=env)
        
        if result.returncode == 0:
            print("  [OK] JPype isolation Phase 3")
        else:
            print(f"  [FAIL] JPype isolation: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] JPype isolation: {e}")
        return False
    
    print("  [OK] Infrastructure Phase 3 opérationnelle")
    return True

def main():
    """Exécution principale de la validation Phase 3"""
    
    print("DÉBUT VALIDATION PHASE 3 - CORRECTIONS COMPLEXES")
    print("=" * 60)
    
    # Validation infrastructure
    if not validate_phase3_infrastructure():
        print("\n[ABORT] Infrastructure Phase 3 défaillante")
        return False
    
    # Tests des corrections
    results = test_complex_targets_phase3()
    
    # Sauvegarde
    os.makedirs("logs", exist_ok=True)
    with open("logs/phase3_complex_validation.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[REPORT] Détails: logs/phase3_complex_validation.json")
    
    # Statut final
    success_rate = results.get('success_rate', 0)
    if success_rate >= 80:
        print(f"\n[SUCCESS] Phase 3 validée - Corrections efficaces ({success_rate:.1f}%)")
        return True
    else:
        print(f"\n[ISSUE] Phase 3 nécessite corrections supplémentaires ({success_rate:.1f}%)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)