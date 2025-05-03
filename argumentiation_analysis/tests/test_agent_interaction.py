"""
Tests d'intégration pour l'interaction entre les différents agents.

Ce module contient des tests d'intégration qui vérifient l'interaction
entre les différents agents (PM, PL, Informal, Extract) dans le contexte
de la stratégie d'équilibrage de participation.
"""

import unittest
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
from tests import setup_import_paths
setup_import_paths()

from core.shared_state import RhetoricalAnalysisState
from core.state_manager_plugin import StateManagerPlugin
from core.strategies import BalancedParticipationStrategy
from orchestration.analysis_runner import run_analysis_conversation
from agents.core.extract.extract_agent import ExtractAgent
from agents.core.pl.pl_definitions import setup_pl_kernel
from agents.core.informal.informal_definitions import setup_informal_kernel
from agents.core.pm.pm_definitions import setup_pm_kernel
from tests.async_test_case import AsyncTestCase


class TestAgentInteraction(AsyncTestCase):
    """Tests d'intégration pour l'interaction entre les différents agents."""

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
        
        # Créer des agents mock
        self.pm_agent = MagicMock(spec=Agent)
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock(spec=Agent)
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock(spec=Agent)
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.extract_agent = MagicMock(spec=Agent)
        self.extract_agent.name = "ExtractAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]
        
        # Créer la stratégie d'équilibrage
        self.balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )

    async def test_pm_informal_interaction(self):
        """Teste l'interaction entre le PM et l'agent informel."""
        # Simuler une conversation entre le PM et l'agent informel
        history = []
        
        # 1. PM ajoute une tâche et désigne l'agent informel
        self.state.add_task("Identifier les arguments dans le texte")
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        # Vérifier que l'agent informel est sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.informal_agent)
        
        # Ajouter un message de l'agent informel à l'historique
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié les arguments suivants."
        history.append(informal_message)
        
        # 2. L'agent informel ajoute des arguments et répond à la tâche
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
        
        # Récupérer l'ID de la tâche (premier élément du dictionnaire)
        task_id = next(iter(self.state.analysis_tasks))
        
        self.state.add_answer(
            task_id,
            "InformalAnalysisAgent",
            "J'ai identifié 2 arguments dans le texte.",
            [arg1_id, arg2_id]
        )
        
        # Sans désignation explicite, la stratégie d'équilibrage devrait sélectionner un autre agent
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertNotEqual(selected_agent, self.informal_agent)
        
        # Vérifier l'état
        self.assertEqual(len(self.state.analysis_tasks), 1)
        self.assertEqual(len(self.state.identified_arguments), 2)
        self.assertEqual(len(self.state.answers), 1)

    async def test_informal_pl_interaction(self):
        """Teste l'interaction entre l'agent informel et l'agent PL."""
        # Simuler une conversation entre l'agent informel et l'agent PL
        history = []
        
        # 1. L'agent informel ajoute un argument
        arg_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        # Ajouter un message de l'agent informel à l'historique
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié un argument."
        history.append(informal_message)
        
        # L'agent informel désigne l'agent PL
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # Vérifier que l'agent PL est sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        # Ajouter un message de l'agent PL à l'historique
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser cet argument."
        history.append(pl_message)
        
        # 2. L'agent PL formalise l'argument
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        log_id = self.state.log_query(bs_id, "p => q", "ACCEPTED (True)")
        
        # Vérifier l'état
        self.assertEqual(len(self.state.identified_arguments), 1)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.query_log), 1)

    async def test_pl_extract_interaction(self):
        """Teste l'interaction entre l'agent PL et l'agent d'extraction."""
        # Simuler une conversation entre l'agent PL et l'agent d'extraction
        history = []
        
        # 1. L'agent PL ajoute un ensemble de croyances
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        # Ajouter un message de l'agent PL à l'historique
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "J'ai formalisé l'argument."
        history.append(pl_message)
        
        # L'agent PL désigne l'agent d'extraction
        self.state.designate_next_agent("ExtractAgent")
        
        # Vérifier que l'agent d'extraction est sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.extract_agent)
        
        # Ajouter un message de l'agent d'extraction à l'historique
        extract_message = MagicMock(spec=ChatMessageContent)
        extract_message.role = AuthorRole.ASSISTANT
        extract_message.name = "ExtractAgent"
        extract_message.content = "Je vais analyser l'extrait du texte."
        history.append(extract_message)
        
        # 2. L'agent d'extraction ajoute un extrait
        extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
        
        # Vérifier l'état
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.extracts), 1)

    async def test_extract_pm_interaction(self):
        """Teste l'interaction entre l'agent d'extraction et le PM."""
        # Simuler une conversation entre l'agent d'extraction et le PM
        history = []
        
        # 1. L'agent d'extraction ajoute un extrait
        extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
        
        # Ajouter un message de l'agent d'extraction à l'historique
        extract_message = MagicMock(spec=ChatMessageContent)
        extract_message.role = AuthorRole.ASSISTANT
        extract_message.name = "ExtractAgent"
        extract_message.content = "J'ai analysé l'extrait du texte."
        history.append(extract_message)
        
        # L'agent d'extraction désigne le PM
        self.state.designate_next_agent("ProjectManagerAgent")
        
        # Vérifier que le PM est sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        # Ajouter un message du PM à l'historique
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais conclure l'analyse."
        history.append(pm_message)
        
        # 2. Le PM ajoute une conclusion
        self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        # Vérifier l'état
        self.assertEqual(len(self.state.extracts), 1)
        self.assertIsNotNone(self.state.final_conclusion)

    async def test_full_agent_interaction_cycle(self):
        """Teste un cycle complet d'interaction entre tous les agents."""
        # Simuler une conversation complète entre tous les agents
        history = []
        
        # 1. PM ajoute une tâche
        self.state.add_task("Identifier les arguments dans le texte")
        
        # Ajouter un message du PM à l'historique
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        # PM désigne l'agent informel
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        # 2. L'agent informel ajoute des arguments
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.informal_agent)
        
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        # Ajouter un message de l'agent informel à l'historique
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié un argument."
        history.append(informal_message)
        
        # L'agent informel désigne l'agent PL
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # 3. L'agent PL formalise l'argument
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        # Ajouter un message de l'agent PL à l'historique
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "J'ai formalisé l'argument."
        history.append(pl_message)
        
        # L'agent PL désigne l'agent d'extraction
        self.state.designate_next_agent("ExtractAgent")
        
        # 4. L'agent d'extraction ajoute un extrait
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.extract_agent)
        
        extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
        
        # Ajouter un message de l'agent d'extraction à l'historique
        extract_message = MagicMock(spec=ChatMessageContent)
        extract_message.role = AuthorRole.ASSISTANT
        extract_message.name = "ExtractAgent"
        extract_message.content = "J'ai analysé l'extrait du texte."
        history.append(extract_message)
        
        # L'agent d'extraction désigne le PM
        self.state.designate_next_agent("ProjectManagerAgent")
        
        # 5. Le PM ajoute une conclusion
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        # Vérifier l'état final
        self.assertEqual(len(self.state.analysis_tasks), 1)
        self.assertEqual(len(self.state.identified_arguments), 1)
        self.assertEqual(len(self.state.belief_sets), 1)
        self.assertEqual(len(self.state.extracts), 1)
        self.assertIsNotNone(self.state.final_conclusion)
        
        # Vérifier les compteurs de participation
        self.assertEqual(self.balanced_strategy._participation_counts["ProjectManagerAgent"], 1)
        self.assertEqual(self.balanced_strategy._participation_counts["InformalAnalysisAgent"], 1)
        self.assertEqual(self.balanced_strategy._participation_counts["PropositionalLogicAgent"], 1)
        self.assertEqual(self.balanced_strategy._participation_counts["ExtractAgent"], 1)
        self.assertEqual(self.balanced_strategy._total_turns, 4)


