#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plugin de façade pour la consolidation des outils d'analyse rhétorique.
"""

import logging
from typing import Dict, List, Any

from argumentation_analysis.core.interfaces.fallacy_detector import AbstractFallacyDetector

# Imports des outils internes depuis le module 'logic'
from .logic.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from .logic.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from .logic.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
from .logic.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer
from .logic.rhetorical_result_visualizer import EnhancedRhetoricalResultVisualizer
from .logic.nlp_model_manager import nlp_model_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisToolsPlugin:
    """
    Façade unifiée pour accéder à la suite d'outils d'analyse rhétorique.
    """

    def __init__(self, fallacy_detector: AbstractFallacyDetector):
        """
        Initialise le plugin et ses dépendances internes.
        """
        logger.info("Initialisation du AnalysisToolsPlugin...")

        # Charger les modèles NLP une seule fois
        # nlp_model_manager.load_models_sync()

        # Instancier les analyseurs internes
        self.contextual_analyzer = EnhancedContextualFallacyAnalyzer(fallacy_detector=fallacy_detector)
        self.severity_evaluator = EnhancedFallacySeverityEvaluator()
        self.complex_analyzer = EnhancedComplexFallacyAnalyzer(fallacy_detector=fallacy_detector)
        self.result_analyzer = EnhancedRhetoricalResultAnalyzer(
            complex_fallacy_analyzer=self.complex_analyzer,
            severity_evaluator=self.severity_evaluator
        )
        self.visualizer = EnhancedRhetoricalResultVisualizer()
        
        logger.info("AnalysisToolsPlugin initialisé avec succès.")

    def analyze_text(self, text: str, context: str) -> Dict[str, Any]:
        """
        Orchestre une analyse rhétorique complète d'un texte.

        Args:
            text (str): Le texte à analyser.
            context (str): Le contexte de l'analyse.

        Returns:
            Dict[str, Any]: Un dictionnaire de résultats complet.
        """
        logger.info(f"Début de l'analyse du texte dans le contexte : {context}")

        # Les analyseurs actuels travaillent sur une liste d'arguments.
        # Pour une première implémentation simple, nous traitons le texte entier comme un seul argument.
        arguments = [text]

        # 1. Analyse contextuelle des sophismes de base
        contextual_fallacy_results = self.contextual_analyzer.analyze_context(text, context)
        
        # 2. Analyse des sophismes complexes et de la structure
        complex_fallacy_results = self.complex_analyzer.detect_composite_fallacies(arguments, context)
        coherence_results = self.complex_analyzer.analyze_inter_argument_coherence(arguments, context)

        # 3. Assembler les résultats pour l'analyseur final
        raw_results = {
            "complex_fallacy_analysis": complex_fallacy_results,
            "contextual_fallacy_analysis": contextual_fallacy_results,
            "argument_coherence_evaluation": coherence_results
        }

        # 4. Analyse des résultats rhétoriques pour la synthèse
        final_analysis = self.result_analyzer.analyze_rhetorical_results(raw_results, context)

        logger.info("Analyse du texte terminée.")
        return final_analysis

    def evaluate_argument_list(self, arguments: List[str], context: str) -> Dict[str, Any]:
        """
        Analyse une liste d'arguments pré-segmentés.
        
        Implémentation à venir.
        """
        logger.warning("evaluate_argument_list n'est pas encore entièrement implémenté.")
        # L'implémentation sera très similaire à analyze_text mais en sautant la segmentation.
        pass

    def generate_visual_report(self, analysis_results: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """
        Crée les rapports visuels à partir de résultats d'analyse.

        Implémentation à venir.
        """
        logger.warning("generate_visual_report n'est pas encore entièrement implémenté.")
        pass
