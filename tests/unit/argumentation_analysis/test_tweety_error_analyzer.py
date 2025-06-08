#!/usr/bin/env python3
"""
Tests unitaires pour TweetyErrorAnalyzer
=======================================

Tests pour l'analyseur d'erreurs Tweety avec feedback BNF constructif.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argumentation_analysis.utils.tweety_error_analyzer import (
    TweetyErrorAnalyzer, 
    TweetyErrorFeedback,
    create_bnf_feedback_for_error
)


class TestTweetyErrorFeedback:
    """Tests pour la classe TweetyErrorFeedback."""
    
    def test_tweety_error_feedback_creation(self):
        """Test de création d'un feedback d'erreur."""
        feedback = TweetyErrorFeedback(
            error_type="DECLARATION_ERROR",
            original_error="Predicate 'test' has not been declared",
            bnf_rules=["Rule 1", "Rule 2"],
            corrections=["Fix 1", "Fix 2"],
            example_fix="constant test\nprop(test)",
            confidence=0.95
        )
        
        assert feedback.error_type == "DECLARATION_ERROR"
        assert feedback.original_error == "Predicate 'test' has not been declared"
        assert len(feedback.bnf_rules) == 2
        assert len(feedback.corrections) == 2
        assert feedback.confidence == 0.95
        assert "constant test" in feedback.example_fix
    
    def test_tweety_error_feedback_dataclass_fields(self):
        """Test des champs de la dataclass TweetyErrorFeedback."""
        feedback = TweetyErrorFeedback(
            error_type="TEST",
            original_error="test error",
            bnf_rules=[],
            corrections=[],
            example_fix="test fix",
            confidence=1.0
        )
        
        # Vérifier que tous les champs requis sont présents
        assert hasattr(feedback, 'error_type')
        assert hasattr(feedback, 'original_error')
        assert hasattr(feedback, 'bnf_rules')
        assert hasattr(feedback, 'corrections')
        assert hasattr(feedback, 'example_fix')
        assert hasattr(feedback, 'confidence')


class TestTweetyErrorAnalyzer:
    """Tests pour la classe TweetyErrorAnalyzer."""
    
    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.analyzer = TweetyErrorAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test d'initialisation de l'analyseur."""
        analyzer = TweetyErrorAnalyzer()
        
        assert hasattr(analyzer, 'logger')
        assert hasattr(analyzer, 'error_patterns')
        assert hasattr(analyzer, 'bnf_rules')
        
        # Vérifier que les patterns d'erreur sont définis
        assert len(analyzer.error_patterns) > 0
        assert len(analyzer.bnf_rules) > 0
    
    def test_analyze_predicate_not_declared_error(self):
        """Test d'analyse d'erreur de prédicat non déclaré."""
        error_message = "Predicate 'human' has not been declared"
        
        feedback = self.analyzer.analyze_error(error_message)
        
        assert isinstance(feedback, TweetyErrorFeedback)
        assert feedback.error_type == "DECLARATION_ERROR"
        assert "human" in feedback.original_error
        assert feedback.confidence >= 0.90
        assert len(feedback.bnf_rules) > 0
        assert len(feedback.corrections) > 0
    
    def test_analyze_constant_syntax_error(self):
        """Test d'analyse d'erreur de syntaxe constant."""
        error_message = "Error parsing: constant(mortal) in modal formula"
        
        feedback = self.analyzer.analyze_error(error_message)
        
        assert isinstance(feedback, TweetyErrorFeedback)
        assert feedback.error_type == "CONSTANT_SYNTAX_ERROR"
        assert feedback.confidence >= 0.85
        assert any("constant" in rule for rule in feedback.bnf_rules)
    
    def test_analyze_modal_syntax_error(self):
        """Test d'analyse d'erreur de syntaxe modale."""
        error_message = "Expected modal operator, found formula"
        
        feedback = self.analyzer.analyze_error(error_message)
        
        assert isinstance(feedback, TweetyErrorFeedback)
        assert feedback.error_type == "MODAL_SYNTAX_ERROR"
        assert feedback.confidence >= 0.80
        assert any("modal" in rule.lower() or "modaux" in rule.lower() for rule in feedback.bnf_rules)
    
    def test_analyze_json_structure_error(self):
        """Test d'analyse d'erreur de structure JSON."""
        error_message = "JSON structure invalid: missing key 'propositions'"
        
        feedback = self.analyzer.analyze_error(error_message)
        
        assert isinstance(feedback, TweetyErrorFeedback)
        assert feedback.error_type == "JSON_STRUCTURE_ERROR"
        assert feedback.confidence >= 0.75
        assert any("JSON" in rule for rule in feedback.bnf_rules)
    
    def test_analyze_unknown_error(self):
        """Test d'analyse d'erreur inconnue."""
        error_message = "Unknown error type that doesn't match patterns"
        
        feedback = self.analyzer.analyze_error(error_message)
        
        assert isinstance(feedback, TweetyErrorFeedback)
        assert feedback.error_type == "UNKNOWN_ERROR"
        assert feedback.confidence <= 0.5
        assert len(feedback.bnf_rules) > 0  # Règles génériques
    
    def test_analyze_error_with_context(self):
        """Test d'analyse d'erreur avec contexte."""
        error_message = "Predicate 'mortal' has not been declared"
        context = {
            "attempt": 2,
            "agent": "ModalLogicAgent",
            "previous_errors": ["syntax error"]
        }
        
        feedback = self.analyzer.analyze_error(error_message, context)
        
        assert isinstance(feedback, TweetyErrorFeedback)
        assert feedback.error_type == "DECLARATION_ERROR"
        
        # Le contexte devrait influencer les corrections
        assert len(feedback.corrections) > 0
    
    def test_generate_bnf_corrections_declaration_error(self):
        """Test de génération de corrections BNF pour erreur de déclaration."""
        feedback = self.analyzer.analyze_error("Predicate 'smart' has not been declared")
        
        # Vérifier que les corrections contiennent des éléments BNF spécifiques
        corrections_text = " ".join(feedback.corrections)
        assert "constant" in corrections_text
        assert "prop(" in corrections_text
        
        # Vérifier l'exemple de correction
        assert "smart" in feedback.example_fix
        assert "constant smart" in feedback.example_fix or "prop(smart)" in feedback.example_fix
    
    def test_generate_bnf_corrections_modal_error(self):
        """Test de génération de corrections BNF pour erreur modale."""
        feedback = self.analyzer.analyze_error("Expected modal operator")
        
        corrections_text = " ".join(feedback.bnf_rules)
        assert "[]" in corrections_text or "<>" in corrections_text
        assert "modal" in corrections_text.lower() or "modaux" in corrections_text.lower()
    
    def test_error_pattern_matching(self):
        """Test de correspondance des patterns d'erreur."""
        # Cas de test adaptés aux patterns réels de l'implémentation
        test_cases = [
            ("Predicate 'test' has not been declared", "DECLARATION_ERROR"),
            ("constant(test)", "CONSTANT_SYNTAX_ERROR"),  # Pattern exact avec parenthèses
            ("Expected modal formula", "MODAL_SYNTAX_ERROR"),
            ("JSON invalid structure", "JSON_STRUCTURE_ERROR")
        ]
        
        for error_msg, expected_type in test_cases:
            feedback = self.analyzer.analyze_error(error_msg)
            assert feedback.error_type == expected_type
    
    def test_confidence_calculation(self):
        """Test de calcul de confiance."""
        # Erreur très spécifique - confiance élevée
        specific_error = "Predicate 'human' has not been declared"
        feedback_specific = self.analyzer.analyze_error(specific_error)
        
        # Erreur vague - confiance plus faible
        vague_error = "Some parsing error occurred"
        feedback_vague = self.analyzer.analyze_error(vague_error)
        
        assert feedback_specific.confidence > feedback_vague.confidence
        assert feedback_specific.confidence >= 0.85
    
    def test_progressive_correction_improvement(self):
        """Test d'amélioration progressive des corrections."""
        # Simuler plusieurs tentatives avec le même type d'erreur
        error_message = "Predicate 'mortal' has not been declared"
        
        # Première tentative
        context1 = {"attempt": 1}
        feedback1 = self.analyzer.analyze_error(error_message, context1)
        
        # Deuxième tentative
        context2 = {"attempt": 2, "previous_errors": [error_message]}
        feedback2 = self.analyzer.analyze_error(error_message, context2)
        
        # Les corrections devraient être plus spécifiques à la deuxième tentative
        assert len(feedback2.corrections) >= len(feedback1.corrections)
    
    def test_multilingual_error_handling(self):
        """Test de gestion des erreurs en différentes langues."""
        # Test avec message d'erreur en anglais
        english_error = "Predicate 'test' has not been declared"
        feedback_en = self.analyzer.analyze_error(english_error)
        
        # Test avec message potentiellement en français
        french_error = "Le prédicat 'test' n'a pas été déclaré"
        feedback_fr = self.analyzer.analyze_error(french_error)
        
        # Les deux devraient produire un feedback valide
        assert isinstance(feedback_en, TweetyErrorFeedback)
        assert isinstance(feedback_fr, TweetyErrorFeedback)


