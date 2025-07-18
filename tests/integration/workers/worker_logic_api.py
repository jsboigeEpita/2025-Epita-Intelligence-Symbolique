# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
# tests/integration/workers/worker_logic_api.py
"""
Worker pour les tests d'intégration de LogicService, à exécuter dans un sous-processus.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

import uuid
import pytest

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import (
    PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet
)

from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest
)
from argumentation_analysis.services.web_api.models.response_models import (
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse
)


# Cette classe peut fonctionner car elle n'utilise pas directement l'app Flask
# mais utilise LogicService directement avec des mocks appropriés
@pytest.fixture
def logic_service_with_mocks():
    """Fixture pour patcher LogicAgentFactory et Kernel et initialiser le service."""
    with patch('argumentation_analysis.services.web_api.logic_service.LogicAgentFactory') as mock_logic_factory, \
         patch('argumentation_analysis.services.web_api.logic_service.Kernel') as mock_kernel_class:
        
        # Créer un mock plus réaliste pour le Kernel
        mock_kernel = MagicMock(spec=Kernel)
        mock_kernel.plugins = {} # Ajouter l'attribut 'plugins' qui est manquant
        mock_kernel_class.return_value = mock_kernel

        mock_pl_agent = MagicMock(spec=PropositionalLogicAgent)
        
        # Simuler le retour d'une coroutine pour text_to_belief_set
        async def mock_text_to_belief_set(*args, **kwargs):
            return (PropositionalBeliefSet(content="a => b", source_text="Si a alors b"), "Conversion réussie")
        # Attribuer la coroutine directement à la méthode mockée
        mock_pl_agent.text_to_belief_set = mock_text_to_belief_set

        # Simuler le retour d'une coroutine pour generate_queries
        async def mock_generate_queries(*args, **kwargs):
            return ["a", "b", "a => b"]
        mock_pl_agent.generate_queries = mock_generate_queries
        
        # Simuler le retour d'une coroutine pour execute_query
        async def mock_execute_query(*args, **kwargs):
            return (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        mock_pl_agent.execute_query = mock_execute_query

        mock_logic_factory.create_agent.return_value = mock_pl_agent

        logic_service = LogicService()
        # Remplacer le kernel instancié par notre mock
        logic_service.kernel = mock_kernel

        yield logic_service, mock_logic_factory, mock_pl_agent, mock_kernel

class TestLogicServiceIntegration:
    """Tests d'intégration pour le service LogicService."""

    @pytest.mark.asyncio
    async def test_text_to_belief_set(self, logic_service_with_mocks):
        """Test de la méthode text_to_belief_set."""
        logic_service, mock_logic_factory, mock_pl_agent, mock_kernel = logic_service_with_mocks

        request = LogicBeliefSetRequest(text="Si a alors b", logic_type="propositional")
        
        response = await logic_service.text_to_belief_set(request)
        
        mock_logic_factory.create_agent.assert_called_once_with("propositional", mock_kernel)
        mock_pl_agent.text_to_belief_set.assert_called_once_with("Si a alors b")
        
        assert response.success
        assert response.belief_set.logic_type == "propositional"
        assert response.belief_set.content == "a => b"
        assert response.belief_set.source_text == "Si a alors b"

    @pytest.mark.asyncio
    async def test_execute_query(self, logic_service_with_mocks):
        """Test de la méthode execute_query."""
        logic_service, mock_logic_factory, mock_pl_agent, mock_kernel = logic_service_with_mocks

        belief_set_request = LogicBeliefSetRequest(text="Si a alors b", logic_type="propositional")
        belief_set_response = await logic_service.text_to_belief_set(belief_set_request)
        belief_set_id = belief_set_response.belief_set.id
        
        request = LogicQueryRequest(
            belief_set_id=belief_set_id,
            query="a => b",
            logic_type="propositional"
        )
        
        response = await logic_service.execute_query(request)
        
        assert mock_logic_factory.create_agent.call_count == 2
        
        assert response.success
        assert response.belief_set_id == belief_set_id
        assert response.logic_type == "propositional"
        assert response.result.query == "a => b"
        assert response.result.result is True

    @pytest.mark.asyncio
    async def test_generate_queries(self, logic_service_with_mocks):
        """Test de la méthode generate_queries."""
        logic_service, mock_logic_factory, mock_pl_agent, mock_kernel = logic_service_with_mocks

        belief_set_request = LogicBeliefSetRequest(text="Si a alors b", logic_type="propositional")
        belief_set_response = await logic_service.text_to_belief_set(belief_set_request)
        belief_set_id = belief_set_response.belief_set.id
        
        request = LogicGenerateQueriesRequest(
            belief_set_id=belief_set_id,
            text="Si a alors b",
            logic_type="propositional"
        )
        
        response = await logic_service.generate_queries(request)
        
        assert mock_logic_factory.create_agent.call_count == 2
        
        assert response.success
        assert response.belief_set_id == belief_set_id
        assert response.logic_type == "propositional"
        assert response.queries == ["a", "b", "a => b"]