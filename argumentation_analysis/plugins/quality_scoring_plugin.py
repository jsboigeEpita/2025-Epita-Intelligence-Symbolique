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
        description=(
            "Get the overall quality score (0-9) for an argument text."
        ),
    )
    def get_quality_score(self, text: str) -> str:
        """Return just the overall quality score as JSON."""
        result = self.evaluator.evaluate(text)
        return json.dumps({
            "note_finale": result["note_finale"],
            "note_moyenne": result["note_moyenne"],
        })

    @kernel_function(
        name="list_virtues",
        description="List the 9 argumentative virtues used for evaluation.",
    )
    def list_virtues(self) -> str:
        """Return the list of 9 virtues as JSON."""
        return json.dumps(VERTUES, ensure_ascii=False)
