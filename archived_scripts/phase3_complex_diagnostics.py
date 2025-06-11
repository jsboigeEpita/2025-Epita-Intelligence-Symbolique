#!/usr/bin/env python3
"""
PHASE 3 - Diagnostic des problèmes complexes
Identification ciblée des échecs dans les 4 domaines critiques
"""
import subprocess
import sys
import os
from pathlib import Path
import json
import time
import re
from datetime import datetime

def setup_environment():
    """Configuration environnement pour tests complexes"""
    env = os.environ.copy()
    env.update({
        'PYTHONPATH': str(Path.cwd()),
        'USE_REAL_JPYPE': 'false',
        'USE_REAL_GPT': 'false', 
        'RUN_OPENAI_TESTS': 'false',
        'RUN_JPYPE_TESTS': 'true',  # Activer pour diagnostic JVM
        'OPENAI_API_KEY': 'sk-fake-test-key-phase3'
    })
    return env

def test_single_file(test_file, timeout=45):
    """Test un fichier spécifique avec diagnostic détaillé"""
    env = setup_environment()
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_file,
            "-v", "--tb=short", "--no-header",
            f"--timeout={timeout}",
            "-x"  # Arrêter au premier échec
        ], capture_output=True, text=True, timeout=timeout+10, env=env)
        
        # Analyse des erreurs
        stderr = result.stderr
        stdout = result.stdout
        
        error_patterns = {
            'jpype_jvm': [
                'jpype', 'JVM', 'java', 'tweety', 'StartJVM', 'shutdownJVM'
            ],
            'oracle_cluedo': [
                'CluedoOracleState', 'DatasetAccessManager', 'RevealPolicy', 'QueryResult'
            ],
            'agents_sherlock': [
                'SherlockEnqueteAgent', 'WatsonLogicAssistant', 'agent_communication'
            ],
            'orchestration': [
                'TacticalResolver', 'OperationalAdapter', 'HierarchicalState'
            ],
            'imports': [
                'ModuleNotFoundError', 'ImportError', 'No module named'
            ],
            'async_issues': [
                'async', 'await', 'asyncio', 'coroutine', 'event loop'
            ],
            'timeout': [
                'timeout', 'TimeoutError', 'timed out'
            ]
        }
        
        detected_issues = {}
        full_output = f"{stdout}\n{stderr}"
        
        for category, patterns in error_patterns.items():
            if any(pattern.lower() in full_output.lower() for pattern in patterns):
                detected_issues[category] = True
        
        return {
            'file': test_file,
            'returncode': result.returncode,
            'passed': result.returncode == 0,
            'output': full_output,
            'issues': detected_issues,
            'stdout': stdout,
            'stderr': stderr
        }
        
    except subprocess.TimeoutExpired:
        return {
            'file': test_file,
            'returncode': -1,
            'passed': False,
            'timeout': True,
            'issues': {'timeout': True}
        }
    except Exception as e:
        return {
            'file': test_file,
            'returncode': -1,
            'passed': False,
            'error': str(e),
            'issues': {'execution_error': True}
        }

def analyze_complex_domains():
    """Analyse ciblée des domaines complexes"""
    
    # Tests représentatifs par domaine
    target_tests = {
        'jpype_jvm': [
            'tests/unit/argumentation_analysis/utils/dev_tools/test_mock_utils.py',
        ],
        'oracle_cluedo': [
            'tests/unit/argumentation_analysis/core/test_cluedo_oracle_state.py',
            'tests/validation_sherlock_watson/test_final_oracle_100_percent.py'
        ],
        'agents_sherlock': [
            'tests/validation_sherlock_watson/test_phase_d_trace_ideale.py',
            'tests/validation_sherlock_watson/test_analyse_simple.py'
        ],
        'orchestration': [
            'tests/unit/orchestration/hierarchical/tactical/test_tactical_resolver.py',
            'tests/unit/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py'
        ]
    }
    
    results = {}
    
    print("PHASE 3 - DIAGNOSTIC COMPLEXE")
    print("=" * 50)
    
    for domain, test_files in target_tests.items():
        print(f"\n[DIAGNOSTIC] Domaine: {domain}")
        print("-" * 30)
        
        domain_results = []
        
        for test_file in test_files:
            test_path = Path(test_file)
            if test_path.exists():
                print(f"  Testing: {test_file}")
                result = test_single_file(test_file)
                domain_results.append(result)
                
                status = "[PASS]" if result['passed'] else "[FAIL]"
                print(f"    {status}")
                
                if not result['passed'] and 'issues' in result:
                    issues = ", ".join(result['issues'].keys())
                    print(f"    Issues: {issues}")
                    
                time.sleep(1)  # Pause entre tests
            else:
                print(f"  [WARNING] Fichier manquant: {test_file}")
        
        results[domain] = domain_results
    
    return results

