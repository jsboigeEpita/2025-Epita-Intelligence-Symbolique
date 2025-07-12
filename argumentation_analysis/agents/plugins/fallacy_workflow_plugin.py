# Fichier: argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py
import asyncio
import csv
import json
import logging
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
from .exploration_plugin import ExplorationPlugin
from .identification_plugin import IdentificationPlugin

# Configuration du logging pour semantic-kernel
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("semantic_kernel").setLevel(logging.DEBUG)

class FallacyWorkflowPlugin:
    """
    Plugin orchestrant le workflow d'analyse de sophismes en utilisant une architecture maître-esclave.
    Le maître gère le processus global, tandis que l'esclave est un agent spécialisé et contraint
    qui explore la taxonomie des sophismes.
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
                    for row in reader:
                        taxonomy_data.append(row)
            except FileNotFoundError:
                self.logger.error(f"Taxonomy file not found at {taxonomy_file_path}")
            except Exception as e:
                self.logger.error(f"Error reading taxonomy file: {e}")

        self.taxonomy_navigator = TaxonomyNavigator(taxonomy_data=taxonomy_data)
        root_nodes = self.taxonomy_navigator.get_root_nodes()
        if root_nodes:
            self.logger.info(
                f"Taxonomy loaded. First root node: {root_nodes[0].get('PK')}"
            )
        else:
            self.logger.error(f"Taxonomy loading failed or has no root.")
        self.exploration_plugin = ExplorationPlugin(taxonomy_navigator=self.taxonomy_navigator)

    def _create_slave_kernel(self) -> tuple[Kernel, OpenAIPromptExecutionSettings]:
        """Crée et configure le kernel 'esclave' pour l'exploration de la taxonomie."""
        slave_kernel = Kernel()
        slave_kernel.add_service(self.llm_service)
        slave_kernel.add_plugin(self.exploration_plugin, "Exploration")

        slave_exec_settings = OpenAIPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                auto_invoke=False
            )
        )
        return slave_kernel, slave_exec_settings

    async def _explore_single_branch(
        self,
        argument_text: str,
        start_node_pk: str,
        slave_kernel: Kernel,
        slave_exec_settings: OpenAIPromptExecutionSettings,
        slave_system_message: str,
    ) -> Optional[dict]:
        """Explore une seule branche de la taxonomie à partir d'un noeud donné."""
        self.logger.info(f"\n--- [Branch Exploration] Starting at node: {start_node_pk} ---")
        candidate_nodes = [start_node_pk]
        
        for i in range(5):  # Limite de 5 itérations par branche
            self.logger.info(f"  [Branch Iteration {i+1}] Candidates: {candidate_nodes}")

            children = self.taxonomy_navigator.get_children(candidate_nodes[0])
            if not children:
                self.logger.info(f"  [Branch End] No children for {candidate_nodes[0]}. Confirming this node.")
                return self.taxonomy_navigator.get_node(candidate_nodes[0])

            options_to_present = []
            current_node_data = self.taxonomy_navigator.get_node(candidate_nodes[0])
            options_to_present.append({
                "id": candidate_nodes[0], "name": current_node_data[f"text_{self.language}"],
                "description": f"PARENT (Confirm this): {current_node_data[f'desc_{self.language}']}"
            })
            for child in children:
                options_to_present.append({
                    "id": child["PK"], "name": child[f"text_{self.language}"],
                    "description": f"CHILD (Explore this): {child[f'desc_{self.language}']}",
                    "example": child[f'example_{self.language}']
                })
            
            context_for_slave = (
                f"Text to analyze: '{argument_text}'\n\n"
                "You are analyzing ONE specific branch. Select the SINGLE most promising path to continue.\n"
                f"{json.dumps(options_to_present, indent=2, ensure_ascii=False)}"
            )

            history = ChatHistory(system_message=slave_system_message)
            history.add_user_message(context_for_slave)
            response_message = await self.llm_service.get_chat_message_content(
                chat_history=history, settings=slave_exec_settings, kernel=slave_kernel
            )
            
            explore_calls = [c for c in response_message.items if isinstance(c, FunctionCallContent) and c.name == "Exploration-explore_branch"]
            if not explore_calls:
                self.logger.info(f"  [Branch End] LLM did not choose a path. Confirming {candidate_nodes[0]}.")
                return self.taxonomy_navigator.get_node(candidate_nodes[0])

            next_pk = json.loads(explore_calls[0].arguments)["node_pk"]
            if next_pk == candidate_nodes[0]:
                self.logger.info(f"  [Branch End] LLM confirmed parent {next_pk}, indicating a dead end for this branch.")
                return None

            candidate_nodes = [next_pk]

        self.logger.warning(f"  [Branch End] Max iterations reached for starting node {start_node_pk}. Branch failed.")
        return None


    @kernel_function(
        name="run_guided_analysis",
        description="Exécute un workflow guidé pour analyser un texte et identifier les sophismes."
    )
    async def run_guided_analysis(
        self, argument_text: Annotated[str, "Le texte de l'argument à analyser."]
    ) -> Annotated[str, "Le résultat final de l'analyse, listant les sophismes identifiés."]:
        print("!!!!!! -------- FallacyWorkflowPlugin.run_guided_analysis (Parallel) CALLED -------- !!!!!")
        self.logger.info(f"--- Starting Guided Fallacy Analysis for: '{argument_text[:80]}...' ---")

        slave_kernel, slave_exec_settings = self._create_slave_kernel()
        root_nodes = self.taxonomy_navigator.get_root_nodes()
        if not root_nodes:
            return json.dumps({"error": "No root nodes found."}, indent=2)

        slave_system_message = "Your ONLY purpose is to classify text by navigating a taxonomy. You MUST call one function. Do NOT output any other text."

        self.logger.info("--- Phase 1: Identifying initial candidate branches with new prompt logic ---")

        prompt_parts = []
        for root in root_nodes:
            root_node = self.taxonomy_navigator.get_node(root["PK"])
            if not root_node:
                continue

            category_pk = root_node.get('PK')
            category_name = root_node.get('text_en', 'Unnamed Category')
            category_desc = root_node.get('desc_en', 'No description available.')

            children_details = []
            children = self.taxonomy_navigator.get_children(category_pk)
            if children:
                for child in children:
                    child_name = child.get('Simple_name_en', child.get('text_en', 'Unnamed Sub-category'))
                    child_desc = child.get('desc_en', 'No description available.')
                    child_ex = child.get('ex_en', 'No example available.')
                    
                    children_details.append(
                        f"  - Sub-Category: {child_name}\n"
                        f"    Description: {child_desc}\n"
                        f"    Example: {child_ex}"
                    )
            
            # Le PK est inclus pour permettre l'appel de la fonction `explore_branch`
            full_block = (
                f"Category: {category_name} (ID: {category_pk})\n"
                f"Description: {category_desc}\n"
                f"It contains the following sub-categories:\n\n"
                f"{'\n\n'.join(children_details) if children_details else '  No sub-categories found.'}"
            )
            prompt_parts.append(full_block)

        prompt_content = "\n\n---\n\n".join(prompt_parts)

        context = (
            f"Text to analyze: '{argument_text}'\n\n"
            "Analyze the following high-level categories. For EACH category that seems plausible, "
            "call the `explore_branch` function with its corresponding ID.\n\n"
            f"{prompt_content}"
        )
        
        history = ChatHistory(system_message=slave_system_message)
        history.add_user_message(context)

        # Amélioration de la journalisation avant l'appel LLM
        self.logger.info(f"--- FallacyWorkflowPlugin: Prompt sent to LLM ---\n{context}")
        available_functions = [f.name for f in slave_kernel.plugins["Exploration"]]
        self.logger.info(f"--- FallacyWorkflowPlugin: Available functions for LLM ---\n{available_functions}")

        response = await self.llm_service.get_chat_message_content(
            chat_history=history, settings=slave_exec_settings, kernel=slave_kernel
        )
        
        # Log de la réponse brute de l'LLM
        self.logger.info(f"--- FallacyWorkflowPlugin: Raw response from LLM ---\n{response}")

        initial_calls = [c for c in response.items if isinstance(c, FunctionCallContent) and c.name == "Exploration-explore_branch"]
        if not initial_calls:
            self.logger.warning("LLM did not select any initial branches.")
            return ""

        candidate_branch_pks = {json.loads(call.arguments)["node_pk"] for call in initial_calls}
        self.logger.info(f"--- Phase 2: Exploring {len(candidate_branch_pks)} candidate branches in parallel ---")

        exploration_tasks = [
            self._explore_single_branch(argument_text, pk, slave_kernel, slave_exec_settings, slave_system_message)
            for pk in candidate_branch_pks
        ]
        branch_results = await asyncio.gather(*exploration_tasks)

        # TODO: Étape 3: Réconcilier les résultats. Pour l'instant, on prend le premier non-nul.
        final_node = next((res for res in branch_results if res), None)

        if final_node:
            nom_technique = final_node.get(f"text_{self.language}", "").strip()
            self.logger.info(f"--- Workflow Finished. Identified fallacy: '{nom_technique}' ---")
            return nom_technique

        self.logger.info("--- Workflow Finished. No fallacies identified. ---")
        return ""