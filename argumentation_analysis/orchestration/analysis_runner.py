# orchestration/analysis_runner.py
import time
import traceback
import asyncio
import logging
import json
import random
import os
import jpype # Pour la vérification finale de la JVM
from typing import List, Optional, Union # Ajout Union

# Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent, Agent
from semantic_kernel.exceptions import AgentChatException
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion # Pour type hint
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
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
    """
    Orchestre une conversation d'analyse rhétorique multi-agents.

    Crée des instances locales de l'état, du kernel, des agents,
    des stratégies et lance la conversation via AgentGroupChat.

    Args:
        texte_a_analyser (str): Le texte brut à analyser.
        llm_service (Union[OpenAIChatCompletion, AzureChatCompletion]): L'instance
                                 du service LLM (OpenAI ou Azure) à utiliser.
    """
    run_start_time = time.time()
    run_id = random.randint(1000, 9999)
    print("\n=====================================================")
    print(f"== Début de l'Analyse Collaborative (Run_{run_id}) ==")
    print("=====================================================")
    run_logger = logging.getLogger(f"Orchestration.Run.{run_id}")
    run_logger.info("--- Début Nouveau Run ---")

    # Vérification argument llm_service
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
        # 1. Créer instance état locale
        run_logger.info("1. Création instance état locale...")
        local_state = RhetoricalAnalysisState(initial_text=texte_a_analyser)
        run_logger.info(f"   Instance état locale créée (id: {id(local_state)}) avec texte (longueur: {len(texte_a_analyser)}).")

        # 2. Créer instance StateManagerPlugin locale
        run_logger.info("2. Création instance StateManagerPlugin locale...")
        local_state_manager_plugin = StateManagerPlugin(local_state)
        run_logger.info(f"   Instance StateManagerPlugin locale créée (id: {id(local_state_manager_plugin)}).")

        # 3. Créer Kernel local
        run_logger.info("3. Création Kernel local...")
        local_kernel = sk.Kernel()
        # Utiliser l'instance de service LLM passée en argument
        local_kernel.add_service(llm_service)
        run_logger.info(f"   Service LLM '{llm_service.service_id}' ajouté.")
        local_kernel.add_plugin(local_state_manager_plugin, plugin_name="StateManager")
        run_logger.info(f"   Plugin 'StateManager' (local) ajouté.")

        # 4. Créer et configurer les instances des agents refactorés
        run_logger.info("4. Création et configuration des instances d'agents refactorés...")
        llm_service_id_str = llm_service.service_id # Utilisé pour setup_agent_components

        # Instanciation et configuration du ProjectManagerAgent
        pm_agent_refactored = ProjectManagerAgent(kernel=local_kernel, agent_name="ProjectManagerAgent_Refactored")
        pm_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {pm_agent_refactored.name} instancié et configuré.")

        # Instanciation et configuration de l'InformalAnalysisAgent
        informal_agent_refactored = InformalAnalysisAgent(kernel=local_kernel, agent_name="InformalAnalysisAgent_Refactored")
        informal_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {informal_agent_refactored.name} instancié et configuré.")

        # Instanciation et configuration du PropositionalLogicAgent
        pl_agent_refactored = PropositionalLogicAgent(kernel=local_kernel, agent_name="PropositionalLogicAgent_Refactored")
        pl_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {pl_agent_refactored.name} instancié et configuré.")

        # Instanciation et configuration de l'ExtractAgent
        extract_agent_refactored = ExtractAgent(kernel=local_kernel, agent_name="ExtractAgent_Refactored")
        extract_agent_refactored.setup_agent_components(llm_service_id=llm_service_id_str)
        run_logger.info(f"   Agent {extract_agent_refactored.name} instancié et configuré.")
        
        run_logger.debug(f"   Plugins enregistrés dans local_kernel après setup des agents: {list(local_kernel.plugins.keys())}")

        # 5. Créer instances agents pour AgentGroupChat (enveloppant les agents refactorés)
        run_logger.info("5. Création des instances ChatCompletionAgent pour AgentGroupChat...")
        prompt_exec_settings = local_kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
        prompt_exec_settings.function_choice_behavior = FunctionChoiceBehavior.Auto(auto_invoke_kernel_functions=True, max_auto_invoke_attempts=5)
        run_logger.info(f"   Settings LLM pour ChatCompletionAgent (auto function call): {prompt_exec_settings.function_choice_behavior}")

        local_pm_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="ProjectManagerAgent",
            instructions=pm_agent_refactored.system_prompt, # Utilise le system_prompt de l'agent refactoré
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        local_informal_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="InformalAnalysisAgent",
            instructions=informal_agent_refactored.system_prompt, # Utilise le system_prompt de l'agent refactoré
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        local_pl_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="PropositionalLogicAgent",
            instructions=pl_agent_refactored.system_prompt, # Utilise le system_prompt de l'agent refactoré
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        local_extract_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="ExtractAgent",
            instructions=extract_agent_refactored.system_prompt, # Utilise le system_prompt de l'agent refactoré
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        agent_list_local = [local_pm_agent, local_informal_agent, local_pl_agent, local_extract_agent]
        run_logger.info(f"   Instances ChatCompletionAgent créées pour AgentGroupChat: {[agent.name for agent in agent_list_local]}.")

        # 6. Créer instances stratégies locales
        run_logger.info("6. Création instances stratégies locales...")
        local_termination_strategy = SimpleTerminationStrategy(local_state, max_steps=15)
        
        # Utilisation de la nouvelle stratégie d'équilibrage de participation
        local_selection_strategy = BalancedParticipationStrategy(
            agents=agent_list_local,
            state=local_state,
            default_agent_name="ProjectManagerAgent"
        )
        run_logger.info(f"   Instances stratégies créées (Terminaison id: {id(local_termination_strategy)}, Sélection id: {id(local_selection_strategy)}).")

        # 7. Créer instance AgentGroupChat locale
        run_logger.info("7. Création instance AgentGroupChat locale...")
        local_group_chat = AgentGroupChat(
            agents=agent_list_local,
            selection_strategy=local_selection_strategy,
            termination_strategy=local_termination_strategy
        )
        run_logger.info(f"   Instance AgentGroupChat locale créée (id: {id(local_group_chat)}).")

        # 8. Initialiser historique et lancer invoke
        run_logger.info("8. Initialisation historique et lancement invoke...")
        # Utiliser le texte reçu dans le prompt initial
        initial_prompt = f"Bonjour à tous. Le texte à analyser est :\n'''\n{texte_a_analyser}\n'''\nProjectManagerAgent, merci de définir les premières tâches d'analyse en suivant la séquence logique."

        print(f"\n--- Tour 0 (Utilisateur) --- \n{initial_prompt}\n")
        run_logger.info(f"Message initial (Utilisateur): {initial_prompt}")

        # Ajouter le message initial à l'historique INTERNE du chat
        if hasattr(local_group_chat, 'history') and hasattr(local_group_chat.history, 'add_user_message'):
            local_group_chat.history.add_user_message(initial_prompt)
            run_logger.info("   Message initial ajouté à l'historique interne de AgentGroupChat.")
        else:
            run_logger.warning("   Impossible d'ajouter le message initial à l'historique interne de AgentGroupChat (attribut manquant?).")

        invoke_start_time = time.time()
        run_logger.info(">>> Début boucle invocation AgentGroupChat <<<")
        turn = 0

        # --- Boucle Invoke ---
        async for message in local_group_chat.invoke():
             turn += 1
             if not message: # Vérifier si l'objet message lui-même est None/vide
                 run_logger.warning(f"Tour {turn}: Invoke a retourné un message vide. Arrêt.")
                 break

             author_display_name = message.name or getattr(message, 'author_name', f"Role:{message.role.name}")
             role_display_name = message.role.name

             print(f"\n--- Tour {turn} ({author_display_name} / {role_display_name}) ---")
             run_logger.info(f"----- Début Tour {turn} - Agent/Author: '{author_display_name}', Role: {role_display_name} -----")

             content_str = str(message.content) if message.content else ""
             content_display = content_str[:500] + "..." if len(content_str) > 500 else content_str
             print(f"  Content: {content_display}")
             run_logger.debug(f"  Msg Content T{turn} (Full): {content_str}")

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

             await asyncio.sleep(0.05) # Garder un petit sleep

        invoke_duration = time.time() - invoke_start_time
        run_logger.info(f"<<< Fin boucle invocation ({invoke_duration:.2f} sec) >>>")
        print("\n--- Conversation Terminée ---")

    except AgentChatException as chat_complete_error:
        if "Chat is already complete" in str(chat_complete_error):
            run_logger.warning(f"Chat déjà terminé: {chat_complete_error}")
            print("\n⚠️ Chat déjà marqué comme terminé.")
        else:
            run_logger.error(f"Erreur AgentChatException: {chat_complete_error}", exc_info=True)
            print(f"\n❌ Erreur AgentChatException : {chat_complete_error}")
            traceback.print_exc()
    except Exception as e:
        run_logger.error(f"Erreur majeure exécution conversation: {e}", exc_info=True)
        print(f"\n❌ Erreur majeure : {e}")
        traceback.print_exc()
    finally:
        # --- Affichage Final ---
         run_end_time = time.time()
         total_duration = run_end_time - run_start_time
         run_logger.info(f"Fin analyse. Durée totale: {total_duration:.2f} sec.")

         print("\n--- Historique Détaillé ---")
         final_history_messages = []
         if local_group_chat and hasattr(local_group_chat, 'history') and hasattr(local_group_chat.history, 'messages'):
             final_history_messages = local_group_chat.history.messages

         if final_history_messages:
             for msg_idx, msg in enumerate(final_history_messages): # Ajouter index pour clarté
                 author = msg.name or getattr(msg, 'author_name', f"Role:{msg.role.name}")
                 role_name = msg.role.name
                 content_display = str(msg.content)[:500] + "..." if len(str(msg.content)) > 500 else str(msg.content)
                 print(f"[{msg_idx}] [{author} ({role_name})]: {content_display}") # Index ajouté
                 tool_calls = getattr(msg, 'tool_calls', []) or []
                 if tool_calls:
                     print("   Tool Calls:")
                     for tc in tool_calls:
                         plugin_name, func_name = 'N/A', 'N/A'
                         function_name_attr = getattr(getattr(tc, 'function', None), 'name', None)
                         if function_name_attr and isinstance(function_name_attr, str) and '-' in function_name_attr:
                             parts = function_name_attr.split('-', 1)
                             if len(parts) == 2: plugin_name, func_name = parts
                         args_dict = getattr(getattr(tc, 'function', None), 'arguments', {}) or {}
                         args_str = json.dumps(args_dict) if args_dict else "{}"
                         args_display = args_str[:100] + "..." if len(args_str) > 100 else args_str
                         print(f"     - {plugin_name}-{func_name}({args_display})")
         else:
             print("(Historique final vide ou inaccessible)")
         print("---------------------------\n")

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

