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
from tests import setup_import_paths
setup_import_paths()

from argumentiation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentiation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentiation_analysis.core.strategies import BalancedParticipationStrategy, SimpleTerminationStrategy
from argumentiation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentiation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentiation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentiation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentiation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
from tests.async_test_case import AsyncTestCase
from models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from models.extract_result import ExtractResult
from services.extract_service import ExtractService
from services.fetch_service import FetchService


class TestEndToEndAnalysis(AsyncTestCase):
    """Tests d'intégration end-to-end pour le flux complet d'analyse argumentative."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un texte de test
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        # Créer un état partagé
        self.state = RhetoricalAnalysisState(self.test_text)
        
        # Créer un service LLM mock
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"
        
        # Créer un kernel
        self.kernel = sk.Kernel()
        
        # Ajouter le plugin StateManager
        self.state_manager = StateManagerPlugin(self.state)
        self.kernel.add_plugin(self.state_manager, "StateManager")

    @patch('orchestration.analysis_runner.AgentGroupChat')
    @patch('orchestration.analysis_runner.ChatCompletionAgent')
    @patch('orchestration.analysis_runner.setup_extract_agent')
    @patch('orchestration.analysis_runner.setup_pl_kernel')
    @patch('orchestration.analysis_runner.setup_informal_kernel')
    @patch('orchestration.analysis_runner.setup_pm_kernel')
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
        # Configurer les mocks pour les agents
        mock_pm_agent = MagicMock(spec=Agent)
        mock_pm_agent.name = "ProjectManagerAgent"
        
        mock_informal_agent = MagicMock(spec=Agent)
        mock_informal_agent.name = "InformalAnalysisAgent"
        
        mock_pl_agent = MagicMock(spec=Agent)
        mock_pl_agent.name = "PropositionalLogicAgent"
        
        mock_extract_agent = MagicMock(spec=Agent)
        mock_extract_agent.name = "ExtractAgent"
        
        # Configurer le mock pour ChatCompletionAgent
        mock_chat_completion_agent.side_effect = [
            mock_pm_agent,
            mock_informal_agent,
            mock_pl_agent,
            mock_extract_agent
        ]
        
        # Configurer le mock pour setup_extract_agent
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        # Configurer le mock pour AgentGroupChat
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        # Configurer le générateur asynchrone pour invoke qui simule une conversation complète
        async def mock_invoke():
            # 1. Message du PM - Définition des tâches
            message1 = MagicMock(spec=ChatMessageContent)
            message1.name = "ProjectManagerAgent"
            message1.role = AuthorRole.ASSISTANT
            message1.content = "Je vais définir les tâches d'analyse."
            # Simuler l'appel à StateManager.AddTask
            self.state.add_task("Identifier les arguments dans le texte")
            self.state.add_task("Analyser les sophismes dans les arguments")
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message1
            
            # 2. Message de l'agent informel - Identification des arguments
            message2 = MagicMock(spec=ChatMessageContent)
            message2.name = "InformalAnalysisAgent"
            message2.role = AuthorRole.ASSISTANT
            message2.content = "J'ai identifié les arguments suivants."
            # Simuler l'ajout d'arguments
            arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
            arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
            arg3_id = self.state.add_argument("Les scientifiques sont payés par la NASA")
            # Ajouter une réponse à la tâche
            # Récupérer l'ID de la première tâche
            task1_id = next(iter(self.state.analysis_tasks))
            self.state.add_answer(
                task1_id,
                "InformalAnalysisAgent",
                "J'ai identifié 3 arguments dans le texte.",
                [arg1_id, arg2_id, arg3_id]
            )
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message2
            
            # 3. Message de l'agent informel - Identification des sophismes
            message3 = MagicMock(spec=ChatMessageContent)
            message3.name = "InformalAnalysisAgent"
            message3.role = AuthorRole.ASSISTANT
            message3.content = "J'ai identifié les sophismes suivants."
            # Simuler l'ajout de sophismes
            fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
            fallacy2_id = self.state.add_fallacy("Fausse analogie", "Mauvaise compréhension de la gravité", arg2_id)
            fallacy3_id = self.state.add_fallacy("Ad hominem", "Attaque la crédibilité plutôt que l'argument", arg3_id)
            # Ajouter une réponse à la tâche
            # Récupérer l'ID de la deuxième tâche
            task_ids = list(self.state.analysis_tasks.keys())
            if len(task_ids) > 1:
                task2_id = task_ids[1]
                self.state.add_answer(
                    task2_id,
                    "InformalAnalysisAgent",
                    "J'ai identifié 3 sophismes dans les arguments.",
                    [fallacy1_id, fallacy2_id, fallacy3_id]
                )
            self.state.designate_next_agent("PropositionalLogicAgent")
            yield message3
            
            # 4. Message de l'agent PL - Formalisation d'un argument
            message4 = MagicMock(spec=ChatMessageContent)
            message4.name = "PropositionalLogicAgent"
            message4.role = AuthorRole.ASSISTANT
            message4.content = "Je vais formaliser l'argument principal."
            # Simuler l'ajout d'un ensemble de croyances
            bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
            # Simuler une requête logique
            log_id = self.state.log_query(bs_id, "p => q", "ACCEPTED (True)")
            self.state.designate_next_agent("ExtractAgent")
            yield message4
            
            # 5. Message de l'agent d'extraction - Analyse d'un extrait
            message5 = MagicMock(spec=ChatMessageContent)
            message5.name = "ExtractAgent"
            message5.role = AuthorRole.ASSISTANT
            message5.content = "J'ai analysé l'extrait du texte."
            # Simuler l'ajout d'un extrait
            extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
            self.state.designate_next_agent("ProjectManagerAgent")
            yield message5
            
            # 6. Message du PM - Conclusion
            message6 = MagicMock(spec=ChatMessageContent)
            message6.name = "ProjectManagerAgent"
            message6.role = AuthorRole.ASSISTANT
            message6.content = "Voici la conclusion de l'analyse."
            # Simuler l'ajout d'une conclusion
            self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
            yield message6
        
        mock_group_chat_instance.invoke = mock_invoke
        
        # Configurer le mock pour history
        mock_group_chat_instance.history = MagicMock()
        mock_group_chat_instance.history.add_user_message = MagicMock()
        mock_group_chat_instance.history.messages = []
        
        # Appeler la fonction à tester
        await run_analysis_conversation(self.test_text, self.llm_service)
        
        # Vérifier l'état final
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.identified_arguments), 3)
        self.assertEqual(len(self.state.identified_fallacies), 3)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(len(self.state.answers), 2)
        self.assertEqual(len(self.state.extracts), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        
        # Vérifier que les agents ont été appelés dans le bon ordre
        mock_agent_group_chat.assert_called_once()
        self.assertEqual(mock_chat_completion_agent.call_count, 4)

    @patch('orchestration.analysis_runner.AgentGroupChat')
    @patch('orchestration.analysis_runner.ChatCompletionAgent')
    @patch('orchestration.analysis_runner.setup_extract_agent')
    @patch('orchestration.analysis_runner.setup_pl_kernel')
    @patch('orchestration.analysis_runner.setup_informal_kernel')
    @patch('orchestration.analysis_runner.setup_pm_kernel')
    async def test_error_handling_and_recovery(
        self,
        mock_setup_pm_kernel,
        mock_setup_informal_kernel,
        mock_setup_pl_kernel,
        mock_setup_extract_agent,
        mock_chat_completion_agent,
        mock_agent_group_chat
    ):
        """Teste la gestion des erreurs et la récupération dans le flux d'analyse."""
        # Configurer les mocks pour les agents
        mock_pm_agent = MagicMock(spec=Agent)
        mock_pm_agent.name = "ProjectManagerAgent"
        
        mock_informal_agent = MagicMock(spec=Agent)
        mock_informal_agent.name = "InformalAnalysisAgent"
        
        mock_pl_agent = MagicMock(spec=Agent)
        mock_pl_agent.name = "PropositionalLogicAgent"
        
        mock_extract_agent = MagicMock(spec=Agent)
        mock_extract_agent.name = "ExtractAgent"
        
        # Configurer le mock pour ChatCompletionAgent
        mock_chat_completion_agent.side_effect = [
            mock_pm_agent,
            mock_informal_agent,
            mock_pl_agent,
            mock_extract_agent
        ]
        
        # Configurer le mock pour setup_extract_agent
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        # Configurer le mock pour AgentGroupChat
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        # Configurer le générateur asynchrone pour invoke qui simule une conversation avec erreur et récupération
        async def mock_invoke():
            # 1. Message du PM - Définition des tâches
            message1 = MagicMock(spec=ChatMessageContent)
            message1.name = "ProjectManagerAgent"
            message1.role = AuthorRole.ASSISTANT
            message1.content = "Je vais définir les tâches d'analyse."
            self.state.add_task("Identifier les arguments dans le texte")
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message1
            
            # 2. Message de l'agent informel - Erreur lors de l'identification des arguments
            message2 = MagicMock(spec=ChatMessageContent)
            message2.name = "InformalAnalysisAgent"
            message2.role = AuthorRole.ASSISTANT
            message2.content = "Je rencontre une difficulté pour identifier les arguments."
            # Simuler une erreur dans l'état
            self.state.log_error("InformalAnalysisAgent", "Erreur lors de l'identification des arguments")
            self.state.designate_next_agent("ProjectManagerAgent")
            yield message2
            
            # 3. Message du PM - Gestion de l'erreur
            message3 = MagicMock(spec=ChatMessageContent)
            message3.name = "ProjectManagerAgent"
            message3.role = AuthorRole.ASSISTANT
            message3.content = "Je vais gérer cette erreur et rediriger l'analyse."
            # Ajouter une nouvelle tâche pour contourner l'erreur
            self.state.add_task("Analyser directement les sophismes potentiels")
            self.state.designate_next_agent("InformalAnalysisAgent")
            yield message3
            
            # 4. Message de l'agent informel - Récupération et analyse des sophismes
            message4 = MagicMock(spec=ChatMessageContent)
            message4.name = "InformalAnalysisAgent"
            message4.role = AuthorRole.ASSISTANT
            message4.content = "Je vais analyser directement les sophismes potentiels."
            # Simuler l'ajout d'arguments et de sophismes
            arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
            fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
            # Ajouter une réponse à la tâche
            # Récupérer l'ID de la deuxième tâche
            task_ids = list(self.state.analysis_tasks.keys())
            if len(task_ids) > 1:
                task2_id = task_ids[1]
                self.state.add_answer(
                    task2_id,
                    "InformalAnalysisAgent",
                    "J'ai identifié un sophisme dans le texte.",
                    [fallacy1_id]
                )
            self.state.designate_next_agent("ProjectManagerAgent")
            yield message4
            
            # 5. Message du PM - Conclusion après récupération
            message5 = MagicMock(spec=ChatMessageContent)
            message5.name = "ProjectManagerAgent"
            message5.role = AuthorRole.ASSISTANT
            message5.content = "Voici la conclusion de l'analyse après récupération."
            # Simuler l'ajout d'une conclusion
            self.state.set_conclusion("Malgré les difficultés initiales, l'analyse a identifié un sophisme majeur.")
            yield message5
        
        mock_group_chat_instance.invoke = mock_invoke
        
        # Configurer le mock pour history
        mock_group_chat_instance.history = MagicMock()
        mock_group_chat_instance.history.add_user_message = MagicMock()
        mock_group_chat_instance.history.messages = []
        
        # Appeler la fonction à tester
        await run_analysis_conversation(self.test_text, self.llm_service)
        
        # Vérifier l'état final
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.identified_arguments), 1)
        self.assertEqual(len(self.state.identified_fallacies), 1)
        self.assertEqual(len(self.state.errors), 1)
        self.assertEqual(len(self.state.answers), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        
        # Vérifier que les erreurs ont été correctement enregistrées
        self.assertEqual(self.state.errors[0]["agent_name"], "InformalAnalysisAgent")
        self.assertEqual(self.state.errors[0]["message"], "Erreur lors de l'identification des arguments")


class TestPerformanceIntegration(AsyncTestCase):
    """Tests d'intégration pour la performance du système."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un texte de test
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        # Créer un service LLM mock
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"

    @patch('orchestration.analysis_runner.AgentGroupChat')
    @patch('orchestration.analysis_runner.ChatCompletionAgent')
    @patch('orchestration.analysis_runner.setup_extract_agent')
    @patch('orchestration.analysis_runner.setup_pl_kernel')
    @patch('orchestration.analysis_runner.setup_informal_kernel')
    @patch('orchestration.analysis_runner.setup_pm_kernel')
    async def test_performance_metrics(
        self,
        mock_setup_pm_kernel,
        mock_setup_informal_kernel,
        mock_setup_pl_kernel,
        mock_setup_extract_agent,
        mock_chat_completion_agent,
        mock_agent_group_chat
    ):
        """Teste les métriques de performance du système."""
        # Configurer les mocks pour les agents
        mock_pm_agent = MagicMock(spec=Agent)
        mock_pm_agent.name = "ProjectManagerAgent"
        
        mock_informal_agent = MagicMock(spec=Agent)
        mock_informal_agent.name = "InformalAnalysisAgent"
        
        mock_pl_agent = MagicMock(spec=Agent)
        mock_pl_agent.name = "PropositionalLogicAgent"
        
        mock_extract_agent = MagicMock(spec=Agent)
        mock_extract_agent.name = "ExtractAgent"
        
        # Configurer le mock pour ChatCompletionAgent
        mock_chat_completion_agent.side_effect = [
            mock_pm_agent,
            mock_informal_agent,
            mock_pl_agent,
            mock_extract_agent
        ]
        
        # Configurer le mock pour setup_extract_agent
        mock_extract_kernel = MagicMock(spec=sk.Kernel)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        # Configurer le mock pour AgentGroupChat
        mock_group_chat_instance = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        # Configurer le générateur asynchrone pour invoke qui simule une conversation
        async def mock_invoke():
            # Simuler des délais réalistes pour chaque agent
            # PM - Rapide
            message1 = MagicMock(spec=ChatMessageContent)
            message1.name = "ProjectManagerAgent"
            message1.role = AuthorRole.ASSISTANT
            message1.content = "Je vais définir les tâches d'analyse."
            await asyncio.sleep(0.1)  # Délai court pour le PM
            yield message1
            
            # Informel - Plus lent
            message2 = MagicMock(spec=ChatMessageContent)
            message2.name = "InformalAnalysisAgent"
            message2.role = AuthorRole.ASSISTANT
            message2.content = "J'analyse les arguments en détail."
            await asyncio.sleep(0.3)  # Délai plus long pour l'analyse informelle
            yield message2
            
            # PL - Très lent
            message3 = MagicMock(spec=ChatMessageContent)
            message3.name = "PropositionalLogicAgent"
            message3.role = AuthorRole.ASSISTANT
            message3.content = "Je formalise les arguments en logique propositionnelle."
            await asyncio.sleep(0.5)  # Délai encore plus long pour la formalisation
            yield message3
            
            # Extract - Moyen
            message4 = MagicMock(spec=ChatMessageContent)
            message4.name = "ExtractAgent"
            message4.role = AuthorRole.ASSISTANT
            message4.content = "J'analyse les extraits du texte."
            await asyncio.sleep(0.2)  # Délai moyen pour l'extraction
            yield message4
            
            # PM - Conclusion
            message5 = MagicMock(spec=ChatMessageContent)
            message5.name = "ProjectManagerAgent"
            message5.role = AuthorRole.ASSISTANT
            message5.content = "Voici la conclusion de l'analyse."
            await asyncio.sleep(0.1)  # Délai court pour la conclusion
            yield message5
        
        mock_group_chat_instance.invoke = mock_invoke
        
        # Configurer le mock pour history
        mock_group_chat_instance.history = MagicMock()
        mock_group_chat_instance.history.add_user_message = MagicMock()
        mock_group_chat_instance.history.messages = []
        
        # Mesurer le temps d'exécution
        start_time = time.time()
        
        # Appeler la fonction à tester
        await run_analysis_conversation(self.test_text, self.llm_service)
        
        # Calculer le temps d'exécution
        execution_time = time.time() - start_time
        
        # Vérifier que le temps d'exécution est raisonnable
        # La somme des délais est de 1.2 secondes, donc le temps total devrait être légèrement supérieur
        self.assertGreaterEqual(execution_time, 1.2)
        # Mais pas trop supérieur (ajout d'une marge pour l'overhead)
        self.assertLessEqual(execution_time, 2.0)


class TestExtractIntegrationWithBalancedStrategy(AsyncTestCase):
    """Tests d'intégration pour les composants d'extraction avec la stratégie d'équilibrage."""

    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un texte de test
        self.test_text = """
        Ceci est un exemple de texte source.
        Il contient plusieurs paragraphes.
        
        Voici un marqueur de début: DEBUT_EXTRAIT
        Ceci est le contenu de l'extrait.
        Il peut contenir plusieurs lignes.
        Voici un marqueur de fin: FIN_EXTRAIT
        
        Et voici la suite du texte après l'extrait.
        """
        
        # Créer un état partagé
        self.state = RhetoricalAnalysisState(self.test_text)
        
        # Créer un service LLM mock
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"

    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """Configure les mocks nécessaires pour le test."""
        # Créer un mock pour le service de récupération
        self.mock_fetch_service = MagicMock(spec=FetchService)
        
        # Simuler le comportement de fetch_text
        def mock_fetch_text(source_info, force_refresh=False):
            return """
            Ceci est un exemple de texte source.
            Il contient plusieurs paragraphes.
            
            Voici un marqueur de début: DEBUT_EXTRAIT
            Ceci est le contenu de l'extrait.
            Il peut contenir plusieurs lignes.
            Voici un marqueur de fin: FIN_EXTRAIT
            
            Et voici la suite du texte après l'extrait.
            """, "https://example.com/test"
        
        self.mock_fetch_service.fetch_text = MagicMock(side_effect=mock_fetch_text)
        self.mock_fetch_service.reconstruct_url = MagicMock(return_value="https://example.com/test")
        
        # Créer un mock pour le service d'extraction
        self.mock_extract_service = MagicMock(spec=ExtractService)
        
        # Simuler le comportement de extract_text_with_markers
        def mock_extract_text_with_markers(text, start_marker, end_marker, template_start=None):
            return "Ceci est le contenu de l'extrait.\nIl peut contenir plusieurs lignes.", "Extraction réussie", True, True
        
        self.mock_extract_service.extract_text_with_markers = MagicMock(side_effect=mock_extract_text_with_markers)
        
        # Créer un échantillon de définitions d'extraits
        self.integration_sample_definitions = ExtractDefinitions(sources=[
            SourceDefinition(
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
        ])
        
        # Monkeypatch les services
        monkeypatch.setattr("services.fetch_service.FetchService", lambda *args, **kwargs: self.mock_fetch_service)
        monkeypatch.setattr("services.extract_service.ExtractService", lambda *args, **kwargs: self.mock_extract_service)
    
    async def test_extract_integration_with_balanced_strategy(self):
        """Teste l'intégration entre les services d'extraction et la stratégie d'équilibrage."""
        # Récupérer la source et l'extrait de test
        source = self.integration_sample_definitions.sources[0]
        extract = source.extracts[0]
        
        # Créer des agents mock
        pm_agent = MagicMock(spec=Agent)
        pm_agent.name = "ProjectManagerAgent"
        
        pl_agent = MagicMock(spec=Agent)
        pl_agent.name = "PropositionalLogicAgent"
        
        informal_agent = MagicMock(spec=Agent)
        informal_agent.name = "InformalAnalysisAgent"
        
        extract_agent = MagicMock(spec=Agent)
        extract_agent.name = "ExtractAgent"
        
        agents = [pm_agent, pl_agent, informal_agent, extract_agent]
        
        # Créer la stratégie d'équilibrage
        balanced_strategy = BalancedParticipationStrategy(
            agents=agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        # Récupérer le texte source via le service de récupération mocké
        source_text, url = self.mock_fetch_service.fetch_text(source.to_dict())
        
        # Vérifier que le texte source a été récupéré
        self.assertIsNotNone(source_text)
        self.assertEqual(url, "https://example.com/test")
        
        # Extraire le texte avec les marqueurs
        extracted_text, status, start_found, end_found = self.mock_extract_service.extract_text_with_markers(
            source_text, extract.start_marker, extract.end_marker
        )
        
        # Vérifier que l'extraction a réussi
        self.assertTrue(start_found)
        self.assertTrue(end_found)
        self.assertIn("Extraction réussie", status)
        
        # Simuler l'ajout de l'extrait à l'état
        extract_id = self.state.add_extract(extract.extract_name, extracted_text)
        
        # Simuler une conversation avec la stratégie d'équilibrage
        history = []
        
        # Désigner l'agent d'extraction pour le prochain tour
        self.state.designate_next_agent("ExtractAgent")
        selected_agent = await balanced_strategy.next(agents, history)
        self.assertEqual(selected_agent, extract_agent)
        
        # Vérifier les compteurs de participation
        self.assertEqual(balanced_strategy._participation_counts["ExtractAgent"], 1)
        self.assertEqual(balanced_strategy._total_turns, 1)
        
        # Vérifier que l'extrait a été ajouté à l'état
        self.assertEqual(len(self.state.extracts), 1)
        self.assertEqual(self.state.extracts[0]["id"], extract_id)
        self.assertEqual(self.state.extracts[0]["name"], extract.extract_name)
        self.assertEqual(self.state.extracts[0]["content"], extracted_text)


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])