# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_first_order_logic_agent.py
"""
Tests unitaires pour la classe FirstOrderLogicAgent.
"""

import unittest
import asyncio 
from unittest.mock import MagicMock, patch, AsyncMock 

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments 

from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent, SYSTEM_PROMPT_FOL
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestFirstOrderLogicAgent(unittest.TestCase):
    """Tests pour la classe FirstOrderLogicAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.invoke = AsyncMock() # Sera configuré par test si besoin de __str__
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock()

        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.first_order_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        
        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge_instance
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_fol_belief_set.return_value = (True, "Ensemble de croyances FOL valide")
        self.mock_tweety_bridge_instance.validate_fol_formula.return_value = (True, "Formule FOL valide")
        self.mock_tweety_bridge_instance.execute_fol_query = MagicMock(return_value="Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).") # Note: execute_fol_query retourne une chaîne, pas un tuple (bool, str) directement. L'agent parse cette chaîne.

        self.agent_name = "FirstOrderLogicAgent" # Nom par défaut de la classe
        
        self.mock_text_to_fol_func = AsyncMock()
        self.mock_gen_fol_queries_func = AsyncMock()
        self.mock_interpret_fol_func = AsyncMock()

        agent_functions_dict = {
            "TextToFOLBeliefSet": self.mock_text_to_fol_func,
            "GenerateFOLQueries": self.mock_gen_fol_queries_func,
            "InterpretFOLResult": self.mock_interpret_fol_func
        }

        self.kernel.plugins = MagicMock()
        
        def plugins_getitem_side_effect(key):
            if key == self.agent_name:
                plugin_mock = MagicMock()
                plugin_mock.__getitem__.side_effect = lambda func_key: agent_functions_dict.get(func_key)
                plugin_mock.__contains__.side_effect = lambda func_key: func_key in agent_functions_dict
                return plugin_mock
            raise KeyError(key)
        
        self.kernel.plugins.__getitem__.side_effect = plugins_getitem_side_effect
        self.kernel.plugins.__contains__.side_effect = lambda key: key == self.agent_name
        
        # Maintenant, initialiser l'agent et appeler setup
        self.agent = FirstOrderLogicAgent(self.kernel)
        self.llm_service_id = "test_fol_llm_service"
        # L'appel à setup_agent_components va maintenant utiliser le kernel avec .plugins mocké
        # et devrait trouver les fonctions via la structure mockée.
        # La méthode add_function du kernel est toujours un MagicMock simple,
        # mais la vérification dans l'agent devrait maintenant passer grâce au mock de .plugins.
        self.agent.setup_agent_components(self.llm_service_id)


    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        self.assertEqual(self.agent.name, self.agent_name)
        self.assertEqual(self.agent.sk_kernel, self.kernel)
        self.assertEqual(self.agent.logic_type, "FOL")
        self.assertEqual(self.agent.system_prompt, SYSTEM_PROMPT_FOL)
        
        self.mock_tweety_bridge_class.assert_called_once_with(logic_type="fol")
        self.mock_tweety_bridge_instance.is_jvm_ready.assert_called_once()
        
        self.assertTrue(self.kernel.add_function.call_count >= 3)
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)

    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec succès."""
        mock_sk_function_result = MagicMock()
        mock_sk_function_result.__str__.return_value = "forall X: (P(X) => Q(X));"
        self.mock_text_to_fol_func.invoke.return_value = mock_sk_function_result # MODIFIED: .invoke
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.mock_text_to_fol_func.invoke.assert_called_once_with(self.kernel, input="Texte de test")
        self.mock_tweety_bridge_instance.validate_fol_belief_set.assert_called_once_with("forall X: (P(X) => Q(X));")
        
        self.assertIsInstance(belief_set, FirstOrderBeliefSet)
        self.assertEqual(belief_set.content, "forall X: (P(X) => Q(X));")
        self.assertEqual(message, "Conversion réussie")

    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec résultat vide."""
        mock_sk_function_result = MagicMock()
        mock_sk_function_result.__str__.return_value = ""
        self.mock_text_to_fol_func.invoke.return_value = mock_sk_function_result # MODIFIED: .invoke
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.mock_text_to_fol_func.invoke.assert_called_once_with(self.kernel, input="Texte de test")
        self.mock_tweety_bridge_instance.validate_fol_belief_set.assert_not_called()
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide")

    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec ensemble invalide."""
        mock_sk_function_result = MagicMock()
        mock_sk_function_result.__str__.return_value = "forall X (P(X)"
        self.mock_text_to_fol_func.invoke.return_value = mock_sk_function_result # MODIFIED: .invoke
        self.mock_tweety_bridge_instance.validate_fol_belief_set.return_value = (False, "Erreur de syntaxe FOL")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.mock_text_to_fol_func.invoke.assert_called_once_with(self.kernel, input="Texte de test")
        self.mock_tweety_bridge_instance.validate_fol_belief_set.assert_called_once_with("forall X (P(X)")
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe FOL")

    async def test_generate_queries(self):
        """Test de la génération de requêtes FOL."""
        mock_sk_function_result = MagicMock()
        mock_sk_function_result.__str__.return_value = "P(a)\nQ(b)\nforall X: (P(X) => Q(X))"
        self.mock_gen_fol_queries_func.invoke.return_value = mock_sk_function_result # MODIFIED: .invoke
        self.mock_tweety_bridge_instance.validate_fol_formula.return_value = (True, "Formule FOL valide")
        
        belief_set_obj = FirstOrderBeliefSet("Human(socrates);")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.mock_gen_fol_queries_func.invoke.assert_called_once_with(self.kernel, input="Texte de test", belief_set="Human(socrates);")
        self.assertEqual(self.mock_tweety_bridge_instance.validate_fol_formula.call_count, 3)
        self.mock_tweety_bridge_instance.validate_fol_formula.assert_any_call("P(a)")
        
        self.assertEqual(queries, ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"])

    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes FOL avec une requête invalide."""
        mock_sk_function_result = MagicMock()
        mock_sk_function_result.__str__.return_value = "P(a)\nInvalid FOL Query {\nQ(c)"
        self.mock_gen_fol_queries_func.invoke.return_value = mock_sk_function_result # MODIFIED: .invoke
    
        def validate_side_effect(formula_str): # Ne prend plus logic_type pour FOL
            if formula_str == "Invalid FOL Query {":
                return (False, "Erreur de syntaxe FOL")
            return (True, "Formule FOL valide")
        self.mock_tweety_bridge_instance.validate_fol_formula.side_effect = validate_side_effect
        
        belief_set_obj = FirstOrderBeliefSet("Human(socrates);")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.mock_gen_fol_queries_func.invoke.assert_called_once_with(self.kernel, input="Texte de test", belief_set="Human(socrates);")
        self.assertEqual(self.mock_tweety_bridge_instance.validate_fol_formula.call_count, 3)
        self.assertEqual(queries, ["P(a)", "Q(c)"])

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête FOL acceptée."""
        belief_set_obj = FirstOrderBeliefSet("forall X: (P(X) => Q(X));")
        self.mock_tweety_bridge_instance.execute_fol_query.return_value = "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."
        
        result, message = self.agent.execute_query(belief_set_obj, "P(a)")
        
        self.mock_tweety_bridge_instance.execute_fol_query.assert_called_once_with(
            belief_set_content="forall X: (P(X) => Q(X));",
            query_string="P(a)"
        )
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).")

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête FOL rejetée."""
        belief_set_obj = FirstOrderBeliefSet("forall X: (P(X) => Q(X));")
        self.mock_tweety_bridge_instance.execute_fol_query.return_value = "Tweety Result: FOL Query 'R(c)' is REJECTED (False)."

        result, message = self.agent.execute_query(belief_set_obj, "R(c)")
        
        self.mock_tweety_bridge_instance.execute_fol_query.assert_called_once_with(
            belief_set_content="forall X: (P(X) => Q(X));",
            query_string="R(c)"
        )
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: FOL Query 'R(c)' is REJECTED (False).")

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête FOL avec erreur de Tweety."""
        belief_set_obj = FirstOrderBeliefSet("forall X: (P(X) => Q(X));")
        self.mock_tweety_bridge_instance.execute_fol_query.return_value = "FUNC_ERROR: Erreur de syntaxe Tweety FOL"

        result, message = self.agent.execute_query(belief_set_obj, "P(a)")
        
        self.mock_tweety_bridge_instance.execute_fol_query.assert_called_once_with(
            belief_set_content="forall X: (P(X) => Q(X));",
            query_string="P(a)"
        )
        self.assertIsNone(result)
        self.assertEqual(message, "FUNC_ERROR: Erreur de syntaxe Tweety FOL")
    
    async def test_interpret_results(self):
        """Test de l'interprétation des résultats FOL."""
        mock_sk_function_result = MagicMock()
        mock_sk_function_result.__str__.return_value = "Interprétation finale des résultats FOL"
        self.mock_interpret_fol_func.invoke.return_value = mock_sk_function_result # MODIFIED: .invoke
        
        belief_set_obj = FirstOrderBeliefSet("forall X: (P(X) => Q(X));")
        queries_list = ["P(a)", "Q(b)"]
        results_tuples = [
            (True, "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."),
            (False, "Tweety Result: FOL Query 'Q(b)' is REJECTED (False).")
        ]
        
        interpretation = await self.agent.interpret_results("Texte de test", belief_set_obj, queries_list, results_tuples)
        
        self.mock_interpret_fol_func.invoke.assert_called_once()
        
        # Vérifier les arguments passés à la méthode invoke du mock
        # L'agent appelle: invoke(self.sk_kernel, input=text, belief_set=..., queries=..., tweety_result=...)
        # Donc le premier argument de invoke est self.kernel, les suivants sont les kwargs.
        
        args_passed_to_invoke, kwargs_passed_to_invoke = self.mock_interpret_fol_func.invoke.call_args
        
        self.assertEqual(args_passed_to_invoke[0], self.kernel) # Vérifie le premier argument positionnel (kernel)
        
        self.assertEqual(kwargs_passed_to_invoke['input'], "Texte de test")
        self.assertEqual(kwargs_passed_to_invoke['belief_set'], "forall X: (P(X) => Q(X));")
        self.assertEqual(kwargs_passed_to_invoke['queries'], "P(a)\nQ(b)")
        expected_tweety_results = "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).\nTweety Result: FOL Query 'Q(b)' is REJECTED (False)."
        self.assertEqual(kwargs_passed_to_invoke['tweety_result'], expected_tweety_results)
        
        self.assertEqual(interpretation, "Interprétation finale des résultats FOL")

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule FOL valide."""
        self.mock_tweety_bridge_instance.validate_fol_formula.return_value = (True, "Formule FOL valide")
        is_valid = self.agent.validate_formula("forall X: (P(X) => Q(X))")
        self.assertTrue(is_valid)
        self.mock_tweety_bridge_instance.validate_fol_formula.assert_called_once_with("forall X: (P(X) => Q(X))")

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule FOL invalide."""
        self.mock_tweety_bridge_instance.validate_fol_formula.return_value = (False, "Erreur de syntaxe FOL")
        is_valid = self.agent.validate_formula("forall X (P(X)") 
        self.assertFalse(is_valid)
        self.mock_tweety_bridge_instance.validate_fol_formula.assert_called_once_with("forall X (P(X)")

def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

TestFirstOrderLogicAgent.test_text_to_belief_set_success = async_test(TestFirstOrderLogicAgent.test_text_to_belief_set_success)
TestFirstOrderLogicAgent.test_text_to_belief_set_empty_result = async_test(TestFirstOrderLogicAgent.test_text_to_belief_set_empty_result)
TestFirstOrderLogicAgent.test_text_to_belief_set_invalid_belief_set = async_test(TestFirstOrderLogicAgent.test_text_to_belief_set_invalid_belief_set)
TestFirstOrderLogicAgent.test_generate_queries = async_test(TestFirstOrderLogicAgent.test_generate_queries)
TestFirstOrderLogicAgent.test_generate_queries_with_invalid_query = async_test(TestFirstOrderLogicAgent.test_generate_queries_with_invalid_query)
TestFirstOrderLogicAgent.test_interpret_results = async_test(TestFirstOrderLogicAgent.test_interpret_results)

if __name__ == "__main__":
    unittest.main()