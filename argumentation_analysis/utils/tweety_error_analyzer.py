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
        self._setup_corrections()

    def _setup_error_patterns(self):
        """Configure les patterns de reconnaissance d'erreurs, des plus spécifiques aux plus génériques."""
        self.error_patterns = {
            # Erreurs très spécifiques
            "DECLARATION_ERROR": [
                r"predicate '.*' has not been declared",
                r"le prédicat '.*' n'a pas été déclaré",
            ],
            "CONSTANT_SYNTAX_ERROR": [
                r"constant\(",  # Erreur comme 'constant(human)'
                r"error parsing.*constant",
            ],
            "MODAL_SYNTAX_ERROR": [
                r"expected modal operator",
                r"expected \[\] or <>",
                r"expected modal formula",
            ],
            "JSON_STRUCTURE_ERROR": [
                r"json.*structure.*invalid",
                r"missing key '.*' in json",
            ],
            # Erreurs génériques
            "atom_error": [
                r"atom.*not defined",
                r"unknown atom",
                r"predicate.*undefined",  # Plus générique que DECLARATION_ERROR
            ],
            "rule_error": [r"rule.*malformed", r"head.*invalid", r"body.*invalid"],
            "constraint_error": [
                r"constraint.*violated",
                r"integrity constraint",
                r"constraint.*failed",
            ],
            "variable_error": [
                r"variable.*unbound",
                r"singleton variable",
                r"variable.*scope",
            ],
            # Doit être à la fin pour ne pas masquer les autres
            "syntax_error": [
                r"syntax error",
                r"unexpected token",
                r"expected.*but found",
                r"missing.*before",
                r"no viable alternative at input",
            ],
        }

    def _setup_bnf_rules(self):
        """Configure les règles BNF pour chaque type d'erreur."""
        self.bnf_rules = {
            "DECLARATION_ERROR": [
                "declaration ::= 'constant' identifier | 'predicate' identifier '(' types ')'",
                "atom ::= predicate '(' terms ')'",
                "predicate ::= lowercase_identifier",
            ],
            "CONSTANT_SYNTAX_ERROR": [
                "declaration ::= 'constant' identifier '.'",
                "Example: constant my_const.",
            ],
            "MODAL_SYNTAX_ERROR": [
                "modal_formula ::= '[]' formula | '<>' formula",
                "formula ::= atom | formula '&&' formula | '!' formula",
            ],
            "JSON_STRUCTURE_ERROR": [
                "json_object ::= '{' members '}'",
                "members ::= pair (',' pair)*",
                "pair ::= string ':' value",
                "NOTE: This describes a generic JSON structure.",
            ],
            "syntax_error": [
                "rule ::= head ':-' body '.'",
                "head ::= atom",
                "body ::= literal (',' literal)*",
                "literal ::= atom | '\\+' atom",
            ],
            "atom_error": [
                "atom ::= predicate '(' terms ')'",
                "predicate ::= lowercase_identifier",
                "terms ::= term (',' term)*",
                "term ::= variable | constant | atom",
            ],
            "rule_error": [
                "rule ::= fact | rule_with_body",
                "fact ::= atom '.'",
                "rule_with_body ::= head ':-' body '.'",
                "head ::= atom",
            ],
            "constraint_error": [
                "constraint ::= ':-' body '.'",
                "integrity_constraint ::= ':-' literal (',' literal)* '.'",
                "weak_constraint ::= ':~' body '.' '[' weight '@' level ']'",
            ],
            "variable_error": [
                "variable ::= uppercase_identifier | '_' identifier",
                "anonymous_variable ::= '_'",
                "variable_binding ::= variable '=' term",
            ],
        }

    def _setup_corrections(self):
        """Configure les suggestions de correction pour chaque type d'erreur."""
        self.corrections = {
            "DECLARATION_ERROR": [
                "Déclarez tous les prédicats ou constantes avant de les utiliser.",
                "Exemple de déclaration de constante: `constant mon_individu.`",
                "Exemple de déclaration de prédicat: `predicate est_humain(individu).`",
                "Pour les propositions simples (0-aire), utilisez `prop(ma_proposition).`",
            ],
            "CONSTANT_SYNTAX_ERROR": [
                "Les déclarations de constantes doivent se terminer par un point.",
                "Syntaxe correcte: `constant nom_de_la_constante.`",
            ],
            "MODAL_SYNTAX_ERROR": [
                "Utilisez les opérateurs modaux `[]` (toujours) ou `<>` (parfois) devant une formule.",
                "Exemple: `[]p` signifie que p est toujours vrai.",
                "Exemple: `<>q` signifie que q est parfois vrai.",
            ],
            "JSON_STRUCTURE_ERROR": [
                "Vérifiez que votre JSON a la structure attendue.",
                "Assurez-vous que toutes les clés requises (ex: 'propositions') sont présentes.",
                "Vérifiez la syntaxe JSON (virgules, accolades, guillemets).",
            ],
            "syntax_error": [
                "Vérifiez la ponctuation (points, virgules)",
                "Assurez-vous que les règles se terminent par un point",
                "Vérifiez les parenthèses et crochets",
                "Utilisez ':-' pour séparer tête et corps de règle",
            ],
            "atom_error": [
                "Définissez tous les prédicats utilisés",
                "Vérifiez l'orthographe des noms de prédicats",
                "Assurez-vous que l'arité correspond aux définitions",
                "Utilisez des minuscules pour les noms de prédicats",
            ],
            "rule_error": [
                "Vérifiez la structure de la règle",
                "La tête doit être un seul atome",
                "Le corps peut contenir plusieurs littéraux séparés par des virgules",
                "Utilisez '\\+' pour la négation",
            ],
            "constraint_error": [
                "Les contraintes d'intégrité commencent par ':-'",
                "Vérifiez que les contraintes sont satisfaites",
                "Utilisez des contraintes faibles ':~' si approprié",
                "Ajoutez des poids et niveaux aux contraintes faibles",
            ],
            "variable_error": [
                "Les variables commencent par une majuscule",
                "Utilisez '_' pour les variables anonymes",
                "Assurez-vous que toutes les variables sont liées",
                "Évitez les variables singleton non intentionnelles",
            ],
        }

    def analyze_error(
        self, error_message: str, context: Optional[str] = None
    ) -> TweetyErrorFeedback:
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
        # Récupérer les règles BNF appropriées, avec un fallback sur les règles de syntaxe générales
        bnf_rules = self.bnf_rules.get(
            error_type, self.bnf_rules.get("syntax_error", [])
        )

        # Générer les corrections, avec un fallback sur les corrections de syntaxe générales
        corrections = self.corrections.get(
            error_type, self.corrections.get("syntax_error", [])
        )

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
            confidence=confidence,
        )

    def _detect_error_type(self, error_message: str) -> str:
        """Détecte le type d'erreur basé sur le message."""
        error_message_lower = error_message.lower()

        # Test spécifique pour JSON pour être plus robuste
        if all(
            word in error_message_lower for word in ["json", "invalid", "structure"]
        ):
            return "JSON_STRUCTURE_ERROR"

        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message_lower):
                    self.logger.debug(
                        f"Pattern '{pattern}' a matché pour le type '{error_type}'."
                    )
                    return error_type

        self.logger.warning(
            f"Aucun pattern spécifique n'a matché pour l'erreur: '{error_message_lower}'. Retour du type par défaut 'UNKNOWN_ERROR'."
        )
        return "UNKNOWN_ERROR"

    def _generate_example_fix(
        self, error_type: str, error_message: str, context: Optional[str]
    ) -> str:
        """Génère un exemple de correction spécifique."""

        # Essayer d'extraire l'entité en cause de l'erreur
        entity_match = re.search(r"'(.*?)'", error_message)
        entity = entity_match.group(1) if entity_match else "votre_entite"

        examples = {
            "syntax_error": "Exemple: règle(X) :- condition(X).",
            "atom_error": f"Exemple: définir prédicat({entity}, terme2).",
            "rule_error": "Exemple: tête :- corps1, corps2.",
            "constraint_error": "Exemple: :- condition_violée.",
            "variable_error": "Exemple: Variable avec majuscule, _anonyme.",
            "DECLARATION_ERROR": f"Exemple: `constant {entity}.` ou `predicate {entity}(arg).`",
            "DEFAULT": "Vérifiez la documentation pour la syntaxe correcte.",
        }

        base_example = examples.get(error_type, examples["DEFAULT"])

        # Personnaliser l'exemple basé sur le contexte
        if context and error_type == "syntax_error":
            if "missing" in error_message.lower() and "." in error_message:
                base_example = "Il manque probablement un point à la fin de la règle."

        return base_example

    def _calculate_confidence(self, error_type: str, error_message: str) -> float:
        """Calcule un score de confiance pour l'analyse."""
        # Logique simple de confiance basée sur la spécificité des patterns
        confidence_map = {
            "DECLARATION_ERROR": 0.95,
            "CONSTANT_SYNTAX_ERROR": 0.9,
            "MODAL_SYNTAX_ERROR": 0.88,
            "JSON_STRUCTURE_ERROR": 0.85,
            "atom_error": 0.9,
            "constraint_error": 0.9,
            "variable_error": 0.85,
            "rule_error": 0.8,
            "syntax_error": 0.7,
            "UNKNOWN_ERROR": 0.3,
        }

        base_confidence = confidence_map.get(error_type, 0.6)

        # Ajuster basé sur la longueur et la structure du message
        if "at line" in error_message and error_type == "UNKNOWN_ERROR":
            base_confidence = 0.5  # Probablement une erreur de parsing réelle
        elif len(error_message) > 40 and error_type != "UNKNOWN_ERROR":
            base_confidence += 0.05

        return min(base_confidence, 1.0)

    def generate_bnf_feedback_message(
        self, feedback: TweetyErrorFeedback, attempt_number: int = 1
    ) -> str:
        """
        Génère un message de feedback formaté pour l'agent.

        Args:
            feedback: Feedback structuré à formater
            attempt_number: Numéro de tentative courante

        Returns:
            Message de feedback formaté
        """
        message_parts = [
            f"**ERREUR TWEETY DETECTEE** (Analyse auto - Tentative #{attempt_number})",
            f"**Type d'erreur probable:** {feedback.error_type}",
            f"**Confiance:** {feedback.confidence:.1%}",
            "",
            f"**Erreur originale:**",
            f"```",
            feedback.original_error,
            f"```",
            "",
            f"**Règles BNF pertinentes:**",
        ]

        for rule in feedback.bnf_rules:
            message_parts.append(f"- `{rule}`")

        message_parts.extend(["", f"**Suggestions de correction:**"])

        for i, correction in enumerate(feedback.corrections, 1):
            message_parts.append(f"{i}. {correction}")

        message_parts.extend(
            [
                "",
                f"**Exemple de correction:**",
                f"```prolog",
                feedback.example_fix,
                f"```",
                "",
                f"💡 **Conseil:** Vérifiez la syntaxe Tweety et assurez-vous que tous les éléments respectent la grammaire BNF.",
            ]
        )

        return "\n".join(message_parts)


def analyze_tweety_error(
    error_message: str, attempt_number: int = 1, context: Optional[str] = None
) -> str:
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


def create_bnf_feedback_for_error(
    error_message: str, context: Optional[str] = None, attempt_number: int = 1
) -> str:
    """
    Crée un feedback BNF pour une erreur Tweety.

    Cette fonction est un alias pour analyze_tweety_error pour compatibilité avec les tests.

    Args:
        error_message: Message d'erreur Tweety
        context: Contexte optionnel
        attempt_number: Numéro de tentative courante

    Returns:
        Message de feedback BNF formaté
    """
    return analyze_tweety_error(error_message, attempt_number, context)


# Logger du module
logger = logging.getLogger(__name__)
logger.debug("Module tweety_error_analyzer chargé.")
