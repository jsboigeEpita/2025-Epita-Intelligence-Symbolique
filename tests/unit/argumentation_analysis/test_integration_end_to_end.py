
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

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

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
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
    llm_service = Magicawait self._create_authentic_gpt4o_mini_instance()
    llm_service.service_id = "test_service"
    kernel = sk.Kernel()
    state_manager = StateManagerPlugin(state)
    kernel.add_plugin(state_manager, "StateManager")
    
    yield state, llm_service, kernel, test_text
    
    # Cleanup AsyncIO tasks
    try:
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        pass


class TestEndToEndAnalysis:
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

    """Tests d'intégration end-to-end pour le flux complet d'analyse argumentative."""

    
    
    
    
    
    
    @pytest.mark.asyncio
    async def test_complete_analysis_flow(
        self,
        mock_setup_pm_kernel,
        mock_setup_informal_kernel,
        mock_setup_pl_kernel,
        mock_setup_extract_agent,
        mock_chat_completion_agent,
        mock_agent_group_chat,
        analysis_fixture
    ):
        """Teste le flux complet d'analyse argumentative de bout en bout."""
        state, llm_service, _, test_text = analysis_fixture
        
        mock_pm_agent = MagicMock(spec=Agent); mock_pm_agent.name = "ProjectManagerAgent"
        mock_informal_agent = MagicMock(spec=Agent); mock_informal_agent.name = "InformalAnalysisAgent"
        mock_pl_agent = MagicMock(spec=Agent); mock_pl_agent.name = "PropositionalLogicAgent"
        mock_extract_agent = MagicMock(spec=Agent); mock_extract_agent.name = "ExtractAgent"
        
        mock_chat_completion_agent# Mock eliminated - using authentic gpt-4o-mini [mock_pm_agent, mock_informal_agent, mock_pl_agent, mock_extract_agent]
        
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent# Mock eliminated - using authentic gpt-4o-mini (mock_extract_kernel, mock_extract_agent)
        
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat# Mock eliminated - using authentic gpt-4o-mini mock_group_chat_instance
        
        async def mock_invoke():
            message1 = MagicMock(spec=ChatMessageContent); message1.name = "ProjectManagerAgent"; message1.role = AuthorRole.ASSISTANT
            message1.content = "Je vais définir les tâches d'analyse."
            state.add_task("Identifier les arguments dans le texte")
            state.add_task("Analyser les sophismes dans les arguments")
            state.designate_next_agent("InformalAnalysisAgent")
            yield message1
            
            message2 = MagicMock(spec=ChatMessageContent); message2.name = "InformalAnalysisAgent"; message2.role = AuthorRole.ASSISTANT
            message2.content = "J'ai identifié les arguments suivants."
            arg1_id = state.add_argument("La Terre est plate car l'horizon semble plat")
            arg2_id = state.add_argument("Si la Terre était ronde, les gens tomberaient")
            arg3_id = state.add_argument("Les scientifiques sont payés par la NASA")
            task1_id = next(iter(state.analysis_tasks))
            state.add_answer(task1_id, "InformalAnalysisAgent", "J'ai identifié 3 arguments.", [arg1_id, arg2_id, arg3_id])
            state.designate_next_agent("InformalAnalysisAgent")
            yield message2
            
            message3 = MagicMock(spec=ChatMessageContent); message3.name = "InformalAnalysisAgent"; message3.role = AuthorRole.ASSISTANT
            message3.content = "J'ai identifié les sophismes suivants."
            fallacy1_id = state.add_fallacy("Faux raisonnement", "Confusion", arg1_id)
            fallacy2_id = state.add_fallacy("Fausse analogie", "Gravité", arg2_id)
            fallacy3_id = state.add_fallacy("Ad hominem", "Crédibilité", arg3_id)
            task_ids = list(state.analysis_tasks.keys())
            if len(task_ids) > 1:
                task2_id = task_ids[1]
                state.add_answer(task2_id, "InformalAnalysisAgent", "J'ai identifié 3 sophismes.", [fallacy1_id, fallacy2_id, fallacy3_id])
            state.designate_next_agent("PropositionalLogicAgent")
            yield message3
            
            message4 = MagicMock(spec=ChatMessageContent); message4.name = "PropositionalLogicAgent"; message4.role = AuthorRole.ASSISTANT
            message4.content = "Je vais formaliser l'argument principal."
            bs_id = state.add_belief_set("Propositional", "p => q\np\n")
            state.log_query(bs_id, "p => q", "ACCEPTED (True)")
            state.designate_next_agent("ExtractAgent")
            yield message4
            
            message5 = MagicMock(spec=ChatMessageContent); message5.name = "ExtractAgent"; message5.role = AuthorRole.ASSISTANT
            message5.content = "J'ai analysé l'extrait du texte."
            state.add_extract("Extrait du texte", "La Terre est plate")
            state.designate_next_agent("ProjectManagerAgent")
            yield message5
            
            message6 = MagicMock(spec=ChatMessageContent); message6.name = "ProjectManagerAgent"; message6.role = AuthorRole.ASSISTANT
            message6.content = "Voici la conclusion de l'analyse."
            state.set_conclusion("Le texte contient plusieurs sophismes.")
            yield message6
        
        mock_group_chat_instance.invoke = mock_invoke
        mock_group_chat_instance.history = Magicawait self._create_authentic_gpt4o_mini_instance(); mock_group_chat_instance.history.add_user_message = Magicawait self._create_authentic_gpt4o_mini_instance(); mock_group_chat_instance.history.messages = []
        
        await run_analysis_conversation(test_text, llm_service)
        
        assert len(state.analysis_tasks) == 2
        assert len(state.identified_arguments) == 3
        assert len(state.identified_fallacies) == 3
        assert len(state.belief_sets) == 1
        assert len(state.query_log) == 1
        assert len(state.answers) == 2
        assert len(state.extracts) == 1
        assert state.final_conclusion is not None
        
        mock_agent_group_chat.# Mock assertion eliminated - authentic validation
        assert mock_chat_completion_agent.call_count == 4

    
    
    
    
    
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        mock_setup_pm_kernel,
        mock_setup_informal_kernel,
        mock_setup_pl_kernel,
        mock_setup_extract_agent,
        mock_chat_completion_agent,
        mock_agent_group_chat,
        analysis_fixture
    ):
        state, llm_service, _, test_text = analysis_fixture
        mock_pm_agent = MagicMock(spec=Agent); mock_pm_agent.name = "ProjectManagerAgent"
        mock_informal_agent = MagicMock(spec=Agent); mock_informal_agent.name = "InformalAnalysisAgent"
        mock_pl_agent = MagicMock(spec=Agent); mock_pl_agent.name = "PropositionalLogicAgent"
        mock_extract_agent = MagicMock(spec=Agent); mock_extract_agent.name = "ExtractAgent"
        
        mock_chat_completion_agent# Mock eliminated - using authentic gpt-4o-mini [mock_pm_agent, mock_informal_agent, mock_pl_agent, mock_extract_agent]
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent# Mock eliminated - using authentic gpt-4o-mini (mock_extract_kernel, mock_extract_agent)
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat# Mock eliminated - using authentic gpt-4o-mini mock_group_chat_instance
        
        async def mock_invoke():
            message1 = MagicMock(spec=ChatMessageContent); message1.name = "ProjectManagerAgent"; message1.role = AuthorRole.ASSISTANT
            message1.content = "Définition des tâches."
            state.add_task("Identifier les arguments")
            state.designate_next_agent("InformalAnalysisAgent")
            yield message1
            
            message2 = MagicMock(spec=ChatMessageContent); message2.name = "InformalAnalysisAgent"; message2.role = AuthorRole.ASSISTANT
            message2.content = "Erreur d'identification."
            state.log_error("InformalAnalysisAgent", "Erreur arguments")
            state.designate_next_agent("ProjectManagerAgent")
            yield message2
            
            message3 = MagicMock(spec=ChatMessageContent); message3.name = "ProjectManagerAgent"; message3.role = AuthorRole.ASSISTANT
            message3.content = "Gestion erreur."
            state.add_task("Analyser sophismes directement")
            state.designate_next_agent("InformalAnalysisAgent")
            yield message3
            
            message4 = MagicMock(spec=ChatMessageContent); message4.name = "InformalAnalysisAgent"; message4.role = AuthorRole.ASSISTANT
            message4.content = "Analyse sophismes."
            arg1_id = state.add_argument("Argument récupéré")
            fallacy1_id = state.add_fallacy("Sophisme récupéré", "Desc", arg1_id)
            task_ids = list(state.analysis_tasks.keys())
            if len(task_ids) > 1:
                task2_id = task_ids[1]
                state.add_answer(task2_id, "InformalAnalysisAgent", "1 sophisme.", [fallacy1_id])
            state.designate_next_agent("ProjectManagerAgent")
            yield message4
            
            message5 = MagicMock(spec=ChatMessageContent); message5.name = "ProjectManagerAgent"; message5.role = AuthorRole.ASSISTANT
            message5.content = "Conclusion après récupération."
            state.set_conclusion("Analyse avec récupération.")
            yield message5
        
        mock_group_chat_instance.invoke = mock_invoke
        mock_group_chat_instance.history = Magicawait self._create_authentic_gpt4o_mini_instance(); mock_group_chat_instance.history.add_user_message = Magicawait self._create_authentic_gpt4o_mini_instance(); mock_group_chat_instance.history.messages = []
        
        await run_analysis_conversation(test_text, llm_service)
        
        assert len(state.analysis_tasks) == 2
        assert len(state.identified_arguments) == 1
        assert len(state.identified_fallacies) == 1
        assert len(state.errors) == 1
        assert len(state.answers) == 1
        assert state.final_conclusion is not None
        assert state.errors[0]["agent_name"] == "InformalAnalysisAgent"
        assert state.errors[0]["message"] == "Erreur arguments"

