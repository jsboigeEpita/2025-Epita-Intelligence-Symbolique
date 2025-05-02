"""
Tests unitaires pour le module state_manager_plugin.
"""

import unittest
import json
from unittest.mock import MagicMock, patch
from core.state_manager_plugin import StateManagerPlugin
from core.shared_state import RhetoricalAnalysisState


class TestStateManagerPlugin(unittest.TestCase):
    """Tests pour la classe StateManagerPlugin."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")
        self.plugin = StateManagerPlugin(self.state)

    def test_initialization(self):
        """Teste l'initialisation correcte du plugin."""
        self.assertEqual(self.plugin._state, self.state)
        self.assertIsNotNone(self.plugin._logger)

    def test_get_current_state_snapshot(self):
        """Teste la récupération d'un snapshot de l'état."""
        # Test avec summarize=True (par défaut)
        snapshot_json = self.plugin.get_current_state_snapshot()
        snapshot = json.loads(snapshot_json)
        self.assertIn("raw_text", snapshot)
        
        # Test avec summarize=False
        detailed_snapshot_json = self.plugin.get_current_state_snapshot(summarize=False)
        detailed_snapshot = json.loads(detailed_snapshot_json)
        self.assertIn("raw_text", detailed_snapshot)
        
        # Vérifier que les deux snapshots sont différents
        # Le snapshot résumé et le snapshot détaillé devraient avoir des structures différentes
        self.assertNotEqual(set(snapshot.keys()), set(detailed_snapshot.keys()))

    def test_add_analysis_task(self):
        """Teste l'ajout d'une tâche d'analyse."""
        task_description = "Analyser les arguments principaux"
        task_id = self.plugin.add_analysis_task(task_description)
        
        # Vérifier que l'ID commence par "task_"
        self.assertTrue(task_id.startswith("task_"))
        
        # Vérifier que la tâche a été ajoutée à l'état
        self.assertIn(task_id, self.state.analysis_tasks)
        self.assertEqual(self.state.analysis_tasks[task_id], task_description)

    def test_add_identified_argument(self):
        """Teste l'ajout d'un argument identifié."""
        arg_description = "La Terre est ronde car on peut en faire le tour"
        arg_id = self.plugin.add_identified_argument(arg_description)
        
        # Vérifier que l'ID commence par "arg_"
        self.assertTrue(arg_id.startswith("arg_"))
        
        # Vérifier que l'argument a été ajouté à l'état
        self.assertIn(arg_id, self.state.identified_arguments)
        self.assertEqual(self.state.identified_arguments[arg_id], arg_description)

    def test_add_identified_fallacy(self):
        """Teste l'ajout d'un sophisme identifié."""
        fallacy_type = "Ad Hominem"
        justification = "Attaque la personne plutôt que l'argument"
        fallacy_id = self.plugin.add_identified_fallacy(fallacy_type, justification)
        
        # Vérifier que l'ID commence par "fallacy_"
        self.assertTrue(fallacy_id.startswith("fallacy_"))
        
        # Vérifier que le sophisme a été ajouté à l'état
        self.assertIn(fallacy_id, self.state.identified_fallacies)
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["type"], fallacy_type)
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["justification"], justification)

    def test_add_identified_fallacy_with_target(self):
        """Teste l'ajout d'un sophisme avec un argument cible."""
        # Ajouter d'abord un argument
        arg_description = "La Terre est ronde car on peut en faire le tour"
        arg_id = self.plugin.add_identified_argument(arg_description)
        
        # Ajouter un sophisme ciblant cet argument
        fallacy_type = "Ad Hominem"
        justification = "Attaque la personne plutôt que l'argument"
        fallacy_id = self.plugin.add_identified_fallacy(fallacy_type, justification, arg_id)
        
        # Vérifier que le sophisme a été ajouté avec la cible
        self.assertIn(fallacy_id, self.state.identified_fallacies)
        self.assertEqual(self.state.identified_fallacies[fallacy_id]["target_argument_id"], arg_id)

    def test_add_belief_set(self):
        """Teste l'ajout d'un belief set."""
        logic_type = "propositional"  # Test avec casse différente
        content = "a => b\nb => c\na"
        bs_id = self.plugin.add_belief_set(logic_type, content)
        
        # Vérifier que l'ID commence par "propositional_bs_"
        self.assertTrue(bs_id.startswith("propositional_bs_"))
        
        # Vérifier que le belief set a été ajouté à l'état
        self.assertIn(bs_id, self.state.belief_sets)
        self.assertEqual(self.state.belief_sets[bs_id]["logic_type"], "Propositional")  # Normalisé
        self.assertEqual(self.state.belief_sets[bs_id]["content"], content)

    def test_add_belief_set_invalid_type(self):
        """Teste l'ajout d'un belief set avec un type invalide."""
        logic_type = "invalid_type"
        content = "a => b"
        result = self.plugin.add_belief_set(logic_type, content)
        
        # Vérifier que l'opération a échoué
        self.assertTrue(result.startswith("FUNC_ERROR:"))
        self.assertNotIn("invalid_type", self.state.belief_sets)

    def test_log_query_result(self):
        """Teste l'enregistrement d'une requête."""
        # Ajouter d'abord un belief set
        bs_id = self.plugin.add_belief_set("propositional", "a => b\nb => c\na")
        
        # Enregistrer une requête
        query = "a => c"
        raw_result = "ACCEPTED (True)"
        log_id = self.plugin.log_query_result(bs_id, query, raw_result)
        
        # Vérifier que l'ID commence par "qlog_"
        self.assertTrue(log_id.startswith("qlog_"))
        
        # Vérifier que la requête a été enregistrée
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(self.state.query_log[0]["belief_set_id"], bs_id)
        self.assertEqual(self.state.query_log[0]["query"], query)
        self.assertEqual(self.state.query_log[0]["raw_result"], raw_result)

    def test_add_answer(self):
        """Teste l'ajout d'une réponse."""
        # Ajouter d'abord une tâche
        task_id = self.plugin.add_analysis_task("Analyser les arguments principaux")
        
        # Ajouter une réponse
        author_agent = "InformalAnalysisAgent"
        answer_text = "Les arguments principaux sont..."
        source_ids = ["arg_1", "arg_2"]
        result = self.plugin.add_answer(task_id, author_agent, answer_text, source_ids)
        
        # Vérifier que l'opération a réussi
        self.assertTrue(result.startswith("OK:"))
        
        # Vérifier que la réponse a été ajoutée
        self.assertIn(task_id, self.state.answers)
        self.assertEqual(self.state.answers[task_id]["author_agent"], author_agent)
        self.assertEqual(self.state.answers[task_id]["answer_text"], answer_text)
        self.assertEqual(self.state.answers[task_id]["source_ids"], source_ids)

    def test_set_final_conclusion(self):
        """Teste la définition de la conclusion finale."""
        conclusion = "L'analyse montre que les arguments sont valides."
        result = self.plugin.set_final_conclusion(conclusion)
        
        # Vérifier que l'opération a réussi
        self.assertTrue(result.startswith("OK:"))
        
        # Vérifier que la conclusion a été définie
        self.assertEqual(self.state.final_conclusion, conclusion)

    def test_designate_next_agent(self):
        """Teste la désignation du prochain agent."""
        agent_name = "PropositionalLogicAgent"
        result = self.plugin.designate_next_agent(agent_name)
        
        # Vérifier que l'opération a réussi
        self.assertTrue(result.startswith("OK."))
        
        # Vérifier que l'agent a été désigné
        self.assertEqual(self.state._next_agent_designated, agent_name)

    def test_error_handling(self):
        """Teste la gestion des erreurs."""
        with patch.object(self.state, 'add_task', side_effect=Exception("Test exception")):
            result = self.plugin.add_analysis_task("Test task")
            self.assertTrue(result.startswith("FUNC_ERROR:"))


if __name__ == '__main__':
    unittest.main()