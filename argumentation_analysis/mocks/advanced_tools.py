# -*- coding: utf-8 -*-
"""
Ce module fournit des mocks pour les outils d'analyse rhétorique avancée.
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Mock des classes d'outils réels pour simuler leur comportement
class MockEnhancedComplexFallacyAnalyzer:
    def analyze(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug(f"MockEnhancedComplexFallacyAnalyzer.analyze appelée pour le texte (début): {text[:50]}...")
        # Simuler la détection de quelques sophismes complexes
        return [
            {"type": "Mock Complex Fallacy A", "details": "Détails du mock sophisme complexe A", "severity": 0.7, "confidence": 0.85},
            {"type": "Mock Complex Fallacy B", "details": "Détails du mock sophisme complexe B", "severity": 0.5, "confidence": 0.70},
        ]

class MockEnhancedContextualFallacyAnalyzer:
    def analyze(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug(f"MockEnhancedContextualFallacyAnalyzer.analyze appelée pour le texte (début): {text[:50]}...")
        # Simuler la détection de sophismes contextuels
        return [
            {"type": "Mock Contextual Fallacy C", "details": "Détails du mock sophisme contextuel C", "severity": 0.6, "confidence": 0.90},
        ]

class MockEnhancedFallacySeverityEvaluator:
    def evaluate(self, fallacies: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug(f"MockEnhancedFallacySeverityEvaluator.evaluate appelée pour {len(fallacies)} sophismes.")
        # Simuler l'évaluation de la sévérité
        evaluated_fallacies = []
        for fallacy in fallacies:
            updated_fallacy = fallacy.copy()
            updated_fallacy["evaluated_severity"] = updated_fallacy.get("severity", 0.5) * 1.1 # Augmenter un peu la sévérité
            updated_fallacy["severity_evaluation_confidence"] = 0.75
            evaluated_fallacies.append(updated_fallacy)
        return evaluated_fallacies

class MockEnhancedRhetoricalResultAnalyzer:
    def analyze(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("MockEnhancedRhetoricalResultAnalyzer.analyze appelée.")
        # Simuler une analyse globale des résultats
        summary = "Ceci est un résumé simulé de l'analyse rhétorique avancée. "
        num_fallacies = len(analysis_data.get("fallacies_evaluated", []))
        summary += f"{num_fallacies} sophismes évalués ont été trouvés. "
        summary += "L'analyse contextuelle a révélé des aspects intéressants."
        
        return {
            "overall_assessment": "Globalement positif avec quelques points d'amélioration (mock).",
            "summary": summary,
            "confidence_score": 0.88,
            "key_findings": [
                "Mock découverte clé 1: La structure argumentative est solide.",
                "Mock découverte clé 2: Certains sophismes contextuels nécessitent une attention particulière."
            ]
        }

def create_mock_advanced_rhetorical_tools() -> Tuple[Any, Any, Any, Any]:
    """
    Crée et retourne des instances des outils d'analyse rhétorique avancés simulés.

    Ces outils sont des versions mockées des analyseurs réels et sont utilisés
    pour les tests ou lorsque les dépendances réelles ne sont pas disponibles.

    :return: Un tuple contenant les instances des outils simulés:
             (complex_fallacy_analyzer, contextual_fallacy_analyzer,
              fallacy_severity_evaluator, rhetorical_result_analyzer)
    :rtype: Tuple[Any, Any, Any, Any]
    """
    logger.info("Création des instances des outils d'analyse rhétorique avancés simulés (mocks).")
    
    complex_fallacy_analyzer = MockEnhancedComplexFallacyAnalyzer()
    contextual_fallacy_analyzer = MockEnhancedContextualFallacyAnalyzer()
    fallacy_severity_evaluator = MockEnhancedFallacySeverityEvaluator()
    rhetorical_result_analyzer = MockEnhancedRhetoricalResultAnalyzer()
    
    logger.debug("Mocks pour EnhancedComplexFallacyAnalyzer, EnhancedContextualFallacyAnalyzer, EnhancedFallacySeverityEvaluator, EnhancedRhetoricalResultAnalyzer créés.")
    
    return (
        complex_fallacy_analyzer,
        contextual_fallacy_analyzer,
        fallacy_severity_evaluator,
        rhetorical_result_analyzer,
    )