class TestCreateBNFFeedbackFunction:
    """Tests pour la fonction create_bnf_feedback_for_error."""
    
    def test_create_bnf_feedback_basic(self):
        """Test de création de feedback BNF basique."""
        error_message = "Predicate 'smart' has not been declared"
        
        feedback_message = create_bnf_feedback_for_error(error_message)
        
        assert isinstance(feedback_message, str)
        assert "ERREUR TWEETY DETECTEE" in feedback_message
        assert "DECLARATION_ERROR" in feedback_message
        assert "smart" in feedback_message
    
    def test_create_bnf_feedback_with_context(self):
        """Test de création de feedback BNF avec contexte."""
        error_message = "Expected modal formula"  # Pattern qui matche
        context = {"logic_type": "modal", "attempt": 3}
        
        feedback_message = create_bnf_feedback_for_error(error_message, context)
        
        assert isinstance(feedback_message, str)
        assert "ERREUR TWEETY DETECTEE" in feedback_message
        assert str(context) in feedback_message or "3" in feedback_message
    
    def test_create_bnf_feedback_edge_cases(self):
        """Test de création de feedback pour cas limites."""
        # Message vide
        feedback_empty = create_bnf_feedback_for_error("")
        assert isinstance(feedback_empty, str)
        assert "ERREUR TWEETY DETECTEE" in feedback_empty
        
        # Message très long
        long_message = "A" * 1000 + " predicate error"
        feedback_long = create_bnf_feedback_for_error(long_message)
        assert isinstance(feedback_long, str)
        assert "ERREUR TWEETY DETECTEE" in feedback_long
        
        # Message avec caractères spéciaux
        special_message = "Error: prédicat 'émotionné' non déclaré"
        feedback_special = create_bnf_feedback_for_error(special_message)
        assert isinstance(feedback_special, str)
        assert "ERREUR TWEETY DETECTEE" in feedback_special


