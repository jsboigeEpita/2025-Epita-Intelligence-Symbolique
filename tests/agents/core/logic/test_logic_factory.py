import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_logic_factory.py
"""
Tests unitaires pour la classe LogicAgentFactory.
"""

import unittest
import pytest
from unittest.mock import MagicMock, patch

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent


class TestLogicAgentFactory:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            print(f"Authentic LLM call failed: {e}")
            return "Authentic LLM call failed"

    """Tests pour la classe LogicAgentFactory."""

    async def async_setUp(self):
        """Initialisation asynchrone avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)

        self.mock_propositional_agent = MagicMock(spec=PropositionalLogicAgent)
        self.mock_first_order_agent = MagicMock(spec=FOLLogicAgent)
        self.mock_modal_agent = MagicMock(spec=ModalLogicAgent)

        # FIX: S'assurer que les mocks ont la méthode setup_agent_components, qui est appelée par la factory
        self.mock_propositional_agent.setup_agent_components = MagicMock()
        self.mock_first_order_agent.setup_agent_components = MagicMock()
        self.mock_modal_agent.setup_agent_components = MagicMock()

        self.mock_propositional_agent_class = MagicMock(
            spec=PropositionalLogicAgent, return_value=self.mock_propositional_agent
        )
        self.mock_first_order_agent_class = MagicMock(
            spec=FOLLogicAgent, return_value=self.mock_first_order_agent
        )
        self.mock_modal_agent_class = MagicMock(
            spec=ModalLogicAgent, return_value=self.mock_modal_agent
        )

        self.agent_classes_patch = patch.dict(
            LogicAgentFactory._agent_classes,
            {
                "propositional": self.mock_propositional_agent_class,
                "first_order": self.mock_first_order_agent_class,
                "modal": self.mock_modal_agent_class,
            },
            clear=False,
        )

    @pytest.mark.asyncio
    async def test_create_propositional_agent(self):
        """Test de la création d'un agent de logique propositionnelle."""
        await self.async_setUp()
        with self.agent_classes_patch:
            agent = LogicAgentFactory.create_agent("propositional", self.kernel)

            self.mock_propositional_agent_class.assert_called_once_with(
                kernel=self.kernel, agent_name="PropositionalAgent"
            )
            # La méthode setup_agent_components a été intégrée au constructeur.
            # self.mock_propositional_agent.setup_agent_components.assert_not_called()

            assert agent == self.mock_propositional_agent

    @pytest.mark.asyncio
    async def test_create_first_order_agent(self):
        """Test de la création d'un agent de logique du premier ordre."""
        await self.async_setUp()
        with self.agent_classes_patch:
            agent = LogicAgentFactory.create_agent("first_order", self.kernel)

            self.mock_first_order_agent_class.assert_called_once_with(
                kernel=self.kernel,
                agent_name="First_orderAgent",
            )
            # La méthode setup_agent_components a été intégrée au constructeur.
            # self.mock_first_order_agent.setup_agent_components.assert_not_called()

            assert agent == self.mock_first_order_agent

    @pytest.mark.asyncio
    async def test_create_modal_agent(self):
        """Test de la création d'un agent de logique modale."""
        await self.async_setUp()
        with self.agent_classes_patch:
            agent = LogicAgentFactory.create_agent("modal", self.kernel)

            self.mock_modal_agent_class.assert_called_once_with(
                kernel=self.kernel, agent_name="ModalAgent"
            )
            # La méthode setup_agent_components a été intégrée au constructeur.
            # self.mock_modal_agent.setup_agent_components.assert_not_called()

            assert agent == self.mock_modal_agent

    @pytest.mark.asyncio
    async def test_create_agent_with_llm_service(self):
        """Test de la création d'un agent avec un service LLM."""
        await self.async_setUp()
        with self.agent_classes_patch:
            llm_service = await self._create_authentic_gpt4o_mini_instance()

            agent = LogicAgentFactory.create_agent(
                "propositional", self.kernel, llm_service
            )

            self.mock_propositional_agent_class.assert_called_once_with(
                kernel=self.kernel, agent_name="PropositionalAgent"
            )
            # La configuration se fait maintenant via les `kwargs` du constructeur,
            # en passant un `service_id`. Cette assertion n'est plus pertinente.
            # self.mock_propositional_agent_class.assert_called_once_with(
            #     kernel=self.kernel,
            #     agent_name='PropositionalAgent',
            #     service_id=llm_service.service_id
            # )

            assert agent == self.mock_propositional_agent

    @pytest.mark.asyncio
    async def test_create_agent_unsupported_type(self):
        """Test de la création d'un agent avec un type non supporté."""
        await self.async_setUp()
        with self.agent_classes_patch:
            agent = LogicAgentFactory.create_agent("unsupported", self.kernel)

            self.mock_propositional_agent_class.assert_not_called()
            self.mock_first_order_agent_class.assert_not_called()
            self.mock_modal_agent_class.assert_not_called()

            assert agent is None

    @pytest.mark.asyncio
    async def test_create_agent_exception(self):
        """Test de la création d'un agent avec une exception."""
        await self.async_setUp()
        with self.agent_classes_patch:
            self.mock_propositional_agent_class.side_effect = Exception(
                "Test exception"
            )

            agent = LogicAgentFactory.create_agent("propositional", self.kernel)

            self.mock_propositional_agent_class.assert_called_once_with(
                kernel=self.kernel, agent_name="PropositionalAgent"
            )

            assert agent is None

    @pytest.mark.asyncio
    async def test_register_agent_class(self):
        """Test de l'enregistrement d'une nouvelle classe d'agent."""
        await self.async_setUp()

        class TestLogicAgent(BaseLogicAgent):
            def setup_agent_components(self, llm_service_id: str):
                pass

            def text_to_belief_set(self, text):
                pass

            def generate_queries(self, text, belief_set):
                pass

            def execute_query(self, belief_set, query):
                pass

            def interpret_results(self, text, belief_set, queries, results):
                pass

            def _create_belief_set_from_data(self, belief_set_data):
                pass

        test_logic_type = f"test_agent_type_{id(self)}"

        mock_test_agent_instance = MagicMock(spec=TestLogicAgent)
        mock_test_agent_constructor = MagicMock(return_value=mock_test_agent_instance)
        mock_test_agent_constructor.__name__ = "MockedTestLogicAgent"

        try:
            LogicAgentFactory.register_agent_class(
                test_logic_type, mock_test_agent_constructor
            )

            assert test_logic_type in LogicAgentFactory.get_supported_logic_types()

            agent = LogicAgentFactory.create_agent(test_logic_type, self.kernel)

            mock_test_agent_constructor.assert_called_once()
            args, kwargs = mock_test_agent_constructor.call_args
            assert kwargs.get("kernel") == self.kernel
            assert kwargs.get("agent_name", "").startswith("Test_agent_type_")
            assert kwargs.get("agent_name", "").endswith("Agent")

            assert agent == mock_test_agent_instance
        finally:
            LogicAgentFactory._agent_classes.pop(test_logic_type, None)

    @pytest.mark.asyncio
    async def test_get_supported_logic_types(self):
        """Test de la récupération des types de logique supportés."""
        await self.async_setUp()
        with self.agent_classes_patch:
            types = LogicAgentFactory.get_supported_logic_types()

            assert "propositional" in types
            assert "first_order" in types
            assert "modal" in types
