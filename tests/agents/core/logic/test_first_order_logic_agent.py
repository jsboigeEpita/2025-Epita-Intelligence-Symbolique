# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_first_order_logic_agent.py
"""
Tests unitaires pour la classe FirstOrderLogicAgent.
"""

import unittest
import asyncio # Ajouté pour les tests async
from unittest.mock import MagicMock, patch, AsyncMock # AsyncMock ajouté

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments # Ajouté

from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent, SYSTEM_PROMPT_FOL
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class TestFirstOrderLogicAgent(unittest.TestCase):
    """Tests pour la classe FirstOrderLogicAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.invoke = AsyncMock()
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock()

        self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.first_order_logic_agent.TweetyBridge')
        self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
        
        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge_instance
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_fol_belief_set.return_value = (True, "Ensemble de croyances FOL valide")
        self.mock_tweety_bridge_instance.validate_fol_formula.return_value = (True, "Formule FOL valide")
        self.mock_tweety_bridge_instance.execute_fol_query.return_value = (True, "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).")


        self.agent_name = "TestFOLAgent"
        # Note: FirstOrderLogicAgent prend kernel en argument, pas agent_name directement dans son __init__
        # mais BaseLogicAgent le prend. FirstOrderLogicAgent le fixe à "FirstOrderLogicAgent".
        # Pour tester le nommage via BaseAgent, on pourrait créer une sous-classe ou mocker différemment.
        # Ici, on va tester avec le nom par défaut de FirstOrderLogicAgent.
        self.agent = FirstOrderLogicAgent(self.kernel)
        # Si on voulait un nom custom, il faudrait modifier FirstOrderLogicAgent ou le passer à BaseAgent
        # self.agent = FirstOrderLogicAgent(self.kernel) # agent_name est fixé dans la classe
        # self.agent._agent_name = self.agent_name # Forcer pour le test si besoin, mais pas idéal

        self.llm_service_id = "test_fol_llm_service"
        self.agent.setup_agent_components(self.llm_service_id)

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.tweety_bridge_patcher.stop()

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        self.assertEqual(self.agent.name, "FirstOrderLogicAgent") # Nom par défaut de la classe
        self.assertEqual(self.agent.sk_kernel, self.kernel)
        self.assertEqual(self.agent.logic_type, "FOL")
        self.assertEqual(self.agent.system_prompt, SYSTEM_PROMPT_FOL)
        
        self.mock_tweety_bridge_class.assert_called_once_with(logic_type="fol")
        self.mock_tweety_bridge_instance.is_jvm_ready.assert_called_once()
        
        self.assertTrue(self.kernel.add_function.call_count >= 3)
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)

    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec succès."""
        self.kernel.invoke.return_value = MagicMock(result="forall X: (P(X) => Q(X));")
        
        # La méthode text_to_belief_set de l'agent FOL utilise kernel.plugins[self.name]["Func"].invoke(kernel, input=...)
        # Nous devons donc mocker cette structure.
        mock_fol_plugin = MagicMock()
        mock_fol_plugin.invoke = AsyncMock(return_value=MagicMock(result="forall X: (P(X) => Q(X));"))
        self.kernel.plugins = {self.agent.name: {"TextToFOLBeliefSet": mock_fol_plugin}}

        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        mock_fol_plugin.invoke.assert_called_once_with(self.kernel, input="Texte de test")
        self.mock_tweety_bridge_instance.validate_fol_belief_set.assert_called_once_with("forall X: (P(X) => Q(X));")
        
        self.assertIsInstance(belief_set, FirstOrderBeliefSet)
        self.assertEqual(belief_set.content, "forall X: (P(X) => Q(X));")
        self.assertEqual(message, "Conversion réussie")

    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec résultat vide."""
        mock_fol_plugin = MagicMock()
        mock_fol_plugin.invoke = AsyncMock(return_value=MagicMock(result=""))
        self.kernel.plugins = {self.agent.name: {"TextToFOLBeliefSet": mock_fol_plugin}}
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        mock_fol_plugin.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_fol_belief_set.assert_not_called()
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide")

    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances FOL avec ensemble invalide."""
        mock_fol_plugin = MagicMock()
        mock_fol_plugin.invoke = AsyncMock(return_value=MagicMock(result="forall X (P(X)")) # Syntaxe invalide
        self.kernel.plugins = {self.agent.name: {"TextToFOLBeliefSet": mock_fol_plugin}}
        self.mock_tweety_bridge_instance.validate_fol_belief_set.return_value = (False, "Erreur de syntaxe FOL")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        mock_fol_plugin.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_fol_belief_set.assert_called_once_with("forall X (P(X)")
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe FOL")

    async def test_generate_queries(self):
        """Test de la génération de requêtes FOL."""
        mock_fol_plugin = MagicMock()
        mock_fol_plugin.invoke = AsyncMock(return_value=MagicMock(result="P(a)\nQ(b)\nforall X: (P(X) => Q(X))"))
        self.kernel.plugins = {self.agent.name: {"GenerateFOLQueries": mock_fol_plugin}}
        self.mock_tweety_bridge_instance.validate_fol_formula.return_value = (True, "Formule FOL valide")
        
        belief_set_obj = FirstOrderBeliefSet("Human(socrates);")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        mock_fol_plugin.invoke.assert_called_once_with(self.kernel, input="Texte de test", belief_set="Human(socrates);")
        self.assertEqual(self.mock_tweety_bridge_instance.validate_fol_formula.call_count, 3)
        self.mock_tweety_bridge_instance.validate_fol_formula.assert_any_call("P(a)")
        
        self.assertEqual(queries, ["P(a)", "Q(b)", "forall X: (P(X) => Q(X))"])

    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes FOL avec une requête invalide."""
        mock_fol_plugin = MagicMock()
        mock_fol_plugin.invoke = AsyncMock(return_value=MagicMock(result="P(a)\nInvalid FOL Query {\nQ(c)"))
        self.kernel.plugins = {self.agent.name: {"GenerateFOLQueries": mock_fol_plugin}}

        def validate_side_effect(formula_str):
            if formula_str == "Invalid FOL Query {":
                return (False, "Erreur de syntaxe FOL")
            return (True, "Formule FOL valide")
        self.mock_tweety_bridge_instance.validate_fol_formula.side_effect = validate_side_effect
        
        belief_set_obj = FirstOrderBeliefSet("Human(socrates);")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        mock_fol_plugin.invoke.assert_called_once()
        self.assertEqual(self.mock_tweety_bridge_instance.validate_fol_formula.call_count, 3)
        self.assertEqual(queries, ["P(a)", "Q(c)"])

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête FOL acceptée."""
        belief_set_obj = FirstOrderBeliefSet("forall X: (P(X) => Q(X));")
        self.mock_tweety_bridge_instance.execute_fol_query.return_value = "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."
        # Note: l'agent FirstOrderLogicAgent.execute_query appelle directement tweety_bridge, pas une fonction SK.
        # Il ne valide pas la formule en interne avant d'appeler le bridge.
        # La validation de formule est une méthode séparée de l'agent.

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
        mock_fol_plugin = MagicMock()
        mock_fol_plugin.invoke = AsyncMock(return_value=MagicMock(result="Interprétation finale des résultats FOL"))
        self.kernel.plugins = {self.agent.name: {"InterpretFOLResult": mock_fol_plugin}}
        
        belief_set_obj = FirstOrderBeliefSet("forall X: (P(X) => Q(X));")
        queries_list = ["P(a)", "Q(b)"]
        results_tuples = [
            (True, "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."),
            (False, "Tweety Result: FOL Query 'Q(b)' is REJECTED (False).")
        ]
        
        interpretation = await self.agent.interpret_results("Texte de test", belief_set_obj, queries_list, results_tuples)
        
        mock_fol_plugin.invoke.assert_called_once()
        args_call = mock_fol_plugin.invoke.call_args[0] # kernel, puis kwargs ou args direct
        kwargs_call = mock_fol_plugin.invoke.call_args[1] # si kwargs utilisés

        self.assertEqual(args_call[0], self.kernel) # Vérifie que le kernel est passé
        # Les arguments suivants peuvent être passés en tant que kwargs ou args positionnels
        # Ici on suppose qu'ils sont passés en kwargs à la fonction SK interne,
        # mais la méthode invoke de SK prend KernelArguments.
        # La méthode de l'agent construit KernelArguments et les passe à kernel.invoke.
        # Le mock ici est sur la fonction SK elle-même, pas sur kernel.invoke.
        # Pour être plus précis, il faudrait mocker kernel.invoke.
        # Pour l'instant, on vérifie les arguments passés à la fonction mockée.
        # Cela dépend de comment FirstOrderLogicAgent.interpret_results appelle la fonction SK.
        # D'après le code de l'agent, il appelle:
        # self.sk_kernel.plugins[self.name]["InterpretFOLResult"].invoke(self.sk_kernel, input=..., belief_set=..., ...)
        
        self.assertEqual(kwargs_call['input'], "Texte de test")
        self.assertEqual(kwargs_call['belief_set'], "forall X: (P(X) => Q(X));")
        self.assertEqual(kwargs_call['queries'], "P(a)\nQ(b)")
        expected_tweety_results = "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True).\nTweety Result: FOL Query 'Q(b)' is REJECTED (False)."
        self.assertEqual(kwargs_call['tweety_result'], expected_tweety_results)
        
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
        is_valid = self.agent.validate_formula("forall X (P(X)") # Manque une parenthèse
        self.assertFalse(is_valid)
        self.mock_tweety_bridge_instance.validate_fol_formula.assert_called_once_with("forall X (P(X)")

# Wrapper pour exécuter les tests async avec unittest
def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

# Appliquer le décorateur aux méthodes de test async
TestFirstOrderLogicAgent.test_text_to_belief_set_success = async_test(TestFirstOrderLogicAgent.test_text_to_belief_set_success)
TestFirstOrderLogicAgent.test_text_to_belief_set_empty_result = async_test(TestFirstOrderLogicAgent.test_text_to_belief_set_empty_result)
TestFirstOrderLogicAgent.test_text_to_belief_set_invalid_belief_set = async_test(TestFirstOrderLogicAgent.test_text_to_belief_set_invalid_belief_set)
TestFirstOrderLogicAgent.test_generate_queries = async_test(TestFirstOrderLogicAgent.test_generate_queries)
TestFirstOrderLogicAgent.test_generate_queries_with_invalid_query = async_test(TestFirstOrderLogicAgent.test_generate_queries_with_invalid_query)
TestFirstOrderLogicAgent.test_interpret_results = async_test(TestFirstOrderLogicAgent.test_interpret_results)

if __name__ == "__main__":
    unittest.main()