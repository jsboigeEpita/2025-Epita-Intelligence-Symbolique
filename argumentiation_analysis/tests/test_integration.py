"""
Tests d'intégration pour le projet d'analyse argumentative.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk
from core.shared_state import RhetoricalAnalysisState
from core.state_manager_plugin import StateManagerPlugin
from core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy
from orchestration.analysis_runner import run_analysis_conversation
from agents.extract.extract_agent import ExtractAgent
from agents.pl.pl_definitions import setup_pl_kernel
from agents.informal.informal_definitions import setup_informal_kernel
from agents.pm.pm_definitions import setup_pm_kernel
from tests.async_test_case import AsyncTestCase


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

    @patch('orchestration.analysis_runner.run_analysis_conversation')
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


if __name__ == '__main__':
    unittest.main()