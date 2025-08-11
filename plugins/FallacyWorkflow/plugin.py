# Fichier: argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py
import asyncio
import csv
import json
import logging
import uuid
from typing import Annotated, List, Optional

from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import KernelFunction
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory, AuthorRole, FunctionCallContent, ChatMessageContent, FunctionResultContent, StreamingChatMessageContent
from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

# Configuration du logging pour semantic-kernel
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("semantic_kernel").setLevel(logging.DEBUG)

class FallacyWorkflowPlugin:
    """
    Plugin orchestrant le workflow d'analyse de sophismes en utilisant une approche "one-shot".
    Le LLM reçoit la taxonomie complète et doit retourner directement le sophisme identifié.
    """

    def __init__(
        self,
        master_kernel: Kernel,
        llm_service: OpenAIChatCompletion,
        taxonomy_file_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialise le plugin du workflow."""
        self.master_kernel = master_kernel
        self.llm_service = llm_service
        self.logger = logger or logging.getLogger(__name__)
        self.language = "fr"

        taxonomy_data = []
        if taxonomy_file_path:
            try:
                with open(taxonomy_file_path, mode='r', encoding='utf-8') as infile:
                    reader = csv.DictReader(infile)
                    taxonomy_data = list(reader)
                    pass # Le log de debug n'est plus nécessaire
            except FileNotFoundError:
                self.logger.error(f"Taxonomy file not found at {taxonomy_file_path}")
            except Exception as e:
                self.logger.error(f"Error reading taxonomy file: {e}")

        self.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=taxonomy_data)
        if self.taxonomy_navigator.get_root_nodes():
            self.logger.info("Taxonomy loaded successfully.")
        else:
            self.logger.error("Taxonomy loading failed or has no root.")
        

    def _create_one_shot_kernel(self) -> tuple[Kernel, OpenAIPromptExecutionSettings]:
        """Crée et configure le kernel pour l'analyse 'one-shot'."""
        one_shot_kernel = Kernel()
        one_shot_kernel.add_service(self.llm_service)
        # Plus de plugin de parsing, le LLM doit répondre en texte brut.
        
        # Les settings sont simplifiés, on n'impose plus d'appel de fonction.
        one_shot_exec_settings = OpenAIPromptExecutionSettings(
            # On laisse le LLM décider (auto) ou répondre en texte (none).
            # Pour ce cas, 'none' est plus sûr pour garantir une réponse textuelle.
            function_choice_behavior=FunctionChoiceBehavior.NONE
        )
        return one_shot_kernel, one_shot_exec_settings

    @kernel_function(
        name="run_guided_analysis",
        description="Exécute une analyse 'one-shot' pour identifier les sophismes dans un texte."
    )
    async def run_guided_analysis(
        self,
        argument_text: Annotated[str, "Le texte de l'argument à analyser."],
        trace_log_path: Optional[str] = None
    ) -> Annotated[str, "Le résultat final de l'analyse, listant les sophismes identifiés."]:
        """
        Exécute une analyse 'one-shot' où le LLM reçoit la taxonomie complète et doit
        choisir le sophisme le plus pertinent.
        """
        print("!!!!!! -------- FallacyWorkflowPlugin.run_guided_analysis (One-Shot) CALLED -------- !!!!!")
        
        file_handler = None
        if trace_log_path:
            file_handler = logging.FileHandler(trace_log_path, mode='w', encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            loggers_to_update = [self.logger, logging.getLogger("semantic_kernel"), logging.getLogger("argumentation_analysis")]
            for l in loggers_to_update:
                l.addHandler(file_handler)

        try:
            self.logger.info(f"--- Starting One-Shot Fallacy Analysis for: '{argument_text[:80]}...' ---")

            one_shot_kernel, one_shot_exec_settings = self._create_one_shot_kernel()
            one_shot_system_message = (
                "You are an expert in logical fallacies. Your task is to analyze the provided text and identify the most specific and relevant fallacy from the complete taxonomy given below. "
                "Carefully consider the definition and example for each fallacy. "
                "You MUST respond with only the exact name of the identified fallacy and nothing else."
            )

            # Obtenir la taxonomie complète formatée en JSON
            full_taxonomy_json = self.taxonomy_navigator.get_taxonomy_as_json()
            
            prompt = (
                f"Analyze the following text:\n--- TEXT ---\n{argument_text}\n--- END TEXT ---\n\n"
                "Based on the text, identify the single most relevant fallacy from the taxonomy below. "
                "Your answer must be only the name of the fallacy.\n\n"
                f"--- COMPLETE FALLACY TAXONOMY ---\n{full_taxonomy_json}\n--- END TAXONOMY ---"
            )
            
            history = ChatHistory(system_message=one_shot_system_message)
            history.add_user_message(prompt)
            
            self.logger.info(f"--- Sending prompt for one-shot analysis ---")
            
            # Le LLM est maintenant configuré pour répondre directement en texte.
            response = await self.llm_service.get_chat_message_content(
                chat_history=history,
                settings=one_shot_exec_settings,
                kernel=one_shot_kernel
            )
            
            self.logger.info(f"LLM response received: {response}")

            # Extraire directement le contenu texte de la réponse.
            final_fallacy_name = str(response).strip()
            self.logger.info(f"--- Analysis complete. Identified fallacy: {final_fallacy_name} ---")
            return final_fallacy_name

        except Exception as e:
            self.logger.error(f"An error occurred during one-shot analysis: {e}", exc_info=True)
            return f"Error during analysis: {e}"
        finally:
            if file_handler:
                loggers_to_update = [self.logger, logging.getLogger("semantic_kernel"), logging.getLogger("argumentation_analysis")]
                for l in loggers_to_update:
                    l.removeHandler(file_handler)
                file_handler.close()