#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour InformalAnalysisAgent avec les nouvelles fonctions d'exploration de taxonomie.
"""

import asyncio
import logging
import json
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion # Gardé pour exemple de config réelle

# Configuration du logging pour voir les messages du plugin
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Ajout des chemins pour les imports de l'application
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState 

async def main():
    logger.info("Début du script de test pour InformalAnalysisAgent et l'exploration de taxonomie.")

    kernel = sk.Kernel()
    
    llm_service = None 
    try:
        logger.warning("Utilisation d'un service LLM simulé. Les appels sémantiques ne seront pas réels.")
        
        class MockLLMService: 
            service_id = "mock_llm_service" 
            def __init__(self):
                self.ai_model_id = "mock_model"
            async def complete_chat_async(self, messages, settings): 
                logger.info(f"MockLLMService ({self.service_id}): complete_chat_async appelé avec messages: {messages}")
                if "semantic_IdentifyArguments" in str(messages):
                     return [sk.ChatMessageContent(role="assistant", content="Argument: Le ciel est bleu parce que c'est sa couleur naturelle.")]
                elif "semantic_AnalyzeFallacies" in str(messages):
                    return [sk.ChatMessageContent(role="assistant", content="Sophisme identifié: Pétition de principe (PK: supposons 123)")]
                return [sk.ChatMessageContent(role="assistant", content="Réponse simulée du LLM.")]

        llm_service = MockLLMService()
        kernel.add_service(llm_service) 
        logger.info(f"Service LLM simulé '{llm_service.service_id}' configuré et ajouté au kernel.")

    except Exception as e:
        logger.error(f"Erreur lors de la configuration du service LLM: {e}. Le test pourrait échouer ou être limité.")

    sample_text_1 = "Le politicien X dit que nous devons baisser les impôts pour relancer l'économie. C'est un homme riche et prospère, donc il doit savoir de quoi il parle et sa proposition est sûrement la meilleure."
    sample_text_2 = "Tous ceux qui ont essayé le nouveau régime Y ont perdu du poids rapidement. Donc, le régime Y est efficace et sans danger pour tout le monde."

    try:
        shared_rhetorical_state = RhetoricalAnalysisState(initial_text=sample_text_1)
        logger.info(f"Instance de RhetoricalAnalysisState créée (id: {id(shared_rhetorical_state)}) avec sample_text_1.")

        state_manager_plugin = StateManagerPlugin(state=shared_rhetorical_state)
        kernel.add_plugin(state_manager_plugin, "StateManager")
        logger.info("StateManagerPlugin configuré avec RhetoricalAnalysisState et ajouté au kernel.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation ou de l'ajout de StateManagerPlugin: {e}", exc_info=True)
        return 

    if not llm_service or not kernel.get_service(llm_service.service_id):
         logger.error(f"Service LLM '{llm_service.service_id if llm_service else 'None'}' non disponible dans le kernel. Impossible de continuer la configuration de l'agent.")
         return

    setup_informal_kernel(kernel, llm_service, taxonomy_file_path="argumentation_analysis/data/mock_taxonomy_cards.csv")
    logger.info("Kernel configuré avec InformalAnalysisPlugin.")

    try:
        informal_agent = InformalAnalysisAgent(kernel=kernel)
        logger.info(f"InformalAnalysisAgent '{informal_agent.name}' instancié.")
    except Exception as e:
        logger.error(f"Erreur lors de l'instanciation de InformalAnalysisAgent: {e}", exc_info=True)
        return

    logger.info(f"\n--- Test direct des fonctions du plugin InformalAnalyzer (sur sample_text_1 implicitement dans l'état) ---")
    
    if "InformalAnalyzer" not in kernel.plugins:
        logger.error("Plugin InformalAnalyzer non trouvé dans le kernel. Arrêt des tests de plugin.")
        return
        
    analyzer_plugin = kernel.plugins["InformalAnalyzer"]
    logger.info(f"Fonctions disponibles dans analyzer_plugin ('InformalAnalyzer'): {list(analyzer_plugin.functions.keys())}")


    logger.info("Test: list_fallacy_categories()")
    if "list_fallacy_categories" in analyzer_plugin:
        result_cats = await kernel.invoke(analyzer_plugin["list_fallacy_categories"])
        logger.info(f"Résultat list_fallacy_categories: {result_cats}")
    else:
        logger.error("Fonction 'list_fallacy_categories' non trouvée dans analyzer_plugin.")

    logger.info("Test: find_fallacy_definition('Argument d\\'autorité')") 
    if "find_fallacy_definition" in analyzer_plugin:
        result_def_auth = await kernel.invoke(analyzer_plugin["find_fallacy_definition"], fallacy_name="Argument d'autorité")
        logger.info(f"Résultat find_fallacy_definition('Argument d'autorité'): {result_def_auth}")
        
        try:
            result_def_auth_str = str(result_def_auth)
            if not result_def_auth_str or not result_def_auth_str.strip().startswith('{'):
                logger.warning(f"find_fallacy_definition n'a pas retourné un JSON valide: {result_def_auth_str}")
                pk_autorite = None
            else:
                def_auth_json = json.loads(result_def_auth_str)
                pk_autorite = def_auth_json.get("pk")

            if pk_autorite and "get_fallacy_details" in analyzer_plugin:
                logger.info(f"Test: get_fallacy_details pour PK {pk_autorite} (obtenu de find_fallacy_definition)")
                result_details_auth = await kernel.invoke(analyzer_plugin["get_fallacy_details"], fallacy_pk_str=str(pk_autorite))
                logger.info(f"Résultat get_fallacy_details(PK={pk_autorite}): {result_details_auth}")
            elif pk_autorite is None and result_def_auth_str.strip().startswith('{'):
                 logger.warning(f"PK non trouvée dans la réponse JSON de find_fallacy_definition: {result_def_auth_str}")
            elif "get_fallacy_details" not in analyzer_plugin:
                logger.error("Fonction 'get_fallacy_details' non trouvée dans analyzer_plugin.")
        except json.JSONDecodeError as jde:
            logger.error(f"Erreur de décodage JSON pour find_fallacy_definition: {jde}. Réponse reçue: {result_def_auth_str}", exc_info=True)
        except Exception as e:
            logger.warning(f"N'a pas pu extraire PK de la définition pour 'Argument d'autorité' ou erreur lors de get_fallacy_details: {e}", exc_info=True)
    else:
        logger.error("Fonction 'find_fallacy_definition' non trouvée dans analyzer_plugin.")


    logger.info("Test: get_fallacy_example('Argument d\\'autorité')")
    if "get_fallacy_example" in analyzer_plugin:
        result_ex_auth = await kernel.invoke(analyzer_plugin["get_fallacy_example"], fallacy_name="Argument d'autorité")
        logger.info(f"Résultat get_fallacy_example('Argument d'autorité'): {result_ex_auth}")
    else:
        logger.error("Fonction 'get_fallacy_example' non trouvée dans analyzer_plugin.")


    logger.info(f"\n--- Test direct des fonctions du plugin pour un autre contexte (sample_text_2) ---")
    logger.info("Test: find_fallacy_definition('Généralisation hâtive')")
    if "find_fallacy_definition" in analyzer_plugin:
        result_def_gen = await kernel.invoke(analyzer_plugin["find_fallacy_definition"], fallacy_name="Généralisation hâtive")
        logger.info(f"Résultat find_fallacy_definition('Généralisation hâtive'): {result_def_gen}")
    else:
        logger.error("Fonction 'find_fallacy_definition' non trouvée dans analyzer_plugin (pour Généralisation hâtive).")

    logger.info("Test: list_fallacies_in_category('Sophismes d\\'induction')") 
    if "list_fallacies_in_category" in analyzer_plugin:
        result_list_ind = await kernel.invoke(analyzer_plugin["list_fallacies_in_category"], category_name="Sophismes d'induction")
        logger.info(f"Résultat list_fallacies_in_category('Sophismes d'induction'): {result_list_ind}")
    else:
        logger.error("Fonction 'list_fallacies_in_category' non trouvée dans analyzer_plugin.")
    
    logger.info("Test: explore_fallacy_hierarchy(current_pk_str='0')") 
    if "explore_fallacy_hierarchy" in analyzer_plugin:
        result_explore_root = await kernel.invoke(analyzer_plugin["explore_fallacy_hierarchy"], current_pk_str="0", max_children=15)
        logger.info(f"Résultat explore_fallacy_hierarchy('0'): {result_explore_root}")
    else:
        logger.error("Fonction 'explore_fallacy_hierarchy' non trouvée dans analyzer_plugin.")

    logger.info("\nFin du script de test.")

if __name__ == "__main__":
    asyncio.run(main())