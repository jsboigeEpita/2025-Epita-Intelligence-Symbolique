# Fichier: argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py

import json
from typing import Dict, Any, List, Optional

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.agents.agent import AgentResponse
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.functions.kernel_arguments import KernelArguments
from pydantic import ValidationError

from ..abc.abstract_agent import AbstractAgent
from ..plugins.fallacy_identification_plugin import FallacyIdentificationPlugin, FallacyIdentificationResult

class InformalFallacyAgent(AbstractAgent):
    """Agent spécialisé dans l'identification des sophismes informels."""

    def __init__(self, kernel: Kernel, name: str, description: Optional[str] = None):
        super().__init__(kernel=kernel, name=name, description=description)


    def setup_agent_components(self, llm_service_id: str, correction_attempts: int = 3) -> None:
        super().setup_agent_components(llm_service_id, correction_attempts)
        
        # Ajoute le plugin contenant l'outil de validation Pydantic
        plugin = FallacyIdentificationPlugin()
        self.kernel.add_plugin(plugin, plugin_name="FallacyIdPlugin")

        # Charge le prompt depuis le fichier
        prompt_path = "argumentation_analysis/agents/prompts/InformalFallacyAgent/skprompt.txt"
        with open(prompt_path, "r") as f:
            prompt = f.read()
        
        self.chat_function = self.kernel.create_function_from_prompt(
            function_name="FallacyChat",
            plugin_name="FallacyChatPlugin",
            prompt=prompt,
            prompt_execution_settings=OpenAIChatPromptExecutionSettings(
                service_id=self.llm_service_id,
                tool_choice="required", # Force le LLM à appeler notre outil
            ),
        )

    def get_agent_capabilities(self) -> Dict[str, Any]:
        # Implémentation future si nécessaire pour la sélection dynamique d'agents
        return {}
        
    async def get_response(
        self,
        messages: List[ChatMessageContent],
        arguments: KernelArguments,
        **kwargs: Any,
    ) -> AgentResponse:
        """Logique principale de l'agent avec boucle d'auto-correction."""
        
        input_text = messages[-1].content
        current_arguments = KernelArguments(input=input_text)
        
        for attempt in range(self.correction_attempts):
            self.logger.info(f"Tentative {attempt + 1}/{self.correction_attempts} d'identification des sophismes.")
            
            try:
                response = await self.kernel.invoke(self.chat_function, current_arguments)
                
                # Extraire le contenu de l'outil appelé par le LLM
                tool_call = response.inner_content.items[0]
                tool_args = json.loads(tool_call.arguments)
                
                # Valider avec Pydantic
                validated_result = FallacyIdentificationResult(**tool_args)
                
                self.logger.info("Validation Pydantic réussie.")
                final_json_output = validated_result.model_dump_json(indent=2)
                
                return AgentResponse(
                    message=ChatMessageContent(role=AuthorRole.ASSISTANT, content=final_json_output),
                    agent=self
                )
            
            except (ValidationError, json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Erreur de validation/parsing (tentative {attempt + 1}): {e}")
                # Préparer la prochaine tentative avec l'erreur comme contexte
                error_feedback = f"Ta précédente tentative a échoué avec l'erreur: {e}. Analyse cette erreur et corrige ta sortie. Ne commets plus cette erreur."
                current_arguments["input"] = f"{input_text}\n\n--- INSTRUCTION DE CORRECTION ---\n{error_feedback}"
            
            except Exception as e:
                self.logger.error(f"Erreur inattendue durant l'invocation: {e}", exc_info=True)
                # En cas d'erreur non gérée, on interrompt la boucle.
                break
        
        # Échec après toutes les tentatives
        self.logger.error("Échec de l'identification des sophismes après toutes les tentatives de correction.")
        return AgentResponse(
            message=ChatMessageContent(role=AuthorRole.ASSISTANT, content="{\"error\": \"Failed to identify fallacies after multiple correction attempts.\"}"),
            agent=self,
        )