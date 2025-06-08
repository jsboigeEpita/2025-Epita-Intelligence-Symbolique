#!/usr/bin/env python3
"""Test d'intégration FOL Agent + LLM Orchestrator"""

print('=== TEST INTÉGRATION FOL + LLM ORCHESTRATOR ===')
try:
    # Test FOL Logic Agent
    print('[1/3] Test import FOL Logic Agent...')
    from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
    fol_agent = FOLLogicAgent()
    print('✅ FOL Logic Agent: Import et instantiation réussis')
    print(f'    Type: {type(fol_agent)}')
    
    # Test LLM Orchestrator
    print('[2/3] Test import LLM Orchestrator...')
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    llm_orch = RealLLMOrchestrator()
    print('✅ LLM Orchestrator: Import et instantiation réussis')
    print(f'    Type: {type(llm_orch)}')
    
    # Test UnifiedConfig
    print('[3/3] Test import UnifiedConfig...')
    from argumentation_analysis.config.unified_config import UnifiedConfig
    config = UnifiedConfig()
    print('✅ UnifiedConfig: Import et instantiation réussis')
    print(f'    Type: {type(config)}')
    
    print('\n🎉 INTÉGRATION MODULES CORE: SUCCÈS COMPLET')
    
except Exception as e:
    print(f'❌ Erreur intégration: {e}')
    import traceback
    traceback.print_exc()