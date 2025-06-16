import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validator for system integration between components.
"""

import logging
import traceback
from typing import Dict, Any

# Ajout du chemin pour les imports si nécessaire
# from pathlib import Path
# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

async def validate_integration(report_errors_list: list, available_components: Dict[str, bool], test_texts: list) -> Dict[str, Any]:
    """Validates integration between components."""
    logger.info("🔗 Validation de l'intégration système...")
    
    integration_results = {
        "handoff_tests": {},
        "config_mapping": {},
        "end_to_end": {}, # Ce test n'était pas implémenté dans l'original
        "errors": []
    }
    
    try:
        # Test handoff conversation -> LLM
        if (available_components.get('conversation_orchestrator', False) and 
            available_components.get('real_llm_orchestrator', False)):
            integration_results["handoff_tests"] = await _test_orchestrator_handoff(test_texts)
        else:
            integration_results["handoff_tests"] = {"status": "skipped", "reason": "Orchestrateurs requis non disponibles"}
        
        # Test mapping de configuration
        if available_components.get('unified_config', False):
            integration_results["config_mapping"] = await _test_config_mapping()
        else:
            integration_results["config_mapping"] = {"status": "skipped", "reason": "Config unifiée non disponible"}
            
    except Exception as e:
        error_details = {
            "context": "integration_validation",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        integration_results["errors"].append(error_details)
        report_errors_list.append(error_details)
        
    return integration_results

async def _test_orchestrator_handoff(test_texts: list) -> Dict[str, Any]:
    """Tests handoff between orchestrators."""
    results = {"status": "unknown", "details": {}}
    
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
        
        logger.info("  Test handoff ConversationOrchestrator -> RealLLMOrchestrator...")
        conv_orch = ConversationOrchestrator(mode="demo")
        conv_result = conv_orch.run_orchestration(test_texts[0] if test_texts else "Test handoff input")
        
        if isinstance(conv_result, str) and conv_result:
            logger.info(f"    ConversationOrchestrator output: {conv_result[:100]}...") # Log tronqué
            llm_orch = RealLLMOrchestrator(mode="real")
            # Assurez-vous que run_real_llm_orchestration est une coroutine si vous l'attendez
            llm_result = await llm_orch.run_real_llm_orchestration(conv_result) 
            
            if isinstance(llm_result, dict):
                results["status"] = "success"
                results["details"]["conv_to_llm"] = "OK"
                logger.info("    ✓ Handoff Conversation vers LLM réussi.")
            else:
                results["status"] = "failed"
                results["details"]["conv_to_llm"] = f"Format LLM invalide: {type(llm_result)}"
                logger.error(f"    ✗ Handoff Conversation vers LLM échoué: Format LLM invalide ({type(llm_result)})")
        else:
            results["status"] = "failed"
            results["details"]["conv_to_llm"] = f"Format conversation invalide ou vide: {type(conv_result)}"
            logger.error(f"    ✗ Handoff Conversation vers LLM échoué: Format conversation invalide ({type(conv_result)})")
            
    except ImportError:
        results["status"] = "failed"
        results["details"]["error"] = "Import manquant pour orchestrateurs"
        logger.error("    ✗ Handoff échoué: Import manquant pour orchestrateurs.")
    except Exception as e:
        results["status"] = "failed"
        results["details"]["error"] = str(e)
        logger.error(f"    ✗ Erreur durant le test de handoff: {e}", exc_info=True)
    
    return results

async def _test_config_mapping() -> Dict[str, Any]:
    """Tests configuration mapping."""
    results = {"status": "unknown", "mappings": {}}
    logger.info("  Test du mapping de configuration...")
    
    try:
        from config.unified_config import UnifiedConfig
        
        configs_params = [
            {"logic_type": "FOL", "orchestration_type": "CONVERSATION"},
            {"logic_type": "PROPOSITIONAL", "orchestration_type": "REAL_LLM"},
            {"mock_level": "NONE", "require_real_gpt": True}
        ]
        
        successful_mappings = 0
        
        for i, params in enumerate(configs_params):
            config_name = f"config_{i}"
            try:
                config = UnifiedConfig(**params)
                # Ajouter une vérification si possible, par ex. que les valeurs sont bien celles attendues
                results["mappings"][config_name] = "OK"
                successful_mappings += 1
                logger.info(f"    ✓ Mapping {config_name} ({params}) réussi.")
            except Exception as e:
                results["mappings"][config_name] = f"Erreur: {str(e)}"
                logger.error(f"    ✗ Erreur mapping {config_name} ({params}): {e}")
        
        if successful_mappings == len(configs_params):
            results["status"] = "success"
        elif successful_mappings > 0:
            results["status"] = "partial"
        else:
            results["status"] = "failed"
            
    except ImportError:
        results["status"] = "failed"
        results["error"] = "Import manquant pour UnifiedConfig"
        logger.error("    ✗ Test de mapping échoué: Import UnifiedConfig manquant.")
    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)
        logger.error(f"    ✗ Erreur générale durant le test de mapping de configuration: {e}", exc_info=True)
        
    return results