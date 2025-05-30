# -*- coding: utf-8 -*-
"""
Tests d'intégration end-to-end pour le système d'analyse argumentative.

Ce module contient des tests d'intégration qui vérifient le flux complet
d'analyse argumentative de bout en bout, y compris l'interaction entre
les différents agents et la gestion des erreurs.
"""

import unittest
import asyncio
import pytest
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch, call
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat
from semantic_kernel.exceptions import AgentChatException

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
# from tests import setup_import_paths # Commenté pour investigation
# setup_import_paths() # Commenté pour investigation

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy, SimpleTerminationStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
from tests.async_test_case import AsyncTestCase
from models.extract_definition import ExtractDefinitions, SourceDefinition, Extract # Ces imports pourraient poser problème
from models.extract_result import ExtractResult # Idem
from argumentation_analysis.services.extract_service import ExtractService # Idem pour 'services'
from argumentation_analysis.services.fetch_service import FetchService # Idem


class TestEndToEndAnalysis(AsyncTestCase):
    """Tests d'intégration end-to-end pour le flux complet d'analyse argumentative."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        self.state = RhetoricalAnalysisState(self.test_text)
        
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"
        
        self.kernel = sk.Kernel()
        
        self.state_manager = StateManagerPlugin(self.state)
        self.kernel.add_plugin(self.state_manager, "StateManager")

    @patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat') 
    @patch('argumentation_analysis.orchestration.analysis_runner.ChatCompletionAgent') 
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_extract_agent') 
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pl_kernel') 
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_informal_kernel') 
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pm_kernel') 
    async def test_complete_analysis_flow(
        self,
        mock_setup_pm_kernel,
        mock_setup_informal_kernel,
        mock_setup_pl_kernel,
        mock_setup_extract_agent,
        mock_chat_completion_agent,
        mock_agent_group_chat
    ):
        """Teste le flux complet d'analyse argumentative de bout en bout."""
        mock_pm_agent = MagicMock(spec=Agent)
        mock_pm_agent.name = "ProjectManagerAgent"
        
        mock_informal_agent = MagicMock(spec=Agent)
        mock_informal_agent.name = "InformalAnalysisAgent"
        
        mock_pl_agent = MagicMock(spec=Agent)
        mock_pl_agent.name = "PropositionalLogicAgent"
        
        mock_extract_agent = MagicMock(spec=Agent)
        mock_extract_agent.name = "ExtractAgent"
        
        mock_chat_completion_agent.side_effect = [
            mock_pm_agent,
            mock_informal_agent,
            mock_pl_agent,
            mock_extract_agent
        ]
        
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        async def mock_invoke():
            message1 = MagicMock(spec=ChatMessageContent)
            message1.name = "ProjectManagerAgent"; message1.role = AuthorRole.ASSISTANT
            message1.content = "Je vais définir les tâches d'analyse."
            self.state.add_task("Identifier les arguments dans le texte")
            self.state.add_task("Analyser les sophismes dans les arguments")
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message1
            
            message2 = MagicMock(spec=ChatMessageContent)
            message2.name = "InformalAnalysisAgent"; message2.role = AuthorRole.ASSISTANT
            message2.content = "J'ai identifié les arguments suivants."
            arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
            arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
            arg3_id = self.state.add_argument("Les scientifiques sont payés par la NASA")
            task1_id = next(iter(self.state.analysis_tasks))
            self.state.add_answer(task1_id, "InformalAnalysisAgent", "J'ai identifié 3 arguments.", [arg1_id, arg2_id, arg3_id])
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message2
            
            message3 = MagicMock(spec=ChatMessageContent)
            message3.name = "InformalAnalysisAgent"; message3.role = AuthorRole.ASSISTANT
            message3.content = "J'ai identifié les sophismes suivants."
            fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion", arg1_id)
            fallacy2_id = self.state.add_fallacy("Fausse analogie", "Gravité", arg2_id)
            fallacy3_id = self.state.add_fallacy("Ad hominem", "Crédibilité", arg3_id)
            task_ids = list(self.state.analysis_tasks.keys())
            if len(task_ids) > 1:
                task2_id = task_ids[1]
                self.state.add_answer(task2_id, "InformalAnalysisAgent", "J'ai identifié 3 sophismes.", [fallacy1_id, fallacy2_id, fallacy3_id])
            self.state.designate_next_agent("PropositionalLogicAgent")
            yield message3
            
            message4 = MagicMock(spec=ChatMessageContent)
            message4.name = "PropositionalLogicAgent"; message4.role = AuthorRole.ASSISTANT
            message4.content = "Je vais formaliser l'argument principal."
            bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
            log_id = self.state.log_query(bs_id, "p => q", "ACCEPTED (True)")
            self.state.designate_next_agent("ExtractAgent")
            yield message4
            
            message5 = MagicMock(spec=ChatMessageContent)
            message5.name = "ExtractAgent"; message5.role = AuthorRole.ASSISTANT
            message5.content = "J'ai analysé l'extrait du texte."
            extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate")
            self.state.designate_next_agent("ProjectManagerAgent")
            yield message5
            
            message6 = MagicMock(spec=ChatMessageContent)
            message6.name = "ProjectManagerAgent"; message6.role = AuthorRole.ASSISTANT
            message6.content = "Voici la conclusion de l'analyse."
            self.state.set_conclusion("Le texte contient plusieurs sophismes.")
            yield message6
        
        mock_group_chat_instance.invoke = mock_invoke
        mock_group_chat_instance.history = MagicMock()
        mock_group_chat_instance.history.add_user_message = MagicMock()
        mock_group_chat_instance.history.messages = []
        
        await run_analysis_conversation(self.test_text, self.llm_service)
        
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.identified_arguments), 3)
        self.assertEqual(len(self.state.identified_fallacies), 3)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(len(self.state.answers), 2)
        self.assertEqual(len(self.state.extracts), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        
        mock_agent_group_chat.assert_called_once()
        self.assertEqual(mock_chat_completion_agent.call_count, 4)

    @patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat')
    @patch('argumentation_analysis.orchestration.analysis_runner.ChatCompletionAgent')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_extract_agent')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pl_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_informal_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pm_kernel')
    async def test_error_handling_and_recovery(
        self,
        mock_setup_pm_kernel,
        mock_setup_informal_kernel,
        mock_setup_pl_kernel,
        mock_setup_extract_agent,
        mock_chat_completion_agent,
        mock_agent_group_chat
    ):
        mock_pm_agent = MagicMock(spec=Agent); mock_pm_agent.name = "ProjectManagerAgent"
        mock_informal_agent = MagicMock(spec=Agent); mock_informal_agent.name = "InformalAnalysisAgent"
        mock_pl_agent = MagicMock(spec=Agent); mock_pl_agent.name = "PropositionalLogicAgent"
        mock_extract_agent = MagicMock(spec=Agent); mock_extract_agent.name = "ExtractAgent"
        
        mock_chat_completion_agent.side_effect = [mock_pm_agent, mock_informal_agent, mock_pl_agent, mock_extract_agent]
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        async def mock_invoke():
            message1 = MagicMock(spec=ChatMessageContent); message1.name = "ProjectManagerAgent"; message1.role = AuthorRole.ASSISTANT
            message1.content = "Définition des tâches."
            self.state.add_task("Identifier les arguments")
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message1
            
            message2 = MagicMock(spec=ChatMessageContent); message2.name = "InformalAnalysisAgent"; message2.role = AuthorRole.ASSISTANT
            message2.content = "Erreur d'identification."
            self.state.log_error("InformalAnalysisAgent", "Erreur arguments")
            self.state.designate_next_agent("ProjectManagerAgent")
            yield message2
            
            message3 = MagicMock(spec=ChatMessageContent); message3.name = "ProjectManagerAgent"; message3.role = AuthorRole.ASSISTANT
            message3.content = "Gestion erreur."
            self.state.add_task("Analyser sophismes directement")
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message3
            
            message4 = MagicMock(spec=ChatMessageContent); message4.name = "InformalAnalysisAgent"; message4.role = AuthorRole.ASSISTANT
            message4.content = "Analyse sophismes."
            arg1_id = self.state.add_argument("Argument récupéré")
            fallacy1_id = self.state.add_fallacy("Sophisme récupéré", "Desc", arg1_id)
            task_ids = list(self.state.analysis_tasks.keys())
            if len(task_ids) > 1:
                task2_id = task_ids[1]
                self.state.add_answer(task2_id, "InformalAnalysisAgent", "1 sophisme.", [fallacy1_id])
            self.state.designate_next_agent("ProjectManagerAgent")
            yield message4
            
            message5 = MagicMock(spec=ChatMessageContent); message5.name = "ProjectManagerAgent"; message5.role = AuthorRole.ASSISTANT
            message5.content = "Conclusion après récupération."
            self.state.set_conclusion("Analyse avec récupération.")
            yield message5
        
        mock_group_chat_instance.invoke = mock_invoke
        mock_group_chat_instance.history = MagicMock(); mock_group_chat_instance.history.add_user_message = MagicMock(); mock_group_chat_instance.history.messages = []
        
        await run_analysis_conversation(self.test_text, self.llm_service)
        
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.identified_arguments), 1)
        self.assertEqual(len(self.state.identified_fallacies), 1)
        self.assertEqual(len(self.state.errors), 1)
        self.assertEqual(len(self.state.answers), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        self.assertEqual(self.state.errors[0]["agent_name"], "InformalAnalysisAgent")
        self.assertEqual(self.state.errors[0]["message"], "Erreur arguments")

class TestPerformanceIntegration(AsyncTestCase):
    """Tests d'intégration pour la performance du système."""

    def setUp(self):
        self.test_text = "Texte pour test de performance."
        self.llm_service = MagicMock(); self.llm_service.service_id = "test_service"

    @patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat')
    @patch('argumentation_analysis.orchestration.analysis_runner.ChatCompletionAgent')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_extract_agent')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pl_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_informal_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pm_kernel')
    async def test_performance_metrics(
        self, mock_setup_pm_kernel, mock_setup_informal_kernel, mock_setup_pl_kernel,
        mock_setup_extract_agent, mock_chat_completion_agent, mock_agent_group_chat
    ):
        mock_pm_agent = MagicMock(spec=Agent); mock_pm_agent.name = "ProjectManagerAgent"
        mock_informal_agent = MagicMock(spec=Agent); mock_informal_agent.name = "InformalAnalysisAgent"
        mock_pl_agent = MagicMock(spec=Agent); mock_pl_agent.name = "PropositionalLogicAgent"
        mock_extract_agent = MagicMock(spec=Agent); mock_extract_agent.name = "ExtractAgent"
        
        mock_chat_completion_agent.side_effect = [mock_pm_agent, mock_informal_agent, mock_pl_agent, mock_extract_agent, mock_pm_agent] 
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        async def mock_invoke():
            async def sleep_and_yield(agent_name, content, delay):
                msg = MagicMock(spec=ChatMessageContent)
                msg.name = agent_name; msg.role = AuthorRole.ASSISTANT; msg.content = content
                await asyncio.sleep(delay)
                yield msg
            
            yield await sleep_and_yield("ProjectManagerAgent", "Tâches définies.", 0.1)
            yield await sleep_and_yield("InformalAnalysisAgent", "Arguments analysés.", 0.3)
            yield await sleep_and_yield("PropositionalLogicAgent", "Arguments formalisés.", 0.5)
            yield await sleep_and_yield("ExtractAgent", "Extraits analysés.", 0.2)
            yield await sleep_and_yield("ProjectManagerAgent", "Conclusion.", 0.1)

        mock_group_chat_instance.invoke = mock_invoke() 

        mock_group_chat_instance.history = MagicMock(); mock_group_chat_instance.history.add_user_message = MagicMock(); mock_group_chat_instance.history.messages = []
        
        start_time = time.time()
        await run_analysis_conversation(self.test_text, self.llm_service)
        execution_time = time.time() - start_time
        
        self.assertGreaterEqual(execution_time, 1.2) 
        self.assertLessEqual(execution_time, 2.0)


