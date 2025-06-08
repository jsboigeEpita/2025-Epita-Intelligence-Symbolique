<<<<<<< MAIN
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
    confidence: float


class TweetyErrorAnalyzer:
    """
    Analyseur intelligent des erreurs TweetyProject avec generation de feedback BNF.
    
    Cette classe analyse les messages d'erreur Tweety et génère un feedback constructif
    basé sur les règles BNF pour guider les agents vers des corrections appropriées.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TweetyErrorAnalyzer")
        
        # Patterns d'erreurs Tweety communes
        self.error_patterns = {
            'predicate_not_declared': {
                'pattern': r"Predicate '([^']+)' has not been declared",
                'type': 'DECLARATION_ERROR',
                'confidence': 0.95
            },
            'constant_in_formula': {
                'pattern': r"constant\([a-z_][a-z0-9_]*\)",
                'type': 'CONSTANT_SYNTAX_ERROR',
                'confidence': 0.90
            },
            'modal_syntax_error': {
                'pattern': r"(Expected|Unexpected).*(modal|formula)",
                'type': 'MODAL_SYNTAX_ERROR',
                'confidence': 0.85
            },
            'json_structure_error': {
                'pattern': r"JSON.*invalid|missing.*key",
                'type': 'JSON_STRUCTURE_ERROR',
                'confidence': 0.80
            }
        }
        
        # Règles BNF pour la syntaxe Tweety modale
        self.bnf_rules = {
            'DECLARATION_ERROR': [
                "RÈGLE BNF TWEETY: Déclaration de prédicat UNIQUEMENT après 'constant'",
                "FORMAT VALIDE: 'constant predicate_name' puis 'prop(predicate_name)'",
                "INTERDICTION: Ne jamais utiliser 'constant predicate_name' dans les formules modales",
                "UTILISATION: Dans les formules, utiliser SEULEMENT 'predicate_name' (sans 'constant')"
            ],
            'CONSTANT_SYNTAX_ERROR': [
                "RÈGLE BNF TWEETY: Séparer déclarations et formules modales",
                "SECTION 1: Déclarations des constantes avec 'constant name'",
                "SECTION 2: Déclarations propositionnelles avec 'prop(name)'", 
                "SECTION 3: Formules modales utilisant SEULEMENT les noms déclarés"
            ],
            'MODAL_SYNTAX_ERROR': [
                "RÈGLE BNF TWEETY: Opérateurs modaux [] (nécessité) et <> (possibilité)",
                "CONNECTEURS LOGIQUES: ! (negation), && (et), || (ou), => (implication)", 
                "SYNTAXE FORMULE: Utiliser SEULEMENT les prédicats déclarés avec prop()",
                "PARENTHÈSES: Obligatoires pour les expressions complexes"
            ],
            'JSON_STRUCTURE_ERROR': [
                "STRUCTURE JSON REQUISE: {\"propositions\": [...], \"modal_formulas\": [...]}",
                "PROPOSITIONS: Liste des noms de prédicats en snake_case",
                "FORMULES MODALES: Liste des formules utilisant [], <> et les prédicats déclarés",
                "COHÉRENCE: Chaque prédicat dans les formules doit être dans 'propositions'"
            ]
        }
        
    def analyze_error(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> TweetyErrorFeedback:
        """
        Analyse un message d'erreur Tweety et génère un feedback BNF constructif.
        
        Args:
            error_message: Message d'erreur de TweetyProject
            context: Contexte optionnel (tentative, agent, etc.)
            
        Returns:
            TweetyErrorFeedback avec les règles BNF et corrections spécifiques
        """
        self.logger.info(f"Analyse d'erreur Tweety: {error_message}")
        
        # Identifier le type d'erreur
        error_type, matched_pattern, confidence = self._identify_error_type(error_message)
        
        # Générer les règles BNF spécifiques
        bnf_rules = self.bnf_rules.get(error_type, ["Erreur non reconnue - application des règles générales"])
        
        # Générer les corrections spécifiques
        corrections = self._generate_specific_corrections(error_message, error_type, matched_pattern)
        
        # Créer un exemple de correction
        example_fix = self._create_example_fix(error_message, error_type, matched_pattern)
        
        feedback = TweetyErrorFeedback(
            error_type=error_type,
            original_error=error_message,
            bnf_rules=bnf_rules,
            corrections=corrections,
            example_fix=example_fix,
            confidence=confidence
        )
        
        self.logger.info(f"Feedback généré: {error_type} (confiance: {confidence:.2f})")
        return feedback
    
    def _identify_error_type(self, error_message: str) -> Tuple[str, Optional[str], float]:
        """Identifie le type d'erreur basé sur les patterns connus."""
        for error_name, error_config in self.error_patterns.items():
            pattern = error_config['pattern']
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return error_config['type'], match.group(0), error_config['confidence']
        
        # Erreur non reconnue
        return 'UNKNOWN_ERROR', None, 0.5
    
    def _generate_specific_corrections(self, error_message: str, error_type: str, matched_pattern: Optional[str]) -> List[str]:
        """Génère des corrections spécifiques basées sur l'erreur."""
        corrections = []
        
        if error_type == 'DECLARATION_ERROR' and matched_pattern:
            # Extraire le nom du prédicat problématique
            predicate_match = re.search(r"Predicate '([^']+)' has not been declared", error_message)
            if predicate_match:
                problematic_predicate = predicate_match.group(1)
                
                # Analyser si c'est un problème de "constant" dans la formule
                if problematic_predicate.startswith('constant'):
                    clean_predicate = problematic_predicate.replace('constant', '')
                    corrections.extend([
                        f"ERREUR DÉTECTÉE: '{problematic_predicate}' contient 'constant' dans une formule",
                        f"CORRECTION: Utiliser '{clean_predicate}' au lieu de '{problematic_predicate}'",
                        f"ÉTAPES: 1) Déclarer 'constant {clean_predicate}' 2) Déclarer 'prop({clean_predicate})' 3) Utiliser '{clean_predicate}' dans les formules"
                    ])
                else:
                    corrections.extend([
                        f"ERREUR DÉTECTÉE: Prédicat '{problematic_predicate}' utilisé sans déclaration",
                        f"CORRECTION: Ajouter 'constant {problematic_predicate}' et 'prop({problematic_predicate})' en début",
                        f"VÉRIFICATION: S'assurer que '{problematic_predicate}' est dans la liste 'propositions' du JSON"
                    ])
        
        elif error_type == 'CONSTANT_SYNTAX_ERROR':
            corrections.extend([
                "ERREUR DÉTECTÉE: Confusion entre déclarations et utilisation des constantes",
                "CORRECTION: Séparer clairement les sections du fichier Tweety",
                "STRUCTURE: 1) constant declarations 2) prop() declarations 3) modal formulas"
            ])
            
        elif error_type == 'MODAL_SYNTAX_ERROR':
            corrections.extend([
                "ERREUR DÉTECTÉE: Syntaxe modale incorrecte", 
                "CORRECTION: Vérifier les opérateurs modaux [] et <> et les connecteurs logiques",
                "VALIDATION: S'assurer que tous les prédicats utilisés sont déclarés"
            ])
            
        elif error_type == 'JSON_STRUCTURE_ERROR':
            corrections.extend([
                "ERREUR DÉTECTÉE: Structure JSON invalide ou incomplète",
                "CORRECTION: Vérifier la présence des clés 'propositions' et 'modal_formulas'",
                "COHÉRENCE: Tous les prédicats des formules doivent être dans 'propositions'"
            ])
        
        return corrections
    
    def _create_example_fix(self, error_message: str, error_type: str, matched_pattern: Optional[str]) -> str:
        """Crée un exemple concret de correction."""
        if error_type == 'DECLARATION_ERROR' and matched_pattern:
            predicate_match = re.search(r"Predicate '([^']+)' has not been declared", error_message)
            if predicate_match:
                problematic_predicate = predicate_match.group(1)
                if problematic_predicate.startswith('constant'):
                    clean_predicate = problematic_predicate.replace('constant', '')
                    return f"""EXEMPLE DE CORRECTION:
[INCORRECT] Utiliser 'constant{clean_predicate}' dans une formule modale
[CORRECT]
   JSON: {{"propositions": ["{clean_predicate}"], "modal_formulas": ["[]{clean_predicate}"]}}
   TWEETY: constant {clean_predicate}
           prop({clean_predicate})
           []{clean_predicate}"""
                else:
                    return f"""EXEMPLE DE CORRECTION:
[INCORRECT] Utiliser '{problematic_predicate}' sans déclaration
[CORRECT]
   JSON: {{"propositions": ["{problematic_predicate}"], "modal_formulas": ["[]{problematic_predicate}"]}}
   TWEETY: constant {problematic_predicate}
           prop({problematic_predicate})
           []{problematic_predicate}"""
        
        return "Consulter les règles BNF ci-dessus pour la syntaxe correcte."
    
    def generate_bnf_feedback_message(self, feedback: TweetyErrorFeedback, attempt_number: int = 1) -> str:
        """
        Génère un message de feedback BNF formaté pour l'agent.
        
        Args:
            feedback: Feedback d'erreur structuré
            attempt_number: Numéro de la tentative courante
            
        Returns:
            Message de feedback formaté pour guider l'agent
        """
        message = f"""
[ERREUR TWEETY DETECTEE] (Tentative {attempt_number}) - FEEDBACK BNF CONSTRUCTIF

ERREUR ORIGINALE: {feedback.original_error}
TYPE D'ERREUR: {feedback.error_type} (Confiance: {feedback.confidence:.0%})

[REGLES BNF] POUR TWEETY MODAL LOGIC:
"""
        for i, rule in enumerate(feedback.bnf_rules, 1):
            message += f"   {i}. {rule}\n"
        
        message += f"""
[CORRECTIONS RECOMMANDEES]:
"""
        for i, correction in enumerate(feedback.corrections, 1):
            message += f"   {i}. {correction}\n"
        
        message += f"""
[EXEMPLE] {feedback.example_fix}

[INSTRUCTIONS] POUR LA PROCHAINE TENTATIVE:
   1. Revoir la structure JSON selon les règles BNF ci-dessus
   2. S'assurer que tous les prédicats sont correctement déclarés
   3. Éviter les mots-clés 'constant' dans les formules modales
   4. Utiliser SEULEMENT les prédicats de la liste 'propositions'

Cette analyse vous guide vers une correction spécifique. Utilisez ces informations
pour ajuster votre génération lors de la prochaine tentative.
"""
        return message


