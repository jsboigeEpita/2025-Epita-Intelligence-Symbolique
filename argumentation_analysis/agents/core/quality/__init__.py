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

# #1842: no register_with_capability_registry here. The quality capability
# table lives on the production surface (registry_setup.setup_registry);
# this module's former second table was only ever called by tests.
