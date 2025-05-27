# tests/agents/core/logic/test_abstract_logic_agent.py
"""
Tests unitaires pour la classe AbstractLogicAgent.
"""

import unittest
from unittest.mock import MagicMock, patch

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.abstract_logic_agent import AbstractLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet


class MockLogicAgent(AbstractLogicAgent):
    """Classe concrète pour tester la classe abstraite AbstractLogicAgent."""
    
    def setup_kernel(self, llm_service):
        """Implémentation de la méthode abstraite."""
        pass
    
    def text_to_belief_set(self, text):
        """Implémentation de la méthode abstraite."""
        return MagicMock(spec=BeliefSet), "Conversion réussie"
    
    def generate_queries(self, text, belief_set):
        """Implémentation de la méthode abstraite."""
        return ["query1", "query2"]
    
    def execute_query(self, belief_set, query):
        """Implémentation de la méthode abstraite."""
        return True, "Requête exécutée avec succès"
    
    def interpret_results(self, text, belief_set, queries, results):
        """Implémentation de la méthode abstraite."""
        return "Interprétation des résultats"
    
    def _create_belief_set_from_data(self, belief_set_data):
        """Implémentation de la méthode abstraite."""
        return MagicMock(spec=BeliefSet)


class TestAbstractLogicAgent(unittest.TestCase):
    """Tests pour la classe AbstractLogicAgent."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.agent = MockLogicAgent(self.kernel, "TestAgent")
        self.state_manager = MagicMock()
        
        # Configuration du state_manager mock
        self.state_manager.get_current_state_snapshot.return_value = {
            "raw_text": "Texte de test",
            "belief_sets": {
                "bs1": {
                    "logic_type": "propositional",
                    "content": "a => b"
                }
            }
        }
        self.state_manager.add_belief_set.return_value = "bs2"
        self.state_manager.add_answer.return_value = None
        self.state_manager.log_query_result.return_value = "log1"
    
    def test_initialization(self):
        """Test de l'initialisation de l'agent."""
        self.assertEqual(self.agent.name, "TestAgent")
        self.assertEqual(self.agent.kernel, self.kernel)
    
    def test_process_task_unknown_task(self):
        """Test du traitement d'une tâche inconnue."""
        result = self.agent.process_task("task1", "Tâche inconnue", self.state_manager)
        self.assertEqual(result["status"], "error")
        self.state_manager.add_answer.assert_called_once()
    
    def test_handle_translation_task(self):
        """Test du traitement d'une tâche de traduction."""
        result = self.agent.process_task("task1", "Traduire le texte en Belief Set", self.state_manager)
        self.assertEqual(result["status"], "success")
        self.state_manager.add_belief_set.assert_called_once()
        self.state_manager.add_answer.assert_called_once()
    
    def test_handle_query_task(self):
        """Test du traitement d'une tâche d'exécution de requêtes."""
        result = self.agent.process_task(
            "task1", 
            "Exécuter les Requêtes sur belief_set_id: bs1", 
            self.state_manager
        )
        self.assertEqual(result["status"], "success")
        self.state_manager.log_query_result.assert_called()
        self.state_manager.add_answer.assert_called_once()
    
    def test_extract_source_text_from_state(self):
        """Test de l'extraction du texte source depuis l'état."""
        text = self.agent._extract_source_text("", self.state_manager.get_current_state_snapshot())
        self.assertEqual(text, "Texte de test")
    
    def test_extract_source_text_from_description(self):
        """Test de l'extraction du texte source depuis la description."""
        text = self.agent._extract_source_text(
            "Analyser le texte: Ceci est un test", 
            {"raw_text": ""}
        )
        self.assertEqual(text, "Ceci est un test")
    
    def test_extract_belief_set_id(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances."""
        bs_id = self.agent._extract_belief_set_id("Requête sur belief_set_id: bs123")
        self.assertEqual(bs_id, "bs123")
    
    def test_extract_belief_set_id_not_found(self):
        """Test de l'extraction de l'ID de l'ensemble de croyances non trouvé."""
        bs_id = self.agent._extract_belief_set_id("Requête sans ID")
        self.assertIsNone(bs_id)


if __name__ == "__main__":
    unittest.main()