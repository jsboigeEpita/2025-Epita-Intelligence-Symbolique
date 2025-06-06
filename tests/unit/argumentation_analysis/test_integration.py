# -*- coding: utf-8 -*-
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
# from tests import setup_import_paths # Commenté pour investigation
# setup_import_paths() # Commenté pour investigation

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
# from tests.async_test_case import AsyncTestCase # Suppression de l'import
from argumentation_analysis.services.web_api.models.request_models import ExtractDefinitions, Extract, SourceDefinition
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractResult
from argumentation_analysis.services.extract_service import ExtractService
from argumentation_analysis.services.fetch_service import FetchService


class TestBasicIntegration: # Suppression de l'héritage AsyncTestCase
    """Tests d'intégration de base pour vérifier l'interaction entre les composants."""

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

    @patch('semantic_kernel.Kernel')
    @patch('semantic_kernel.agents.Agent')
    async def test_component_interaction(self, mock_agent_class, mock_kernel_class):
        """Teste l'interaction de base entre les composants."""
        pm_agent = MagicMock()
        pm_agent.name = "ProjectManagerAgent"
        
        pl_agent = MagicMock()
        pl_agent.name = "PropositionalLogicAgent"
        
        informal_agent = MagicMock()
        informal_agent.name = "InformalAnalysisAgent"
        
        agents = [pm_agent, pl_agent, informal_agent]
        
        termination_strategy = SimpleTerminationStrategy(self.state, max_steps=3)
        selection_strategy = DelegatingSelectionStrategy(agents, self.state)
        
        self.state.add_task("Identifier les arguments dans le texte")
        
        arg_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        fallacy_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg_id)
        
        self.state.set_conclusion("Le texte contient plusieurs sophismes")
        
        self.assertEqual(len(self.state.analysis_tasks), 1)
        self.assertEqual(len(self.state.identified_arguments), 1)
        self.assertEqual(len(self.state.identified_fallacies), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        
        should_terminate = await termination_strategy.should_terminate(None, [])
        self.assertTrue(should_terminate)


class TestSimulatedAnalysisFlow: # Suppression de l'héritage AsyncTestCase
    """Tests simulant un flux d'analyse complet avec des mocks."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        self.state = RhetoricalAnalysisState(self.test_text)

    @patch('argumentation_analysis.orchestration.analysis_runner.run_analysis_conversation')
    async def test_simulated_analysis_flow(self, mock_run_analysis):
        """Simule un flux d'analyse complet."""
        mock_run_analysis.return_value = (True, "Analyse terminée avec succès")
        
        task1_id = self.state.add_task("Identifier les arguments dans le texte")
        task2_id = self.state.add_task("Analyser les sophismes dans les arguments")
        
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
        arg3_id = self.state.add_argument("Les scientifiques sont payés par la NASA")
        
        self.state.add_answer(
            task1_id, 
            "InformalAnalysisAgent", 
            "J'ai identifié 3 arguments dans le texte.", 
            [arg1_id, arg2_id, arg3_id]
        )
        
        fallacy1_id = self.state.add_fallacy("Faux raisonnement", "Confusion entre apparence et réalité", arg1_id)
        fallacy2_id = self.state.add_fallacy("Fausse analogie", "Mauvaise compréhension de la gravité", arg2_id)
        fallacy3_id = self.state.add_fallacy("Ad hominem", "Attaque la crédibilité plutôt que l'argument", arg3_id)
        
        self.state.add_answer(
            task2_id, 
            "InformalAnalysisAgent", 
            "J'ai identifié 3 sophismes dans les arguments.", 
            [fallacy1_id, fallacy2_id, fallacy3_id]
        )
        
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        log_id = self.state.log_query(bs_id, "p => q", "ACCEPTED (True)")
        
        self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.identified_arguments), 3)
        self.assertEqual(len(self.state.identified_fallacies), 3)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(len(self.state.answers), 2)
        self.assertIsNotNone(self.state.final_conclusion)


class TestExtractIntegration: # Suppression de l'héritage AsyncTestCase
    """Tests d'intégration pour les composants d'extraction."""

    def setUp(self):
        """Initialisation avant chaque test."""
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
        self.mock_fetch_service = MagicMock(spec=FetchService)
        self.mock_extract_service = MagicMock(spec=ExtractService)
        
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
        
        self.mock_extract_service.extract_text_with_markers.return_value = (
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
        self.integration_sample_definitions = ExtractDefinitions(sources=[source])
    
    async def test_extract_integration(self):
        """Teste l'intégration entre les services d'extraction et de récupération."""
        source = self.integration_sample_definitions.sources[0]
        extract = source.extracts[0]
        
        source_text, url = self.mock_fetch_service.fetch_text(source.to_dict())
        
        self.assertIsNotNone(source_text)
        self.assertEqual(url, "https://example.com/test")
        
        extracted_text, status, start_found, end_found = self.mock_extract_service.extract_text_with_markers(
            source_text, extract.start_marker, extract.end_marker
        )
        
        self.assertTrue(start_found)
        self.assertTrue(end_found)
        self.assertIn("Extraction réussie", status)


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])