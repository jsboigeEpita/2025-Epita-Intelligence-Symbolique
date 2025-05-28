# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_first_order_logic_agent.py
"""
Tests unitaires pour la classe FirstOrderLogicAgent.
"""

import unittest
from unittest.mock import MagicMock, patch

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestFirstOrderLogicAgent(unittest.TestCase):
    """Tests pour la classe FirstOrderLogicAgent."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Mock du kernel
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.plugins = {}
        
        # Mock des fonctions du kernel
        self.text_to_fol_function = MagicMock()
        self.text_to_fol_function.invoke.return_value = MagicMock(result="forall X: (P(X) => Q(X))")
        
        self.generate_queries_function = MagicMock()
        self.generate_queries_function.invoke.return_value = MagicMock(result="P(a)\nQ(b)\nforall X: (P(X) => Q(X))")
        
        self.interpret_function = MagicMock()
        self.interpret_function.invoke.return_value = MagicMock(result="Interprétation des résultats FOL")
        
        self.execute_query_function = MagicMock()
        self.execute_query_function.invoke.return_value = MagicMock(
            result="Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True)."
        )
        
        # Configuration du mock du plugin
        self.kernel.plugins = {
            "FOLAnalyzer": {
                "semantic_TextToFOLBeliefSet": self.text_to_fol_function,
                "semantic_GenerateFOLQueries": self.generate_queries_function,
                "semantic_InterpretFOLResult": self.interpret_function,
                "execute_fol_query": self.execute_query_function
            }
        }
        
        # Mock de TweetyBridge
        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.first_order_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        self.mock_tweety_bridge = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge
        self.mock_tweety_bridge.is_jvm_ready.return_value = True
        self.mock_tweety_bridge.validate_fol_belief_set.return_value = (True, "Ensemble de croyances FOL valide")
        self.mock_tweety_bridge.validate_fol_formula.return_value = (True, "Formule FOL valide")
        
        # Création de l'agent
        self.agent = FirstOrderLogicAgent(self.kernel)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()
    
    def test_initialization(self):
        """Test de l'initialisation de l'agent."""
        self.assertEqual(self.agent.name, "FirstOrderLogicAgent")
        self.assertEqual(self.agent.kernel, self.kernel)
        self.mock_tweety_bridge_class.assert_called_once()
    
    def test_setup_kernel(self):
        """Test de la configuration du kernel."""
        llm_service = MagicMock()
        llm_service.service_id = "test_service"
        
        # Mock pour get_prompt_execution_settings_from_service_id
        self.kernel.get_prompt_execution_settings_from_service_id.return_value = {"temperature": 0.7}
        
        self.agent.setup_kernel(llm_service)
        
        # Vérifier que la JVM est prête
        self.mock_tweety_bridge.is_jvm_ready.assert_called_once()
        
        # Vérifier que le plugin a été ajouté
        self.kernel.add_plugin.assert_called_once()
        
        # Vérifier que les fonctions sémantiques ont été ajoutées
        self.assertEqual(self.kernel.add_function.call_count, 3)
    
    def test_setup_kernel_jvm_not_ready(self):
        """Test de la configuration du kernel lorsque la JVM n'est pas prête."""
        self.mock_tweety_bridge.is_jvm_ready.return_value = False
        
        self.agent.setup_kernel(None)
        
        # Vérifier que la JVM est prête
        self.mock_tweety_bridge.is_jvm_ready.assert_called_once()
        
        # Vérifier que le plugin n'a pas été ajouté
        self.kernel.add_plugin.assert_not_called()
        
        # Vérifier que les fonctions sémantiques n'ont pas été ajoutées
        self.kernel.add_function.assert_not_called()
    
    def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec succès."""
        belief_set, message = self.agent.text_to_belief_set("Texte de test")
        
        # Vérifier que la fonction sémantique a été appelée
        self.text_to_fol_function.invoke.assert_called_once_with("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été validé
        self.mock_tweety_bridge.validate_fol_belief_set.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsInstance(belief_set, FirstOrderBeliefSet)
        self.assertEqual(belief_set.content, "forall X: (P(X) => Q(X))")
        self.assertEqual(message, "Conversion réussie")
    
    def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec résultat vide."""
        self.text_to_fol_function.invoke.return_value = MagicMock(result="")
        
        belief_set, message = self.agent.text_to_belief_set("Texte de test")
        
        # Vérifier que la fonction sémantique a été appelée
        self.text_to_fol_function.invoke.assert_called_once_with("Texte de test")
        
        # Vérifier que l'ensemble de croyances n'a pas été validé
        self.mock_tweety_bridge.validate_fol_belief_set.assert_not_called()
        
        # Vérifier le résultat
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide")
    
    def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec ensemble invalide."""
        self.mock_tweety_bridge.validate_fol_belief_set.return_value = (False, "Erreur de syntaxe FOL")
        
        belief_set, message = self.agent.text_to_belief_set("Texte de test")
        
        # Vérifier que la fonction sémantique a été appelée
        self.text_to_fol_function.invoke.assert_called_once_with("Texte de test")
        
        # Vérifier que l'ensemble de croyances a été validé
        self.mock_tweety_bridge.validate_fol_belief_set.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe FOL")
    
    def test_generate_queries(self):
        """Test de la génération de requêtes FOL."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        
        queries = self.agent.generate_queries("Texte de test", belief_set)
        
        # Vérifier que la fonction sémantique a été appelée
        self.generate_queries_function.invoke.assert_called_once_with(
            input="Texte de test",
            belief_set="forall X: (P(X) => Q(X))"
        )
        
        # Vérifier que les requêtes ont été validées
        self.assertEqual(self.mock_tweety_bridge.validate_fol_formula.call_count, 3)
        
        # Vérifier le résultat
        self.assertEqual(queries, ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"])
    
    def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes FOL avec une requête invalide."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        
        # Configurer le mock pour rejeter la deuxième requête
        self.mock_tweety_bridge.validate_fol_formula.side_effect = [
            (True, "Formule FOL valide"),
            (False, "Erreur de syntaxe FOL"),
            (True, "Formule FOL valide")
        ]
        
        queries = self.agent.generate_queries("Texte de test", belief_set)
        
        # Vérifier que la fonction sémantique a été appelée
        self.generate_queries_function.invoke.assert_called_once_with(
            input="Texte de test",
            belief_set="forall X: (P(X) => Q(X))"
        )
        
        # Vérifier que les requêtes ont été validées
        self.assertEqual(self.mock_tweety_bridge.validate_fol_formula.call_count, 3)
        
        # Vérifier le résultat (la deuxième requête doit être filtrée)
        self.assertEqual(queries, ["P(a)", "forall X: (P(X) => Q(X))"])
    
    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête FOL acceptée."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        
        result, message = self.agent.execute_query(belief_set, "forall X: (P(X) => Q(X))")
        
        # Vérifier que la fonction native a été appelée
        self.execute_query_function.invoke.assert_called_once_with(
            belief_set_content="forall X: (P(X) => Q(X))",
            query_string="forall X: (P(X) => Q(X))"
        )
        
        # Vérifier le résultat
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True).")
    
    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête FOL rejetée."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        self.execute_query_function.invoke.return_value = MagicMock(
            result="Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is REJECTED (False)."
        )
        
        result, message = self.agent.execute_query(belief_set, "forall X: (P(X) => Q(X))")
        
        # Vérifier que la fonction native a été appelée
        self.execute_query_function.invoke.assert_called_once_with(
            belief_set_content="forall X: (P(X) => Q(X))",
            query_string="forall X: (P(X) => Q(X))"
        )
        
        # Vérifier le résultat
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is REJECTED (False).")
    
    def test_execute_query_error(self):
        """Test de l'exécution d'une requête FOL avec erreur."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        self.execute_query_function.invoke.return_value = MagicMock(
            result="FUNC_ERROR: Erreur de syntaxe FOL"
        )
        
        result, message = self.agent.execute_query(belief_set, "forall X: (P(X) => Q(X))")
        
        # Vérifier que la fonction native a été appelée
        self.execute_query_function.invoke.assert_called_once_with(
            belief_set_content="forall X: (P(X) => Q(X))",
            query_string="forall X: (P(X) => Q(X))"
        )
        
        # Vérifier le résultat
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe FOL")
    
    def test_interpret_results(self):
        """Test de l'interprétation des résultats FOL."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        queries = ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"]
        results = [
            "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).",
            "Tweety Result: FOL Query 'Q(b)' is REJECTED (False).",
            "Tweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True)."
        ]
        
        interpretation = self.agent.interpret_results("Texte de test", belief_set, queries, results)
        
        # Vérifier que la fonction sémantique a été appelée
        self.interpret_function.invoke.assert_called_once_with(
            input="Texte de test",
            belief_set="forall X: (P(X) => Q(X))",
            queries="P(a)\nQ(b)\nforall X: (P(X) => Q(X))",
            tweety_result="Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).\nTweety Result: FOL Query 'Q(b)' is REJECTED (False).\nTweety Result: FOL Query 'forall X: (P(X) => Q(X))' is ACCEPTED (True)."
        )
        
        # Vérifier le résultat
        self.assertEqual(interpretation, "Interprétation des résultats FOL")
    
    def test_create_belief_set_from_data(self):
        """Test de la création d'un ensemble de croyances FOL à partir de données."""
        belief_set_data = {
            "logic_type": "first_order",
            "content": "forall X: (P(X) => Q(X))"
        }
        
        belief_set = self.agent._create_belief_set_from_data(belief_set_data)
        
        # Vérifier le résultat
        self.assertIsInstance(belief_set, FirstOrderBeliefSet)
        self.assertEqual(belief_set.content, "forall X: (P(X) => Q(X))")
        self.assertEqual(belief_set.logic_type, "first_order")


if __name__ == "__main__":
    unittest.main()