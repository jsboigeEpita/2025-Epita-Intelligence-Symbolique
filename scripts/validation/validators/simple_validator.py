import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validator for a simplified, quick system check.
"""

import logging
import traceback
from typing import Dict, Any

# Ajout du chemin pour les imports si nécessaire
# from pathlib import Path
# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

async def validate_simple(report_errors_list: list, available_components: Dict[str, bool]) -> Dict[str, Any]:
    """Performs a simplified validation without emojis, focusing on core component availability and basic orchestration."""
    logger.info("Validation simplifiée en cours...")
    
    simple_results = {
        "components_available_count": sum(1 for comp_status in available_components.values() if comp_status),
        "total_components_checked": len(available_components),
        "basic_tests": {},
        "status": "unknown",
        "errors": [] # Pour capturer les erreurs spécifiques à ce validateur
    }
    
    basic_tests_results = {
        "import_unified_config": {"status": "pending", "details": ""},
        "import_orchestrators": {"status": "pending", "details": ""},
        "basic_orchestration_conversation_micro": {"status": "pending", "details": ""}
    }
    
    try:
        # Test import config
        if available_components.get('unified_config', False):
            try:
                from config.unified_config import UnifiedConfig
                # Optionnel: instancier pour vérifier
                # config = UnifiedConfig() 
                basic_tests_results["import_unified_config"]["status"] = "success"
                logger.info("  ✓ Test import UnifiedConfig: Réussi")
            except ImportError as e:
                basic_tests_results["import_unified_config"]["status"] = "failed"
                basic_tests_results["import_unified_config"]["details"] = f"ImportError: {e}"
                logger.error(f"  ✗ Test import UnifiedConfig: Échoué ({e})")
            except Exception as e:
                basic_tests_results["import_unified_config"]["status"] = "error"
                basic_tests_results["import_unified_config"]["details"] = f"Exception: {e}"
                logger.error(f"  ✗ Test import UnifiedConfig: Erreur ({e})")
        else:
            basic_tests_results["import_unified_config"]["status"] = "skipped"
            basic_tests_results["import_unified_config"]["details"] = "UnifiedConfig non marqué comme disponible."
            logger.info("  - Test import UnifiedConfig: Skipped (non disponible)")

        # Test import orchestrateurs
        if (available_components.get('conversation_orchestrator', False) or 
            available_components.get('real_llm_orchestrator', False)):
            try:
                if available_components.get('conversation_orchestrator', False):
                    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
                if available_components.get('real_llm_orchestrator', False):
                    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
                basic_tests_results["import_orchestrators"]["status"] = "success"
                logger.info("  ✓ Test import Orchestrators: Réussi")
            except ImportError as e:
                basic_tests_results["import_orchestrators"]["status"] = "failed"
                basic_tests_results["import_orchestrators"]["details"] = f"ImportError: {e}"
                logger.error(f"  ✗ Test import Orchestrators: Échoué ({e})")
            except Exception as e:
                basic_tests_results["import_orchestrators"]["status"] = "error"
                basic_tests_results["import_orchestrators"]["details"] = f"Exception: {e}"
                logger.error(f"  ✗ Test import Orchestrators: Erreur ({e})")
        else:
            basic_tests_results["import_orchestrators"]["status"] = "skipped"
            basic_tests_results["import_orchestrators"]["details"] = "Orchestrateurs non marqués comme disponibles."
            logger.info("  - Test import Orchestrators: Skipped (non disponibles)")
        
        # Test orchestration de base (ConversationOrchestrator en mode micro)
        if available_components.get('conversation_orchestrator', False):
            try:
                from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
                orchestrator = ConversationOrchestrator(mode="micro")
                result = orchestrator.run_orchestration("Test simple d'orchestration.")
                if result and isinstance(result, str):
                    basic_tests_results["basic_orchestration_conversation_micro"]["status"] = "success"
                    logger.info("  ✓ Test basic_orchestration (ConversationOrchestrator micro): Réussi")
                else:
                    basic_tests_results["basic_orchestration_conversation_micro"]["status"] = "failed"
                    basic_tests_results["basic_orchestration_conversation_micro"]["details"] = f"Résultat invalide ou vide (type: {type(result)})"
                    logger.error(f"  ✗ Test basic_orchestration (ConversationOrchestrator micro): Résultat invalide ou vide.")
            except ImportError as e:
                basic_tests_results["basic_orchestration_conversation_micro"]["status"] = "failed"
                basic_tests_results["basic_orchestration_conversation_micro"]["details"] = f"ImportError: {e}"
                logger.error(f"  ✗ Test basic_orchestration (ConversationOrchestrator micro): Échoué import ({e})")
            except Exception as e:
                basic_tests_results["basic_orchestration_conversation_micro"]["status"] = "error"
                basic_tests_results["basic_orchestration_conversation_micro"]["details"] = f"Exception: {e}"
                logger.error(f"  ✗ Test basic_orchestration (ConversationOrchestrator micro): Erreur ({e})")
        else:
            basic_tests_results["basic_orchestration_conversation_micro"]["status"] = "skipped"
            basic_tests_results["basic_orchestration_conversation_micro"]["details"] = "ConversationOrchestrator non marqué comme disponible."
            logger.info("  - Test basic_orchestration (ConversationOrchestrator micro): Skipped (non disponible)")
            
        simple_results["basic_tests"] = basic_tests_results
        
        # Status final basé sur les tests effectués
        successful_tests_count = sum(1 for test_result in basic_tests_results.values() if test_result["status"] == "success")
        total_relevant_tests = sum(1 for test_result in basic_tests_results.values() if test_result["status"] != "skipped")

        if total_relevant_tests == 0 : # Aucun test n'a pu être effectué
             simple_results["status"] = "SKIPPED" # Ou "UNKNOWN"
             logger.warning("  Validation simple: Aucun test pertinent n'a pu être exécuté.")
        elif successful_tests_count == total_relevant_tests:
            simple_results["status"] = "SUCCESS"
            logger.info("  ✓ Validation simple: Tous les tests pertinents ont réussi.")
        elif successful_tests_count > 0:
            simple_results["status"] = "PARTIAL"
            logger.warning("  ~ Validation simple: Certains tests ont échoué ou ont des erreurs.")
        else: # Aucun test n'a réussi
            simple_results["status"] = "FAILED"
            logger.error("  ✗ Validation simple: Tous les tests pertinents ont échoué ou ont des erreurs.")
            
    except Exception as e:
        simple_results["status"] = "ERROR"
        error_details = {
            "context": "simple_validation_main",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        simple_results["errors"].append(error_details)
        report_errors_list.append(error_details)
        logger.error(f"  ✗ Erreur majeure durant la validation simple: {e}", exc_info=True)
        
    return simple_results