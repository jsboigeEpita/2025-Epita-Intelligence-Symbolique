#!/usr/bin/env python3
"""
Analyseur d'erreurs Tweety avec feedback BNF constructif
========================================================

Ce module fournit un système intelligent de correction des erreurs de parsing Tweety
en générant un feedback BNF spécifique pour guider les agents vers les bonnes corrections.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class TweetyErrorFeedback:
    """Structure pour encapsuler le feedback d'erreur BNF."""
    error_type: str
    original_error: str
    bnf_rules: List[str]
    corrections: List[str]
    example_fix: str
    confidence: float = 0.8


class TweetyErrorAnalyzer:
    """
    Analyseur intelligent d'erreurs Tweety pour génération de feedback BNF.
    
    Cette classe détecte les types d'erreurs courants dans le parsing Tweety
    et génère un feedback BNF constructif pour guider la correction.
    """
    
    def __init__(self):
        """Initialise l'analyseur avec les patterns d'erreur."""
        self.logger = logging.getLogger(__name__)
        self._setup_error_patterns()
        self._setup_bnf_rules()
    
    def _setup_error_patterns(self):
        """Configure les patterns de reconnaissance d'erreurs."""
        self.error_patterns = {
            'syntax_error': [
                r"syntax error at token",
                r"unexpected token",
                r"expected.*but found",
                r"missing.*before"
            ],
            'atom_error': [
                r"atom.*not defined",
                r"unknown atom",
                r"predicate.*undefined"
            ],
            'rule_error': [
                r"rule.*malformed",
                r"head.*invalid",
                r"body.*invalid"
            ],
            'constraint_error': [
                r"constraint.*violated",
                r"integrity constraint",
                r"constraint.*failed"
            ],
            'variable_error': [
                r"variable.*unbound",
                r"singleton variable",
                r"variable.*scope"
            ]
        }
    
    def _setup_bnf_rules(self):
        """Configure les règles BNF pour chaque type d'erreur."""
        self.bnf_rules = {
            'syntax_error': [
                "rule ::= head ':-' body '.'",
                "head ::= atom",
                "body ::= literal (',' literal)*",
                "literal ::= atom | '\\+' atom"
            ],
            'atom_error': [
                "atom ::= predicate '(' terms ')'",
                "predicate ::= lowercase_identifier",
                "terms ::= term (',' term)*",
                "term ::= variable | constant | atom"
            ],
            'rule_error': [
                "rule ::= fact | rule_with_body",
                "fact ::= atom '.'",
                "rule_with_body ::= head ':-' body '.'",
                "head ::= atom"
            ],
            'constraint_error': [
                "constraint ::= ':-' body '.'",
                "integrity_constraint ::= ':-' literal (',' literal)* '.'",
                "weak_constraint ::= ':~' body '.' '[' weight '@' level ']'"
            ],
            'variable_error': [
                "variable ::= uppercase_identifier | '_' identifier",
                "anonymous_variable ::= '_'",
                "variable_binding ::= variable '=' term"
            ]
        }
    
    def _setup_corrections(self):
        """Configure les suggestions de correction pour chaque type d'erreur."""
        self.corrections = {
            'syntax_error': [
                "Vérifiez la ponctuation (points, virgules)",
                "Assurez-vous que les règles se terminent par un point",
                "Vérifiez les parenthèses et crochets",
                "Utilisez ':-' pour séparer tête et corps de règle"
            ],
            'atom_error': [
                "Définissez tous les prédicats utilisés",
                "Vérifiez l'orthographe des noms de prédicats",
                "Assurez-vous que l'arité correspond aux définitions",
                "Utilisez des minuscules pour les noms de prédicats"
            ],
            'rule_error': [
                "Vérifiez la structure de la règle",
                "La tête doit être un seul atome",
                "Le corps peut contenir plusieurs littéraux séparés par des virgules",
                "Utilisez '\\+' pour la négation"
            ],
            'constraint_error': [
                "Les contraintes d'intégrité commencent par ':-'",
                "Vérifiez que les contraintes sont satisfaites",
                "Utilisez des contraintes faibles ':~' si approprié",
                "Ajoutez des poids et niveaux aux contraintes faibles"
            ],
            'variable_error': [
                "Les variables commencent par une majuscule",
                "Utilisez '_' pour les variables anonymes",
                "Assurez-vous que toutes les variables sont liées",
                "Évitez les variables singleton non intentionnelles"
            ]
        }
    
    def analyze_error(self, error_message: str, context: Optional[str] = None) -> TweetyErrorFeedback:
        """
        Analyse un message d'erreur Tweety et génère un feedback BNF.
        
        Args:
            error_message: Le message d'erreur à analyser
            context: Contexte optionnel (code source, ligne, etc.)
            
        Returns:
            TweetyErrorFeedback: Feedback structuré avec règles BNF et corrections
        """
        self.logger.debug(f"Analyse d'erreur Tweety: {error_message}")
        
        # Détecter le type d'erreur
        error_type = self._detect_error_type(error_message)
        
        # Récupérer les règles BNF appropriées
        bnf_rules = self.bnf_rules.get(error_type, [])
        
        # Générer les corrections
        corrections = self.corrections.get(error_type, [])
        
        # Générer un exemple de correction
        example_fix = self._generate_example_fix(error_type, error_message, context)
        
        # Calculer la confiance
        confidence = self._calculate_confidence(error_type, error_message)
        
        return TweetyErrorFeedback(
            error_type=error_type,
            original_error=error_message,
            bnf_rules=bnf_rules,
            corrections=corrections,
            example_fix=example_fix,
            confidence=confidence
        )
    
    def _detect_error_type(self, error_message: str) -> str:
        """Détecte le type d'erreur basé sur le message."""
        error_message_lower = error_message.lower()
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message_lower):
                    return error_type
        
        return 'syntax_error'  # Type par défaut
    
    def _generate_example_fix(self, error_type: str, error_message: str, context: Optional[str]) -> str:
        """Génère un exemple de correction spécifique."""
        examples = {
            'syntax_error': "Exemple: règle(X) :- condition(X).",
            'atom_error': "Exemple: définir prédicat(terme1, terme2).",
            'rule_error': "Exemple: tête :- corps1, corps2.",
            'constraint_error': "Exemple: :- condition_violée.",
            'variable_error': "Exemple: Variable avec majuscule, _anonyme."
        }
        
        base_example = examples.get(error_type, "Vérifiez la syntaxe Tweety.")
        
        # Personnaliser l'exemple basé sur le contexte
        if context and error_type == 'syntax_error':
            # Essayer d'extraire des informations du contexte
            if 'missing' in error_message.lower() and '.' in error_message:
                base_example = "Il manque probablement un point à la fin de la règle."
        
        return base_example
    
    def _calculate_confidence(self, error_type: str, error_message: str) -> float:
        """Calcule un score de confiance pour l'analyse."""
        # Logique simple de confiance basée sur la spécificité des patterns
        confidence_map = {
            'atom_error': 0.9,
            'constraint_error': 0.9,
            'variable_error': 0.85,
            'rule_error': 0.8,
            'syntax_error': 0.7
        }
        
        base_confidence = confidence_map.get(error_type, 0.6)
        
        # Ajuster basé sur la longueur et spécificité du message
        if len(error_message) > 50:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def generate_bnf_feedback_message(self, feedback: TweetyErrorFeedback, attempt_number: int = 1) -> str:
        """
        Génère un message de feedback formaté pour l'agent.
        
        Args:
            feedback: Feedback structuré à formater
            attempt_number: Numéro de tentative courante
            
        Returns:
            Message de feedback formaté
        """
        message_parts = [
            f"🔍 **Analyse d'erreur Tweety (Tentative #{attempt_number})**",
            f"**Type d'erreur détecté:** {feedback.error_type}",
            f"**Confiance:** {feedback.confidence:.1%}",
            "",
            f"**Erreur originale:**",
            f"```",
            feedback.original_error,
            f"```",
            "",
            f"**Règles BNF pertinentes:**"
        ]
        
        for rule in feedback.bnf_rules:
            message_parts.append(f"- `{rule}`")
        
        message_parts.extend([
            "",
            f"**Suggestions de correction:**"
        ])
        
        for i, correction in enumerate(feedback.corrections, 1):
            message_parts.append(f"{i}. {correction}")
        
        message_parts.extend([
            "",
            f"**Exemple de correction:**",
            f"```prolog",
            feedback.example_fix,
            f"```",
            "",
            f"💡 **Conseil:** Vérifiez la syntaxe Tweety et assurez-vous que tous les éléments respectent la grammaire BNF."
        ])
        
        return "\n".join(message_parts)


def analyze_tweety_error(error_message: str, attempt_number: int = 1, context: Optional[str] = None) -> str:
    """
    Fonction utilitaire pour analyser rapidement une erreur Tweety.
    
    Args:
        error_message: Message d'erreur Tweety
        attempt_number: Numéro de tentative courante
        context: Contexte optionnel
        
    Returns:
        Message de feedback BNF formaté
    """
    analyzer = TweetyErrorAnalyzer()
    feedback = analyzer.analyze_error(error_message, context)
    return analyzer.generate_bnf_feedback_message(feedback, attempt_number)


# Logger du module
logger = logging.getLogger(__name__)
logger.debug("Module tweety_error_analyzer chargé.")
