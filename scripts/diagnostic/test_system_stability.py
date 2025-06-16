import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
"""Test de stabilité du système récupéré sur 3 exécutions"""

import time
import traceback

def test_core_modules():
    """Test des modules core disponibles"""
    try:
        from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
        
        # Instantiation des modules core
        fol_agent = FOLLogicAgent()
        llm_orch = RealLLMOrchestrator()
        
        return {
            'success': True,
            'fol_agent_type': str(type(fol_agent)),
            'llm_orch_type': str(type(llm_orch))
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def main():
    print('=== TEST STABILITÉ SYSTÈME RÉCUPÉRÉ ===')
    results = []
    
    for i in range(3):
        print(f'\n[{i+1}/3] Exécution de test...')
        start_time = time.time()
        
        result = test_core_modules()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        result['execution_time'] = execution_time
        result['iteration'] = i + 1
        results.append(result)
        
        if result['success']:
            print(f'✅ Exécution {i+1}/3: {execution_time:.3f}s')
        else:
            print(f'❌ Échec exécution {i+1}/3: {result["error"]}')
    
    # Analyse des résultats
    print('\n=== ANALYSE STABILITÉ ===')
    successes = sum(1 for r in results if r['success'])
    success_rate = (successes / 3) * 100
    
    if successes > 0:
        avg_time = sum(r['execution_time'] for r in results if r['success']) / successes
        print(f'✅ Taux de succès: {success_rate:.1f}% ({successes}/3)')
        print(f'⏱️ Temps moyen d\'exécution: {avg_time:.3f}s')
    else:
        print(f'❌ Taux de succès: {success_rate:.1f}% ({successes}/3)')
    
    print('=== FIN TEST STABILITÉ ===')
    return success_rate >= 66.7  # Au moins 2/3 de succès

if __name__ == '__main__':
    main()