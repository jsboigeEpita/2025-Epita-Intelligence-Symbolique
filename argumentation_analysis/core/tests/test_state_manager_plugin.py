# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module state_manager_plugin.py qui fournit une interface
entre le kernel et l'état partagé d'une analyse rhétorique.
"""

import unittest
import json
import sys
from unittest.mock import patch, MagicMock, call

# Mock pour semantic_kernel.functions.kernel_function
sys.modules["semantic_kernel.functions"] = MagicMock()
sys.modules[
    "semantic_kernel.functions"
].kernel_function = lambda **kwargs: lambda func: func

# Maintenant on peut importer les modules à tester
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin


class TestStateManagerPlugin(unittest.TestCase):
    """Tests pour la classe StateManagerPlugin."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.initial_text = "Ceci est un texte d'exemple pour l'analyse rhétorique."
        self.state = RhetoricalAnalysisState(self.initial_text)
        self.plugin = StateManagerPlugin(self.state)

    def test_initialization(self):
        """Test de l'initialisation du plugin."""
        self.assertEqual(self.plugin._state, self.state)
        self.assertIsNotNone(self.plugin._logger)

    def test_get_current_state_snapshot(self):
        """Test de la récupération d'un snapshot de l'état."""
        # Test avec summarize=True (par défaut)
        snapshot_json = self.plugin.get_current_state_snapshot()
        snapshot = json.loads(snapshot_json)

        self.assertIn("raw_text", snapshot)
        self.assertIn("task_count", snapshot)
        self.assertIn("argument_count", snapshot)

        # Test avec summarize=False
        snapshot_json_full = self.plugin.get_current_state_snapshot(summarize=False)
        snapshot_full = json.loads(snapshot_json_full)

        self.assertIn("raw_text", snapshot_full)
        self.assertIn("analysis_tasks", snapshot_full)
        self.assertIn("identified_arguments", snapshot_full)

    def test_get_current_state_snapshot_error(self):
        """Test de la gestion des erreurs lors de la récupération d'un snapshot."""
        # Simuler une erreur dans get_state_snapshot
        with patch.object(
            self.state, "get_state_snapshot", side_effect=Exception("Erreur simulée")
        ):
            snapshot_json = self.plugin.get_current_state_snapshot()
            snapshot = json.loads(snapshot_json)

            self.assertIn("error", snapshot)

    def test_add_analysis_task(self):
        """Test de l'ajout d'une tâche via le plugin."""
        # Espionner la méthode add_task de l'état
        with patch.object(
            self.state, "add_task", return_value="task_1"
        ) as mock_add_task:
            task_description = "Analyser les arguments principaux"
            task_id = self.plugin.add_analysis_task(task_description)

            # Vérifier que la méthode de l'état a été appelée
            mock_add_task.assert_called_once_with(task_description)
            self.assertEqual(task_id, "task_1")

    def test_add_analysis_task_error(self):
        """Test de la gestion des erreurs lors de l'ajout d'une tâche."""
        # Simuler une erreur dans add_task
        with patch.object(
            self.state, "add_task", side_effect=Exception("Erreur simulée")
        ):
            task_description = "Analyser les arguments principaux"
            result = self.plugin.add_analysis_task(task_description)

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_add_identified_argument(self):
        """Test de l'ajout d'un argument via le plugin."""
        # Espionner la méthode add_argument de l'état
        with patch.object(
            self.state, "add_argument", return_value="arg_1"
        ) as mock_add_argument:
            arg_description = "L'auteur affirme que la Terre est ronde"
            arg_id = self.plugin.add_identified_argument(arg_description)

            # Vérifier que la méthode de l'état a été appelée
            mock_add_argument.assert_called_once_with(arg_description)
            self.assertEqual(arg_id, "arg_1")

    def test_add_identified_argument_error(self):
        """Test de la gestion des erreurs lors de l'ajout d'un argument."""
        # Simuler une erreur dans add_argument
        with patch.object(
            self.state, "add_argument", side_effect=Exception("Erreur simulée")
        ):
            arg_description = "L'auteur affirme que la Terre est ronde"
            result = self.plugin.add_identified_argument(arg_description)

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_add_identified_fallacy(self):
        """Test de l'ajout d'un sophisme via le plugin."""
        # Espionner la méthode add_fallacy de l'état
        with patch.object(
            self.state, "add_fallacy", return_value="fallacy_1"
        ) as mock_add_fallacy:
            fallacy_type = "ad_hominem"
            justification = "L'auteur attaque la personne plutôt que l'argument"
            target_arg_id = "arg_1"

            fallacy_id = self.plugin.add_identified_fallacy(
                fallacy_type, justification, target_arg_id
            )

            # Vérifier que la méthode de l'état a été appelée
            mock_add_fallacy.assert_called_once_with(
                fallacy_type, justification, target_arg_id
            )
            self.assertEqual(fallacy_id, "fallacy_1")

    def test_add_identified_fallacy_error(self):
        """Test de la gestion des erreurs lors de l'ajout d'un sophisme."""
        # Simuler une erreur dans add_fallacy
        with patch.object(
            self.state, "add_fallacy", side_effect=Exception("Erreur simulée")
        ):
            fallacy_type = "ad_hominem"
            justification = "L'auteur attaque la personne plutôt que l'argument"

            result = self.plugin.add_identified_fallacy(fallacy_type, justification)

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_add_belief_set_valid_type(self):
        """Test de l'ajout d'un belief set avec un type valide."""
        # Espionner la méthode add_belief_set de l'état
        with patch.object(
            self.state, "add_belief_set", return_value="bs_1"
        ) as mock_add_belief_set:
            # Tester avec différentes variations de "propositional"
            valid_types = [
                "propositional",
                "Propositional",
                "PROPOSITIONAL",
                "pl",
                "PL",
            ]

            for logic_type in valid_types:
                content = "A -> B, B -> C, A"
                bs_id = self.plugin.add_belief_set(logic_type, content)

                # Vérifier que la méthode de l'état a été appelée avec le type normalisé
                mock_add_belief_set.assert_called_with("Propositional", content)
                self.assertEqual(bs_id, "bs_1")

    def test_add_belief_set_invalid_type(self):
        """Test de l'ajout d'un belief set avec un type invalide."""
        logic_type = "invalid_type"
        content = "A -> B, B -> C, A"

        result = self.plugin.add_belief_set(logic_type, content)

        self.assertTrue(result.startswith("FUNC_ERROR"))
        self.assertIn("non supporté", result)

    def test_add_belief_set_error(self):
        """Test de la gestion des erreurs lors de l'ajout d'un belief set."""
        # Simuler une erreur dans add_belief_set
        with patch.object(
            self.state, "add_belief_set", side_effect=Exception("Erreur simulée")
        ):
            logic_type = "propositional"
            content = "A -> B, B -> C, A"

            result = self.plugin.add_belief_set(logic_type, content)

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_log_query_result(self):
        """Test de l'enregistrement d'une requête via le plugin."""
        # Espionner la méthode log_query de l'état
        with patch.object(
            self.state, "log_query", return_value="qlog_1"
        ) as mock_log_query:
            belief_set_id = "bs_1"
            query = "A -> C?"
            raw_result = "True"

            log_id = self.plugin.log_query_result(belief_set_id, query, raw_result)

            # Vérifier que la méthode de l'état a été appelée
            mock_log_query.assert_called_once_with(belief_set_id, query, raw_result)
            self.assertEqual(log_id, "qlog_1")

    def test_log_query_result_error(self):
        """Test de la gestion des erreurs lors de l'enregistrement d'une requête."""
        # Simuler une erreur dans log_query
        with patch.object(
            self.state, "log_query", side_effect=Exception("Erreur simulée")
        ):
            belief_set_id = "bs_1"
            query = "A -> C?"
            raw_result = "True"

            result = self.plugin.log_query_result(belief_set_id, query, raw_result)

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_add_answer(self):
        """Test de l'ajout d'une réponse via le plugin."""
        # Espionner la méthode add_answer de l'état
        with patch.object(self.state, "add_answer") as mock_add_answer:
            task_id = "task_1"
            author_agent = "agent_1"
            answer_text = "Les arguments principaux sont..."
            source_ids = ["arg_1", "arg_2"]

            result = self.plugin.add_answer(
                task_id, author_agent, answer_text, source_ids
            )

            # Vérifier que la méthode de l'état a été appelée
            mock_add_answer.assert_called_once_with(
                task_id, author_agent, answer_text, source_ids
            )
            self.assertTrue(result.startswith("OK"))

    def test_add_answer_error(self):
        """Test de la gestion des erreurs lors de l'ajout d'une réponse."""
        # Simuler une erreur dans add_answer
        with patch.object(
            self.state, "add_answer", side_effect=Exception("Erreur simulée")
        ):
            task_id = "task_1"
            author_agent = "agent_1"
            answer_text = "Les arguments principaux sont..."
            source_ids = ["arg_1", "arg_2"]

            result = self.plugin.add_answer(
                task_id, author_agent, answer_text, source_ids
            )

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_set_final_conclusion(self):
        """Test de l'enregistrement de la conclusion finale via le plugin."""
        # Espionner la méthode set_conclusion de l'état
        with patch.object(self.state, "set_conclusion") as mock_set_conclusion:
            conclusion = "La conclusion de l'analyse est..."

            result = self.plugin.set_final_conclusion(conclusion)

            # Vérifier que la méthode de l'état a été appelée
            mock_set_conclusion.assert_called_once_with(conclusion)
            self.assertTrue(result.startswith("OK"))

    def test_set_final_conclusion_error(self):
        """Test de la gestion des erreurs lors de l'enregistrement de la conclusion."""
        # Simuler une erreur dans set_conclusion
        with patch.object(
            self.state, "set_conclusion", side_effect=Exception("Erreur simulée")
        ):
            conclusion = "La conclusion de l'analyse est..."

            result = self.plugin.set_final_conclusion(conclusion)

            self.assertTrue(result.startswith("FUNC_ERROR"))

    def test_designate_next_agent(self):
        """Test de la désignation du prochain agent via le plugin."""
        # Espionner la méthode designate_next_agent de l'état
        with patch.object(self.state, "designate_next_agent") as mock_designate:
            agent_name = "agent_1"

            result = self.plugin.designate_next_agent(agent_name)

            # Vérifier que la méthode de l'état a été appelée
            mock_designate.assert_called_once_with(agent_name)
            self.assertTrue(result.startswith("OK"))

    def test_designate_next_agent_error(self):
        """Test de la gestion des erreurs lors de la désignation du prochain agent."""
        # Simuler une erreur dans designate_next_agent
        with patch.object(
            self.state, "designate_next_agent", side_effect=Exception("Erreur simulée")
        ):
            agent_name = "agent_1"

            result = self.plugin.designate_next_agent(agent_name)

            self.assertTrue(result.startswith("FUNC_ERROR"))


if __name__ == "__main__":
    unittest.main()
