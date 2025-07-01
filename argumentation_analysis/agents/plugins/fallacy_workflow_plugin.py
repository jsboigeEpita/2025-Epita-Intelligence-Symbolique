# Fichier: argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py
import asyncio
import json
from typing import Annotated, List

from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory, AuthorRole, FunctionCallContent, ChatMessageContent, FunctionResultContent
from argumentation_analysis.agents.utils.taxonomy_utils import Taxonomy
from .exploration_plugin import ExplorationPlugin
from .identification_plugin import IdentificationPlugin

class FallacyWorkflowPlugin:
    """Plugin orchestrant le workflow séquentiel d'analyse de sophismes."""

    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.taxonomy = Taxonomy()

    @kernel_function(
        name="parallel_exploration",
        description="Explore plusieurs branches de la taxonomie en parallèle.",
    )
    def parallel_exploration(
        self, nodes: Annotated[List[str], "Liste des IDs de noeuds à explorer."],
    ) -> Annotated[str, "Un dictionnaire JSON des résultats."]:
        """Explore plusieurs branches de la taxonomie."""
        results = {
            node_id: self.taxonomy.get_branch(node_id) or {"error": "Not found"}
            for node_id in nodes
        }
        return json.dumps(results, indent=2, ensure_ascii=False)

    async def run_workflow(self, argument_text: str) -> str:
        """Exécute le workflow en deux étapes avec une gestion manuelle des outils."""
        service = self.kernel.get_service(type=OpenAIChatCompletion)
        if not service:
            raise ValueError("Service OpenAIChatCompletion non trouvé.")

        # --- ÉTAPE 1: EXPLORATION ---
        exploration_kernel = Kernel()
        exploration_kernel.add_service(service)
        exploration_kernel.add_plugin(ExplorationPlugin(), "exploration")
        exploration_kernel.add_plugin(self, "workflow_tools")

        exploration_history = ChatHistory(
            system_message="Votre tâche est d'explorer la taxonomie des sophismes. "
            "Utilisez les outils à votre disposition pour naviguer."
        )
        exploration_history.add_user_message(
            f"Argument: \"{argument_text}\". "
            "Commencez par `exploration_explore_branch` sur 'fallacy_root'."
        )
        
        exploration_settings = OpenAIPromptExecutionSettings(
            service_id=service.service_id,
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                auto_invoke=False, filters={'included_plugins': ['exploration', 'workflow_tools']}
            )
        )
        
        for _ in range(3):  # Limite de 3 tours pour l'exploration
            result_message = (await service.get_chat_message_contents(
                exploration_history,
                settings=exploration_settings,
                kernel=exploration_kernel
            ))[0]
            exploration_history.add_message(message=result_message)

            tool_calls = [item for item in result_message.items if isinstance(item, FunctionCallContent)]
            if not tool_calls:
                break
            
            for tool_call in tool_calls:
                plugin_name, function_name = tool_call.name.split('-')
                function_to_invoke = exploration_kernel.get_function(plugin_name, function_name)
                arguments = json.loads(tool_call.arguments)
                tool_result = await exploration_kernel.invoke(function_to_invoke, **arguments)
                exploration_history.add_message(
                    ChatMessageContent(
                        role=AuthorRole.TOOL,
                        items=[FunctionResultContent(id=tool_call.id, result=str(tool_result))],
                    )
                )

        exploration_context = "\n".join([f"{msg.role}: {msg.content}" for msg in exploration_history if msg.role == AuthorRole.TOOL])
        
        # --- ÉTAPE 2: IDENTIFICATION ---
        id_kernel = Kernel()
        id_kernel.add_service(service)
        id_kernel.add_plugin(IdentificationPlugin(), "identifier")

        id_history = ChatHistory(
            system_message="Votre tâche est d'identifier les sophismes dans le texte fourni en vous basant sur le contexte. "
            "Portez une attention particulière aux arguments qui se contredisent eux-mêmes, comme utiliser un concept tout en niant sa validité (par exemple, le sophisme du 'concept-volé'). "
            "Vous DEVEZ utiliser l'outil `identifier_identify_fallacies`."
        )
        id_history.add_user_message(f"Contexte de l'exploration:\n{exploration_context}")
        id_history.add_user_message(f"Argument à analyser: \"{argument_text}\"")
        
        id_settings = OpenAIPromptExecutionSettings(
            service_id=service.service_id,
            function_choice_behavior=FunctionChoiceBehavior.Required(
                auto_invoke=False, function_filter={'included_plugins': ['identifier']}
            )
        )

        final_result_message = (await service.get_chat_message_contents(
            id_history,
            settings=id_settings,
            kernel=id_kernel
        ))[0]
        id_history.add_message(message=final_result_message)
        
        # Invoquer manuellement le tool call final
        final_tool_calls = [item for item in final_result_message.items if isinstance(item, FunctionCallContent)]
        if final_tool_calls:
            final_plugin_name, final_function_name = final_tool_calls[0].name.split('-')
            final_function_to_invoke = id_kernel.get_function(final_plugin_name, final_function_name)
            final_tool_arguments = json.loads(final_tool_calls[0].arguments)
            final_tool_result = await id_kernel.invoke(final_function_to_invoke, **final_tool_arguments)
            # Le résultat est une liste d'objets Pydantic. Il faut les convertir en dict
            # avant de les sérialiser en JSON pour le script de test.
            fallacies_list = final_tool_result.value
            if isinstance(fallacies_list, list):
                # Extraire le premier élément s'il y en a un, comme le veut le test
                if fallacies_list:
                    fallacy_data = [f.dict() for f in fallacies_list]
                    return json.dumps(fallacy_data, indent=2, ensure_ascii=False)
                else:
                    return json.dumps([], indent=2, ensure_ascii=False)

            # Fallback si le format n'est pas celui attendu
            return str(final_tool_result)

        return json.dumps({"error": "Aucune identification produite."}, indent=2, ensure_ascii=False)