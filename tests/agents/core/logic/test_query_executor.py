
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_query_executor.py
"""
Tests unitaires pour la classe QueryExecutor.
"""

import unittest
import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.agents.core.logic.query_executor import QueryExecutor
from argumentation_analysis.agents.core.logic.belief_set import (
    PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet
)


class TestQueryExecutor:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            print(f"Authentic LLM call failed: {e}")
            return "Authentic LLM call failed"

    """Tests pour la classe QueryExecutor."""
    
    @pytest.fixture(autouse=True)
    async def async_setUp(self):
        """Initialisation asynchrone avant chaque test."""
        with patch('argumentation_analysis.agents.core.logic.query_executor.TweetyBridge') as mock_tweety_bridge_class:
            self.mock_tweety_bridge = await self._create_authentic_gpt4o_mini_instance()
            mock_tweety_bridge_class.return_value = self.mock_tweety_bridge
            
            self.mock_tweety_bridge.is_jvm_ready.return_value = True
            
            self.query_executor = QueryExecutor()
            self.mock_tweety_bridge_class = mock_tweety_bridge_class
            yield
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test de l'initialisation de l'exécuteur de requêtes."""
        self.mock_tweety_bridge_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_query_jvm_not_ready(self):
        """Test de l'exécution d'une requête lorsque la JVM n'est pas prête."""
        self.mock_tweety_bridge.is_jvm_ready.return_value = False
        
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        self.mock_tweety_bridge.is_jvm_ready.assert_called_once()
        
        assert result is None
        assert "FUNC_ERROR" in message
    
    @pytest.mark.asyncio
    async def test_execute_query_propositional_accepted(self):
        """Test de l'exécution d'une requête propositionnelle acceptée."""
        self.mock_tweety_bridge.validate_formula.return_value = (True, "OK")
        self.mock_tweety_bridge.execute_pl_query.return_value = "Tweety Result: Query 'a' is ACCEPTED (True)."
        
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        self.mock_tweety_bridge.validate_formula.assert_called_once_with("a")
        self.mock_tweety_bridge.execute_pl_query.assert_called_once_with("a => b", "a")
        
        assert result is True
        assert message == "Tweety Result: Query 'a' is ACCEPTED (True)."
    
    @pytest.mark.asyncio
    async def test_execute_query_propositional_rejected(self):
        """Test de l'exécution d'une requête propositionnelle rejetée."""
        self.mock_tweety_bridge.validate_formula.return_value = (True, "OK")
        self.mock_tweety_bridge.execute_pl_query.return_value = "Tweety Result: Query 'a' is REJECTED (False)."
        
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        self.mock_tweety_bridge.validate_formula.assert_called_once_with("a")
        self.mock_tweety_bridge.execute_pl_query.assert_called_once_with("a => b", "a")
        
        assert result is False
        assert message == "Tweety Result: Query 'a' is REJECTED (False)."
    
    @pytest.mark.asyncio
    async def test_execute_query_propositional_error(self):
        """Test de l'exécution d'une requête propositionnelle avec erreur."""
        self.mock_tweety_bridge.validate_formula.return_value = (True, "OK")
        self.mock_tweety_bridge.execute_pl_query.return_value = "FUNC_ERROR: Erreur de syntaxe"
        
        belief_set = PropositionalBeliefSet("a => b")
        result, message = self.query_executor.execute_query(belief_set, "a")
        
        self.mock_tweety_bridge.validate_formula.assert_called_once_with("a")
        self.mock_tweety_bridge.execute_pl_query.assert_called_once_with("a => b", "a")
        
        assert result is None
        assert message == "FUNC_ERROR: Erreur de syntaxe"
    
    @pytest.mark.async_io
    async def test_execute_query_first_order_accepted(self):
        """Test de l'exécution d'une requête du premier ordre acceptée."""
        self.mock_tweety_bridge.validate_fol_formula.return_value = (True, "OK")
        self.mock_tweety_bridge.execute_fol_query.return_value = "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."
        
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        result, message = self.query_executor.execute_query(belief_set, "P(a)")
        
        self.mock_tweety_bridge.validate_fol_formula.assert_called_once_with("P(a)")
        self.mock_tweety_bridge.execute_fol_query.assert_called_once_with("forall X: (P(X) => Q(X))", "P(a)")
        
        assert result is True
        assert message == "Tweety Result: FOL Query 'P(a)' is ACCEPTED (True)."
    
    @pytest.mark.asyncio
    async def test_execute_query_modal_accepted(self):
        """Test de l'exécution d'une requête modale acceptée."""
        self.mock_tweety_bridge.validate_modal_formula.return_value = (True, "OK")
        self.mock_tweety_bridge.execute_modal_query.return_value = "Tweety Result: Modal Query '[]p' is ACCEPTED (True)."
        
        belief_set = ModalBeliefSet("[]p => <>q")
        result, message = self.query_executor.execute_query(belief_set, "[]p")
        
        self.mock_tweety_bridge.validate_modal_formula.assert_called_once_with("[]p")
        self.mock_tweety_bridge.execute_modal_query.assert_called_once_with("[]p => <>q", "[]p")
        
        assert result is True
        assert message == "Tweety Result: Modal Query '[]p' is ACCEPTED (True)."
    
    @pytest.mark.asyncio
    async def test_execute_query_unsupported_type(self):
        """Test de l'exécution d'une requête avec un type non supporté."""
        mock_belief_set = MagicMock()
        mock_belief_set.logic_type = "unsupported"
        mock_belief_set.content = "content"
        
        result, message = self.query_executor.execute_query(mock_belief_set, "query")
        
        assert result is None
        assert "FUNC_ERROR" in message
        assert "Type de logique non supporté" in message
    
    @pytest.mark.asyncio
    async def test_execute_queries(self):
        """Test de l'exécution de plusieurs requêtes."""
        self.mock_tweety_bridge.validate_formula.side_effect = [
            (True, "OK"),
            (True, "OK"),
            (False, "Syntax Error in c")
        ]
        self.mock_tweety_bridge.execute_pl_query.side_effect = [
            "Tweety Result: Query 'a' is ACCEPTED (True).",
            "Tweety Result: Query 'b' is REJECTED (False)."
        ]
        
        belief_set = PropositionalBeliefSet("a => b")
        results = self.query_executor.execute_queries(belief_set, ["a", "b", "c"])
        
        assert self.mock_tweety_bridge.validate_formula.call_count == 3
        assert self.mock_tweety_bridge.execute_pl_query.call_count == 2
        
        assert len(results) == 3
        
        query1, result1, message1 = results[0]
        assert query1 == "a"
        assert result1 is True
        assert message1 == "Tweety Result: Query 'a' is ACCEPTED (True)."
        
        query2, result2, message2 = results[1]
        assert query2 == "b"
        assert result2 is False
        assert message2 == "Tweety Result: Query 'b' is REJECTED (False)."
        
        query3, result3, message3 = results[2]
        assert query3 == "c"
        assert result3 is None
        assert message3 == "FUNC_ERROR: Requête invalide: Syntax Error in c"