# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module shared_state.py qui gère l'état partagé d'une analyse rhétorique.
"""

import unittest
import json
from unittest.mock import patch, MagicMock

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    SharedState,
)


class TestRhetoricalAnalysisState(unittest.TestCase):
    """Tests pour la classe RhetoricalAnalysisState."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.initial_text = "Ceci est un texte d'exemple pour l'analyse rhétorique."
        self.state = RhetoricalAnalysisState(self.initial_text)

    def test_initialization(self):
        """Test de l'initialisation de l'état."""
        self.assertEqual(self.state.raw_text, self.initial_text)
        self.assertEqual(self.state.analysis_tasks, {})
        self.assertEqual(self.state.identified_arguments, {})
        self.assertEqual(self.state.identified_fallacies, {})
        self.assertEqual(self.state.belief_sets, {})
        self.assertEqual(self.state.query_log, [])
        self.assertEqual(self.state.answers, {})
        self.assertEqual(self.state.extracts, [])
        self.assertEqual(self.state.errors, [])
        self.assertIsNone(self.state.final_conclusion)
        self.assertIsNone(self.state._next_agent_designated)

    def test_generate_id(self):
        """Test de la génération d'ID."""
        # Test avec un dictionnaire vide
        id1 = self.state._generate_id("test", {})
        self.assertEqual(id1, "test_1")

        # Test avec un dictionnaire contenant des éléments
        test_dict = {"test_1": "value1", "test_2": "value2"}
        id2 = self.state._generate_id("test", test_dict)
        self.assertEqual(id2, "test_3")

        # Test avec une liste
        test_list = ["item1", "item2", "item3"]
        id3 = self.state._generate_id("test", test_list)
        self.assertEqual(id3, "test_4")

        # Test avec un type non valide
        id4 = self.state._generate_id("test", "not_a_dict_or_list")
        self.assertEqual(id4, "test_1")

    def test_add_task(self):
        """Test de l'ajout d'une tâche."""
        task_description = "Analyser les arguments principaux"
        task_id = self.state.add_task(task_description)

        self.assertIn(task_id, self.state.analysis_tasks)
        self.assertEqual(self.state.analysis_tasks[task_id], task_description)
        self.assertTrue(task_id.startswith("task_"))

    def test_add_argument(self):
        """Test de l'ajout d'un argument."""
        arg_description = "L'auteur affirme que la Terre est ronde"
        arg_id = self.state.add_argument(arg_description)

        self.assertIn(arg_id, self.state.identified_arguments)
        self.assertEqual(self.state.identified_arguments[arg_id], arg_description)
        self.assertTrue(arg_id.startswith("arg_"))

    def test_add_fallacy(self):
        """Test de l'ajout d'un sophisme."""
        fallacy_type = "ad_hominem"
        justification = "L'auteur attaque la personne plutôt que l'argument"

        # Test sans argument cible
        fallacy_id1 = self.state.add_fallacy(fallacy_type, justification)
        self.assertIn(fallacy_id1, self.state.identified_fallacies)
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id1]["type"], fallacy_type
        )
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id1]["justification"], justification
        )
        self.assertNotIn(
            "target_argument_id", self.state.identified_fallacies[fallacy_id1]
        )

        # Test avec argument cible
        arg_id = self.state.add_argument("Un argument cible")
        fallacy_id2 = self.state.add_fallacy(fallacy_type, justification, arg_id)
        self.assertIn(fallacy_id2, self.state.identified_fallacies)
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id2]["target_argument_id"], arg_id
        )

        # Test avec un argument cible inexistant
        with patch("logging.Logger.warning") as mock_warning:
            fallacy_id3 = self.state.add_fallacy(
                fallacy_type, justification, "arg_inexistant"
            )
            mock_warning.assert_called_once()

    def test_add_belief_set(self):
        """Test de l'ajout d'un belief set."""
        logic_type = "Propositional"
        content = "A -> B, B -> C, A"
        bs_id = self.state.add_belief_set(logic_type, content)

        self.assertIn(bs_id, self.state.belief_sets)
        self.assertEqual(self.state.belief_sets[bs_id]["logic_type"], logic_type)
        self.assertEqual(self.state.belief_sets[bs_id]["content"], content)
        self.assertTrue(bs_id.startswith("propositional_bs_"))

    def test_log_query(self):
        """Test de l'enregistrement d'une requête."""
        # Ajouter d'abord un belief set
        bs_id = self.state.add_belief_set("Propositional", "A -> B, B -> C, A")

        query = "A -> C?"
        raw_result = "True"
        log_id = self.state.log_query(bs_id, query, raw_result)

        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(self.state.query_log[0]["log_id"], log_id)
        self.assertEqual(self.state.query_log[0]["belief_set_id"], bs_id)
        self.assertEqual(self.state.query_log[0]["query"], query)
        self.assertEqual(self.state.query_log[0]["raw_result"], raw_result)

        # Test avec un belief set inexistant
        with patch("logging.Logger.warning") as mock_warning:
            log_id2 = self.state.log_query("bs_inexistant", query, raw_result)
            mock_warning.assert_called_once()

    def test_add_answer(self):
        """Test de l'ajout d'une réponse."""
        # Ajouter d'abord une tâche
        task_id = self.state.add_task("Analyser les arguments principaux")

        author_agent = "agent_1"
        answer_text = "Les arguments principaux sont..."
        source_ids = ["arg_1", "arg_2"]

        self.state.add_answer(task_id, author_agent, answer_text, source_ids)

        self.assertIn(task_id, self.state.answers)
        self.assertEqual(self.state.answers[task_id]["author_agent"], author_agent)
        self.assertEqual(self.state.answers[task_id]["answer_text"], answer_text)
        self.assertEqual(self.state.answers[task_id]["source_ids"], source_ids)

        # Test avec une tâche inexistante
        with patch("logging.Logger.warning") as mock_warning:
            self.state.add_answer(
                "task_inexistante", author_agent, answer_text, source_ids
            )
            mock_warning.assert_called_once()

    def test_set_conclusion(self):
        """Test de l'enregistrement de la conclusion finale."""
        conclusion = "La conclusion de l'analyse est..."
        self.state.set_conclusion(conclusion)

        self.assertEqual(self.state.final_conclusion, conclusion)

    def test_designate_next_agent(self):
        """Test de la désignation du prochain agent."""
        agent_name = "agent_1"
        self.state.designate_next_agent(agent_name)

        self.assertEqual(self.state._next_agent_designated, agent_name)

    def test_add_extract(self):
        """Test de l'ajout d'un extrait."""
        name = "Extrait important"
        content = "Contenu de l'extrait..."
        extract_id = self.state.add_extract(name, content)

        self.assertEqual(len(self.state.extracts), 1)
        self.assertEqual(self.state.extracts[0]["id"], extract_id)
        self.assertEqual(self.state.extracts[0]["name"], name)
        self.assertEqual(self.state.extracts[0]["content"], content)

    def test_log_error(self):
        """Test de l'enregistrement d'une erreur."""
        agent_name = "agent_1"
        message = "Une erreur s'est produite"
        error_id = self.state.log_error(agent_name, message)

        self.assertEqual(len(self.state.errors), 1)
        self.assertEqual(self.state.errors[0]["id"], error_id)
        self.assertEqual(self.state.errors[0]["agent_name"], agent_name)
        self.assertEqual(self.state.errors[0]["message"], message)

    def test_consume_next_agent_designation(self):
        """Test de la consommation de la désignation du prochain agent."""
        agent_name = "agent_1"
        self.state.designate_next_agent(agent_name)

        # Consommer la désignation
        consumed_agent = self.state.consume_next_agent_designation()
        self.assertEqual(consumed_agent, agent_name)

        # Vérifier que la désignation a été réinitialisée
        self.assertIsNone(self.state._next_agent_designated)

        # Consommer à nouveau (devrait retourner None)
        consumed_agent2 = self.state.consume_next_agent_designation()
        self.assertIsNone(consumed_agent2)

    def test_reset_state(self):
        """Test de la réinitialisation de l'état."""
        # Ajouter des données à l'état
        self.state.add_task("Tâche 1")
        self.state.add_argument("Argument 1")
        self.state.add_fallacy("ad_hominem", "Justification")
        self.state.add_belief_set("Propositional", "A -> B")
        self.state.add_extract("Extrait 1", "Contenu")
        self.state.log_error("agent_1", "Erreur")
        self.state.set_conclusion("Conclusion")
        self.state.designate_next_agent("agent_1")

        # Réinitialiser l'état
        self.state.reset_state()

        # Vérifier que l'état a été réinitialisé
        self.assertEqual(self.state.raw_text, self.initial_text)
        self.assertEqual(self.state.analysis_tasks, {})
        self.assertEqual(self.state.identified_arguments, {})
        self.assertEqual(self.state.identified_fallacies, {})
        self.assertEqual(self.state.belief_sets, {})
        self.assertEqual(self.state.query_log, [])
        self.assertEqual(self.state.answers, {})
        self.assertEqual(self.state.extracts, [])
        self.assertEqual(self.state.errors, [])
        self.assertIsNone(self.state.final_conclusion)
        self.assertIsNone(self.state._next_agent_designated)

    def test_get_state_snapshot_summarized(self):
        """Test de la récupération d'un snapshot résumé de l'état."""
        # Ajouter des données à l'état
        self.state.add_task("Tâche 1")
        self.state.add_argument("Argument 1")

        # Récupérer un snapshot résumé
        snapshot = self.state.get_state_snapshot(summarize=True)

        # Vérifier le contenu du snapshot
        self.assertIn("raw_text", snapshot)
        self.assertIn("task_count", snapshot)
        self.assertEqual(snapshot["task_count"], 1)
        self.assertIn("argument_count", snapshot)
        self.assertEqual(snapshot["argument_count"], 1)
        self.assertIn("tasks_defined", snapshot)
        self.assertEqual(len(snapshot["tasks_defined"]), 1)

    def test_get_state_snapshot_full(self):
        """Test de la récupération d'un snapshot complet de l'état."""
        # Ajouter des données à l'état
        task_id = self.state.add_task("Tâche 1")
        arg_id = self.state.add_argument("Argument 1")

        # Récupérer un snapshot complet
        snapshot = self.state.get_state_snapshot(summarize=False)

        # Vérifier le contenu du snapshot
        self.assertIn("raw_text", snapshot)
        self.assertIn("analysis_tasks", snapshot)
        self.assertIn(task_id, snapshot["analysis_tasks"])
        self.assertIn("identified_arguments", snapshot)
        self.assertIn(arg_id, snapshot["identified_arguments"])

    def test_to_json(self):
        """Test de la sérialisation en JSON."""
        # Ajouter des données à l'état
        self.state.add_task("Tâche 1")
        self.state.add_argument("Argument 1")

        # Sérialiser en JSON
        json_str = self.state.to_json()

        # Vérifier que le JSON est valide
        json_dict = json.loads(json_str)
        self.assertIn("raw_text", json_dict)
        self.assertIn("analysis_tasks", json_dict)
        self.assertIn("identified_arguments", json_dict)

    def test_from_dict(self):
        """Test de la création d'un état à partir d'un dictionnaire."""
        # Créer un dictionnaire d'état
        state_dict = {
            "raw_text": "Texte d'exemple",
            "analysis_tasks": {"task_1": "Tâche 1"},
            "identified_arguments": {"arg_1": "Argument 1"},
            "identified_fallacies": {
                "fallacy_1": {"type": "ad_hominem", "justification": "Justification"}
            },
            "belief_sets": {
                "bs_1": {"logic_type": "Propositional", "content": "A -> B"}
            },
            "query_log": [
                {
                    "log_id": "qlog_1",
                    "belief_set_id": "bs_1",
                    "query": "A -> B?",
                    "raw_result": "True",
                }
            ],
            "answers": {
                "task_1": {
                    "author_agent": "agent_1",
                    "answer_text": "Réponse",
                    "source_ids": ["arg_1"],
                }
            },
            "extracts": [
                {"id": "extract_1", "name": "Extrait 1", "content": "Contenu"}
            ],
            "errors": [
                {
                    "id": "error_1",
                    "agent_name": "agent_1",
                    "message": "Erreur",
                    "timestamp": None,
                }
            ],
            "final_conclusion": "Conclusion finale",
            "_next_agent_designated": "agent_1",
        }

        # Créer un état à partir du dictionnaire
        state = RhetoricalAnalysisState.from_dict(state_dict)

        # Vérifier que l'état a été correctement créé
        self.assertEqual(state.raw_text, "Texte d'exemple")
        self.assertEqual(state.analysis_tasks, {"task_1": "Tâche 1"})
        self.assertEqual(state.identified_arguments, {"arg_1": "Argument 1"})
        self.assertEqual(state.final_conclusion, "Conclusion finale")
        self.assertEqual(state._next_agent_designated, "agent_1")

    def test_shared_state_alias(self):
        """Test que SharedState est bien un alias de RhetoricalAnalysisState."""
        self.assertEqual(SharedState, RhetoricalAnalysisState)


if __name__ == "__main__":
    unittest.main()
