# tests/mocks/llm_service_mocks.py
import logging
import json
import asyncio
from typing import List
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)

# Logger pour ce module
logger = logging.getLogger("Tests.Mocks.LLM")


class MockChatCompletion(ChatCompletionClientBase):
    """
    Service de complétion de chat mocké qui simule une réponse non-streamée
    contenant un appel d'outil (tool_call) ou une réponse JSON simple.
    """

    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        **kwargs,
    ) -> List[ChatMessageContent]:
        """
        Retourne une réponse mockée adaptée au service qui l'appelle.
        """
        logger.warning(
            f"--- ADVANCED MOCK LLM SERVICE USED (service_id: {self.service_id}, simulating NON-STREAMING) ---"
        )

        if self.service_id == "analysis_service":
            input_text = (
                chat_history.messages[-1].content if chat_history.messages else ""
            )
            mock_tool_arguments = {
                "analysis_id": "mock-analysis-e2e-default-123",
                "fallacies": [
                    {
                        "fallacy_name": "Ad Hominem",
                        "explanation": "Attaque la personne.",
                        "original_text": "son auteur est un gauchiste notoire",
                        "severity": 0.9,
                    },
                    {
                        "fallacy_name": "Pente Glissante",
                        "explanation": "Conséquences extrêmes.",
                        "original_text": "tous les prix vont exploser",
                        "severity": 0.7,
                    },
                ],
                "is_argument_valid": False,
                "overall_assessment": "L'argument est invalide car il repose sur des sophismes.",
                "confidence_score": 0.95,
            }
            tool_call_dict = {
                "id": "mock_tool_call_e2e",
                "type": "function",
                "function": {
                    "name": "submit_fallacy_analysis",
                    "arguments": json.dumps(mock_tool_arguments),
                },
            }
            response_message = ChatMessageContent(
                role="assistant", content=None, tool_calls=[tool_call_dict]
            )

        elif self.service_id == "logic_service":
            # Logique de mock conditionnelle pour les différentes étapes de l'agent logique
            logger.info("--- MOCK LLM (logic_service) TRIGGERED ---")
            input_text = (
                chat_history.messages[-1].content if chat_history.messages else ""
            )
            logger.debug(
                f"Mock logic_service received input text: {input_text[:500]}..."
            )

            # Étape 2: Le prompt contient la liste des propositions déjà définies
            if "Propositions Autorisées" in input_text:
                mock_logic_response = {
                    "formulas": ["P => Q", "Q => R", "P"],
                    "definitions": [],
                }
            # Étape 1: Le prompt demande de définir les propositions (par défaut)
            else:
                mock_logic_response = {
                    "propositions": ["P", "Q", "R"],
                    "definitions": [
                        {"proposition": "P", "definition": "Il pleut"},
                        {"proposition": "Q", "definition": "Le sol est mouillé"},
                        {"proposition": "R", "definition": "Je prends mon parapluie"},
                    ],
                }

            # Le service de logique attend un JSON direct, pas un tool_call.
            # Les autres services (analyse, etc.) attendent un tool_call.
            # Le mock doit donc être adaptatif.

            if self.service_id == "logic_service":
                # Pour le service logique, retourner le contenu JSON brut.
                response_message = ChatMessageContent(
                    role="assistant", content=json.dumps(mock_logic_response)
                )
            else:
                # Pour tous les autres services, encapsuler dans un tool_call.
                tool_call_dict = {
                    "id": f"mock_tool_call_{self.service_id}",
                    "type": "function",
                    "function": {
                        "name": "submit_generic_analysis",
                        "arguments": json.dumps(mock_logic_response),
                    },
                }
                response_message = ChatMessageContent(
                    role="assistant", content=None, tool_calls=[tool_call_dict]
                )

        else:
            # Réponse par défaut
            response_message = ChatMessageContent(role="assistant", content="{}")

        await asyncio.sleep(0.05)

        # La méthode doit retourner un awaitable contenant une liste.
        return [response_message]