def create_bnf_feedback_for_error(error_message: str, attempt_number: int = 1, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Fonction utilitaire pour créer rapidement un feedback BNF à partir d'une erreur.
    
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

=======
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
    confidence: float


class TweetyErrorAnalyzer:
    """
    Analyseur intelligent des erreurs TweetyProject avec generation de feedback BNF.
    
    Cette classe analyse les messages d'erreur Tweety et génère un feedback constructif
    basé sur les règles BNF pour guider les agents vers des corrections appropriées.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TweetyErrorAnalyzer")
        
        # Patterns d'erreurs Tweety communes
        self.error_patterns = {
            'predicate_not_declared': {
                'pattern': r"Predicate '([^']+)' has not been declared",
                'type': 'DECLARATION_ERROR',
                'confidence': 0.95
            },
            'constant_in_formula': {
                'pattern': r"constant\([a-z_][a-z0-9_]*\)",
                'type': 'CONSTANT_SYNTAX_ERROR',
                'confidence': 0.90
            },
            'modal_syntax_error': {
                'pattern': r"(Expected|Unexpected).*(modal|formula)",
                'type': 'MODAL_SYNTAX_ERROR',
                'confidence': 0.85
            },
            'json_structure_error': {
                'pattern': r"JSON.*invalid|missing.*key",
                'type': 'JSON_STRUCTURE_ERROR',
                'confidence': 0.80
            }
        }
        
        # Règles BNF pour la syntaxe Tweety modale
        self.bnf_rules = {
            'DECLARATION_ERROR': [
                "RÈGLE BNF TWEETY: Déclaration de prédicat UNIQUEMENT après 'constant'",
                "FORMAT VALIDE: 'constant predicate_name' puis 'prop(predicate_name)'",
                "INTERDICTION: Ne jamais utiliser 'constant predicate_name' dans les formules modales",
                "UTILISATION: Dans les formules, utiliser SEULEMENT 'predicate_name' (sans 'constant')"
            ],
            'CONSTANT_SYNTAX_ERROR': [
                "RÈGLE BNF TWEETY: Séparer déclarations et formules modales",
                "SECTION 1: Déclarations des constantes avec 'constant name'",
                "SECTION 2: Déclarations propositionnelles avec 'prop(name)'", 
                "SECTION 3: Formules modales utilisant SEULEMENT les noms déclarés"
            ],
            'MODAL_SYNTAX_ERROR': [
                "RÈGLE BNF TWEETY: Opérateurs modaux [] (nécessité) et <> (possibilité)",
                "CONNECTEURS LOGIQUES: ! (negation), && (et), || (ou), => (implication)", 
                "SYNTAXE FORMULE: Utiliser SEULEMENT les prédicats déclarés avec prop()",
                "PARENTHÈSES: Obligatoires pour les expressions complexes"
            ],
            'JSON_STRUCTURE_ERROR': [
                "STRUCTURE JSON REQUISE: {\"propositions\": [...], \"modal_formulas\": [...]}",
                "PROPOSITIONS: Liste des noms de prédicats en snake_case",
                "FORMULES MODALES: Liste des formules utilisant [], <> et les prédicats déclarés",
                "COHÉRENCE: Chaque prédicat dans les formules doit être dans 'propositions'"
            ]
        }
        
    def analyze_error(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> TweetyErrorFeedback:
        """
        Analyse un message d'erreur Tweety et génère un feedback BNF constructif.
        
        Args:
            error_message: Message d'erreur de TweetyProject
            context: Contexte optionnel (tentative, agent, etc.)
            
        Returns:
            TweetyErrorFeedback avec les règles BNF et corrections spécifiques
        """
        self.logger.info(f"Analyse d'erreur Tweety: {error_message}")
        
        # Identifier le type d'erreur
        error_type, matched_pattern, confidence = self._identify_error_type(error_message)
        
        # Générer les règles BNF spécifiques
        bnf_rules = self.bnf_rules.get(error_type, ["Erreur non reconnue - application des règles générales"])
        
        # Générer les corrections spécifiques
        corrections = self._generate_specific_corrections(error_message, error_type, matched_pattern)
        
        # Créer un exemple de correction
        example_fix = self._create_example_fix(error_message, error_type, matched_pattern)
        
        feedback = TweetyErrorFeedback(
            error_type=error_type,
            original_error=error_message,
            bnf_rules=bnf_rules,
            corrections=corrections,
            example_fix=example_fix,
            confidence=confidence
        )
        
        self.logger.info(f"Feedback généré: {error_type} (confiance: {confidence:.2f})")
        return feedback
    
    def _identify_error_type(self, error_message: str) -> Tuple[str, Optional[str], float]:
        """Identifie le type d'erreur basé sur les patterns connus."""
        for error_name, error_config in self.error_patterns.items():
            pattern = error_config['pattern']
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return error_config['type'], match.group(0), error_config['confidence']
        
        # Erreur non reconnue
        return 'UNKNOWN_ERROR', None, 0.5
    
    def _generate_specific_corrections(self, error_message: str, error_type: str, matched_pattern: Optional[str]) -> List[str]:
        """Génère des corrections spécifiques basées sur l'erreur."""
        corrections = []
        
        if error_type == 'DECLARATION_ERROR' and matched_pattern:
            # Extraire le nom du prédicat problématique
            predicate_match = re.search(r"Predicate '([^']+)' has not been declared", error_message)
            if predicate_match:
                problematic_predicate = predicate_match.group(1)
                
                # Analyser si c'est un problème de "constant" dans la formule
                if problematic_predicate.startswith('constant'):
                    clean_predicate = problematic_predicate.replace('constant', '')
                    corrections.extend([
                        f"ERREUR DÉTECTÉE: '{problematic_predicate}' contient 'constant' dans une formule",
                        f"CORRECTION: Utiliser '{clean_predicate}' au lieu de '{problematic_predicate}'",
                        f"ÉTAPES: 1) Déclarer 'constant {clean_predicate}' 2) Déclarer 'prop({clean_predicate})' 3) Utiliser '{clean_predicate}' dans les formules"
                    ])
                else:
                    corrections.extend([
                        f"ERREUR DÉTECTÉE: Prédicat '{problematic_predicate}' utilisé sans déclaration",
                        f"CORRECTION: Ajouter 'constant {problematic_predicate}' et 'prop({problematic_predicate})' en début",
                        f"VÉRIFICATION: S'assurer que '{problematic_predicate}' est dans la liste 'propositions' du JSON"
                    ])
        
        elif error_type == 'CONSTANT_SYNTAX_ERROR':
            corrections.extend([
                "ERREUR DÉTECTÉE: Confusion entre déclarations et utilisation des constantes",
                "CORRECTION: Séparer clairement les sections du fichier Tweety",
                "STRUCTURE: 1) constant declarations 2) prop() declarations 3) modal formulas"
            ])
            
        elif error_type == 'MODAL_SYNTAX_ERROR':
            corrections.extend([
                "ERREUR DÉTECTÉE: Syntaxe modale incorrecte", 
                "CORRECTION: Vérifier les opérateurs modaux [] et <> et les connecteurs logiques",
                "VALIDATION: S'assurer que tous les prédicats utilisés sont déclarés"
            ])
            
        elif error_type == 'JSON_STRUCTURE_ERROR':
            corrections.extend([
                "ERREUR DÉTECTÉE: Structure JSON invalide ou incomplète",
                "CORRECTION: Vérifier la présence des clés 'propositions' et 'modal_formulas'",
                "COHÉRENCE: Tous les prédicats des formules doivent être dans 'propositions'"
            ])
        
        return corrections
    
    def _create_example_fix(self, error_message: str, error_type: str, matched_pattern: Optional[str]) -> str:
        """Crée un exemple concret de correction."""
        if error_type == 'DECLARATION_ERROR' and matched_pattern:
            predicate_match = re.search(r"Predicate '([^']+)' has not been declared", error_message)
            if predicate_match:
                problematic_predicate = predicate_match.group(1)
                if problematic_predicate.startswith('constant'):
                    clean_predicate = problematic_predicate.replace('constant', '')
                    return f"""EXEMPLE DE CORRECTION:
[INCORRECT] Utiliser 'constant{clean_predicate}' dans une formule modale
[CORRECT]
   JSON: {{"propositions": ["{clean_predicate}"], "modal_formulas": ["[]{clean_predicate}"]}}
   TWEETY: constant {clean_predicate}
           prop({clean_predicate})
           []{clean_predicate}"""
                else:
                    return f"""EXEMPLE DE CORRECTION:
[INCORRECT] Utiliser '{problematic_predicate}' sans déclaration
[CORRECT]
   JSON: {{"propositions": ["{problematic_predicate}"], "modal_formulas": ["[]{problematic_predicate}"]}}
   TWEETY: constant {problematic_predicate}
           prop({problematic_predicate})
           []{problematic_predicate}"""
        
        return "Consulter les règles BNF ci-dessus pour la syntaxe correcte."
    
    def generate_bnf_feedback_message(self, feedback: TweetyErrorFeedback, attempt_number: int = 1) -> str:
        """
        Génère un message de feedback BNF formaté pour l'agent.
        
        Args:
            feedback: Feedback d'erreur structuré
            attempt_number: Numéro de la tentative courante
            
        Returns:
            Message de feedback formaté pour guider l'agent
        """
        message = f"""
[ERREUR TWEETY DETECTEE] (Tentative {attempt_number}) - FEEDBACK BNF CONSTRUCTIF

ERREUR ORIGINALE: {feedback.original_error}
TYPE D'ERREUR: {feedback.error_type} (Confiance: {feedback.confidence:.0%})

[REGLES BNF] POUR TWEETY MODAL LOGIC:
"""
        for i, rule in enumerate(feedback.bnf_rules, 1):
            message += f"   {i}. {rule}\n"
        
        message += f"""
[CORRECTIONS RECOMMANDEES]:
"""
        for i, correction in enumerate(feedback.corrections, 1):
            message += f"   {i}. {correction}\n"
        
        message += f"""
[EXEMPLE] {feedback.example_fix}

[INSTRUCTIONS] POUR LA PROCHAINE TENTATIVE:
   1. Revoir la structure JSON selon les règles BNF ci-dessus
   2. S'assurer que tous les prédicats sont correctement déclarés
   3. Éviter les mots-clés 'constant' dans les formules modales
   4. Utiliser SEULEMENT les prédicats de la liste 'propositions'

Cette analyse vous guide vers une correction spécifique. Utilisez ces informations
pour ajuster votre génération lors de la prochaine tentative.
"""
        return message


def create_bnf_feedback_for_error(error_message: str, attempt_number: int = 1, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Fonction utilitaire pour créer rapidement un feedback BNF à partir d'une erreur.
    
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
>>>>>>> BACKUP
