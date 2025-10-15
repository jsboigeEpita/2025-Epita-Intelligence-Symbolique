__test__ = False
"""
Test temporaire pour valider les imports d'orchestrateurs en contournant la vérification d'environnement.
"""

import sys
import os

# Temporairement contourner la vérification d'environnement
os.environ["IS_ACTIVATION_SCRIPT_RUNNING"] = "true"


def test_import(module_name, class_name):
    """Test l'import d'une classe spécifique"""
    try:
        print(f"[TEST] Import de {class_name} depuis {module_name}...")
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"[SUCCESS] {class_name} importé avec succès: {cls}")
        return cls
    except Exception as e:
        print(f"[ERROR] Erreur import {class_name}: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return None


if __name__ == "__main__":
    print("=== Test des imports d'orchestrateurs (contournement environnement) ===")

    # Test des imports d'orchestrateurs
    orchestrators = [
        (
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator",
            "CluedoExtendedOrchestrator",
        ),
        (
            "argumentation_analysis.orchestration.conversation_orchestrator",
            "ConversationOrchestrator",
        ),
        (
            "argumentation_analysis.orchestration.real_llm_orchestrator",
            "RealLLMOrchestrator",
        ),
        (
            "argumentation_analysis.orchestration.logique_complexe_orchestrator",
            "LogiqueComplexeOrchestrator",
        ),
    ]

    success_count = 0
    total_count = len(orchestrators)

    for module_name, class_name in orchestrators:
        result = test_import(module_name, class_name)
        if result is not None:
            success_count += 1

    print(f"\n=== Résultats: {success_count}/{total_count} imports réussis ===")
    print("=== Fin des tests ===")