def generate_complex_analysis_report(results):
    """Génère un rapport d'analyse des problèmes complexes"""
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'phase': 'Phase 3 - Complex Diagnostics',
        'domains_analyzed': list(results.keys()),
        'summary': {},
        'detailed_results': results,
        'recommendations': []
    }
    
    # Analyse par domaine
    for domain, domain_results in results.items():
        total_tests = len(domain_results)
        passed_tests = sum(1 for r in domain_results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        # Collecte des problèmes
        all_issues = {}
        for result in domain_results:
            if 'issues' in result:
                for issue in result['issues']:
                    all_issues[issue] = all_issues.get(issue, 0) + 1
        
        report['summary'][domain] = {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'common_issues': all_issues
        }
    
    # Recommandations par domaine
    for domain, summary in report['summary'].items():
        if summary['success_rate'] < 90:
            issues = summary['common_issues']
            
            if 'jpype_jvm' in issues:
                report['recommendations'].append({
                    'domain': domain,
                    'priority': 'HIGH',
                    'issue': 'JPype/JVM integration',
                    'action': 'Improve JVM lifecycle management and memory isolation'
                })
            
            if 'oracle_cluedo' in issues:
                report['recommendations'].append({
                    'domain': domain,
                    'priority': 'HIGH',
                    'issue': 'Oracle/Cluedo architecture',
                    'action': 'Stabilize mock dependencies and state management'
                })
            
            if 'agents_sherlock' in issues:
                report['recommendations'].append({
                    'domain': domain,
                    'priority': 'MEDIUM',
                    'issue': 'Agent state corruption',
                    'action': 'Enhance agent isolation and communication protocols'
                })
            
            if 'orchestration' in issues:
                report['recommendations'].append({
                    'domain': domain,
                    'priority': 'MEDIUM',
                    'issue': 'Hierarchical orchestration',
                    'action': 'Optimize timeout handling and state sharing'
                })
    
    return report

def main():
    """Exécution principale du diagnostic Phase 3"""
    print("Démarrage du diagnostic complexe Phase 3...")
    
    # Diagnostic par domaine
    results = analyze_complex_domains()
    
    # Génération du rapport
    from datetime import datetime
    report = generate_complex_analysis_report(results)
    
    # Affichage du résumé
    print(f"\n{'='*50}")
    print("RÉSUMÉ DIAGNOSTIC COMPLEXE")
    print(f"{'='*50}")
    
    total_success_rates = []
    for domain, summary in report['summary'].items():
        rate = summary['success_rate']
        total_success_rates.append(rate)
        status = "[OK]" if rate >= 90 else "[WARN]" if rate >= 70 else "[FAIL]"
        print(f"{status} {domain}: {rate:.1f}% ({summary['passed']}/{summary['total_tests']})")
    
    # Taux global estimé
    if total_success_rates:
        global_rate = sum(total_success_rates) / len(total_success_rates)
        print(f"\nTaux de réussite complexe estimé: {global_rate:.1f}%")
        
        # Estimation pour Phase 3
        if global_rate >= 85:
            print("[TARGET] Pret pour corrections ciblees Phase 3")
        else:
            print("[WARNING] Problemes fondamentaux a resoudre en priorite")
    
    # Recommandations prioritaires
    high_priority = [r for r in report['recommendations'] if r['priority'] == 'HIGH']
    if high_priority:
        print(f"\n[URGENT] ACTIONS PRIORITAIRES:")
        for rec in high_priority:
            print(f"  - {rec['domain']}: {rec['action']}")
    
    # Sauvegarde
    os.makedirs("logs", exist_ok=True)
    with open("logs/phase3_complex_diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n[REPORT] Rapport detaille: logs/phase3_complex_diagnostics.json")
    
    return report

if __name__ == "__main__":
    main()