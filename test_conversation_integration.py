<<<<<<< MAIN
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'intégration ConversationOrchestrator avec RealLLMOrchestrator
===================================================================

Valide que les deux composants refactorisés peuvent s'intégrer harmonieusement.
"""

import sys
import io
from pathlib import Path

# Configuration encodage
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ajout du chemin projet
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Test que les imports des composants refactorisés fonctionnent."""
    print("[TEST] Test des imports...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import (
            ConversationOrchestrator,
            create_conversation_orchestrator,
            run_mode_micro
        )
        print("[OK] ConversationOrchestrator importé avec succès")
    except Exception as e:
        print(f"[ERROR] Erreur import ConversationOrchestrator: {e}")
        return False
    
    try:
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            RealConversationLogger
        )
        print("[OK] RealLLMOrchestrator importé avec succès")
    except Exception as e:
        print(f"[ERROR] Erreur import RealLLMOrchestrator: {e}")
        return False
    
    return True

def test_conversation_orchestrator():
    """Test que ConversationOrchestrator fonctionne en mode micro."""
    print("\n[TEST] Test ConversationOrchestrator mode micro...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import create_conversation_orchestrator
        
        orchestrator = create_conversation_orchestrator("micro")
        report = orchestrator.run_orchestration("Test d'intégration réussi")
        
        # Vérifications basiques
        assert "Test d'intégration réussi" in report
        assert "Score global:" in report
        assert "Analyse complète" in report
        
        print("[OK] ConversationOrchestrator micro test réussi")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur test ConversationOrchestrator: {e}")
        return False

def test_logger_compatibility():
    """Test la compatibilité des loggers."""
    print("\n[TEST] Test compatibilité des loggers...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationLogger
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealConversationLogger
        
        # Test ConversationLogger
        conv_logger = ConversationLogger("micro")
        conv_logger.log_agent_message("TestAgent", "Message de test", "test")
        conv_logger.log_tool_call("TestAgent", "test_tool", {"param": "value"}, "result")
        
        # Test RealConversationLogger
        real_logger = RealConversationLogger()
        real_logger.log_agent_message("TestAgent", "Message de test", "test")
        
        print("[OK] Compatibilité des loggers validée")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur test compatibilité loggers: {e}")
        return False

def test_state_compatibility():
    """Test la compatibilité des états."""
    print("\n[TEST] Test compatibilité des états...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import AnalysisState
        
        state = AnalysisState()
        state.update_from_informal({"fallacies_count": 2, "sophistication_score": 0.8})
        state.update_from_modal({"propositions_count": 3, "consistency": 0.7})
        
        # Test conversion
        state_dict = state.to_dict()
        assert "score" in state_dict
        assert "completed" in state_dict
        
        print("[OK] Compatibilité des états validée")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur test compatibilité états: {e}")
        return False

def main():
    """Point d'entrée principal."""
    print("TEST D'INTEGRATION CONVERSATION ORCHESTRATOR")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_conversation_orchestrator,
        test_logger_compatibility,
        test_state_compatibility
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[ERROR] Erreur inattendue dans {test.__name__}: {e}")
    
    print(f"\nRESULTATS: {passed}/{len(tests)} tests réussis")
    
    if passed == len(tests):
        print("TOUS LES TESTS D'INTEGRATION REUSSIS!")
        print("Les composants refactorisés sont parfaitement compatibles")
    else:
        print("Certains tests ont échoué")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'intégration ConversationOrchestrator avec RealLLMOrchestrator
===================================================================

Valide que les deux composants refactorisés peuvent s'intégrer harmonieusement.
"""

import sys
import io
from pathlib import Path

# Configuration encodage
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ajout du chemin projet
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Test que les imports des composants refactorisés fonctionnent."""
    print("[TEST] Test des imports...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import (
            ConversationOrchestrator,
            create_conversation_orchestrator,
            run_mode_micro
        )
        print("[OK] ConversationOrchestrator importé avec succès")
    except Exception as e:
        print(f"[ERROR] Erreur import ConversationOrchestrator: {e}")
        return False
    
    try:
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            RealConversationLogger
        )
        print("[OK] RealLLMOrchestrator importé avec succès")
    except Exception as e:
        print(f"[ERROR] Erreur import RealLLMOrchestrator: {e}")
        return False
    
    return True

def test_conversation_orchestrator():
    """Test que ConversationOrchestrator fonctionne en mode micro."""
    print("\n[TEST] Test ConversationOrchestrator mode micro...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import create_conversation_orchestrator
        
        orchestrator = create_conversation_orchestrator("micro")
        report = orchestrator.run_orchestration("Test d'intégration réussi")
        
        # Vérifications basiques
        assert "Test d'intégration réussi" in report
        assert "Score global:" in report
        assert "Analyse complète" in report
        
        print("[OK] ConversationOrchestrator micro test réussi")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur test ConversationOrchestrator: {e}")
        return False

def test_logger_compatibility():
    """Test la compatibilité des loggers."""
    print("\n[TEST] Test compatibilité des loggers...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationLogger
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealConversationLogger
        
        # Test ConversationLogger
        conv_logger = ConversationLogger("micro")
        conv_logger.log_agent_message("TestAgent", "Message de test", "test")
        conv_logger.log_tool_call("TestAgent", "test_tool", {"param": "value"}, "result")
        
        # Test RealConversationLogger
        real_logger = RealConversationLogger()
        real_logger.log_agent_message("TestAgent", "Message de test", "test")
        
        print("[OK] Compatibilité des loggers validée")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur test compatibilité loggers: {e}")
        return False

def test_state_compatibility():
    """Test la compatibilité des états."""
    print("\n[TEST] Test compatibilité des états...")
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import AnalysisState
        
        state = AnalysisState()
        state.update_from_informal({"fallacies_count": 2, "sophistication_score": 0.8})
        state.update_from_modal({"propositions_count": 3, "consistency": 0.7})
        
        # Test conversion
        state_dict = state.to_dict()
        assert "score" in state_dict
        assert "completed" in state_dict
        
        print("[OK] Compatibilité des états validée")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur test compatibilité états: {e}")
        return False

def main():
    """Point d'entrée principal."""
    print("TEST D'INTEGRATION CONVERSATION ORCHESTRATOR")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_conversation_orchestrator,
        test_logger_compatibility,
        test_state_compatibility
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[ERROR] Erreur inattendue dans {test.__name__}: {e}")
    
    print(f"\nRESULTATS: {passed}/{len(tests)} tests réussis")
    
    if passed == len(tests):
        print("TOUS LES TESTS D'INTEGRATION REUSSIS!")
        print("Les composants refactorisés sont parfaitement compatibles")
    else:
        print("Certains tests ont échoué")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
>>>>>>> BACKUP
