import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments

from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.pl.pl_definitions import PL_AGENT_INSTRUCTIONS


class TestPropositionalLogicAgent:
    """Tests pour la classe PropositionalLogicAgent."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mocker):
        """Initialisation avant chaque test."""
        self.kernel = MagicMock(spec=Kernel)
        self.kernel.invoke = AsyncMock()
        self.kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value={"temperature": 0.7})
        self.kernel.add_function = MagicMock()

        self.mock_tweety_bridge_instance = MagicMock(spec=TweetyBridge)
        mocker.patch(
            'argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge',
            return_value=self.mock_tweety_bridge_instance
        )
        
        self.mock_tweety_bridge_instance.is_jvm_ready.return_value = True
        self.mock_tweety_bridge_instance.validate_belief_set.return_value = (True, "Ensemble de croyances valide")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        self.mock_tweety_bridge_instance.execute_pl_query = MagicMock(return_value=(True, "Tweety Result: Query 'a => b' is ACCEPTED (True)."))
        self.mock_tweety_bridge_instance.is_pl_kb_consistent.return_value = (True, "Belief set is consistent")

        self.agent_name = "TestPLAgent"
        self.llm_service_id = "test_llm_service"
        self.agent = PropositionalLogicAgent(self.kernel, agent_name=self.agent_name)
        self.agent.setup_agent_components(self.llm_service_id)

    def test_initialization_and_setup(self):
        """Test de l'initialisation et de la configuration de l'agent."""
        assert self.agent.name == self.agent_name
        assert self.agent.sk_kernel == self.kernel
        assert self.agent.logic_type == "PL"
        assert self.agent.system_prompt == PL_AGENT_INSTRUCTIONS
        
        self.mock_tweety_bridge_instance.is_jvm_ready.assert_called()
        assert self.kernel.add_function.call_count >= 3
        self.kernel.get_prompt_execution_settings_from_service_id.assert_called_with(self.llm_service_id)

    @pytest.mark.asyncio
    async def test_text_to_belief_set_success(self):
        """Test de la conversion de texte en ensemble de croyances avec succès."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a => b" 
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        assert kwargs['plugin_name'] == self.agent_name
        assert kwargs['function_name'] == "TextToPLBeliefSet"
        assert isinstance(kwargs['arguments'], KernelArguments)
        assert kwargs['arguments']['input'] == "Texte de test"
        
        self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with(belief_set_str="a => b")
        
        assert isinstance(belief_set, PropositionalBeliefSet)
        assert belief_set.content == "a => b"
        assert message == "Conversion réussie."

    @pytest.mark.asyncio
    async def test_text_to_belief_set_empty_result(self):
        """Test de la conversion de texte en ensemble de croyances avec résultat vide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "" 
        self.kernel.invoke.return_value = mock_sk_result
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_belief_set.assert_not_called()
        
        assert belief_set is None
        assert message == "La conversion a produit un ensemble de croyances vide."

    @pytest.mark.asyncio
    async def test_text_to_belief_set_invalid_belief_set(self):
        """Test de la conversion de texte en ensemble de croyances avec ensemble invalide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "invalid_pl_syntax {"
        self.kernel.invoke.return_value = mock_sk_result
        self.mock_tweety_bridge_instance.validate_belief_set.return_value = (False, "Erreur de syntaxe")
        
        belief_set, message = await self.agent.text_to_belief_set("Texte de test")
        
        self.kernel.invoke.assert_called_once()
        self.mock_tweety_bridge_instance.validate_belief_set.assert_called_once_with(belief_set_str="invalid_pl_syntax {")
        
        assert belief_set is None
        assert message == "Ensemble de croyances invalide: Erreur de syntaxe"

    @pytest.mark.asyncio
    async def test_generate_queries(self):
        """Test de la génération de requêtes."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a\nb\na => b"
        self.kernel.invoke.return_value = mock_sk_result
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        args, kwargs = self.kernel.invoke.call_args
        assert kwargs['plugin_name'] == self.agent_name
        assert kwargs['function_name'] == "GeneratePLQueries"
        assert kwargs['arguments']['input'] == "Texte de test"
        assert kwargs['arguments']['belief_set'] == "x => y"

        assert self.mock_tweety_bridge_instance.validate_formula.call_count == 3
        self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="a")
        self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="b")
        self.mock_tweety_bridge_instance.validate_formula.assert_any_call(formula_string="a => b")
        assert queries == ["a", "b", "a => b"]

    @pytest.mark.asyncio
    async def test_generate_queries_with_invalid_query(self):
        """Test de la génération de requêtes avec une requête invalide."""
        mock_sk_result = MagicMock()
        mock_sk_result.__str__.return_value = "a\ninvalid_query {\nc"
        self.kernel.invoke.return_value = mock_sk_result
        
        def validate_side_effect(formula_string):
            if formula_string == "invalid_query {":
                return (False, "Erreur de syntaxe")
            return (True, "Formule valide")
        self.mock_tweety_bridge_instance.validate_formula.side_effect = validate_side_effect
        
        belief_set_obj = PropositionalBeliefSet("x => y")
        queries = await self.agent.generate_queries("Texte de test", belief_set_obj)
        
        self.kernel.invoke.assert_called_once()
        assert self.mock_tweety_bridge_instance.validate_formula.call_count == 3
        assert queries == ["a", "c"]

    def test_execute_query_accepted(self):
        """Test de l'exécution d'une requête acceptée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.return_value = (True, "Tweety Result: Query 'a => b' is ACCEPTED (True).")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a => b")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
            belief_set_content="a => b",
            query_string="a => b"
        )
        
        assert result is True
        assert message == "Tweety Result: Query 'a => b' is ACCEPTED (True)."

    def test_execute_query_rejected(self):
        """Test de l'exécution d'une requête rejetée."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.return_value = (False, "Tweety Result: Query 'c' is REJECTED (False).")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "c")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="c")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
            belief_set_content="a => b",
            query_string="c"
        )
        assert result is False
        if not os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1'):
            assert message == "Tweety Result: Query 'c' is REJECTED (False)."

    def test_execute_query_error_tweety(self):
        """Test de l'exécution d'une requête avec erreur de Tweety."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.execute_pl_query.return_value = (False, "FUNC_ERROR: Erreur de syntaxe Tweety")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")

        result, message = self.agent.execute_query(belief_set_obj, "a")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_called_once_with(
            belief_set_content="a => b",
            query_string="a"
        )
        
        assert result is None
        assert "FUNC_ERROR" in message

    def test_execute_query_invalid_formula(self):
        """Test de l'exécution d'une requête avec une formule invalide."""
        belief_set_obj = PropositionalBeliefSet("a => b")
        self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Syntax Error in query")

        result, message = self.agent.execute_query(belief_set_obj, "invalid_query {")
        
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="invalid_query {")
        self.mock_tweety_bridge_instance.execute_pl_query.assert_not_called()
        
        assert result is False
        assert message.startswith("FUNC_ERROR: Requête invalide: invalid_query {")


    @pytest.mark.asyncio
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
        assert kwargs['plugin_name'] == self.agent_name
        assert kwargs['function_name'] == "InterpretPLResults"
        assert kwargs['arguments']['input'] == "Texte de test"
        assert kwargs['arguments']['belief_set'] == "a => b"
        assert kwargs['arguments']['queries'] == "a\nb\na => b"
        expected_tweety_results = "Tweety Result: Query 'a' is ACCEPTED (True).\nTweety Result: Query 'b' is REJECTED (False).\nTweety Result: Query 'a => b' is ACCEPTED (True)."
        assert kwargs['arguments']['tweety_result'] == expected_tweety_results
        
        assert interpretation == "Interprétation finale des résultats"

    def test_validate_formula_valid(self):
        """Test de la validation d'une formule valide."""
        self.mock_tweety_bridge_instance.validate_formula.return_value = (True, "Formule valide")
        is_valid = self.agent.validate_formula("a => b")
        assert is_valid is True
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => b")

    def test_validate_formula_invalid(self):
        """Test de la validation d'une formule invalide."""
        self.mock_tweety_bridge_instance.validate_formula.return_value = (False, "Erreur de syntaxe")
        is_valid = self.agent.validate_formula("a => (b")
        assert is_valid is False
        self.mock_tweety_bridge_instance.validate_formula.assert_called_once_with(formula_string="a => (b")