# Classe AnalysisRunner pour encapsuler la fonction run_analysis_conversation
class AnalysisRunner:
   """
   Classe pour encapsuler la fonction run_analysis_conversation.
   
   Cette classe permet d'exécuter une analyse rhétorique en utilisant
   la fonction run_analysis_conversation avec des paramètres supplémentaires.
   """
   
   def __init__(self, strategy=None):
       """
       Initialise un AnalysisRunner.
       
       Args:
           strategy: La stratégie à utiliser pour l'analyse (non utilisée actuellement)
       """
       self.strategy = strategy
       self.logger = logging.getLogger("AnalysisRunner")
       self.logger.info("AnalysisRunner initialisé.")
   
   def run_analysis(self, text_content=None, input_file=None, output_dir=None, agent_type=None, analysis_type=None, llm_service=None, use_informal_agent=True, use_pl_agent=True, message_hook=None):
       """
       Exécute une analyse rhétorique sur le texte fourni.
       
       Args:
           text_content: Le texte à analyser (optionnel si input_file est fourni)
           input_file: Fichier d'entrée à analyser (optionnel si text_content est fourni)
           output_dir: Répertoire de sortie pour les résultats
           agent_type: Type d'agent à utiliser pour l'analyse
           analysis_type: Type d'analyse à effectuer
           llm_service: Le service LLM à utiliser
           use_informal_agent: Indique si l'agent informel doit être utilisé
           use_pl_agent: Indique si l'agent PL doit être utilisé
           message_hook: Hook pour intercepter les messages entre agents
           
       Returns:
           str: Le chemin du fichier de résultats généré
       """
       # Obtenir le texte à analyser
       if text_content is None and input_file is not None:
           # Utiliser l'agent d'extraction pour lire le fichier
           extract_agent = self._get_agent_instance("extract")
           text_content = extract_agent.extract_text_from_file(input_file)
       elif text_content is None:
           raise ValueError("text_content ou input_file doit être fourni")
           
       # Exécuter l'analyse
       self.logger.info(f"Exécution de l'analyse sur un texte de {len(text_content)} caractères")
       
       # Obtenir l'agent approprié
       if agent_type:
           agent = self._get_agent_instance(agent_type)
           # Exécuter l'analyse avec l'agent spécifique
           if hasattr(agent, 'analyze_text'):
               analysis_results = agent.analyze_text(text_content)
           else:
               # Fallback vers des résultats simulés pour les tests
               analysis_results = {
                   "fallacies": [],
                   "analysis_metadata": {
                       "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "agent_type": agent_type,
                       "analysis_type": analysis_type
                   }
               }
       else:
           # Résultats simulés si aucun agent spécifique
           analysis_results = {
               "fallacies": [],
               "analysis_metadata": {
                   "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "analysis_type": analysis_type or "general"
               }
           }
       
       # Générer le rapport
       if output_dir:
           os.makedirs(output_dir, exist_ok=True)
           timestamp = time.strftime("%Y%m%d_%H%M%S")
           output_file = os.path.join(output_dir, f"analysis_result_{timestamp}.json")
       else:
           output_file = None
           
       return generate_report(analysis_results, output_file)
   
   async def run_analysis_async(self, text_content, llm_service=None, use_informal_agent=True, use_pl_agent=True, message_hook=None):
       """
       Version asynchrone de run_analysis pour la conversation complète.
       
       Args:
           text_content: Le texte à analyser
           llm_service: Le service LLM à utiliser
           use_informal_agent: Indique si l'agent informel doit être utilisé
           use_pl_agent: Indique si l'agent PL doit être utilisé
           message_hook: Hook pour intercepter les messages entre agents
           
       Returns:
           Les résultats de l'analyse
       """
       # Créer le service LLM si non fourni
       if llm_service is None:
           from argumentation_analysis.core.llm_service import create_llm_service
           llm_service = create_llm_service()
           
       # Exécuter l'analyse
       self.logger.info(f"Exécution de l'analyse asynchrone sur un texte de {len(text_content)} caractères")
       
       # Appeler la fonction run_analysis_conversation
       return await run_analysis_conversation(
           texte_a_analyser=text_content,
           llm_service=llm_service
       )
   
   def run_multi_document_analysis(self, input_files, output_dir=None, agent_type=None, analysis_type=None):
       """
       Exécute une analyse rhétorique sur plusieurs documents.
       
       Args:
           input_files: Liste des fichiers d'entrée à analyser
           output_dir: Répertoire de sortie pour les résultats
           agent_type: Type d'agent à utiliser pour l'analyse
           analysis_type: Type d'analyse à effectuer
           
       Returns:
           str: Le chemin du fichier de résultats consolidé
       """
       self.logger.info(f"Exécution de l'analyse multi-documents sur {len(input_files)} fichiers")
       
       all_results = []
       
       # Analyser chaque fichier
       for input_file in input_files:
           try:
               # Utiliser l'agent d'extraction pour lire le fichier
               extract_agent = self._get_agent_instance("extract")
               text_content = extract_agent.extract_text_from_file(input_file)
               
               # Obtenir l'agent approprié pour l'analyse
               if agent_type:
                   agent = self._get_agent_instance(agent_type)
                   if hasattr(agent, 'analyze_text'):
                       file_results = agent.analyze_text(text_content)
                   else:
                       file_results = {"error": "Agent ne supporte pas analyze_text"}
               else:
                   file_results = {"error": "Type d'agent non spécifié"}
               
               all_results.append({
                   "file": input_file,
                   "results": file_results
               })
               
           except Exception as e:
               self.logger.error(f"Erreur lors de l'analyse de {input_file}: {e}")
               all_results.append({
                   "file": input_file,
                   "error": str(e)
               })
       
       # Générer le rapport consolidé
       if output_dir:
           os.makedirs(output_dir, exist_ok=True)
           timestamp = time.strftime("%Y%m%d_%H%M%S")
           output_file = os.path.join(output_dir, f"multi_analysis_result_{timestamp}.json")
       else:
           output_file = None
           
       return generate_report(all_results, output_file)
   
   def _get_agent_instance(self, agent_type, **kwargs):
       """
       Obtient une instance d'agent du type spécifié.
       
       Args:
           agent_type: Le type d'agent à créer ("informal", "extract", etc.)
           **kwargs: Arguments supplémentaires pour la création de l'agent
           
       Returns:
           L'instance de l'agent
       """
       self.logger.debug(f"Création d'une instance d'agent de type: {agent_type}")
       
       if agent_type == "informal":
           from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
           return InformalAgent(agent_id=f"informal_agent_{agent_type}", **kwargs)
       elif agent_type == "extract":
           from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
           return ExtractAgentAdapter(**kwargs)
       else:
           raise ValueError(f"Type d'agent non supporté: {agent_type}")

# Fonction pour exécuter l'analyse depuis l'extérieur du module
async def run_analysis(text_content, llm_service=None):
   """Fonction wrapper pour exécuter l'analyse depuis l'extérieur du module."""
   if llm_service is None:
       from argumentation_analysis.core.llm_service import create_llm_service
       llm_service = create_llm_service()
   
   return await run_analysis_conversation(
       texte_a_analyser=text_content,
       llm_service=llm_service
   )

def generate_report(analysis_results, output_path=None):
    """
    Génère un rapport d'analyse rhétorique.
    
    Args:
        analysis_results: Les résultats de l'analyse
        output_path: Le chemin de sortie pour le rapport (optionnel)
        
    Returns:
        str: Le chemin du fichier de rapport généré
    """
    logger = logging.getLogger("generate_report")
    
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"rapport_analyse_{timestamp}.json"
    
    # Créer le répertoire de sortie si nécessaire
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Préparer les données du rapport
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_results": analysis_results,
        "metadata": {
            "generator": "AnalysisRunner",
            "version": "1.0"
        }
    }
    
    # Écrire le rapport
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Rapport généré: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {e}")
        raise

# Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module orchestration.analysis_runner chargé.")