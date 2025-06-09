# orchestration/analysis_runner.py
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
from semantic_kernel.contents.chat_message_content import ChatMessageContent as SKChatMessageContent # Alias pour éviter conflit
from semantic_kernel.kernel import Kernel as SKernel # Alias pour éviter conflit avec Kernel de SK
# KernelArguments est déjà importé plus bas
 # Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité
from argumentation_analysis.utils.semantic_kernel_compatibility import AgentGroupChat, ChatCompletionAgent, Agent, AuthorRole, AgentChatException, FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion # Pour type hint
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports depuis les modules du projet
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import SimpleTerminationStrategy, BalancedParticipationStrategy
# NOTE: create_llm_service n'est plus importé ici, le service est passé en argument

# Fonction d'importation paresseuse pour éviter les importations circulaires
# _lazy_imports() n'est plus nécessaire de la même manière, les classes sont importées directement.

# Imports des classes d'agents refactorées
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent

# Les instructions système sont maintenant gérées par les classes d'agents elles-mêmes.
# PM_INSTRUCTIONS, INFORMAL_AGENT_INSTRUCTIONS, etc., sont utilisées en interne par les agents.

# Logger principal pour cette fonction
logger = logging.getLogger("Orchestration.Run")
# Assurer un handler de base si non configuré globalement
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)


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
        from argumentation_analysis.utils.semantic_kernel_compatibility import Agent
        
        local_pm_agent = Agent(
            name="ProjectManagerAgent",
            kernel=local_kernel,
            instructions=pm_agent_refactored.system_prompt,
            description="Chef de projet pour l'analyse argumentative"
        )
        local_informal_agent = Agent(
            name="InformalAnalysisAgent",
            kernel=local_kernel,
            instructions=informal_agent_refactored.system_prompt,
            description="Analyste des sophismes informels"
        )
        # TEMPORAIREMENT DÉSACTIVÉ - PropositionalLogicAgent
        # local_pl_agent = Agent(
        #     name="PropositionalLogicAgent",
        #     kernel=local_kernel,
        #     instructions=pl_agent_refactored.system_prompt,
        #     description="Analyste de logique propositionnelle"
        # )
        local_extract_agent = Agent(
            name="ExtractAgent",
            kernel=local_kernel,
            instructions=extract_agent_refactored.system_prompt,
            description="Agent d'extraction de données"
        )
        agent_list_local = [local_pm_agent, local_informal_agent, local_extract_agent]  # Sans PropositionalLogicAgent
        run_logger.info(f"   Instances ChatCompletionAgent créées pour AgentGroupChat: {[agent.name for agent in agent_list_local]}.")

        run_logger.info("6. Création instances stratégies locales...")
        local_termination_strategy = SimpleTerminationStrategy(local_state, max_steps=15)
        
        local_selection_strategy = BalancedParticipationStrategy(
            agents=agent_list_local,
            state=local_state,
            default_agent_name="ProjectManagerAgent"
        )
        run_logger.info(f"   Instances stratégies créées (Terminaison id: {id(local_termination_strategy)}, Sélection id: {id(local_selection_strategy)}).")

        run_logger.info("7. Création instance AgentGroupChat locale...")
        local_group_chat = AgentGroupChat(
            agents=agent_list_local,
            selection_strategy=local_selection_strategy,
            termination_strategy=local_termination_strategy
        )
        run_logger.info(f"   Instance AgentGroupChat locale créée (id: {id(local_group_chat)}).")

        run_logger.info("8. Initialisation historique et lancement invoke...")
        initial_prompt = f"Bonjour à tous. Le texte à analyser est :\n'''\n{texte_a_analyser}\n'''\nProjectManagerAgent, merci de définir les premières tâches d'analyse en suivant la séquence logique."

        # Gestion sécurisée de l'affichage Unicode
        try:
            print(f"\n--- Tour 0 (Utilisateur) --- \n{initial_prompt}\n")
        except UnicodeEncodeError:
            # Fallback pour les consoles qui ne supportent pas l'Unicode
            safe_prompt = initial_prompt.encode('ascii', errors='replace').decode('ascii')
            print(f"\n--- Tour 0 (Utilisateur) --- \n{safe_prompt}\n")
        run_logger.info(f"Message initial (Utilisateur): {initial_prompt}")

        if hasattr(local_group_chat, 'history') and hasattr(local_group_chat.history, 'add_user_message'):
            local_group_chat.history.add_user_message(initial_prompt)
            run_logger.info("   Message initial ajouté à l'historique interne de AgentGroupChat.")
        else:
            run_logger.warning("   Impossible d'ajouter le message initial à l'historique interne de AgentGroupChat (attribut manquant?).")

        invoke_start_time = time.time()
        run_logger.info(">>> Début boucle invocation AgentGroupChat <<<")
        turn = 0

        # AgentGroupChat.invoke() retourne List[ChatMessageContent], pas un async iterator
        conversation_messages = await local_group_chat.invoke(initial_prompt)
        run_logger.info(f"Conversation terminée avec {len(conversation_messages)} messages")
        
        # Afficher tous les messages de la conversation
        for turn, message in enumerate(conversation_messages, 1):
            if not message:
                run_logger.warning(f"Tour {turn}: Message vide trouvé. Ignoré.")
                continue

            author_display_name = message.name or getattr(message, 'author_name', f"Role:{getattr(message, 'role', 'unknown')}")
            role_display_name = getattr(message, 'role', 'unknown')

            print(f"\n--- Tour {turn} ({author_display_name} / {role_display_name}) ---")
            run_logger.info(f"----- Tour {turn} - Agent/Author: '{author_display_name}', Role: {role_display_name} -----")

            content_str = str(message.content) if message.content else ""
            content_display = content_str[:2000] + "..." if len(content_str) > 2000 else content_str
            print(f"  Content: {content_display}")
            run_logger.debug(f"  Msg Content T{turn} (Full): {content_str}")
 
            # Recherche d'appels d'outils potentiels
            tool_calls = getattr(message, 'tool_calls', []) or []
            if tool_calls:
                print("   Tool Calls:")
                run_logger.info("   Tool Calls:")
                for tc in tool_calls:
                    plugin_name, func_name = 'N/A', 'N/A'
                    function_name_attr = getattr(getattr(tc, 'function', None), 'name', None)
                    if function_name_attr and isinstance(function_name_attr, str) and '-' in function_name_attr:
                        parts = function_name_attr.split('-', 1)
                        if len(parts) == 2: plugin_name, func_name = parts
                    args_dict = getattr(getattr(tc, 'function', None), 'arguments', {}) or {}
                    args_str = json.dumps(args_dict) if args_dict else "{}"
                    args_display = args_str[:200] + "..." if len(args_str) > 200 else args_str
                    log_msg_tc = f"     - ID: {getattr(tc, 'id', 'N/A')}, Func: {plugin_name}-{func_name}, Args: {args_display}"
                    print(log_msg_tc)
                    run_logger.info(log_msg_tc)
                    run_logger.debug(f"     - Tool Call Full Args: {args_str}")

        invoke_duration = time.time() - invoke_start_time
        run_logger.info(f"<<< Fin boucle invocation ({invoke_duration:.2f} sec) >>>")
        print("\n--- Conversation Terminée ---")

    except AgentChatException as chat_complete_error:
        if "Chat is already complete" in str(chat_complete_error):
            run_logger.warning(f"Chat déjà terminé: {chat_complete_error}")
            print("\n⚠️ Chat déjà marqué comme terminé.")
        else:
            run_logger.error(f"Erreur AgentChatException: {chat_complete_error}", exc_info=True)
            print(f"\nERREUR: Erreur AgentChatException : {chat_complete_error}")
            traceback.print_exc()
    except Exception as e:
        run_logger.error(f"Erreur majeure exécution conversation: {e}", exc_info=True)
        print(f"\nERREUR: Erreur majeure : {e}")
        traceback.print_exc()
    finally:
         run_end_time = time.time()
         total_duration = run_end_time - run_start_time
         run_logger.info(f"Fin analyse. Durée totale: {total_duration:.2f} sec.")

         print("\n--- Historique Détaillé de la Conversation ---")
         final_history_messages = []
         # Utiliser conversation_messages si disponible, sinon essayer local_group_chat.history
         if 'conversation_messages' in locals() and conversation_messages:
             final_history_messages = conversation_messages
         elif local_group_chat and hasattr(local_group_chat, 'history'):
             final_history_messages = local_group_chat.history
         
         if final_history_messages:
             for msg_idx, msg in enumerate(final_history_messages):
                 author = msg.name or getattr(msg, 'author_name', f"Role:{getattr(msg, 'role', 'unknown')}")
                 role_name = getattr(msg, 'role', 'unknown')
                 content_display = str(msg.content)[:2000] + "..." if len(str(msg.content)) > 2000 else str(msg.content)
                 print(f"[{msg_idx}] [{author} ({role_name})]: {content_display}")
                 tool_calls = getattr(msg, 'tool_calls', []) or []
                 if tool_calls:
                     print("   Tool Calls:")
                     for tc_idx, tc in enumerate(tool_calls):
                         plugin_name, func_name = 'N/A', 'N/A'
                         function_name_attr = getattr(getattr(tc, 'function', None), 'name', None)
                         if function_name_attr and isinstance(function_name_attr, str) and '-' in function_name_attr:
                             parts = function_name_attr.split('-', 1)
                             if len(parts) == 2: plugin_name, func_name = parts
                         args_dict = getattr(getattr(tc, 'function', None), 'arguments', {}) or {}
                         args_str = json.dumps(args_dict) if args_dict else "{}"
                         args_display = args_str[:200] + "..." if len(args_str) > 200 else args_str
                         print(f"     [{tc_idx}] - {plugin_name}-{func_name}({args_display})")
         else:
             print("(Historique final vide ou inaccessible)")
         print("----------------------------------------------\n")
         
         if 'raw_logger_hook' in locals() and hasattr(llm_service, "remove_chat_hook_handler"):
             try:
                 llm_service.remove_chat_hook_handler(raw_logger_hook)
                 run_logger.info("RawResponseLogger hook retiré du service LLM.")
             except Exception as e_rm_hook:
                 run_logger.warning(f"Erreur lors du retrait du RawResponseLogger hook: {e_rm_hook}")
 
         print("=========================================")
         print("== Fin de l'Analyse Collaborative ==")
         print(f"== Durée: {total_duration:.2f} secondes ==")
         print("=========================================")
         print("\n--- État Final de l'Analyse (Instance Locale) ---")
         if local_state:
             try: print(local_state.to_json(indent=2))
             except Exception as e_json: print(f"(Erreur sérialisation état final: {e_json})"); print(f"Repr: {repr(local_state)}")
         else: print("(Instance état locale non disponible)")

         jvm_status = "(JVM active)" if ('jpype' in globals() and jpype.isJVMStarted()) else "(JVM non active)"
         print(f"\n{jvm_status}")
         run_logger.info(f"État final JVM: {jvm_status}")
         run_logger.info(f"--- Fin Run_{run_id} ---")

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
       from argumentation_analysis.core.llm_service import create_llm_service
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
