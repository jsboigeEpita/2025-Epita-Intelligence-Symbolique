"""
Quality scoring SK plugin — wraps ArgumentQualityEvaluator as kernel functions.

Provides @kernel_function methods for evaluating argument quality
across 9 argumentative virtues. Can be registered in any agent's kernel
via kernel.add_plugin().

Integrated from student project 2.3.5 (Argument Quality Evaluation).
"""

import json
from typing import Any, Dict

from semantic_kernel.functions import kernel_function

from argumentation_analysis.agents.core.quality.quality_evaluator import (
    ArgumentQualityEvaluator,
    VERTUES,
)


class QualityScoringPlugin:
    """Semantic Kernel plugin for argument quality evaluation.

    Wraps ArgumentQualityEvaluator's 9-virtue scoring system as
    @kernel_function methods for use through kernel.invoke().
    """

    def __init__(self):
        self.evaluator = ArgumentQualityEvaluator()

    @kernel_function(
        name="evaluate_argument_quality",
        description=(
            "Evaluate argument quality across 9 virtues (clarity, relevance, "
            "sources, refutation, logical structure, analogy, source reliability, "
            "exhaustiveness, low redundancy). Returns JSON with scores."
        ),
    )
    def evaluate_argument_quality(self, text: str) -> str:
        """Evaluate argument text and return quality scores as JSON."""
        result = self.evaluator.evaluate(text)
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="get_quality_score",
        description=("Get the overall quality score (0-9) for an argument text."),
    )
    def get_quality_score(self, text: str) -> str:
        """Return just the overall quality score as JSON."""
        result = self.evaluator.evaluate(text)
        return json.dumps(
            {
                "note_finale": result["note_finale"],
                "note_moyenne": result["note_moyenne"],
            }
        )

    @kernel_function(
        name="evaluate_with_cross_kb_context",
        description=(
            "Evaluate argument quality with cross-KB context for LLM-enriched scoring. "
            "Takes the argument text and optional JSON context (detected fallacies, "
            "formal inconsistencies). Returns heuristic base scores PLUS adjustment "
            "recommendations based on cross-KB findings. The agent should use its own "
            "reasoning to produce final adjusted scores."
        ),
    )
    def evaluate_with_cross_kb_context(
        self, text: str, cross_kb_context: str = "{}"
    ) -> str:
        """Evaluate with cross-KB enrichment context.

        Returns base heuristic scores plus adjustment recommendations
        informed by fallacies, formal results, and other agent findings.
        The calling agent (QualityAgent) applies its LLM reasoning to
        produce the final adjusted scores.
        """
        base_result = self.evaluator.evaluate(text)

        try:
            context = json.loads(cross_kb_context)
        except (json.JSONDecodeError, TypeError):
            context = {}

        # Build adjustment recommendations based on cross-KB context
        adjustments = []
        fallacies = context.get("fallacies", [])
        formal_issues = context.get("formal_inconsistencies", [])

        if fallacies:
            adjustments.append(
                f"DETECTED {len(fallacies)} FALLACIES — reduce 'structure_logique' "
                f"and 'fiabilite_sources' by 2-3 points for affected arguments. "
                f"Fallacy types: {', '.join(f.get('type', '?') for f in fallacies if isinstance(f, dict))}"
            )
        if formal_issues:
            adjustments.append(
                f"FORMAL INCONSISTENCIES detected — reduce 'coherence' and "
                f"'structure_logique' by 1-2 points. Issues: {len(formal_issues)}"
            )

        enriched = {
            "base_heuristic_scores": base_result,
            "cross_kb_adjustments": adjustments,
            "instruction": (
                "Use these base scores as a starting point. Apply your LLM reasoning "
                "to adjust scores based on the cross-KB context. Report both the "
                "original heuristic scores AND your adjusted scores with justifications."
            ),
        }
        return json.dumps(enriched, ensure_ascii=False)

    @kernel_function(
        name="list_virtues",
        description="List the 9 argumentative virtues used for evaluation.",
    )
    def list_virtues(self) -> str:
        """Return the list of 9 virtues as JSON."""
        return json.dumps(VERTUES, ensure_ascii=False)
