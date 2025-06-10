# orchestration/analysis_runner.py
import scripts.core.auto_env  # Auto-activation environnement intelligent
import sys
import os
# Ajout pour résoudre les problèmes d'import de project_core
# Obtient le répertoire du script actuel (orchestration)
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Remonte de deux niveaux pour atteindre la racine du projet (depuis argumentation_analysis/orchestration)
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import time
import traceback
import asyncio
import logging
import json
import random
# import os # Déjà importé plus haut
# Ajout des imports nécessaires pour initialize_jvm
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.paths import LIBS_DIR # Nécessaire pour initialize_jvm

import jpype # Pour la vérification finale de la JVM
from typing import List, Optional, Union, Any, Dict # Ajout Any, Dict

# Imports pour le hook LLM
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent as SKChatMessageContent # Alias pour éviter conflit
from semantic_kernel.kernel import Kernel as SKernel # Alias pour éviter conflit avec Kernel de SK
# KernelArguments est déjà importé plus bas
 # Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent, Agent
from argumentation_analysis.utils.semantic_kernel_compatibility import AuthorRole, AgentChatException, FunctionChoiceBehavior


# --- Fonction Principale d'Exécution (Modifiée V10.7 - Accepte Service LLM) ---
async def run_analysis_conversation(
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
    run_logger.info(f"Attributs de llm_service: {dir(llm_service)}")
    
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
    local_group_chat: Optional[AgentGroupChat] = None
    local_state_manager_plugin: Optional[StateManagerPlugin] = None
    agent_list_local: List[Agent] = []

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

        # TEMPORAIREMENT DÉSACTIVÉ - Problème compatibilité Java (version 59.0 vs 52.0)
        # pl_agent_refactored = PropositionalLogicAgent(kernel=local_kernel, agent_name="PropositionalLogicAgent_Refactored")
        # pl_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        # run_logger.info(f"   Agent {pl_agent_refactored.name} instancié et configuré.")
        run_logger.warning("ATTENTION: PropositionalLogicAgent DÉSACTIVÉ temporairement (incompatibilité Java)")
        pl_agent_refactored = None  # Placeholder pour éviter les erreurs

        extract_agent_refactored = ExtractAgent(kernel=local_kernel, agent_name="ExtractAgent_Refactored")
        extract_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {extract_agent_refactored.name} instancié et configuré.")
        
        run_logger.debug(f"   Plugins enregistrés dans local_kernel après setup des agents: {list(local_kernel.plugins.keys())}")

        run_logger.info("5. Création des instances Agent de compatibilité pour AgentGroupChat...")
        
        # Utiliser nos propres agents de compatibilité au lieu de ChatCompletionAgent
        try:
            from argumentation_analysis.utils.semantic_kernel_compatibility import AuthorRole, AgentChatException, FunctionChoiceBehavior
            if 'local_state' in locals():
                print(f"Repr: {repr(local_state)}")
            else:
                print("(Instance état locale non disponible)")

            jvm_status = "(JVM active)" if ('jpype' in globals() and jpype.isJVMStarted()) else "(JVM non active)"
            print(f"\n{jvm_status}")
        except ImportError as e:
            run_logger.warning(f"Import semantic_kernel_compatibility échoué: {e}")
            jvm_status = "Import error"
        
        run_logger.info(f"État final JVM: {jvm_status}")
        run_logger.info(f"--- Fin Run_{run_id} ---")
        
    except Exception as e:
        run_logger.error(f"Erreur dans run_analysis_conversation: {e}")
        raise

class AnalysisRunner:
   """
   Classe pour encapsuler la fonction run_analysis_conversation.
   
   Cette classe permet d'exécuter une analyse rhétorique en utilisant
   la fonction run_analysis_conversation avec des paramètres supplémentaires.
   """
   
   def __init__(self, strategy=None):
       self.strategy = strategy
       self.logger = logging.getLogger("AnalysisRunner")
       self.logger.info("AnalysisRunner initialisé.")
   
   def run_analysis(self, text_content=None, input_file=None, output_dir=None, agent_type=None, analysis_type=None, llm_service=None, use_informal_agent=True, use_pl_agent=True, message_hook=None):
       if text_content is None and input_file is not None:
           extract_agent = self._get_agent_instance("extract")
           text_content = extract_agent.extract_text_from_file(input_file)
       elif text_content is None:
           raise ValueError("text_content ou input_file doit être fourni")
           
       self.logger.info(f"Exécution de l'analyse sur un texte de {len(text_content)} caractères")
       
       if agent_type:
           agent = self._get_agent_instance(agent_type)
           if hasattr(agent, 'analyze_text'):
               analysis_results = agent.analyze_text(text_content)
           else:
               analysis_results = {
                   "fallacies": [],
                   "analysis_metadata": {
                       "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "agent_type": agent_type,
                       "analysis_type": analysis_type
                   }
               }
       else:
           analysis_results = {
               "fallacies": [],
               "analysis_metadata": {
                   "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "analysis_type": analysis_type or "general"
               }
           }
       
       if output_dir:
           os.makedirs(output_dir, exist_ok=True)
           timestamp = time.strftime("%Y%m%d_%H%M%S")
           output_file = os.path.join(output_dir, f"analysis_result_{timestamp}.json")
       else:
           output_file = None
           
       return generate_report(analysis_results, output_file)
   
   async def run_analysis_async(self, text_content, llm_service=None, use_informal_agent=True, use_pl_agent=True, message_hook=None):
       if llm_service is None:
           from argumentation_analysis.core.llm_service import create_llm_service
           llm_service = create_llm_service()
           
       self.logger.info(f"Exécution de l'analyse asynchrone sur un texte de {len(text_content)} caractères")
       
       return await run_analysis_conversation(
           texte_a_analyser=text_content,
           llm_service=llm_service
       )
   
   def run_multi_document_analysis(self, input_files, output_dir=None, agent_type=None, analysis_type=None):
       self.logger.info(f"Exécution de l'analyse multi-documents sur {len(input_files)} fichiers")
       all_results = []
       for input_file in input_files:
           try:
               extract_agent = self._get_agent_instance("extract")
               text_content = extract_agent.extract_text_from_file(input_file)
               if agent_type:
                   agent = self._get_agent_instance(agent_type)
                   if hasattr(agent, 'analyze_text'):
                       file_results = agent.analyze_text(text_content)
                   else:
                       file_results = {"error": "Agent ne supporte pas analyze_text"}
               else:
                   file_results = {"error": "Type d'agent non spécifié"}
               all_results.append({"file": input_file, "results": file_results})
           except Exception as e:
               self.logger.error(f"Erreur lors de l'analyse de {input_file}: {e}")
               all_results.append({"file": input_file, "error": str(e)})
       
       if output_dir:
           os.makedirs(output_dir, exist_ok=True)
           timestamp = time.strftime("%Y%m%d_%H%M%S")
           output_file = os.path.join(output_dir, f"multi_analysis_result_{timestamp}.json")
       else:
           output_file = None
       return generate_report(all_results, output_file)
   
   def _get_agent_instance(self, agent_type, **kwargs):
       self.logger.debug(f"Création d'une instance d'agent de type: {agent_type}")
       if agent_type == "informal":
           from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
           return InformalAnalysisAgent(agent_id=f"informal_agent_{agent_type}", **kwargs)
       elif agent_type == "extract":
           from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
           temp_kernel_for_extract = sk.Kernel() 
           return ExtractAgent(kernel=temp_kernel_for_extract, agent_name=f"temp_extract_agent_for_file_read", **kwargs)
       else:
           raise ValueError(f"Type d'agent non supporté: {agent_type}")

async def run_analysis(text_content, llm_service=None):
   if llm_service is None:
       llm_service = create_llm_service()
   return await run_analysis_conversation(
       texte_a_analyser=text_content,
       llm_service=llm_service
   )

def generate_report(analysis_results, output_path=None):
    logger = logging.getLogger("generate_report")
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"rapport_analyse_{timestamp}.json"
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_results": analysis_results,
        "metadata": {"generator": "AnalysisRunner", "version": "1.0"}
    }
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Rapport généré: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {e}")
        raise

