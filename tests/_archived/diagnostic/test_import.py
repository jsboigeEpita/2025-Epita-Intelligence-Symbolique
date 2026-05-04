__test__ = False
__test__ = False
#!/usr/bin/env python3
# Test d'import des orchestrateurs spécialisés

import sys
import traceback


def test_import(module_name, class_name):
    try:
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"[OK] Import reussi: {class_name} depuis {module_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Erreur import {class_name}: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


print("=== Test des imports d'orchestrateurs ===")

# Test CluedoExtendedOrchestrator
test_import(
    "argumentation_analysis.orchestration.cluedo_extended_orchestrator",
    "CluedoExtendedOrchestrator",
)

# Test ConversationOrchestrator
test_import(
    "argumentation_analysis.orchestration.conversation_orchestrator",
    "ConversationOrchestrator",
)

# Test RealLLMOrchestrator
test_import(
    "argumentation_analysis.orchestration.real_llm_orchestrator", "RealLLMOrchestrator"
)

# Test LogiqueComplexeOrchestrator
test_import(
    "argumentation_analysis.orchestration.logique_complexe_orchestrator",
    "LogiqueComplexeOrchestrator",
)

print("=== Fin des tests ===")
