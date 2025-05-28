# -*- coding: utf-8 -*-
"""
Tests d'intégration pour la communication entre agents via l'état partagé.

Ce module contient des tests d'intégration qui vérifient que les agents peuvent
communiquer efficacement via l'état partagé, en ajoutant et en consommant des
informations de manière cohérente.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
from argumentation_analysis.tests import setup_import_paths
setup_import_paths()

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
from argumentation_analysis.tests.async_test_case import AsyncTestCase


class TestAgentCommunication(AsyncTestCase):
    """Tests d'intégration pour la communication entre agents via l'état partagé."""

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
        self.pm_agent = MagicMock()
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock()
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock()
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.extract_agent = MagicMock()
        self.extract_agent.name = "ExtractAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]
        
        # Créer la stratégie d'équilibrage
        self.balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )

    async def test_state_sharing_between_agents(self):
        """Teste le partage d'état entre les agents."""
        # 1. Le PM ajoute une tâche
        task_id = self.state.add_task("Identifier les sophismes dans le texte")
        
        # Vérifier que la tâche a été ajoutée correctement
        self.assertIn(task_id, self.state.analysis_tasks)
        self.assertEqual(self.state.analysis_tasks[task_id], "Identifier les sophismes dans le texte")
        
        # 2. L'agent informel ajoute un argument
        arg_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        # Vérifier que l'argument a été ajouté correctement
        self.assertIn(arg_id, self.state.identified_arguments)
        self.assertEqual(self.state.identified_arguments[arg_id], "La Terre est plate car l'horizon semble plat")
        
        # 3. L'agent informel ajoute un sophisme lié à cet argument
        fallacy_id = self.state.add_fallacy(
            "Faux raisonnement", 
            "Confusion entre apparence et réalité", 
            arg_id
        )
        
        # Vérifier que le sophisme a été ajouté correctement
        self.assertIn(fallacy_id, self.state.identified_fallacies)
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["type"], "Faux raisonnement")
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["justification"], "Confusion entre apparence et réalité")
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["target_argument_id"], arg_id)
        
        # 4. L'agent PL ajoute un ensemble de croyances
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        # Vérifier que l'ensemble de croyances a été ajouté correctement
        self.assertIn(bs_id, self.state.belief_sets)
        self.assertEqual(self.state.belief_sets[bs_id]["logic_type"], "Propositional")
        self.assertEqual(self.state.belief_sets[bs_id]["content"], "p => q\np\n")
        
        # 5. L'agent PL enregistre une requête
        query = "p => q"
        raw_result = "ACCEPTED (True)"
        log_id = self.state.log_query(bs_id, query, raw_result)
        
        # Vérifier que la requête a été enregistrée correctement
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(self.state.query_log[0]["log_id"], log_id)
        self.assertEqual(self.state.query_log[0]["belief_set_id"], bs_id)
        self.assertEqual(self.state.query_log[0]["query"], query)
        self.assertEqual(self.state.query_log[0]["raw_result"], raw_result)
        
        # 6. L'agent informel ajoute une réponse à la tâche
        self.state.add_answer(
            task_id,
            "InformalAnalysisAgent",
            "J'ai identifié un sophisme de faux raisonnement.",
            [fallacy_id]
        )
        
        # Vérifier que la réponse a été ajoutée correctement
        self.assertIn(task_id, self.state.answers)
        self.assertEqual(self.state.answers[task_id]["author_agent"], "InformalAnalysisAgent")
        self.assertEqual(self.state.answers[task_id]["answer_text"], "J'ai identifié un sophisme de faux raisonnement.")
        self.assertEqual(self.state.answers[task_id]["source_ids"], [fallacy_id])
        
        # 7. Le PM ajoute une conclusion
        conclusion = "Le texte contient un sophisme de faux raisonnement qui invalide l'argument principal."
        self.state.set_conclusion(conclusion)
        
        # Vérifier que la conclusion a été définie correctement
        self.assertEqual(self.state.final_conclusion, conclusion)

    async def test_agent_designation_mechanism(self):
        """Teste le mécanisme de désignation d'agents."""
        # Créer un historique de messages vide
        history = []
        
        # 1. Par défaut, le PM devrait être sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        # Ajouter un message du PM à l'historique
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        # 2. Le PM désigne l'agent informel
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        # Vérifier que l'agent informel est sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.informal_agent)
        
        # Ajouter un message de l'agent informel à l'historique
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié un argument."
        history.append(informal_message)
        
        # 3. L'agent informel désigne l'agent PL
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # Vérifier que l'agent PL est sélectionné
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        # Ajouter un message de l'agent PL à l'historique
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser l'argument."
        history.append(pl_message)
        
        # 4. L'agent PL désigne l'agent d'extraction
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
        
        # 5. Vérifier que la désignation est consommée correctement
        self.assertEqual(self.state._next_agent_designated, "ExtractAgent")
        consumed_agent = self.state.consume_next_agent_designation()
        self.assertEqual(consumed_agent, "ExtractAgent")
        self.assertIsNone(self.state._next_agent_designated)

    async def test_concurrent_state_access(self):
        """Teste l'accès concurrent à l'état partagé."""
        # Définir une fonction asynchrone qui ajoute des arguments à l'état
        async def add_arguments(state, prefix, count):
            arg_ids = []
            for i in range(count):
                arg_id = state.add_argument(f"{prefix} argument {i}")
                arg_ids.append(arg_id)
                await asyncio.sleep(0.01)  # Simuler un délai
            return arg_ids
        
        # Exécuter plusieurs tâches concurrentes qui ajoutent des arguments
        task1 = asyncio.create_task(add_arguments(self.state, "Informel", 5))
        task2 = asyncio.create_task(add_arguments(self.state, "PL", 5))
        task3 = asyncio.create_task(add_arguments(self.state, "Extract", 5))
        
        # Attendre que toutes les tâches soient terminées
        arg_ids1 = await task1
        arg_ids2 = await task2
        arg_ids3 = await task3
        
        # Vérifier que tous les arguments ont été ajoutés correctement
        self.assertEqual(len(self.state.identified_arguments), 15)
        
        # Vérifier que chaque ID d'argument est unique
        all_ids = arg_ids1 + arg_ids2 + arg_ids3
        self.assertEqual(len(all_ids), len(set(all_ids)))
        
        # Vérifier que tous les arguments sont présents dans l'état
        for arg_id in all_ids:
            self.assertIn(arg_id, self.state.identified_arguments)

    async def test_error_handling_in_communication(self):
        """Teste la gestion des erreurs dans la communication entre agents."""
        # 1. Enregistrer une erreur
        self.state.log_error("InformalAnalysisAgent", "Erreur lors de l'identification des arguments")
        
        # Vérifier que l'erreur a été enregistrée correctement
        self.assertEqual(len(self.state.errors), 1)
        self.assertEqual(self.state.errors[0]["agent_name"], "InformalAnalysisAgent")
        self.assertEqual(self.state.errors[0]["message"], "Erreur lors de l'identification des arguments")
        
        # 2. Tester la récupération après une erreur
        # Le PM ajoute une nouvelle tâche pour contourner l'erreur
        task_id = self.state.add_task("Analyser directement les sophismes potentiels")
        
        # L'agent informel ajoute un sophisme sans argument cible
        fallacy_id = self.state.add_fallacy("Ad hominem", "Attaque la personne plutôt que l'argument")
        
        # Vérifier que le sophisme a été ajouté correctement
        self.assertIn(fallacy_id, self.state.identified_fallacies)
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["type"], "Ad hominem")
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["justification"], "Attaque la personne plutôt que l'argument")
        self.assertNotIn("target_argument_id", self.state.identified_fallacies[fallacy_id])
        
        # L'agent informel ajoute une réponse à la tâche
        self.state.add_answer(
            task_id,
            "InformalAnalysisAgent",
            "J'ai identifié un sophisme ad hominem.",
            [fallacy_id]
        )
        
        # Vérifier que la réponse a été ajoutée correctement
        self.assertIn(task_id, self.state.answers)
        self.assertEqual(self.state.answers[task_id]["author_agent"], "InformalAnalysisAgent")
        self.assertEqual(self.state.answers[task_id]["answer_text"], "J'ai identifié un sophisme ad hominem.")
        self.assertEqual(self.state.answers[task_id]["source_ids"], [fallacy_id])


if __name__ == "__main__":
    unittest.main()