# Fichier : argumentation_analysis/agents/utils/tracer.py

import json
import logging
from typing import List, AsyncIterator, Optional
from semantic_kernel import Kernel
from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.contents import (
    ChatMessageContent,
    AuthorRole,
    StreamingChatMessageContent,
    FunctionCallContent,
    FunctionResultContent,
)
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

class TracedAgent:
    """
    Un simple wrapper (proxy) qui encapsule un agent sémantique pour journaliser
    les interactions (avant/après l'invocation) sans interférer avec son fonctionnement interne.
    Il ne doit PAS hériter de ChatCompletionAgent pour éviter les conflits d'état.
    """

    def __init__(self, agent_to_wrap: ChatCompletionAgent, trace_log_path: str):
        """
        Initialise le wrapper.
        
        :param agent_to_wrap: L'instance de l'agent à tracer.
        :param trace_log_path: Le chemin vers le fichier de log.
        """
        self.agent = agent_to_wrap
        self.name = agent_to_wrap.name if hasattr(agent_to_wrap, 'name') else 'UnnamedAgent'
        self._trace_log_path = trace_log_path
        self._logger = self._setup_logger()
        self._logger.info(f"TracedAgent for '{self.name}' enabled. Log file: {self._trace_log_path}")

    def _setup_logger(self):
        """Configure et retourne un logger pour la trace (mode de débogage robuste)."""
        # Utiliser basicConfig avec force=True est une manière robuste de s'assurer
        # que la configuration est réinitialisée à chaque appel, évitant les deadlocks
        # potentiels liés à la manipulation manuelle des handlers dans un contexte de multiprocesseing.
        logging.basicConfig(
            filename=self._trace_log_path,
            filemode='w',  # 'w' pour écraser le fichier à chaque fois
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            encoding='utf-8',
            force=True  # force=True est crucial ici
        )
        # Retourne le logger root qui vient d'être configuré.
        return logging.getLogger()

    def _format_messages(self, history: "ChatHistory") -> str:
        """Formate un historique de chat en une chaîne détaillée."""
        if not history or not history.messages:
            return "No messages in history."

        formatted_list = []
        for i, msg in enumerate(history.messages):
            role = msg.role.name.upper() if hasattr(msg.role, 'name') else str(msg.role).upper()
            line = f"--- Message {i}: Role: {role} ---"
            
            content_parts = []
            if hasattr(msg, 'content') and msg.content:
                content_parts.append(f"  Content: \"{str(msg.content)}\"")

            all_items = (getattr(msg, 'items', []) or []) + (getattr(msg, 'tool_calls', []) or [])
            if all_items:
                for j, item in enumerate(all_items):
                    item_type_name = type(item).__name__
                    item_str = f"  Item/ToolCall {j} (type {item_type_name}): "
                    
                    if isinstance(item, FunctionCallContent):
                        item_str += f"FunctionCall: {item.function.name}, ID: {item.id}, Args: {item.function.arguments}"
                    elif isinstance(item, FunctionResultContent):
                        item_str += f"FunctionResult: ID: {item.tool_call_id}, Result: {item.result}"
                    else:
                        item_str += str(item)
                    content_parts.append(item_str)
            
            if not content_parts:
                 content_parts.append("  (No visible content or tool calls)")

            line += "\n" + "\n".join(content_parts)
            formatted_list.append(line)

        return "\n".join(formatted_list)

    async def invoke(self, history: "ChatHistory", **kwargs) -> AsyncIterator[ChatMessageContent]:
        """
        Invoque l'agent encapsulé et journalise l'historique complet avant et après.
        """
        # Log de l'historique d'entrée dans un format JSON sérialisable
        try:
            # Tente de sérialiser l'historique complet, qui est un objet ChatHistory
            # La méthode `model_dump_json` de Pydantic est idéale pour cela.
            history_json = history.model_dump_json(indent=2)
            self._logger.info(f"--- START INVOKE on {self.name} ---\nHISTORY:\n{history_json}\n")
        except Exception as e:
            self._logger.error(f"Erreur lors de la sérialisation de l'historique initial: {e}")

        # Invocation de l'agent en mode stream
        response_stream = self.agent.invoke_stream(history, **kwargs)

        # Consommation et retransmission du stream
        async for response_part in response_stream:
            yield response_part
        
        # Log de l'historique final après l'invocation
        try:
            final_history_json = history.model_dump_json(indent=2)
            self._logger.info(f"--- FINAL HISTORY for {self.name} ---\nHISTORY:\n{final_history_json}\n")
        except Exception as e:
            self._logger.error(f"Erreur lors de la sérialisation de l'historique final: {e}")