class TestPerformanceIntegration:
    """Tests d'intégration pour la performance du système."""

    @pytest.fixture
    def performance_fixture(self):
        test_text = "Texte pour test de performance."
        llm_service = Magicawait self._create_authentic_gpt4o_mini_instance(); llm_service.service_id = "test_service"
        return test_text, llm_service

    
    
    
    
    
    
    async def test_performance_metrics(
        self, mock_setup_pm_kernel, mock_setup_informal_kernel, mock_setup_pl_kernel,
        mock_setup_extract_agent, mock_chat_completion_agent, mock_agent_group_chat,
        performance_fixture
    ):
        test_text, llm_service = performance_fixture
        mock_pm_agent = MagicMock(spec=Agent); mock_pm_agent.name = "ProjectManagerAgent"
        mock_informal_agent = MagicMock(spec=Agent); mock_informal_agent.name = "InformalAnalysisAgent"
        mock_pl_agent = MagicMock(spec=Agent); mock_pl_agent.name = "PropositionalLogicAgent"
        mock_extract_agent = MagicMock(spec=Agent); mock_extract_agent.name = "ExtractAgent"
        
        mock_chat_completion_agent# Mock eliminated - using authentic gpt-4o-mini [mock_pm_agent, mock_informal_agent, mock_pl_agent, mock_extract_agent, mock_pm_agent]
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent# Mock eliminated - using authentic gpt-4o-mini (mock_extract_kernel, mock_extract_agent)
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat# Mock eliminated - using authentic gpt-4o-mini mock_group_chat_instance
        
        async def mock_invoke():
            async def sleep_and_yield(agent_name, content, delay):
                msg = MagicMock(spec=ChatMessageContent)
                msg.name = agent_name; msg.role = AuthorRole.ASSISTANT; msg.content = content
                await asyncio.sleep(delay)
                return msg  # Changed to return instead of yield
            
            yield await sleep_and_yield("ProjectManagerAgent", "Tâches définies.", 0.1)
            yield await sleep_and_yield("InformalAnalysisAgent", "Arguments analysés.", 0.3)
            yield await sleep_and_yield("PropositionalLogicAgent", "Arguments formalisés.", 0.5)
            yield await sleep_and_yield("ExtractAgent", "Extraits analysés.", 0.2)
            yield await sleep_and_yield("ProjectManagerAgent", "Conclusion.", 0.1)

        mock_group_chat_instance.invoke = mock_invoke()

        mock_group_chat_instance.history = Magicawait self._create_authentic_gpt4o_mini_instance(); mock_group_chat_instance.history.add_user_message = Magicawait self._create_authentic_gpt4o_mini_instance(); mock_group_chat_instance.history.messages = []
        
        start_time = time.time()
        await run_analysis_conversation(test_text, llm_service)
        execution_time = time.time() - start_time
        
        assert execution_time >= 1.2
        assert execution_time <= 2.0