module_logger = logging.getLogger(__name__)
module_logger.debug("Module orchestration.analysis_runner chargé.")

if __name__ == "__main__":
    import argparse 
    parser = argparse.ArgumentParser(description="Exécute l'analyse d'argumentation sur un texte donné.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", type=str, help="Le texte à analyser directement.")
    group.add_argument("--file-path", type=str, help="Chemin vers le fichier texte à analyser.")
    args = parser.parse_args()

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
 
    runner_logger = logging.getLogger("AnalysisRunnerCLI")
    
    text_to_analyze = "" 
    if args.text:
        text_to_analyze = args.text
        runner_logger.info(f"Lancement de AnalysisRunner en mode CLI pour le texte fourni (début) : \"{text_to_analyze[:100]}...\"")
    elif args.file_path:
        runner_logger.info(f"Lancement de AnalysisRunner en mode CLI pour le fichier : \"{args.file_path}\"")
        try:
            with open(args.file_path, 'r', encoding='utf-8') as f:
                text_to_analyze = f.read()
            runner_logger.info(f"Contenu du fichier '{args.file_path}' lu (longueur: {len(text_to_analyze)}).")
            if not text_to_analyze.strip(): 
                 runner_logger.error(f"Le fichier {args.file_path} est vide ou ne contient que des espaces.")
                 sys.exit(1) 
        except FileNotFoundError:
            runner_logger.error(f"Fichier non trouvé : {args.file_path}")
            sys.exit(1) 
        except Exception as e:
            runner_logger.error(f"Erreur lors de la lecture du fichier {args.file_path}: {e}", exc_info=True)
            sys.exit(1) 
    
    try:
        runner_logger.info("Initialisation explicite de la JVM depuis analysis_runner...")
        jvm_ready = initialize_jvm(lib_dir_path=str(LIBS_DIR)) 
        if not jvm_ready:
            runner_logger.error("Échec de l'initialisation de la JVM. L'agent PL et d'autres fonctionnalités Java pourraient ne pas fonctionner.")
        else:
            runner_logger.info("JVM initialisée avec succès (ou déjà prête).")

        runner = AnalysisRunner() 
        asyncio.run(runner.run_analysis_async(text_content=text_to_analyze))
        runner_logger.info("Analyse terminée avec succès.")
    except Exception as e:
        runner_logger.error(f"Une erreur est survenue lors de l'exécution de l'analyse : {e}", exc_info=True)
        print(f"ERREUR CLI: {e}") 
        traceback.print_exc()
