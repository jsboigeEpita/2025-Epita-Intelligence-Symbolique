# -*- coding: utf-8 -*-
"""
Tests d'intégration end-to-end pour le système d'analyse argumentative.

Ce module contient des tests d'intégration qui vérifient le flux complet
d'analyse argumentative de bout en bout, y compris l'interaction entre
les différents agents et la gestion des erreurs.
"""

import asyncio
import pytest
import pytest_asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
# Correction de l'importation de AuthorRole suite à la refactorisation de semantic-kernel
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
# from argumentation_analysis.orchestration.enhanced_pm_analysis_runner import EnhancedPMAnalysisRunner
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService

# Configuration pytest-asyncio
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def analysis_fixture():
    """Fixture pour initialiser les composants de base pour les tests d'analyse."""
    test_text = """
    La Terre est plate car l'horizon semble plat quand on regarde au loin.
    De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
    Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
    """
    state = RhetoricalAnalysisState(test_text)
    llm_service = AsyncMock()
    llm_service.service_id = "test_service"
    kernel = sk.Kernel()
    state_manager = StateManagerPlugin(state)
    kernel.add_plugin(state_manager, "StateManager")
    
    return state, llm_service, kernel, test_text
    



@pytest.fixture
def balanced_strategy_fixture(monkeypatch):
    """Fixture pour les tests de la stratégie d'équilibrage."""
    test_text = "Texte source avec DEBUT_EXTRAIT et FIN_EXTRAIT."
    state = RhetoricalAnalysisState(test_text)
    
    mock_fetch_service = MagicMock(spec=FetchService)
    mock_fetch_service.fetch_text.return_value = ("Texte source avec DEBUT_EXTRAIT contenu FIN_EXTRAIT.", "https://example.com/test")
    mock_fetch_service.reconstruct_url.return_value = "https://example.com/test"
    
    mock_extract_service = MagicMock(spec=ExtractService)
    mock_extract_service.extract_text_with_markers.return_value = ("contenu", "Extraction réussie", True, True)
    
    integration_sample_definitions = ExtractDefinitions(sources=[
        SourceDefinition(source_name="SourceInt", source_type="url", schema="https", host_parts=["example", "com"], path="/test",
                         extracts=[Extract(extract_name="ExtraitInt1", start_marker="DEBUT_EXTRAIT", end_marker="FIN_EXTRAIT")])
    ])
    
    monkeypatch.setattr("argumentation_analysis.services.fetch_service.FetchService", lambda: mock_fetch_service)
    monkeypatch.setattr("argumentation_analysis.services.extract_service.ExtractService", lambda: mock_extract_service)
    
    return state, mock_fetch_service, mock_extract_service, integration_sample_definitions


class TestExtractIntegrationWithBalancedStrategy:
    """Tests d'intégration pour les composants d'extraction avec la stratégie d'équilibrage."""

    async def test_extract_integration_with_balanced_strategy(self, balanced_strategy_fixture):
        state, mock_fetch_service, mock_extract_service, integration_sample_definitions = balanced_strategy_fixture
        
        source = integration_sample_definitions.sources[0]
        extract_def = source.extracts[0]
        
        pm_agent = MagicMock(); pm_agent.name = "ProjectManagerAgent"
        pl_agent = MagicMock(); pl_agent.name = "PropositionalLogicAgent"
        informal_agent = MagicMock(); informal_agent.name = "InformalAnalysisAgent"
        extract_agent_mock = MagicMock(); extract_agent_mock.name = "ExtractAgent"
        
        agents = [pm_agent, pl_agent, informal_agent, extract_agent_mock]
        
        balanced_strategy = BalancedParticipationStrategy(agents=agents, state=state, default_agent_name="ProjectManagerAgent")
        
        source_text, url = mock_fetch_service.fetch_text(source.to_dict())
        assert source_text is not None
        assert url == "https://example.com/test"
        
        extracted_text, status, start_found, end_found = mock_extract_service.extract_text_with_markers(
            source_text, extract_def.start_marker, extract_def.end_marker
        )
        assert start_found
        assert end_found
        assert "Extraction réussie" in status
        
        extract_id = state.add_extract(extract_def.extract_name, extracted_text)
        
        history = []
        state.designate_next_agent("ExtractAgent")
        selected_agent = await balanced_strategy.next(agents, history)
        assert selected_agent == extract_agent_mock
        
        assert balanced_strategy._participation_counts["ExtractAgent"] == 1
        assert balanced_strategy._total_turns == 1
        assert len(state.extracts) == 1
        assert state.extracts[0]["id"] == extract_id
        assert state.extracts[0]["name"] == extract_def.extract_name
        assert state.extracts[0]["content"] == extracted_text


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])


