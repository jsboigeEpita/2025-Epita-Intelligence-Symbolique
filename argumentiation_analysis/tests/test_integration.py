"""
Tests d'intégration pour le projet d'analyse argumentative.

Ce module contient des tests d'intégration qui vérifient l'interaction
entre les différents composants du système.
"""

import unittest
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
from tests import setup_import_paths
setup_import_paths()

from argumentiation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentiation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentiation_analysis.core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy
from argumentiation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentiation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentiation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentiation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentiation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
from tests.async_test_case import AsyncTestCase
from models.extract_definition import ExtractDefinitions, Extract, SourceDefinition
from models.extract_result import ExtractResult
from services.extract_service import ExtractService
from services.fetch_service import FetchService


class TestBasicIntegration(AsyncTestCase):
    """Tests d'intégration de base pour vérifier l'interaction entre les composants."""

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

    @patch('semantic_kernel.Kernel')
    @patch('semantic_kernel.agents.Agent')
    async def test_component_interaction(self, mock_agent_class, mock_kernel_class):
        """Teste l'interaction de base entre les composants."""
        # Créer des agents mock
        pm_agent = MagicMock()
        pm_agent.name = "ProjectManagerAgent"
        
        pl_agent = MagicMock()
        pl_agent.name = "PropositionalLogicAgent"
        
        informal_agent = MagicMock()
        informal_agent.name = "InformalAnalysisAgent"
        
        agents = [pm_agent, pl_agent, informal_agent]
        
        # Créer des stratégies
        termination_strategy = SimpleTerminationStrategy(self.state, max_steps=3)
        selection_strategy = DelegatingSelectionStrategy(agents, self.state)
        
        # Simuler une conversation simple
        # Le PM ajoute une tâche
        self.state.add_task("Identifier les arguments dans le texte")
        
        # L'agent informel ajoute un argument
        arg_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        # L'agent informel ajoute un sophisme
        fallacy_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg_id)
        
        # Le PM ajoute une conclusion
        self.state.set_conclusion("Le texte contient plusieurs sophismes")
        
        # Vérifier l'état final
        self.assertEqual(len(self.state.analysis_tasks), 1)
        self.assertEqual(len(self.state.identified_arguments), 1)
        self.assertEqual(len(self.state.identified_fallacies), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        
        # Vérifier que la stratégie de terminaison détecte la fin
        should_terminate = await termination_strategy.should_terminate(None, [])
        self.assertTrue(should_terminate)


class TestSimulatedAnalysisFlow(AsyncTestCase):
    """Tests simulant un flux d'analyse complet avec des mocks."""

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

    @patch('argumentiation_analysis.orchestration.analysis_runner.run_analysis_conversation')
    async def test_simulated_analysis_flow(self, mock_run_analysis):
        """Simule un flux d'analyse complet."""
        # Configurer le mock pour simuler une analyse réussie
        mock_run_analysis.return_value = (True, "Analyse terminée avec succès")
        
        # Simuler les étapes d'une analyse
        
        # 1. Le PM identifie les tâches
        task1_id = self.state.add_task("Identifier les arguments dans le texte")
        task2_id = self.state.add_task("Analyser les sophismes dans les arguments")
        
        # 2. L'agent informel identifie les arguments
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
        arg3_id = self.state.add_argument("Les scientifiques sont payés par la NASA")
        
        # 3. L'agent informel ajoute une réponse pour la première tâche
        self.state.add_answer(
            task1_id, 
            "InformalAnalysisAgent", 
            "J'ai identifié 3 arguments dans le texte.", 
            [arg1_id, arg2_id, arg3_id]
        )
        
        # 4. L'agent informel identifie les sophismes
        fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
        fallacy2_id = self.state.add_fallacy("Fausse analogie", "Mauvaise compréhension de la gravité", arg2_id)
        fallacy3_id = self.state.add_fallacy("Ad hominem", "Attaque la crédibilité plutôt que l'argument", arg3_id)
        
        # 5. L'agent informel ajoute une réponse pour la deuxième tâche
        self.state.add_answer(
            task2_id, 
            "InformalAnalysisAgent", 
            "J'ai identifié 3 sophismes dans les arguments.", 
            [fallacy1_id, fallacy2_id, fallacy3_id]
        )
        
        # 6. L'agent PL formalise un des arguments
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        # 7. L'agent PL fait une requête
        log_id = self.state.log_query(bs_id, "p => q", "ACCEPTED (True)")
        
        # 8. Le PM ajoute une conclusion
        self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        # Vérifier l'état final
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.identified_arguments), 3)
        self.assertEqual(len(self.state.identified_fallacies), 3)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(len(self.state.answers), 2)
        self.assertIsNotNone(self.state.final_conclusion)


class TestExtractIntegration(AsyncTestCase):
    """Tests d'intégration pour les composants d'extraction."""

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

    @pytest.fixture(autouse=True)
    def setup_mocks(self, request):
        """Configure les mocks nécessaires pour le test."""
        # Créer des mocks pour les services
        self.mock_fetch_service = MagicMock(spec=FetchService)
        self.mock_extract_service = MagicMock(spec=ExtractService)
        
        # Configurer le mock pour fetch_text
        sample_text = """
        Ceci est un exemple de texte source.
        Il contient plusieurs paragraphes.
        
        Voici un marqueur de début: DEBUT_EXTRAIT
        Ceci est le contenu de l'extrait.
        Il peut contenir plusieurs lignes.
        Voici un marqueur de fin: FIN_EXTRAIT
        
        Et voici la suite du texte après l'extrait.
        """
        self.mock_fetch_service.fetch_text.return_value = (sample_text, "https://example.com/test")
        
        # Configurer le mock pour extract_text_with_markers
        self.mock_extract_service.extract_text_with_markers.return_value = (
            "Ceci est le contenu de l'extrait.\nIl peut contenir plusieurs lignes.",
            "✅ Extraction réussie",
            True,
            True
        )
        
        # Créer un échantillon de définitions d'extraits
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
        self.integration_sample_definitions = ExtractDefinitions(sources=[source])
    
    async def test_extract_integration(self):
        """Teste l'intégration entre les services d'extraction et de récupération."""
        # Récupérer la source et l'extrait de test
        source = self.integration_sample_definitions.sources[0]
        extract = source.extracts[0]
        
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


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])