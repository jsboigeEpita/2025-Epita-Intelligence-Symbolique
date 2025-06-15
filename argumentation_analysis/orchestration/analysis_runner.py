# orchestration/analysis_runner.py
import project_core.core_from_scripts.auto_env  # Auto-activation environnement intelligent
import sys
import os
# Ajout pour résoudre les problèmes d'import de project_core
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import time
import traceback
import asyncio
import logging
import json
import random
from typing import List, Optional, Union, Any, Dict

# from argumentation_analysis.core.jvm_setup import initialize_jvm
# from argumentation_analysis.paths import LIBS_DIR # Nécessaire pour initialize_jvm

import jpype # Pour la vérification finale de la JVM
# Imports pour le hook LLM
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent as SKChatMessageContent # Alias pour éviter conflit
from semantic_kernel.kernel import Kernel as SKernel # Alias pour éviter conflit avec Kernel de SK

# Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
from semantic_kernel.contents.utils.author_role import AuthorRole

# Correct imports
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.pl.pl_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent

class AgentChatException(Exception):
    """Custom exception for errors during the agent chat execution."""
    pass

class AnalysisRunner:
    """
    Orchestre l'analyse d'argumentation en utilisant une flotte d'agents spécialisés.
    """
    def __init__(self, llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None):
        self._llm_service = llm_service

    async def run_analysis_async(self, text_content: str, llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None):
        """Exécute le pipeline d'analyse complet."""
        # Utilise le service fourni en priorité, sinon celui de l'instance
        active_llm_service = llm_service or self._llm_service
        if not active_llm_service:
            # Ici, ajouter la logique pour créer un service par défaut si aucun n'est fourni
            # Pour l'instant, on lève une erreur comme dans le test.
            raise ValueError("Un service LLM doit être fourni soit à l'initialisation, soit à l'appel de la méthode.")
        
        return await _run_analysis_conversation(
            texte_a_analyser=text_content,
            llm_service=active_llm_service
        )


async def run_analysis(text_content: str, llm_service: Optional[Union[OpenAIChatCompletion, AzureChatCompletion]] = None):
    """Fonction wrapper pour une exécution simple."""
    runner = AnalysisRunner()
    return await runner.run_analysis_async(text_content=text_content, llm_service=llm_service)


async def _run_analysis_conversation(
    texte_a_analyser: str,
    llm_service: Union[OpenAIChatCompletion, AzureChatCompletion] # Service LLM passé en argument
    ):
    run_start_time = time.time()
    run_id = random.randint(1000, 9999)
    print("\n=====================================================")
    print(f"== Début de l'Analyse Collaborative (Run_{run_id}) ==")
    print("=====================================================")
    run_logger = logging.getLogger(f"Orchestration.Run.{run_id}")
    run_logger.info("--- Début Nouveau Run ---")

    run_logger.info(f"Type de llm_service: {type(llm_service)}")
    
    class RawResponseLogger: 
        def __init__(self, logger_instance): self.logger = logger_instance
        def on_chat_completion_response(self, message, raw_response): 
            self.logger.debug(f"Raw LLM Response for message ID {message.id if hasattr(message, 'id') else 'N/A'}: {raw_response}")

    if hasattr(llm_service, "add_chat_hook_handler"):
        raw_logger_hook = RawResponseLogger(run_logger) 
        llm_service.add_chat_hook_handler(raw_logger_hook)
        run_logger.info("RawResponseLogger hook ajouté au service LLM.")
    else:
        run_logger.warning("Le service LLM ne supporte pas add_chat_hook_handler. Le RawResponseLogger ne sera pas actif.")

    if not llm_service or not hasattr(llm_service, 'service_id'):
         run_logger.critical("❌ Service LLM invalide ou manquant fourni à run_analysis_conversation.")
         raise ValueError("Un service LLM valide est requis.")
    run_logger.info(f"Utilisation du service LLM fourni: ID='{llm_service.service_id}'")

    local_state: Optional[RhetoricalAnalysisState] = None
    local_kernel: Optional[sk.Kernel] = None
    local_group_chat: Optional[Any] = None # AgentGroupChat non disponible
    local_state_manager_plugin: Optional[StateManagerPlugin] = None

    agent_list_local: List[Any] = []

    try:
        run_logger.info("1. Création instance état locale...")
        local_state = RhetoricalAnalysisState(initial_text=texte_a_analyser)
        run_logger.info(f"   Instance état locale créée (id: {id(local_state)}) avec texte (longueur: {len(texte_a_analyser)}).")

        run_logger.info("2. Création instance StateManagerPlugin locale...")
        local_state_manager_plugin = StateManagerPlugin(local_state)
        run_logger.info(f"   Instance StateManagerPlugin locale créée (id: {id(local_state_manager_plugin)}).")

        run_logger.info("3. Création Kernel local...")
        local_kernel = sk.Kernel()
        local_kernel.add_service(llm_service)
        run_logger.info(f"   Service LLM '{llm_service.service_id}' ajouté.")
        local_kernel.add_plugin(local_state_manager_plugin, plugin_name="StateManager")
        run_logger.info(f"   Plugin 'StateManager' (local) ajouté.")

        run_logger.info("4. Création et configuration des instances d'agents refactorés...")
        llm_service_id_str = llm_service.service_id

        pm_agent_refactored = ProjectManagerAgent(kernel=local_kernel, agent_name="ProjectManagerAgent_Refactored")
        pm_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {pm_agent_refactored.name} instancié et configuré.")

        informal_agent_refactored = InformalAnalysisAgent(kernel=local_kernel, agent_name="InformalAnalysisAgent_Refactored")
        informal_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {informal_agent_refactored.name} instancié et configuré.")
        
        run_logger.warning("ATTENTION: PropositionalLogicAgent DÉSACTIVÉ temporairement (incompatibilité Java)")
        pl_agent_refactored = None  # Placeholder pour éviter les erreurs

        extract_agent_refactored = ExtractAgent(kernel=local_kernel, agent_name="ExtractAgent_Refactored")
        extract_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {extract_agent_refactored.name} instancié et configuré.")
        
        run_logger.debug(f"   Plugins enregistrés dans local_kernel après setup des agents: {list(local_kernel.plugins.keys())}")

        run_logger.info("5. Création des instances Agent de compatibilité pour AgentGroupChat...")
        
        if 'local_state' in locals():
            print(f"Repr: {repr(local_state)}")
        else:
            print("(Instance état locale non disponible)")

        jvm_status = "(JVM active)" if ('jpype' in globals() and jpype.isJVMStarted()) else "(JVM non active)"
        print(f"\n{jvm_status}")
        run_logger.info("Agents de compatibilité configurés.")

        run_logger.info(f"--- Fin Run_{run_id} ---")
        
        return {"status": "success", "message": "Analyse terminée"}
        
    except Exception as e:
        run_logger.error(f"Erreur durant l'analyse: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        run_logger.info("Nettoyage en cours...")