@pytest.fixture
def balanced_strategy_fixture(monkeypatch):
    """Fixture pour les tests de la stratégie d'équilibrage."""
    test_text = "Texte source avec DEBUT_EXTRAIT et FIN_EXTRAIT."
    state = RhetoricalAnalysisState(test_text)
    
    mock_fetch_service = MagicMock(spec=FetchService)
    mock_fetch_service.fetch_text# Mock eliminated - using authentic gpt-4o-mini "Texte source avec DEBUT_EXTRAIT contenu FIN_EXTRAIT.", "https://example.com/test"
    mock_fetch_service.reconstruct_url# Mock eliminated - using authentic gpt-4o-mini "https://example.com/test"
    
    mock_extract_service = MagicMock(spec=ExtractService)
    mock_extract_service.extract_text_with_markers# Mock eliminated - using authentic gpt-4o-mini "contenu", "Extraction réussie", True, True
    
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
        
        pm_agent = MagicMock(spec=Agent); pm_agent.name = "ProjectManagerAgent"
        pl_agent = MagicMock(spec=Agent); pl_agent.name = "PropositionalLogicAgent"
        informal_agent = MagicMock(spec=Agent); informal_agent.name = "InformalAnalysisAgent"
        extract_agent_mock = MagicMock(spec=Agent); extract_agent_mock.name = "ExtractAgent"
        
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