#!/usr/bin/env python3
"""
Test JPype Killer - Validation que JPype est complètement neutralisé
"""
import sys
import os
from pathlib import Path

def test_jpype_killer():
    """Test que JPype Killer fonctionne"""
    
    print("TEST JPYPE KILLER")
    print("=" * 30)
    
    # Charger JPype Killer
    sys.path.insert(0, '.')
    try:
        from tests.conftest_phase3_jpype_killer import JPYPE_KILLER_MOCK
        print("[OK] JPype Killer chargé")
    except Exception as e:
        print(f"[FAIL] Impossible de charger JPype Killer: {e}")
        return False
    
    # Test mock jpype
    try:
        import jpype
        print(f"[OK] jpype importé: {type(jpype)}")
        print(f"[OK] jpype.isJVMStarted(): {jpype.isJVMStarted()}")
        
        # Test que c'est bien le mock
        if hasattr(jpype, '_mock_name'):
            print("[OK] jpype est bien un mock")
        else:
            print("[OK] jpype remplacé par le killer")
            
    except Exception as e:
        print(f"[FAIL] Problème avec jpype: {e}")
        return False
    
    # Test import TweetyBridge avec JPype Killer actif
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge()
        print("[OK] TweetyBridge créé sans erreur JVM")
        return True
    except Exception as e:
        print(f"[FAIL] TweetyBridge échoue: {e}")
        return False

def test_single_complex_target():
    """Test un seul target complexe avec JPype Killer"""
    
    print("\nTEST TARGET COMPLEXE")
    print("=" * 30)
    
    # Ajouter le chemin
    sys.path.insert(0, '.')
    
    # Charger JPype Killer
    from tests.conftest_phase3_jpype_killer import JPYPE_KILLER_MOCK
    
    # Environnement de test
    os.environ.update({
        'USE_REAL_JPYPE': 'false',
        'JPYPE_JVM': 'false',
        'DISABLE_JVM': 'true'
    })
    
    # Test direct d'import problématique
    try:
        # Ces imports causaient les timeouts
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
        print("[OK] CluedoOracleState importé")
        
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
        print("[OK] WatsonLogicAssistant importé")
        
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
        print("[OK] SherlockEnqueteAgent importé")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Import complexe échoue: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test principal"""
    
    print("VALIDATION JPYPE KILLER PHASE 3")
    print("=" * 40)
    
    # Test 1: JPype Killer de base
    if not test_jpype_killer():
        print("\n[FAIL] JPype Killer non fonctionnel")
        return False
    
    # Test 2: Imports complexes
    if not test_single_complex_target():
        print("\n[FAIL] Imports complexes toujours problématiques")
        return False
    
    print("\n[SUCCESS] JPype Killer opérationnel")
    print("Les tests complexes devraient maintenant passer")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)