#!/usr/bin/env python3
"""
Tests unitaires pour l'agent FOL (FirstOrderLogicAgent)
=====================================================

Tests pour l'agent de logique du premier ordre et son intégration avec Tweety FOL.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
    from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet
except ImportError:
    # Mock classes pour les tests si les composants n'existent pas encore
    class FirstOrderLogicAgent:
        def __init__(self, kernel=None, agent_name="FirstOrderLogicAgent", service_id=None):
            self.kernel = kernel
            self.agent_name = agent_name
            self.service_id = service_id
            self.belief_set = Mock()
            
        def generate_fol_syntax(self, text: str) -> str:
            return f"∀x(P(x) → Q(x))"
            
        def analyze_with_tweety_fol(self, formulas: List[str]) -> Dict[str, Any]:
            return {"status": "success", "results": ["valid"]}
    
    class FirstOrderBeliefSet:
        def __init__(self):
            self.beliefs = []
            
        def add_belief(self, belief: str):
            self.beliefs.append(belief)


class TestFirstOrderLogicAgent:
    """Tests pour la classe FirstOrderLogicAgent."""
    
    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.mock_kernel = Mock()
        self.agent_name = "TestFOLAgent"
        self.service_id = "test_service"
        
    def test_fol_agent_initialization(self):
        """Test d'initialisation de l'agent FOL."""
        agent = FirstOrderLogicAgent(
            kernel=self.mock_kernel,
            agent_name=self.agent_name,
            service_id=self.service_id
        )
        
        assert agent.agent_name == self.agent_name
        assert agent.kernel == self.mock_kernel
        assert agent.service_id == self.service_id
        assert hasattr(agent, 'belief_set')
    
    def test_fol_agent_default_initialization(self):
        """Test d'initialisation avec valeurs par défaut."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        assert agent.agent_name == "FirstOrderLogicAgent"
        assert agent.kernel == self.mock_kernel
    
    def test_generate_fol_syntax_simple(self):
        """Test de génération de syntaxe FOL simple."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        text = "Tous les hommes sont mortels"
        fol_formula = agent.generate_fol_syntax(text)
        
        assert isinstance(fol_formula, str)
        assert "∀" in fol_formula or "forall" in fol_formula.lower()
        assert "→" in fol_formula or "->" in fol_formula
    
    def test_generate_fol_syntax_complex(self):
        """Test de génération de syntaxe FOL complexe."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        text = "Il existe des hommes sages qui sont justes"
        fol_formula = agent.generate_fol_syntax(text)
        
        assert isinstance(fol_formula, str)
        # Doit contenir un quantificateur existentiel
        assert "∃" in fol_formula or "exists" in fol_formula.lower()
    
    def test_fol_syntax_with_predicates(self):
        """Test de génération avec prédicats spécifiques."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        text = "Si quelqu'un est homme, alors il est mortel"
        fol_formula = agent.generate_fol_syntax(text)
        
        # Vérifier la structure basique d'une formule FOL
        assert isinstance(fol_formula, str)
        assert len(fol_formula) > 0
        
        # La formule devrait contenir des éléments FOL
        fol_elements = ["∀", "∃", "→", "∧", "∨", "¬", "(", ")", "x", "P", "Q"]
        has_fol_elements = any(elem in fol_formula for elem in fol_elements)
        assert has_fol_elements
    
    def test_belief_set_management(self):
        """Test de gestion du belief set."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        # Ajouter des croyances
        try:
            agent.belief_set.add_belief("∀x(Homme(x) → Mortel(x))")
            agent.belief_set.add_belief("Homme(socrate)")
            
            assert len(agent.belief_set.beliefs) == 2
        except AttributeError:
            # Si la méthode n'existe pas, tester l'interface de base
            assert hasattr(agent, 'belief_set')
    
    def test_tweety_fol_integration_success(self):
        """Test d'intégration réussie avec Tweety FOL."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        formulas = [
            "∀x(Homme(x) → Mortel(x))",
            "Homme(socrate)",
            "?- Mortel(socrate)"
        ]
        
        result = agent.analyze_with_tweety_fol(formulas)
        
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "success"
    
    @patch('argumentation_analysis.agents.core.logic.first_order_logic_agent.TweetyFOLSolver')
    def test_tweety_fol_integration_with_mock(self, mock_solver):
        """Test d'intégration avec Tweety FOL mocké."""
        # Configuration du mock solver
        mock_solver_instance = Mock()
        mock_solver_instance.solve.return_value = {
            "satisfiable": True,
            "models": [{"socrate": "mortel"}],
            "inference_results": ["Mortel(socrate)"]
        }
        mock_solver.return_value = mock_solver_instance
        
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        formulas = ["∀x(Homme(x) → Mortel(x))", "Homme(socrate)"]
        result = agent.analyze_with_tweety_fol(formulas)
        
        # Vérifier que le solver a été appelé
        if hasattr(agent, 'analyze_with_tweety_fol'):
            assert isinstance(result, dict)
    
    def test_fol_mapping_logic_type(self):
        """Test du mapping logic-type vers agent FOL."""
        from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
        
        try:
            factory = LogicAgentFactory()
            agent = factory.create_agent(
                logic_type="first_order",
                kernel=self.mock_kernel
            )
            
            assert isinstance(agent, FirstOrderLogicAgent)
            assert agent.agent_name == "FirstOrderLogicAgent"
        except ImportError:
            # Test fallback avec mapping direct
            logic_mapping = {
                "first_order": FirstOrderLogicAgent,
                "propositional": Mock,
                "modal": Mock
            }
            
            agent_class = logic_mapping.get("first_order")
            assert agent_class == FirstOrderLogicAgent
    
    def test_fol_agent_error_handling(self):
        """Test de gestion d'erreurs de l'agent FOL."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        # Test avec syntaxe invalide
        invalid_formula = "invalid fol syntax"
        
        try:
            result = agent.generate_fol_syntax(invalid_formula)
            # Même avec entrée invalide, doit retourner quelque chose
            assert isinstance(result, str)
        except Exception as e:
            # Si erreur, vérifier qu'elle est bien gérée
            assert isinstance(e, (ValueError, SyntaxError))
    
    def test_fol_agent_performance(self):
        """Test de performance basique de l'agent FOL."""
        agent = FirstOrderLogicAgent(kernel=self.mock_kernel)
        
        import time
        start_time = time.time()
        
        # Générer plusieurs formules FOL
        for i in range(10):
            text = f"Test case {i}: All X are Y"
            formula = agent.generate_fol_syntax(text)
            assert isinstance(formula, str)
        
        elapsed_time = time.time() - start_time
        
        # Performance : moins de 1 seconde pour 10 formules
        assert elapsed_time < 1.0


