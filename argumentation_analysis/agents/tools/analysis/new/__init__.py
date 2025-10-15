#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package pour les nouveaux outils d'analyse rhétorique.

Ce package contient de nouveaux outils d'analyse rhétorique qui offrent
des fonctionnalités complémentaires aux outils existants.
"""

from .argument_coherence_evaluator import ArgumentCoherenceEvaluator
from .argument_structure_visualizer import ArgumentStructureVisualizer
from .contextual_fallacy_detector import ContextualFallacyDetector
from .semantic_argument_analyzer import SemanticArgumentAnalyzer

__all__ = [
    "ArgumentCoherenceEvaluator",
    "ArgumentStructureVisualizer",
    "ContextualFallacyDetector",
    "SemanticArgumentAnalyzer",
]
