
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests d'intégration pour le projet d'analyse argumentative.

Ce module contient des tests d'intégration qui vérifient l'interaction
entre les différents composants du système.
"""

import asyncio
import pytest
from unittest.mock import MagicMock

import semantic_kernel as sk

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy
from argumentation_analysis.models.extract_definition import ExtractDefinitions, Extract, SourceDefinition
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService


@pytest.fixture
def basic_state():
    """Fixture pour initialiser un état de base pour les tests."""
    test_text = """
    La Terre est plate car l'horizon semble plat quand on regarde au loin.
    De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
    Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
    """
    return RhetoricalAnalysisState(test_text)


@pytest.fixture
def mock_agent_class(mocker):
    """Fixture pour mocker la classe de l'agent."""
    return mocker.patch('argumentation_analysis.agents.core.logic.fol_logic_agent.ChatCompletionAgent')

@pytest.fixture
def mock_kernel_class(mocker):
    """Fixture pour mocker la classe du kernel."""
    return mocker.patch('semantic_kernel.Kernel')

@pytest.fixture
def mock_run_analysis(mocker):
    """Fixture pour mocker la fonction run_analysis."""
    return mocker.patch('argumentation_analysis.orchestration.analysis_runner.run_analysis')


class TestBasicIntegration:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests d'intégration de base pour vérifier l'interaction entre les composants."""

    
    
    @pytest.mark.asyncio
    async def test_component_interaction(self, mock_agent_class, mock_kernel_class, basic_state):
        """Teste l'interaction de base entre les composants."""
        state = basic_state
        pm_agent = await self._create_authentic_gpt4o_mini_instance()
        pm_agent.name = "ProjectManagerAgent"
        
        pl_agent = await self._create_authentic_gpt4o_mini_instance()
        pl_agent.name = "PropositionalLogicAgent"
        
        informal_agent = await self._create_authentic_gpt4o_mini_instance()
        informal_agent.name = "InformalAnalysisAgent"
        
        agents = [pm_agent, pl_agent, informal_agent]
        
        termination_strategy = SimpleTerminationStrategy(state, max_steps=3)
        
        state.add_task("Identifier les arguments dans le texte")
        
        arg_id = state.add_argument("La Terre est plate car l'horizon semble plat")
        
        state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg_id)
        
        state.set_conclusion("Le texte contient plusieurs sophismes")
        
        assert len(state.analysis_tasks) == 1
        assert len(state.identified_arguments) == 1
        assert len(state.identified_fallacies) == 1
        assert state.final_conclusion is not None
        
        should_terminate = await termination_strategy.should_terminate(None, [])
        assert should_terminate


class TestSimulatedAnalysisFlow:
    """Tests simulant un flux d'analyse complet avec des mocks."""

    
    @pytest.mark.asyncio
    async def test_simulated_analysis_flow(self, mock_run_analysis, basic_state):
        """Simule un flux d'analyse complet."""
        state = basic_state
        mock_run_analysis.return_value = (True, "Analyse terminée avec succès")
        
        task1_id = state.add_task("Identifier les arguments dans le texte")
        task2_id = state.add_task("Analyser les sophismes dans les arguments")
        
        arg1_id = state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = state.add_argument("Si la Terre était ronde, les gens tomberaient")
        arg3_id = state.add_argument("Les scientifiques sont payés par la NASA")
        
        state.add_answer(
            task1_id,
            "InformalAnalysisAgent",
            "J'ai identifié 3 arguments dans le texte.",
            [arg1_id, arg2_id, arg3_id]
        )
        
        fallacy1_id = state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
        fallacy2_id = state.add_fallacy("Fausse analogie", "Mauvaise compréhension de la gravité", arg2_id)
        fallacy3_id = state.add_fallacy("Ad hominem", "Attaque la crédibilité plutôt que l'argument", arg3_id)
        
        state.add_answer(
            task2_id,
            "InformalAnalysisAgent",
            "J'ai identifié 3 sophismes dans les arguments.",
            [fallacy1_id, fallacy2_id, fallacy3_id]
        )
        
        bs_id = state.add_belief_set("Propositional", "p => q\np\n")
        
        state.log_query(bs_id, "p => q", "ACCEPTED (True)")
        
        state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        assert len(state.analysis_tasks) == 2
        assert len(state.identified_arguments) == 3
        assert len(state.identified_fallacies) == 3
        assert len(state.belief_sets) == 1
        assert len(state.query_log) == 1
        assert len(state.answers) == 2
        assert state.final_conclusion is not None


@pytest.fixture
def mocked_services():
    """Fixture pour créer des services mockés d'extraction et de récupération."""
    mock_fetch_service = MagicMock(spec=FetchService)
    mock_extract_service = MagicMock(spec=ExtractService)
    
    sample_text = """
    Ceci est un exemple de texte source.
    Il contient plusieurs paragraphes.
    
    Voici un marqueur de début: DEBUT_EXTRAIT
    Ceci est le contenu de l'extrait.
    Il peut contenir plusieurs lignes.
    Voici un marqueur de fin: FIN_EXTRAIT
    
    Et voici la suite du texte après l'extrait.
    """
    mock_fetch_service.fetch_text.return_value = (sample_text, "https://example.com/test")
    
    mock_extract_service.extract_text_with_markers.return_value = (
        "Ceci est le contenu de l'extrait.\nIl peut contenir plusieurs lignes.",
        "✅ Extraction réussie",
        True,
        True
    )
    
    source = SourceDefinition(
        source_name="Source d'intégration",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[
            Extract(
                extract_name="Extrait d'intégration 1",
                start_marker="DEBUT_EXTRAIT",
                end_marker="FIN_EXTRAIT"
            )
        ]
    )
    integration_sample_definitions = ExtractDefinitions(sources=[source])
    
    return mock_fetch_service, mock_extract_service, integration_sample_definitions


class TestExtractIntegration:
    """Tests d'intégration pour les composants d'extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_integration(self, mocked_services):
        """Teste l'intégration entre les services d'extraction et de récupération."""
        mock_fetch_service, mock_extract_service, integration_sample_definitions = mocked_services
        
        source = integration_sample_definitions.sources[0]
        extract = source.extracts[0]
        
        source_text, url = mock_fetch_service.fetch_text(source.to_dict())
        
        assert source_text is not None
        assert url == "https://example.com/test"
        
        extracted_text, status, start_found, end_found = mock_extract_service.extract_text_with_markers(
            source_text, extract.start_marker, extract.end_marker
        )
        
        assert start_found
        assert end_found
        assert "Extraction réussie" in status


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])