class TestTweetyErrorAnalyzerIntegration:
    """Tests d'intégration pour TweetyErrorAnalyzer."""
    
    def test_integration_with_modal_logic_agent(self):
        """Test d'intégration avec ModalLogicAgent."""
        analyzer = TweetyErrorAnalyzer()
        
        # Simuler une erreur typique de ModalLogicAgent
        modal_error = "Expected [] or <> operator in modal formula"
        context = {
            "agent_type": "ModalLogicAgent",
            "logic_type": "modal",
            "formula": "!(mortal) && human"
        }
        
        feedback = analyzer.analyze_error(modal_error, context)
        
        assert feedback.error_type == "MODAL_SYNTAX_ERROR"
        assert any("[]" in rule or "<>" in rule for rule in feedback.bnf_rules)
    
    def test_integration_with_real_tweety_errors(self):
        """Test d'intégration avec vraies erreurs Tweety."""
        analyzer = TweetyErrorAnalyzer()
        
        # Erreurs réelles possibles de TweetyProject
        real_errors = [
            "at line 1:14 no viable alternative at input 'constant(human)'",
            "MissingTokenException: at line 1:0 missing EOF at 'prop'",
            "RecognitionException: at line 2:5 extraneous input 'constant'"
        ]
        
        for error in real_errors:
            feedback = analyzer.analyze_error(error)
            assert isinstance(feedback, TweetyErrorFeedback)
            # Pour les erreurs non reconnues, corrections peuvent être vides
            assert feedback.error_type in ["UNKNOWN_ERROR", "CONSTANT_SYNTAX_ERROR"]
            assert feedback.confidence >= 0.5
    
    @patch('argumentation_analysis.utils.tweety_error_analyzer.logging')
    def test_logging_functionality(self, mock_logging):
        """Test de la fonctionnalité de logging."""
        analyzer = TweetyErrorAnalyzer()
        
        error_message = "Test error for logging"
        feedback = analyzer.analyze_error(error_message)
        
        # Vérifier que le logger a été configuré
        assert hasattr(analyzer, 'logger')
        assert analyzer.logger.name.endswith('TweetyErrorAnalyzer')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
