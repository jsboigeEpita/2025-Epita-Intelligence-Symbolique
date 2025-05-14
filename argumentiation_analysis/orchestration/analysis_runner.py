# orchestration/analysis_runner.py
import time
import traceback
import asyncio
import logging
import json
import random
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
from argumentiation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentiation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentiation_analysis.core.strategies import SimpleTerminationStrategy, BalancedParticipationStrategy
# NOTE: create_llm_service n'est plus importé ici, le service est passé en argument

# Imports des définitions d'agents (setup + instructions)
from argumentiation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel, PM_INSTRUCTIONS
from argumentiation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel, INFORMAL_AGENT_INSTRUCTIONS
from argumentiation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel, PL_AGENT_INSTRUCTIONS
from argumentiation_analysis.agents.core.extract.extract_agent import setup_extract_agent
from argumentiation_analysis.agents.core.extract.prompts import EXTRACT_AGENT_INSTRUCTIONS

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

        # 4. Configurer plugins agents sur Kernel local
        run_logger.info("4. Configuration plugins agents sur Kernel local...")
        # Passer l'instance de service LLM aux fonctions setup
        setup_pm_kernel(local_kernel, llm_service)
        setup_informal_kernel(local_kernel, llm_service)
        setup_pl_kernel(local_kernel, llm_service) # Cette fonction vérifie maintenant la JVM en interne
        # Configuration de l'agent d'extraction
        extract_kernel, extract_agent_instance = await setup_extract_agent(llm_service)
        run_logger.info("   Plugins agents configurés.")
        run_logger.debug(f"   Plugins enregistrés: {list(local_kernel.plugins.keys())}")

        # 5. Créer instances agents locales
        run_logger.info("5. Création instances agents...")
        # Utiliser l'instance de service LLM passée en argument pour obtenir les settings
        prompt_exec_settings = local_kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
        prompt_exec_settings.function_choice_behavior = FunctionChoiceBehavior.Auto(auto_invoke_kernel_functions=True, max_auto_invoke_attempts=5)
        run_logger.info(f"   Settings LLM (auto function call): {prompt_exec_settings.function_choice_behavior}")

        # Utiliser l'instance de service LLM passée en argument pour créer les agents
        local_pm_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="ProjectManagerAgent",
            instructions=PM_INSTRUCTIONS, arguments=KernelArguments(settings=prompt_exec_settings)
        )
        local_informal_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="InformalAnalysisAgent",
            instructions=INFORMAL_AGENT_INSTRUCTIONS, arguments=KernelArguments(settings=prompt_exec_settings)
        )
        local_pl_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="PropositionalLogicAgent",
            instructions=PL_AGENT_INSTRUCTIONS, arguments=KernelArguments(settings=prompt_exec_settings)
        )
        # Création de l'agent d'extraction
        local_extract_agent = ChatCompletionAgent(
            kernel=local_kernel, service=llm_service, name="ExtractAgent",
            instructions=EXTRACT_AGENT_INSTRUCTIONS, arguments=KernelArguments(settings=prompt_exec_settings)
        )
        agent_list_local = [local_pm_agent, local_informal_agent, local_pl_agent, local_extract_agent]
        run_logger.info(f"   Instances agents créées: {[agent.name for agent in agent_list_local]}.")

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

# Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module orchestration.analysis_runner chargé.")