class TestExtractIntegrationWithBalancedStrategy(AsyncTestCase):
    """Tests d'intégration pour les composants d'extraction avec la stratégie d'équilibrage."""

    def setUp(self):
        self.test_text = "Texte source avec DEBUT_EXTRAIT et FIN_EXTRAIT."
        self.state = RhetoricalAnalysisState(self.test_text)
        self.llm_service = MagicMock(); self.llm_service.service_id = "test_service"

    @pytest.fixture(autouse=True)
    def setup_mocks_for_extract_test(self, monkeypatch): 
        self.mock_fetch_service = MagicMock(spec=FetchService)
        def mock_fetch_text_impl(source_info, force_refresh=False):
            return "Texte source avec DEBUT_EXTRAIT contenu FIN_EXTRAIT.", "https://example.com/test"
        self.mock_fetch_service.fetch_text = MagicMock(side_effect=mock_fetch_text_impl)
        self.mock_fetch_service.reconstruct_url = MagicMock(return_value="https://example.com/test")
        
        self.mock_extract_service = MagicMock(spec=ExtractService)
        def mock_extract_text_impl(text, start_marker, end_marker, template_start=None):
            return "contenu", "Extraction réussie", True, True
        self.mock_extract_service.extract_text_with_markers = MagicMock(side_effect=mock_extract_text_impl)
        
        self.integration_sample_definitions = ExtractDefinitions(sources=[
            SourceDefinition(source_name="SourceInt", source_type="url", schema="https", host_parts=["example", "com"], path="/test",
                             extracts=[Extract(extract_name="ExtraitInt1", start_marker="DEBUT_EXTRAIT", end_marker="FIN_EXTRAIT")])
        ])
        
        monkeypatch.setattr("argumentation_analysis.services.fetch_service.FetchService", lambda: self.mock_fetch_service)
        monkeypatch.setattr("argumentation_analysis.services.extract_service.ExtractService", lambda: self.mock_extract_service)


    async def test_extract_integration_with_balanced_strategy(self):
        source = self.integration_sample_definitions.sources[0]
        extract_def = source.extracts[0] 
        
        pm_agent = MagicMock(spec=Agent); pm_agent.name = "ProjectManagerAgent"
        pl_agent = MagicMock(spec=Agent); pl_agent.name = "PropositionalLogicAgent"
        informal_agent = MagicMock(spec=Agent); informal_agent.name = "InformalAnalysisAgent"
        extract_agent_mock = MagicMock(spec=Agent); extract_agent_mock.name = "ExtractAgent" 
        
        agents = [pm_agent, pl_agent, informal_agent, extract_agent_mock]
        
        balanced_strategy = BalancedParticipationStrategy(agents=agents, state=self.state, default_agent_name="ProjectManagerAgent")
        
        source_text, url = self.mock_fetch_service.fetch_text(source.to_dict())
        self.assertIsNotNone(source_text)
        self.assertEqual(url, "https://example.com/test")
        
        extracted_text, status, start_found, end_found = self.mock_extract_service.extract_text_with_markers(
            source_text, extract_def.start_marker, extract_def.end_marker
        )
        self.assertTrue(start_found); self.assertTrue(end_found)
        self.assertIn("Extraction réussie", status)
        
        extract_id = self.state.add_extract(extract_def.extract_name, extracted_text)
        
        history = []
        self.state.designate_next_agent("ExtractAgent")
        selected_agent = await balanced_strategy.next(agents, history)
        self.assertEqual(selected_agent, extract_agent_mock)
        
        self.assertEqual(balanced_strategy._participation_counts["ExtractAgent"], 1)
        self.assertEqual(balanced_strategy._total_turns, 1)
        self.assertEqual(len(self.state.extracts), 1)
        self.assertEqual(self.state.extracts[0]["id"], extract_id)
        self.assertEqual(self.state.extracts[0]["name"], extract_def.extract_name)
        self.assertEqual(self.state.extracts[0]["content"], extracted_text)


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])