class TestAgentInteractionWithErrors(AsyncTestCase):
    """Tests d'intégration pour l'interaction entre les agents avec des erreurs."""

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
        
        # Créer des agents mock
        self.pm_agent = MagicMock(spec=Agent)
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock(spec=Agent)
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock(spec=Agent)
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.extract_agent = MagicMock(spec=Agent)
        self.extract_agent.name = "ExtractAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]
        
        # Créer la stratégie d'équilibrage
        self.balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )

    async def test_error_recovery_interaction(self):
        """Teste l'interaction entre les agents lors de la récupération d'erreurs."""
        # Simuler une conversation avec une erreur et une récupération
        history = []
        
        # 1. PM ajoute une tâche
        self.state.add_task("Identifier les arguments dans le texte")
        
        # Ajouter un message du PM à l'historique
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        # PM désigne l'agent informel
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        # 2. L'agent informel rencontre une erreur
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.informal_agent)
        
        # Simuler une erreur
        self.state.log_error("InformalAnalysisAgent", "Erreur lors de l'identification des arguments")
        
        # Ajouter un message d'erreur de l'agent informel à l'historique
        informal_error_message = MagicMock(spec=ChatMessageContent)
        informal_error_message.role = AuthorRole.ASSISTANT
        informal_error_message.name = "InformalAnalysisAgent"
        informal_error_message.content = "Je rencontre une difficulté pour identifier les arguments."
        history.append(informal_error_message)
        
        # L'agent informel désigne le PM pour gérer l'erreur
        self.state.designate_next_agent("ProjectManagerAgent")
        
        # 3. Le PM gère l'erreur
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        # PM ajoute une nouvelle tâche pour contourner l'erreur
        self.state.add_task("Analyser directement les sophismes potentiels")
        
        # Ajouter un message du PM à l'historique
        pm_recovery_message = MagicMock(spec=ChatMessageContent)
        pm_recovery_message.role = AuthorRole.ASSISTANT
        pm_recovery_message.name = "ProjectManagerAgent"
        pm_recovery_message.content = "Je vais gérer cette erreur et rediriger l'analyse."
        history.append(pm_recovery_message)
        
        # PM désigne l'agent PL pour continuer l'analyse
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # 4. L'agent PL continue l'analyse
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        # Ajouter un message de l'agent PL à l'historique
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser les arguments potentiels."
        history.append(pl_message)
        
        # Vérifier l'état
        self.assertEqual(len(self.state.analysis_tasks), 2)
        self.assertEqual(len(self.state.errors), 1)
        self.assertEqual(self.state.errors[0]["agent_name"], "InformalAnalysisAgent")
        self.assertEqual(self.state.errors[0]["message"], "Erreur lors de l'identification des arguments")
        
        # Vérifier les compteurs de participation
        self.assertEqual(self.balanced_strategy._participation_counts["ProjectManagerAgent"], 1)
        self.assertEqual(self.balanced_strategy._participation_counts["InformalAnalysisAgent"], 1)
        self.assertEqual(self.balanced_strategy._participation_counts["PropositionalLogicAgent"], 1)
        self.assertEqual(self.balanced_strategy._total_turns, 3)


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])