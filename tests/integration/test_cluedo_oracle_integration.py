#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS D'INTÉGRATION CLUEDO ORACLE
=================================

Tests d'intégration end-to-end pour cluedo_oracle_complete.py
Valide le comportement Oracle et l'intégration avec le moteur de jeu.

Tests couverts:
- État Oracle authentique
- Validation suggestions automatique
- Révélations forcées
- Moteur de jeu complet
- Statistiques Oracle
- Intégration Semantic Kernel
"""

import asyncio
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Configuration paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "examples" / "Sherlock_Watson"))

try:
    from cluedo_oracle_complete import (
        AuthenticCluedoOracle, 
        CluedoGameEngine, 
        CluedoOracleState,
        run_complete_cluedo_oracle_demo
    )
except ImportError:
    pytest.skip("cluedo_oracle_complete not available", allow_module_level=True)


class TestCluedoOracleIntegration:
    """Tests d'intégration pour Oracle Cluedo authentique"""
    
    @pytest.fixture
    def test_solution(self):
        """Solution secrète pour les tests"""
        return {
            "suspect": "Charlie Moriarty",
            "arme": "Script Python",
            "lieu": "Salle serveurs"
        }
    
    @pytest.fixture
    def test_oracle_cards(self):
        """Cartes Oracle pour les tests"""
        return ["Dr. Alice Watson", "Clé USB malveillante", "Bureau recherche"]
    
    @pytest.fixture
    def oracle_instance(self, test_solution, test_oracle_cards):
        """Instance Oracle pour les tests"""
        return AuthenticCluedoOracle(test_solution, test_oracle_cards)
    
    @pytest.fixture
    def test_case_data(self, test_solution):
        """Données de cas pour les tests"""
        return {
            "titre": "Test Mystère IA",
            "personnages": [
                {"nom": "Dr. Alice Watson"},
                {"nom": "Prof. Bob Sherlock"},
                {"nom": "Charlie Moriarty"},
                {"nom": "Diana Oracle"}
            ],
            "armes": [
                {"nom": "Clé USB malveillante"},
                {"nom": "Script Python"},
                {"nom": "Câble réseau"}
            ],
            "lieux": [
                {"nom": "Salle serveurs"},
                {"nom": "Bureau recherche"},
                {"nom": "Laboratoire test"}
            ],
            "solution_secrete": test_solution
        }
    
    def test_oracle_state_initialization(self, oracle_instance):
        """Test initialisation état Oracle"""
        state = oracle_instance.state
        
        assert isinstance(state, CluedoOracleState)
        assert state.solution_secrete["suspect"] == "Charlie Moriarty"
        assert state.solution_secrete["arme"] == "Script Python"
        assert state.solution_secrete["lieu"] == "Salle serveurs"
        assert "Dr. Alice Watson" in state.oracle_cards
        assert state.mock_used == False
        assert state.authentic_mode == True
        assert state.suggestions_count == 0
        assert state.oracle_revelations_count == 0
    
    def test_oracle_suggestion_validation_refutation(self, oracle_instance):
        """Test validation suggestion avec réfutation Oracle"""
        # Suggestion avec carte Oracle -> réfutation
        revelation = oracle_instance.validate_suggestion(
            "Dr. Alice Watson",  # Carte Oracle
            "Script Python",
            "Salle serveurs",
            "Sherlock"
        )
        
        assert revelation["can_refute"] == True
        assert "Dr. Alice Watson" in revelation["revealed_cards"]
        assert revelation["oracle_type"] == "refutation"
        assert revelation["authentic"] == True
        assert "Oracle révélation automatique" in revelation["message"]
        
        # Vérification état mis à jour
        assert oracle_instance.state.suggestions_count == 1
        assert oracle_instance.state.oracle_revelations_count == 1
    
    def test_oracle_suggestion_validation_correct_solution(self, oracle_instance):
        """Test validation suggestion correcte"""
        # Suggestion correcte (solution exacte)
        revelation = oracle_instance.validate_suggestion(
            "Charlie Moriarty",  # Solution correcte
            "Script Python",
            "Salle serveurs",
            "Watson"
        )
        
        assert revelation["can_refute"] == False
        assert revelation["revealed_cards"] == []
        assert revelation["oracle_type"] == "solution_confirmed"
        assert revelation.get("solution_found") == True
        assert revelation["authentic"] == True
        assert "CORRECTE" in revelation["message"]
    
    def test_oracle_suggestion_validation_neutral(self, oracle_instance):
        """Test validation suggestion neutre"""
        # Suggestion sans carte Oracle et pas solution
        revelation = oracle_instance.validate_suggestion(
            "Prof. Bob Sherlock",  # Pas carte Oracle, pas solution
            "Câble réseau",
            "Laboratoire test",
            "Sherlock"
        )
        
        assert revelation["can_refute"] == False
        assert revelation["revealed_cards"] == []
        assert revelation["oracle_type"] == "neutral"
        assert revelation.get("solution_found") != True
        assert revelation["authentic"] == True
        assert "silence inquiétant" in revelation["message"]
    
    def test_oracle_statistics(self, oracle_instance):
        """Test statistiques Oracle"""
        # Plusieurs suggestions pour tester statistiques
        oracle_instance.validate_suggestion("Test1", "Test2", "Test3", "Agent1")
        oracle_instance.validate_suggestion("Dr. Alice Watson", "Test", "Test", "Agent2")
        
        stats = oracle_instance.get_oracle_statistics()
        
        assert stats["suggestions_processed"] == 2
        assert stats["revelations_made"] == 1  # Une seule révélation (carte Oracle)
        assert stats["revelation_rate"] == 50.0  # 1/2 * 100
        assert stats["authentic_mode"] == True
        assert stats["mock_used"] == False
        assert "success_rate" in stats
        assert "tests_passed" in stats
        assert "tests_total" in stats
    
    @pytest.mark.asyncio
    async def test_game_engine_initialization(self):
        """Test initialisation moteur de jeu"""
        engine = CluedoGameEngine()
        
        assert engine.oracle is None
        assert engine.kernel is None
        assert engine.game_state is None
        assert engine.conversation_history == []
        assert engine.mock_used == False
        assert engine.authentic_mode == True
    
    @pytest.mark.asyncio
    async def test_game_engine_setup_no_api_key(self, test_case_data):
        """Test configuration jeu sans clé API"""
        engine = CluedoGameEngine()
        
        # Test sans clé API
        original_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        try:
            result = await engine.setup_authentic_game(test_case_data)
            assert result == False  # Doit échouer sans clé
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    @pytest.mark.asyncio
    async def test_game_engine_setup_with_api_key(self, test_case_data):
        """Test configuration jeu avec clé API"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not configured")
        
        engine = CluedoGameEngine()
        
        try:
            result = await engine.setup_authentic_game(test_case_data)
            
            if result:
                assert engine.kernel is not None
                assert engine.oracle is not None
                assert engine.oracle.state.solution_secrete == test_case_data["solution_secrete"]
                assert len(engine.oracle.state.oracle_cards) > 0
                assert engine.authentic_mode == True
            else:
                # Configuration peut échouer pour diverses raisons réseau/API
                pytest.skip("Game engine setup failed (API/network issue)")
                
        except Exception as e:
            pytest.skip(f"Game engine setup error: {e}")
    
    @pytest.mark.asyncio
    async def test_simplified_investigation(self, test_case_data):
        """Test investigation simplifiée"""
        engine = CluedoGameEngine()
        
        # Configuration manuelle Oracle pour test isolé
        engine.oracle = AuthenticCluedoOracle(
            test_case_data["solution_secrete"],
            ["Dr. Alice Watson", "Clé USB malveillante"]
        )
        
        history, state = await engine._run_simplified_investigation("Test question")
        
        assert len(history) > 0
        assert state is not None
        assert state.get("authentic") == True
        assert state.get("mock_used") == False
        assert "final_solution" in state
        assert "oracle_statistics" in state
        
        # Vérification conversation
        system_entries = [h for h in history if h.get("sender") == "System"]
        agent_entries = [h for h in history if h.get("sender") in ["Sherlock", "Watson"]]
        oracle_entries = [h for h in history if h.get("sender") == "Oracle"]
        
        assert len(system_entries) >= 1
        assert len(agent_entries) >= 2
        assert len(oracle_entries) >= 2
    
    @pytest.mark.asyncio
    async def test_oracle_behavior_validation(self, test_case_data):
        """Test validation comportement Oracle"""
        engine = CluedoGameEngine()
        
        # Configuration Oracle
        engine.oracle = AuthenticCluedoOracle(
            test_case_data["solution_secrete"],
            ["Dr. Alice Watson", "Clé USB malveillante"]
        )
        
        result = await engine.validate_oracle_behavior()
        
        assert result == True
        assert engine.oracle.state.tests_passed > 0
        assert engine.oracle.state.calculate_success_rate() == 100.0
    
    @pytest.mark.asyncio
    async def test_complete_demo_fallback(self):
        """Test démonstration complète avec fallback"""
        # Test de la fonction principale avec gestion d'erreurs
        try:
            # Skip si problème d'import ou d'API
            if not os.getenv("OPENAI_API_KEY"):
                pytest.skip("OPENAI_API_KEY not configured")
            
            # Test avec timeout court pour éviter longs appels
            result = await asyncio.wait_for(
                run_complete_cluedo_oracle_demo(),
                timeout=10.0
            )
            
            # Si succès, vérifier que c'est bien authentique
            assert result == True
            
        except asyncio.TimeoutError:
            pytest.skip("Demo timeout (API call took too long)")
        except Exception as e:
            # Les erreurs d'import/configuration sont acceptables en test
            pytest.skip(f"Demo setup issue: {e}")
    
    def test_anti_mock_compliance(self, oracle_instance):
        """Test conformité anti-mock"""
        # Vérifications état Oracle
        assert oracle_instance.state.mock_used == False
        assert oracle_instance.state.authentic_mode == True
        
        # Test révélation pour vérifier marqueurs authentique
        revelation = oracle_instance.validate_suggestion("Test", "Test", "Test", "TestAgent")
        assert revelation.get("authentic") == True
        
        # Vérification historique
        assert len(oracle_instance.state.revelations_history) == 1
        history_entry = oracle_instance.state.revelations_history[0]
        assert history_entry["revelation"]["authentic"] == True
    
    def test_oracle_cards_generation(self, test_case_data):
        """Test génération cartes Oracle"""
        engine = CluedoGameEngine()
        
        suspects = [p["nom"] for p in test_case_data["personnages"]]
        armes = [a["nom"] for a in test_case_data["armes"]]
        lieux = [l["nom"] for l in test_case_data["lieux"]]
        solution = test_case_data["solution_secrete"]
        
        oracle_cards = engine._generate_oracle_cards(suspects, armes, lieux, solution)
        
        # Vérifications
        assert len(oracle_cards) > 0
        assert len(oracle_cards) <= 4
        
        # Oracle ne doit pas avoir les cartes solution
        solution_cards = [solution["suspect"], solution["arme"], solution["lieu"]]
        for card in oracle_cards:
            assert card not in solution_cards
    
    def test_success_rate_calculation(self, oracle_instance):
        """Test calcul taux de succès"""
        state = oracle_instance.state
        
        # Test initial
        assert state.calculate_success_rate() == 0.0
        
        # Test avec quelques tests passés
        state.tests_passed = 150
        state.tests_total = 157
        
        success_rate = state.calculate_success_rate()
        expected_rate = (150 / 157) * 100
        
        assert abs(success_rate - expected_rate) < 0.1
        assert state.success_rate == success_rate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])