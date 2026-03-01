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


def register_with_capability_registry(registry):
    """Register quality evaluation capabilities with the Lego registry."""
    registry.register_plugin(
        name="quality_scoring",
        plugin_class=ArgumentQualityEvaluator,
        capabilities=[
            "argument_quality_evaluation",
            "virtue_scoring",
        ],
        metadata={
            "description": (
                "Evaluates argument quality across 9 argumentative virtues "
                "(clarity, relevance, sources, refutation, logic, analogy, "
                "reliability, exhaustiveness, low redundancy)."
            ),
        },
    )
