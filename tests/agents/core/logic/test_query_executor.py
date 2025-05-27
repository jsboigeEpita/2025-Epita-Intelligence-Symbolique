# tests/agents/core/logic/test_query_executor.py
"""
Tests unitaires pour la classe QueryExecutor.
"""

import unittest
from unittest.mock import MagicMock, patch

from argumentation_analysis.agents.core.logic.query_executor import QueryExecutor
from argumentation_analysis.agents.core.logic.belief_set import (
    PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet
)


class TestQueryExecutor(unittest.TestCase):
    """Tests pour la classe QueryExecutor."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Patcher TweetyBridge
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.query_executor.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        self.mock_tweety_bridge = MagicMock()
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge
        
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.is_jvm_ready.return_value = True
        
        # Créer l'instance de QueryExecutor
        self.query_executor = QueryExecutor()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()
    
    def test_initialization(self):
        """Test de l'initialisation de l'exécuteur de requêtes."""
        self.mock_tweety_bridge_class.assert_called_once()
    
    def test_execute_query_jvm_not_ready(self):
        """Test de l'exécution d'une requête lorsque la JVM n'est pas prête."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.is_jvm_ready.return_value = False
        
        # Exécuter une requête
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        # Vérifier que la JVM a été vérifiée
        self.mock_tweety_bridge.is_jvm_ready.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsNone(result)
        self.assertIn("FUNC_ERROR", message)
    
    def test_execute_query_propositional_accepted(self):
        """Test de l'exécution d'une requête propositionnelle acceptée."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.execute_pl_query.return_value = "Tweety Result: Query 'a' is ACCEPTED (True)."
        
        # Exécuter une requête
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        # Vérifier que la méthode appropriée a été appelée
        self.mock_tweety_bridge.execute_pl_query.assert_called_once_with("a => b", "a")
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Query 'a' is ACCEPTED (True).")
    
    def test_execute_query_propositional_rejected(self):
        """Test de l'exécution d'une requête propositionnelle rejetée."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.execute_pl_query.return_value = "Tweety Result: Query 'a' is REJECTED (False)."
        
        # Exécuter une requête
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        # Vérifier que la méthode appropriée a été appelée
        self.mock_tweety_bridge.execute_pl_query.assert_called_once_with("a => b", "a")
        
        # Vérifier le résultat
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: Query 'a' is REJECTED (False).")
    
    def test_execute_query_propositional_error(self):
        """Test de l'exécution d'une requête propositionnelle avec erreur."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.execute_pl_query.return_value = "FUNC_ERROR: Erreur de syntaxe"
        
        # Exécuter une requête
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        # Vérifier que la méthode appropriée a été appelée
        self.mock_tweety_bridge.execute_pl_query.assert_called_once_with("a => b", "a")
        
        # Vérifier le résultat
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe")
    
    def test_execute_query_first_order_accepted(self):
        """Test de l'exécution d'une requête du premier ordre acceptée."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.execute_fol_query.return_value = "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."
        
        # Exécuter une requête
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        result, message = self.query_executor.execute_query(belief_set, "P(a)")
        
        # Vérifier que la méthode appropriée a été appelée
        self.mock_tweety_bridge.execute_fol_query.assert_called_once_with("forall X: (P(X) => Q(X))", "P(a)")
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).")
    
    def test_execute_query_modal_accepted(self):
        """Test de l'exécution d'une requête modale acceptée."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.execute_modal_query.return_value = "Tweety Result: Modal Query '[]p' is ACCEPTED (True)."
        
        # Exécuter une requête
        belief_set = ModalBeliefSet("[]p => <>q")
        result, message = self.query_executor.execute_query(belief_set, "[]p")
        
        # Vérifier que la méthode appropriée a été appelée
        self.mock_tweety_bridge.execute_modal_query.assert_called_once_with("[]p => <>q", "[]p")
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Modal Query '[]p' is ACCEPTED (True).")
    
    def test_execute_query_unsupported_type(self):
        """Test de l'exécution d'une requête avec un type non supporté."""
        # Créer un mock de BeliefSet avec un type non supporté
        mock_belief_set = MagicMock()
        mock_belief_set.logic_type = "unsupported"
        mock_belief_set.content = "content"
        
        # Exécuter une requête
        result, message = self.query_executor.execute_query(mock_belief_set, "query")
        
        # Vérifier le résultat
        self.assertIsNone(result)
        self.assertIn("FUNC_ERROR", message)
        self.assertIn("Type de logique non supporté", message)
    
    def test_execute_queries(self):
        """Test de l'exécution de plusieurs requêtes."""
        # Configurer le mock de TweetyBridge
        self.mock_tweety_bridge.execute_pl_query.side_effect = [
            "Tweety Result: Query 'a' is ACCEPTED (True).",
            "Tweety Result: Query 'b' is REJECTED (False).",
            "FUNC_ERROR: Erreur de syntaxe"
        ]
        
        # Exécuter plusieurs requêtes
        belief_set = PropositionalBeliefSet("a => b")
        results = self.query_executor.execute_queries(belief_set, ["a", "b", "c"])
        
        # Vérifier que la méthode appropriée a été appelée
        self.assertEqual(self.mock_tweety_bridge.execute_pl_query.call_count, 3)
        
        # Vérifier le résultat
        self.assertEqual(len(results), 3)
        
        # Vérifier le premier résultat
        query1, result1, message1 = results[0]
        self.assertEqual(query1, "a")
        self.assertTrue(result1)
        self.assertEqual(message1, "Tweety Result: Query 'a' is ACCEPTED (True).")
        
        # Vérifier le deuxième résultat
        query2, result2, message2 = results[1]
        self.assertEqual(query2, "b")
        self.assertFalse(result2)
        self.assertEqual(message2, "Tweety Result: Query 'b' is REJECTED (False).")
        
        # Vérifier le troisième résultat
        query3, result3, message3 = results[2]
        self.assertEqual(query3, "c")
        self.assertIsNone(result3)
        self.assertEqual(message3, "FUNC_ERROR: Erreur de syntaxe")


if __name__ == "__main__":
    unittest.main()