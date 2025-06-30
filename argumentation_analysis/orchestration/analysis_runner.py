# orchestration/analysis_runner.py
import sys
import os

import time
import traceback
import asyncio
import logging
import json
import random
from typing import List, Optional, Union, Any, Dict

# from argumentation_analysis.core.jvm_setup import initialize_jvm
# from argumentation_analysis.paths import LIBS_DIR # Nécessaire pour initialize_jvm

# Imports pour le hook LLM
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent as SKChatMessageContent
from semantic_kernel.kernel import Kernel as SKernel
# Imports Semantic Kernel
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat
from semantic_kernel.agents.agent import Agent
from semantic_kernel.exceptions import AgentChatException
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion # Pour type hint
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory

# Correct imports
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.kernel.kernel_builder import KernelBuilder
from argumentation_analysis.agents.agent_factory import AgentFactory


# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnalysisRunner:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.kernel = KernelBuilder.create_kernel(self.settings)
        self.llm_service_id = self.settings.service_manager.default_llm_service_id
        self.factory = AgentFactory(self.kernel, self.llm_service_id)

    async def run_analysis(self, input_text: str) -> list[ChatMessageContent]:
        logger.info("Démarrage du processus d'analyse d'argumentation.")

        try:
            fallacy_agent = self.factory.create_informal_fallacy_agent()
            manager_agent = self.factory.create_project_manager_agent()
            logger.info(f"Agents créés : {fallacy_agent.name}, {manager_agent.name}")
        except Exception as e:
            logger.error(f"Erreur lors de la création des agents : {e}")
            return []

        chat_history = ChatHistory()
        chat_history.add_message(message=ChatMessageContent(role=AuthorRole.USER, content=input_text))

        chat = await AgentGroupChat(
            agents=[manager_agent, fallacy_agent],
            chat_history=chat_history
        )
        logger.info("AgentGroupChat créé et pré-configuré avec l'historique initial.")

        logger.info(f"Début de l'invocation du chat.")
        
        history = [chat_history.messages[0]]
        async for message in await chat.invoke():
            history.append(message)
        
        logger.info("Invocation du chat terminée.")
        return history

async def main():
    """
    Orchestre l'analyse d'argumentation en utilisant une flotte d'agents spécialisés.
    """
    try:
        settings = AppSettings()
        runner = AnalysisRunner(settings)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Erreur de configuration critique: {e}")
        return

    input_text = (
        "Le sénateur prétend que sa loi va créer des emplois, "
        "mais il a été vu en train de manger une glace au chocolat. "
        "On ne peut pas faire confiance à un homme politique qui aime le chocolat. "
        "Son projet est donc mauvais."
    )

    history = await runner.run_analysis(input_text)
    
    # Affichage des résultats
    for message in history:
        print(f"[{message.role.value.upper()}] - {message.name or 'User'}:\n---\n{message.content}\n---")
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
