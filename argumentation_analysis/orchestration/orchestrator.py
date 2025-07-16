#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.config.settings import AppSettings
# Supprimé : from argumentation_analysis.core.kernel_builder import KernelBuilder
from argumentation_analysis.agents.factory import AgentFactory
from semantic_kernel import Kernel

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Orchestrates the argumentation analysis using a group of agents.
    """
    def __init__(self, kernel: Kernel, llm_service_id: str):
        self._kernel = kernel
        self._llm_service_id = llm_service_id
        self._agent_factory = AgentFactory(self._kernel, self._llm_service_id)

    async def run_analysis_async(self, text_content: str):
        """
        Runs the argumentation analysis.
        """
        logger.info("Starting argumentation analysis process.")

        # 1. Create agents
        try:
            fallacy_agent = self._agent_factory.create_informal_fallacy_agent()
            manager_agent = self._agent_factory.create_project_manager_agent()
            logger.info("Agents created: %s, %s", fallacy_agent.name, manager_agent.name)
        except Exception as e:
            logger.error("Error creating agents: %s", e)
            return

        # 2. Prepare chat
        chat_history = ChatHistory()
        chat_history.add_message(message=ChatMessageContent(role=AuthorRole.USER, content=text_content))

        # 3. Create and configure Agent Group Chat
        chat = AgentGroupChat(
            agents=[manager_agent, fallacy_agent],
            chat_history=chat_history
        )
        logger.info("AgentGroupChat created and pre-configured with initial history.")

        # 4. Execute analysis
        logger.info("Starting chat invocation.")
        history = [chat_history.messages[0]]
        async for message in chat.invoke():
            history.append(message)
        logger.info("Chat invocation finished. Displaying full conversation history.")

        # 5. Display results
        for message in history:
            print(f"[{message.role.value.upper()}] - {message.name or 'User'}:\n---\n{message.content}\n---")
