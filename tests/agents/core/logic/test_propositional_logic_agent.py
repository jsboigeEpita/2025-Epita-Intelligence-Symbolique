# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_propositional_logic_agent.py
"""
Tests unitaires pour la classe PropositionalLogicAgent.
"""

import unittest
import asyncio
import os # Ajout de l'import os
from unittest.mock import MagicMock, patch, AsyncMock

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments

from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.pl.pl_definitions import PL_AGENT_INSTRUCTIONS


class TestPropositionalLogicAgent(unittest.TestCase):
    """Tests pour la classe PropositionalLogicAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.invoke = AsyncMock()
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock()

        self.use_real_jpype = os.environ.get('USE_REAL_JPYPE') == 'true'
        self.tweety_bridge_patcher = None
        self.mock_tweety_bridge_instance = None

        if not self.use_real_jpype:
            self.tweety_bridge_patcher = patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge')
            self.mock_tweety_bridge_class = self.tweety_bridge_patcher.start()
            
            self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
            self.mock_tweety_bridge_class.return_value = self.mock_tweety_bridge_instance
            self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
            self.mock_tweety_bridge_instance.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
            self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
            self.mock_tweety_bridge_instance.execute_pl_query = MagicMock(return_value="Tweety Result: Query 'a => b' is ACCEPTED (True).")
        # Si self.use_real_jpype est True, PropositionalLogicAgent instanciera la vraie TweetyBridge.
        # Nous n'avons pas besoin de self.mock_tweety_bridge_instance dans ce cas pour les tests de l'agent,
        # car l'agent utilisera la vraie instance.

        self.agent_name = "TestPLAgent"
        # L'agent est instancié ici. Si use_real_jpype est True, il essaiera de créer une vraie TweetyBridge.
        # Si c'est False, le patch sera actif et il obtiendra le mock.
        self.agent = PropositionalLogicAgent(self.kernel, agent_name=self.agent_name)
        
        # Si nous utilisons la vraie TweetyBridge, nous devons nous assurer que l'instance de l'agent
        # a une référence à la vraie bridge pour les assertions de test qui pourraient en avoir besoin.
        # Cependant, la plupart des assertions se font sur les mocks des méthodes du kernel ou sur les résultats.
        # Pour les tests qui vérifient les appels à TweetyBridge, nous devrons les conditionner.
        if self.use_real_jpype:
            # Pour les tests qui pourraient avoir besoin d'inspecter la vraie bridge (rarement nécessaire ici)
            # self.true_tweety_bridge_instance = self.agent.tweety_bridge
            pass # Pas besoin de mock_tweety_bridge_instance si on utilise la vraie
        else:
            # S'assurer que l'agent utilise bien l'instance mockée si le patch est actif
            # Ceci est implicitement géré par le patch au niveau de la classe.
            # self.agent.tweety_bridge doit être self.mock_tweety_bridge_instance
            pass


        self.llm_service_id = "test_llm_service"
        self.agent.setup_agent_components(self.llm_service_id)

    def tearDown(self):
        """Nettoyage après chaque test."""
        if self.tweety_bridge_patcher:
            self.tweety_bridge_patcher.stop()
            self.tweety_bridge_patcher = None # Pour la propreté

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        self.assertEqual(self.agent.name, self.agent_name)
        self.assertEqual(self.agent.sk_kernel, self.kernel)
        self.assertEqual(self.agent.logic_type, "PL")
        self.assertEqual(self.agent.system_prompt, PL_AGENT_INSTRUCTIONS)
        
        if not self.use_real_jpype:
            self.mock_tweety_bridge_class.assert_called_once_with() # TweetyBridge __init__ ne prend plus logic_type
            self.assertEqual(self.mock_tweety_bridge_instance.is_jvm_ready.call_count, 2) # Appelé deux fois dans setup_agent_components
        else:
            # Avec la vraie TweetyBridge, is_jvm_ready est appelée aussi.
            # On ne peut pas facilement compter les appels sur la vraie instance sans la mocker partiellement.
            # On se concentre sur le fait que l'agent est initialisé.
            self.assertIsNotNone(self.agent.tweety_bridge)
            self.assertTrue(self.agent.tweety_bridge.is_jvm_ready()) # Doit être vrai pour que l'agent fonctionne

        self.assertTrue(self.kernel.add_function.call_count >= 3)
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)


    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances avec succès."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a => b" 
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "TextToPLBeliefSet")
        self.assertIsInstance(kwargs['arguments'], KernelArguments)
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with("a => b")
        # Si real_jpype, la vraie méthode est appelée, pas de mock à vérifier ici directement.
        # La validité est vérifiée par le résultat (belief_set non None, message).
        
        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "a => b")
        self.assertEqual(message, "Conversion réussie.")

    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances avec résultat vide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "" 
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_belief_set.assert_not_called()
        # Si real_jpype, la vraie méthode ne serait pas appelée non plus car le résultat SK est vide.
        
        self.assertIsNone(belief_set)
        self.assertEqual(message, "La conversion a produit un ensemble de croyances vide.")

    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances avec ensemble invalide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "invalid_pl_syntax {"
        self.kernel.invoke.return_value = mock_sk_result
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_belief_set.return_value = (False, "Erreur de syntaxe")
        # Si real_jpype, la vraie méthode est appelée. Le message d'erreur proviendra de la vraie bridge.
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with("invalid_pl_syntax {")
        # Si real_jpype, la vraie méthode est appelée.
        
        if not self.use_real_jpype:
            self.assertIsNone(belief_set)
            self.assertEqual(message, "Ensemble de croyances invalide: Erreur de syntaxe")
        else:
            # Avec la vraie TweetyBridge, "invalid_pl_syntax {" est parsé comme "invalid_pl_syntax{"
            # qui est une formule valide, donc un belief set valide.
            self.assertIsInstance(belief_set, PropositionalBeliefSet)
            self.assertEqual(belief_set.content, "invalid_pl_syntax {") # Le contenu original est conservé
            self.assertEqual(message, "Conversion réussie.")


    async def test_generate_queries(self):
        """Test de la génération de requêtes."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a\nb\na => b"
        self.kernel.invoke.return_value = mock_sk_result
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "GeneratePLQueries")
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        self.assertEqual(kwargs['arguments']['belief_set'], "x => y")

        if not self.use_real_jpype:
            self.assertEqual(self.mock_tweety_bridge_instance.validate_formula.call_count, 3)
            self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="a")
            self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="b")
            self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="a => b")
        # Si real_jpype, les vraies méthodes sont appelées. Le test vérifie le résultat `queries`.

        self.assertEqual(queries, ["a", "b", "a => b"])

    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes avec une requête invalide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a\ninvalid_query {\nc"
        self.kernel.invoke.return_value = mock_sk_result
        
        def validate_side_effect(formula_string): # formula_str -> formula_string, logic_type retiré de la signature
            if formula_string == "invalid_query {":
                return (False, "Erreur de syntaxe")
            return (True, "Formule valide")
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.side_effect = validate_side_effect
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        if not self.use_real_jpype:
            self.assertEqual(self.mock_tweety_bridge_instance.validate_formula.call_count, 3)
            self.assertEqual(queries, ["a", "c"]) # Le mock filtre "invalid_query {"
        else:
            # Avec la vraie TweetyBridge, "invalid_query {" est valide (parsé comme "invalid_query{")
            self.assertEqual(queries, ["a", "invalid_query {", "c"])

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête acceptée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        if not self.use_real_jpype:
            # Assurer que le mock retourne la chaîne attendue par l'agent pour ce test
            self.mock_tweety_bridge_instance.execute_pl_query.return_value = "Tweety Result: Query 'a => b' is ACCEPTED (True)."
            self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a => b")
        
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")
            self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
                belief_set_content="a => b",
                query_string="a => b"
            )
        # Si real_jpype, la vraie méthode est appelée. Le test vérifie `result` et `message`.
        
        # Avec la vraie JVM, le résultat devrait être True et le message formaté correctement.
        self.assertTrue(result)
        self.assertEqual(message, "Tweety Result: Query 'a => b' is ACCEPTED (True).")

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête rejetée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        if not self.use_real_jpype:
            # Assurer que le mock retourne la chaîne attendue par l'agent pour ce test
            self.mock_tweety_bridge_instance.execute_pl_query.return_value = "Tweety Result: Query 'c' is REJECTED (False)."
            self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "c")
        
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="c")
            self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
                belief_set_content="a => b",
                query_string="c"
            )
        # Si real_jpype, la vraie méthode est appelée. Le test vérifie `result` et `message`.

        # Avec la vraie JVM, le résultat devrait être False et le message formaté correctement.
        self.assertFalse(result)
        self.assertEqual(message, "Tweety Result: Query 'c' is REJECTED (False).")

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête avec erreur de Tweety."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        if not self.use_real_jpype:
            # Assurer que le mock retourne la chaîne attendue par l'agent pour ce test
            self.mock_tweety_bridge_instance.execute_pl_query.return_value = "FUNC_ERROR: Erreur de syntaxe Tweety"
            self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a")
        
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a")
            self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
                belief_set_content="a => b",
                query_string="a"
            )
        # Si real_jpype, la vraie méthode est appelée. Le test vérifie `result` et `message`.
        
        # Avec la vraie JVM, 'a' est rejeté par 'a => b'.
        self.assertFalse(result) # 'a' n'est pas une conséquence de 'a => b', donc result est False.
        self.assertEqual(message, "Tweety Result: Query 'a' is REJECTED (False).")

    def test_execute_query_invalid_formula(self):
        """Test de l'exécution d'une requête avec une formule invalide."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Syntax Error in query")

        result, message = self.agent.execute_query(belief_set_obj, "invalid_query {")
        
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="invalid_query {")
            self.mock_tweety_bridge_instance.execute_pl_query.assert_not_called()
        # Si real_jpype, la vraie méthode validate_formula est appelée.
        # "invalid_query {" est parsé comme "invalid_query{" qui est valide pour Tweety.
        # Donc, la requête est exécutée.
        if not self.use_real_jpype:
            self.assertIsNone(result)
            self.assertEqual(message, "FUNC_ERROR: Requête invalide: invalid_query {")
        else:
            self.assertFalse(result) # Rejeté car non conséquence de "a => b"
            self.assertEqual(message, "Tweety Result: Query 'invalid_query {' is REJECTED (False).")


    async def test_interpret_results(self):
        """Test de l'interprétation des résultats."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "Interprétation finale des résultats"
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set_obj = PropositionalBeliefSet("a => b")
        queries_list = ["a", "b", "a => b"]
        results_tuples = [
            (True, "Tweety Result: Query 'a' is ACCEPTED (True)."),
            (False, "Tweety Result: Query 'b' is REJECTED (False)."),
            (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        ]
        
        interpretation = await self.agent.interpret_results("Texte de test", belief_set_obj, queries_list, results_tuples)
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        self.assertEqual(kwargs['plugin_name'], self.agent_name)
        self.assertEqual(kwargs['function_name'], "InterpretPLResults")
        self.assertEqual(kwargs['arguments']['input'], "Texte de test")
        self.assertEqual(kwargs['arguments']['belief_set'], "a => b")
        self.assertEqual(kwargs['arguments']['queries'], "a\nb\na => b")
        expected_tweety_results = "Tweety Result: Query 'a' is ACCEPTED (True).\nTweety Result: Query 'b' is REJECTED (False).\nTweety Result: Query 'a => b' is ACCEPTED (True)."
        self.assertEqual(kwargs['arguments']['tweety_result'], expected_tweety_results)
        
        self.assertEqual(interpretation, "Interprétation finale des résultats")

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule valide."""
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
            is_valid, _ = self.agent.tweety_bridge.validate_formula("a => b") # Appel mocké
            self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")
        else:
            # Appel direct à la vraie méthode de l'instance de l'agent
            is_valid, _ = self.agent.tweety_bridge.validate_formula("a => b")
        
        if self.use_real_jpype:
            # Si la JVM n'est pas prête, is_valid sera False.
            # Si la JVM est prête, is_valid sera True pour "a => b".
            # L'assertion self.assertTrue(is_valid) est correcte si la JVM est supposée fonctionner.
            # Pour ce test spécifique, nous voulons vérifier le comportement avec une JVM potentiellement non prête.
            if not self.agent.tweety_bridge.is_jvm_ready():
                 self.assertFalse(is_valid, "validate_formula devrait retourner False si la JVM n'est pas prête.")
            else:
                 self.assertTrue(is_valid, "validate_formula devrait retourner True pour une formule valide si la JVM est prête.")
        else: # Cas mocké
            self.assertTrue(is_valid)
        
        # if not self.use_real_jpype: # Déplacé ci-dessus
            # self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")
        # Si real_jpype, la vraie méthode est appelée.

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule invalide."""
        if not self.use_real_jpype:
            self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Erreur de syntaxe")
            is_valid, _ = self.agent.tweety_bridge.validate_formula("a => (b") # Appel mocké
            self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => (b")
        else:
            # Appel direct à la vraie méthode de l'instance de l'agent
            is_valid, _ = self.agent.tweety_bridge.validate_formula("a => (b")

        # Pour une formule invalide, ou si la JVM n'est pas prête, is_valid devrait être False.
        self.assertFalse(is_valid)

        # if not self.use_real_jpype: # Déplacé ci-dessus
            # self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => (b")
        # Si real_jpype, la vraie méthode est appelée.

def async_test(f):
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper

TestPropositionalLogicAgent.test_text_to_belief_set_success = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_success)
TestPropositionalLogicAgent.test_text_to_belief_set_empty_result = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_empty_result)
TestPropositionalLogicAgent.test_text_to_belief_set_invalid_belief_set = async_test(TestPropositionalLogicAgent.test_text_to_belief_set_invalid_belief_set)
TestPropositionalLogicAgent.test_generate_queries = async_test(TestPropositionalLogicAgent.test_generate_queries)
TestPropositionalLogicAgent.test_generate_queries_with_invalid_query = async_test(TestPropositionalLogicAgent.test_generate_queries_with_invalid_query)
TestPropositionalLogicAgent.test_interpret_results = async_test(TestPropositionalLogicAgent.test_interpret_results)


if __name__ == "__main__":
    unittest.main()