#!/usr/bin/env python3
"""
Test de validation de l'environnement Oracle Enhanced v2.1.0
Validation en conditions réelles des orchestrations Sherlock-Watson
"""

import sys
import os
import traceback
from datetime import datetime

def test_oracle_imports():
    """Test des imports principaux du système Oracle Enhanced v2.1.0"""
    print("=== TEST ORACLE ENHANCED v2.1.0 - VALIDATION IMPORTS ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Python: {sys.version}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Non défini')}")
    print(f"JAVA_HOME: {os.environ.get('JAVA_HOME', 'Non défini')}")
    print(f"USE_REAL_JPYPE: {os.environ.get('USE_REAL_JPYPE', 'Non défini')}")
    print()
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Import base argumentation_analysis
    total_tests += 1
    try:
        import argumentation_analysis
        print("✅ Import argumentation_analysis: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import argumentation_analysis: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 2: Import agents.core
    total_tests += 1
    try:
        from argumentation_analysis.agents.core import oracle
        print("✅ Import agents.core.oracle: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import agents.core.oracle: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 3: Import Oracle Base Agent
    total_tests += 1
    try:
        from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent
        print("✅ Import OracleBaseAgent: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import OracleBaseAgent: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 4: Import Moriarty Interrogator Agent
    total_tests += 1
    try:
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
        print("✅ Import MoriartyInterrogatorAgent: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import MoriartyInterrogatorAgent: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 5: Import Dataset Access Manager
    total_tests += 1
    try:
        from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
        print("✅ Import DatasetAccessManager: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import DatasetAccessManager: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 6: Import Cluedo Dataset
    total_tests += 1
    try:
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
        print("✅ Import CluedoDataset: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import CluedoDataset: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 7: Import Phase D Extensions
    total_tests += 1
    try:
        from argumentation_analysis.agents.core.oracle.phase_d_extensions import PhaseDExtensions
        print("✅ Import PhaseDExtensions: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import PhaseDExtensions: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 8: Test Tweety Bridge (JPype)
    total_tests += 1
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        print("✅ Import TweetyBridge: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import TweetyBridge: ERREUR - {e}")
        traceback.print_exc()
    
    # Test 9: Test Orchestration
    total_tests += 1
    try:
        from argumentation_analysis.orchestration import cluedo_orchestrator
        print("✅ Import orchestration.cluedo_orchestrator: OK")
        success_count += 1
    except Exception as e:
        print(f"❌ Import orchestration.cluedo_orchestrator: ERREUR - {e}")
        traceback.print_exc()
    
    print()
    print("=== RÉSUMÉ DES TESTS ===")
    success_rate = (success_count / total_tests) * 100
    print(f"Tests réussis: {success_count}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("✅ ORACLE ENHANCED v2.1.0 - ENVIRONNEMENT VALIDE")
        return True
    else:
        print("❌ ORACLE ENHANCED v2.1.0 - ENVIRONNEMENT NON VALIDE")
        return False

def test_agents_configuration():
    """Test de la configuration des agents en mode réel"""
    print("\n=== TEST CONFIGURATION AGENTS GPT-4o-mini ===")
    
    try:
        openai_model = os.environ.get('OPENAI_CHAT_MODEL_ID', 'Non défini')
        print(f"Modèle configuré: {openai_model}")
        
        if openai_model == 'gpt-4o-mini':
            print("✅ Configuration GPT-4o-mini: OK")
            return True
        else:
            print("❌ Configuration GPT-4o-mini: ERREUR - Modèle incorrect")
            return False
    except Exception as e:
        print(f"❌ Configuration agents: ERREUR - {e}")
        return False

if __name__ == "__main__":
    print("VALIDATION ORACLE ENHANCED v2.1.0 - CONDITIONS RÉELLES")
    print("=" * 60)
    
    # Test des imports
    imports_ok = test_oracle_imports()
    
    # Test de la configuration
    config_ok = test_agents_configuration()
    
    overall_success = imports_ok and config_ok
    
    print("\n" + "=" * 60)
    if overall_success:
        print("🎉 VALIDATION ORACLE ENHANCED v2.1.0: SUCCÈS")
        sys.exit(0)
    else:
        print("❌ VALIDATION ORACLE ENHANCED v2.1.0: ÉCHEC")
        sys.exit(1)