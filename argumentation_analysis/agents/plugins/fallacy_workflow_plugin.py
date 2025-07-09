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

    @kernel_function(
        name="run_guided_analysis",
        description="Exécute un workflow guidé pour analyser un texte et identifier les sophismes."
    )
    async def run_guided_analysis(
        self, argument_text: Annotated[str, "Le texte de l'argument à analyser."]
    ) -> Annotated[str, "Le résultat final de l'analyse, listant les sophismes identifiés."]:
        """
        Exécute une analyse séquentielle en deux étapes pour identifier un sophisme.
        Étape 1: Le LLM choisit la catégorie de premier niveau la plus pertinente.
        Étape 2: Le LLM explore cette catégorie en profondeur jusqu'à trouver un sophisme ou conclure.
        """
        print("!!!!!! -------- FallacyWorkflowPlugin.run_guided_analysis (Sequential) CALLED -------- !!!!!")
        self.logger.info(f"--- Starting Sequential Fallacy Analysis for: '{argument_text[:80]}...' ---")

        slave_kernel, slave_exec_settings = self._create_slave_kernel()
        slave_system_message = "Your ONLY purpose is to classify text by navigating a taxonomy. You MUST call one function. Do NOT output any other text."

        # --- Étape 1: Sélection de la catégorie racine ---
        self.logger.info("--- Phase 1: Selecting Root Category ---")
        root_nodes = self.taxonomy_navigator.get_root_nodes()
        if not root_nodes:
            return json.dumps({"error": "No root nodes found."}, indent=2)

        root_options = [
            {
                "id": node["PK"],
                "name": node[f"text_{self.language}"],
                "description": node[f"desc_{self.language}"],
            }
            for node in root_nodes
        ]

        context_for_root_selection = (
            f"Text to analyze: '{argument_text}'\n\n"
            "Select the SINGLE most relevant high-level category for the text from the list below. "
            "Use the `explore_branch` function with the chosen category's ID.\n\n"
            f"{json.dumps(root_options, indent=2, ensure_ascii=False)}"
        )

        history = ChatHistory(system_message=slave_system_message)
        history.add_user_message(context_for_root_selection)
        
        self.logger.info(f"--- Sending prompt for root selection ---\n{context_for_root_selection}")
        response = await self.llm_service.get_chat_message_content(
            chat_history=history, settings=slave_exec_settings, kernel=slave_kernel
        )
        self.logger.info(f"--- Raw response from LLM for root selection ---\n{response}")

        root_calls = [c for c in response.items if isinstance(c, FunctionCallContent) and c.name == "Exploration-explore_branch"]
        if not root_calls:
            self.logger.warning("LLM did not select a root category.")
            return ""
        
        # On ne prend que le premier choix pour l'exploration séquentielle
        current_node_pk = json.loads(root_calls[0].arguments)["node_pk"]
        self.logger.info(f"--- Root category selected: {current_node_pk} ---")

        # --- Étape 2: Exploration en profondeur de la catégorie choisie ---
        self.logger.info(f"--- Phase 2: Exploring branch starting from {current_node_pk} ---")
        
        for i in range(10):  # Limite de 10 itérations pour éviter les boucles infinies
            self.logger.info(f"  [Iteration {i+1}] Current node: {current_node_pk}")

            # Vérifier si une conclusion a été demandée
            conclusion_calls = [c for c in response.items if isinstance(c, FunctionCallContent) and c.name.startswith("Exploration-conclude")]
            if conclusion_calls:
                conclusion_call = conclusion_calls[0]
                self.logger.info(f"  Conclusion function called: {conclusion_call.name}")
                if conclusion_call.name == "Exploration-conclude_fallacy":
                    args = json.loads(conclusion_call.arguments)
                    final_fallacy_name = args.get("fallacy_name", "Unknown")
                    self.logger.info(f"--- Workflow Finished. Identified fallacy: '{final_fallacy_name}' ---")
                    return final_fallacy_name
                else: # conclude_no_fallacy
                    self.logger.info("--- Workflow Finished. No fallacies identified. ---")
                    return ""

            children = self.taxonomy_navigator.get_children(current_node_pk)
            current_node_data = self.taxonomy_navigator.get_node(current_node_pk)

            if not children:
                self.logger.info(f"  [Leaf Node] No children for {current_node_pk}. Concluding with this node.")
                final_fallacy_name = current_node_data.get(f"text_{self.language}", "Unknown")
                self.logger.info(f"--- Workflow Finished. Identified fallacy at leaf node: '{final_fallacy_name}' ---")
                return final_fallacy_name

            options_to_present = []
            # Ajouter le noeud parent comme option pour permettre la confirmation
            options_to_present.append({
                "id": current_node_pk,
                "name": current_node_data[f"text_{self.language}"],
                "description": f"PARENT (Confirm this is the correct category): {current_node_data[f'desc_{self.language}']}"
            })
            # Ajouter les enfants comme options d'exploration
            for child in children:
                options_to_present.append({
                    "id": child["PK"],
                    "name": child[f"text_{self.language}"],
                    "description": f"CHILD (Explore this sub-category): {child[f'desc_{self.language}']}",
                    "example": child[f'example_{self.language}']
                })

            context_for_exploration = (
                f"Text to analyze: '{argument_text}'\n\n"
                f"You are currently at category: '{current_node_data[f'text_{self.language}']}'.\n"
                "Choose the next step: explore a more specific sub-category, confirm the current one as the final answer, or conclude that no fallacy is present.\n"
                "Use `explore_branch(node_pk)` to navigate or `conclude_fallacy(fallacy_name)` to finish.\n\n"
                f"{json.dumps(options_to_present, indent=2, ensure_ascii=False)}"
            )

            history = ChatHistory(system_message=slave_system_message)
            history.add_user_message(context_for_exploration)
            
            self.logger.info(f"--- Sending prompt for exploration ---\n{context_for_exploration}")
            response = await self.llm_service.get_chat_message_content(
                chat_history=history, settings=slave_exec_settings, kernel=slave_kernel
            )
            self.logger.info(f"--- Raw response from LLM for exploration ---\n{response}")

            explore_calls = [c for c in response.items if isinstance(c, FunctionCallContent) and c.name == "Exploration-explore_branch"]
            
            if not explore_calls:
                self.logger.warning("  LLM did not choose a path. Concluding with current node.")
                final_fallacy_name = current_node_data.get(f"text_{self.language}", "Unknown")
                self.logger.info(f"--- Workflow Finished. Identified fallacy by default: '{final_fallacy_name}' ---")
                return final_fallacy_name

            next_pk = json.loads(explore_calls[0].arguments)["node_pk"]

            # Si le LLM choisit à nouveau le parent, c'est la conclusion
            if next_pk == current_node_pk:
                self.logger.info(f"  LLM confirmed parent {next_pk}. Concluding with this node.")
                final_fallacy_name = current_node_data.get(f"text_{self.language}", "Unknown")
                self.logger.info(f"--- Workflow Finished. Identified fallacy by confirmation: '{final_fallacy_name}' ---")
                return final_fallacy_name
            
            current_node_pk = next_pk

        self.logger.warning(f"--- Workflow Finished. Max iterations reached. ---")
        return ""