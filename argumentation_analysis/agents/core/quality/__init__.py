"""
Quality evaluation agent — integration of student project 2.3.5.

Provides argument quality assessment based on 9 argumentative virtues:
clarte, pertinence, presence_sources, refutation_constructive,
structure_logique, analogie_pertinente, fiabilite_sources,
exhaustivite, redondance_faible.
"""

from argumentation_analysis.agents.core.quality.quality_evaluator import (
    ArgumentQualityEvaluator,
    VERTUES,
    evaluer_argument,
)

__all__ = ["ArgumentQualityEvaluator", "VERTUES", "evaluer_argument"]