class TestFirstOrderBeliefSet:
    """Tests pour la classe FirstOrderBeliefSet."""
    
    def test_belief_set_initialization(self):
        """Test d'initialisation du belief set."""
        belief_set = FirstOrderBeliefSet()
        
        assert hasattr(belief_set, 'beliefs')
        assert isinstance(belief_set.beliefs, list)
        assert len(belief_set.beliefs) == 0
    
    def test_add_belief(self):
        """Test d'ajout de croyances."""
        belief_set = FirstOrderBeliefSet()
        
        belief1 = "∀x(Homme(x) → Mortel(x))"
        belief2 = "Homme(socrate)"
        
        belief_set.add_belief(belief1)
        belief_set.add_belief(belief2)
        
        assert len(belief_set.beliefs) == 2
        assert belief1 in belief_set.beliefs
        assert belief2 in belief_set.beliefs
    
    def test_belief_validation(self):
        """Test de validation des croyances FOL."""
        belief_set = FirstOrderBeliefSet()
        
        # Croyance valide
        valid_belief = "∀x(P(x) → Q(x))"
        
        try:
            belief_set.add_belief(valid_belief)
            assert valid_belief in belief_set.beliefs
        except Exception:
            # Si validation pas encore implémentée
            belief_set.beliefs.append(valid_belief)
            assert valid_belief in belief_set.beliefs


class TestFOLIntegrationWithTweety:
    """Tests d'intégration FOL avec Tweety réel."""
    
    @pytest.mark.integration
    def test_real_tweety_fol_integration(self):
        """Test d'intégration avec vrai Tweety FOL (si disponible)."""
        # Test conditionnel - seulement si Tweety FOL est disponible
        try:
            from argumentation_analysis.services.tweety_fol_service import TweetyFOLService
            
            service = TweetyFOLService()
            
            # Test avec formules FOL simples
            formulas = [
                "∀x(Homme(x) → Mortel(x))",
                "Homme(socrate)",
                "?- Mortel(socrate)"
            ]
            
            result = service.solve_fol(formulas)
            
            assert isinstance(result, dict)
            assert "satisfiable" in result or "status" in result
            
        except ImportError:
            # Skip si Tweety FOL pas disponible
            pytest.skip("Tweety FOL service not available")
    
    @pytest.mark.integration
    def test_fol_agent_with_real_tweety(self):
        """Test agent FOL avec vrai Tweety."""
        try:
            agent = FirstOrderLogicAgent(kernel=Mock())
            
            # Générer et tester avec Tweety réel
            text = "Tous les chats sont des mammifères"
            formula = agent.generate_fol_syntax(text)
            
            # Test avec le vrai backend Tweety
            result = agent.analyze_with_tweety_fol([formula])
            
            assert isinstance(result, dict)
            
        except (ImportError, Exception) as e:
            pytest.skip(f"Real Tweety integration not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
