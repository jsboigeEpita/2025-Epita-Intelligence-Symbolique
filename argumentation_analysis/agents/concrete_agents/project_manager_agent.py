# Fichier: argumentation_analysis/agents/concrete_agents/project_manager_agent.py

import json
from typing import Dict, Any, List

from semantic_kernel.agents.agent import AgentResponseItem
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.functions.kernel_arguments import KernelArguments
from pydantic import ValidationError

from ..abc.abstract_agent import AbstractAgent
from ..plugins.project_management_plugin import ProjectManagementPlugin, AnalysisReport

class ProjectManagerAgent(AbstractAgent):
    """Agent chef de projet, responsable de l'orchestration du groupe."""

    def setup_agent_components(self, llm_service_id: str, correction_attempts: int = 2) -> None:
        super().setup_agent_components(llm_service_id, correction_attempts)
        
        plugin = ProjectManagementPlugin()
        self.kernel.add_plugin(plugin, plugin_name="ProjectMgmtPlugin")
        
        prompt_path = "argumentation_analysis/agents/prompts/ProjectManagerAgent/skprompt.txt"
        with open(prompt_path, "r") as f:
            prompt_template = f.read()
        
        self.chat_function = self.kernel.create_function_from_prompt(
            function_name="ProjectManagerChat",
            plugin_name="ProjectManagerChatPlugin",
            prompt=prompt_template,
            prompt_execution_settings=OpenAIChatPromptExecutionSettings(
                service_id=self.llm_service_id,
                tool_choice="required",
            ),
        )

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {}

    async def get_response(
        self,
        messages: List[ChatMessageContent],
        arguments: KernelArguments,
        **kwargs: Any,
    ) -> AgentResponseItem[ChatMessageContent]:
        """
        Logique de l'agent : invoque le LLM, valide la sortie et la retourne.
        Pour le WO-04, cette logique est simple et n'inclut pas d'agrégation.
        """
        input_text = messages[-1].content
        current_arguments = KernelArguments(input=input_text)
        
        try:
            # Dans cette version, pas de boucle de correction, on garde simple.
            response = await self.kernel.invoke(self.chat_function, current_arguments)
            
            tool_call = response.inner_content.items[0]
            tool_args = json.loads(tool_call.arguments)
            
            # Valider avec Pydantic
            report = AnalysisReport(final_summary=tool_args.get("summary"))
            
            # Pour le chat, on transmet juste le texte original pour que les autres agents le voient.
            # La vraie orchestration se passera dans AgentGroupChat.
            return AgentResponseItem(
                message=ChatMessageContent(role=AuthorRole.ASSISTANT, content=input_text),
                agent=self
            )
            
        except (ValidationError, json.JSONDecodeError, KeyError, IndexError) as e:
            self.logger.error(f"Erreur lors de la génération du rapport : {e}", exc_info=True)
            error_message = f'{{"error": "Failed to generate project manager report.", "details": "{e}"}}'
            return AgentResponseItem(
                message=ChatMessageContent(role=AuthorRole.ASSISTANT, content=error_message),
                agent=self,
            )