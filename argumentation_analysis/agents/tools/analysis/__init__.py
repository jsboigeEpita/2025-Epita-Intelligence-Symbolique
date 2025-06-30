"""
Package d'outils d'analyse rhétorique.

Ce package fournit des outils pour l'analyse rhétorique, comme l'analyse contextuelle
des sophismes, l'évaluation de la gravité des sophismes, l'analyse des sophismes
complexes, l'analyse des résultats et la visualisation des résultats.
"""

from .contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from .fallacy_severity_evaluator import FallacySeverityEvaluator
from .complex_fallacy_analyzer import ComplexFallacyAnalyzer
from .rhetorical_result_visualizer import RhetoricalResultVisualizer

__all__ = [
    'ContextualFallacyAnalyzer',
    'FallacySeverityEvaluator',
    'ComplexFallacyAnalyzer',
    'RhetoricalResultAnalyzer',
    'RhetoricalResultVisualizer'
]