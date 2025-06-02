#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package pour les outils d'analyse rhétorique améliorés.

Ce package contient des versions améliorées des outils d'analyse rhétorique
qui offrent des fonctionnalités plus avancées et des analyses plus détaillées.
"""

from .rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer
from .complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from .fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
from .contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer

__all__ = [
    'EnhancedRhetoricalResultAnalyzer',
    'EnhancedComplexFallacyAnalyzer',
    'EnhancedFallacySeverityEvaluator',
    'EnhancedContextualFallacyAnalyzer'
]