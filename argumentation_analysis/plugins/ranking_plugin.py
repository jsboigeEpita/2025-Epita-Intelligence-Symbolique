"""Semantic Kernel plugin for argument ranking via Tweety.

Wraps RankingHandler to expose 7 formal ranking methods
(categorizer, burden, discussion, counting, tuples, strategy, propagation)
as @kernel_function methods for SK agent integration.
"""

import json
import logging
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class RankingPlugin:
    """SK plugin for qualitative argument ranking."""

    @kernel_function(
        name="rank_arguments",
        description="Rank arguments in a Dung framework using formal ranking semantics. "
        "Input: JSON with 'arguments' (list of strings), 'attacks' (list of [src, tgt] pairs), "
        "and optional 'method' (default: 'categorizer').",
    )
    def rank_arguments(self, arguments_json: str) -> str:
        """Rank arguments and return ordered comparisons."""
        from argumentation_analysis.agents.core.logic.ranking_handler import RankingHandler

        data = json.loads(arguments_json)
        handler = RankingHandler()
        result = handler.rank_arguments(
            arguments=data["arguments"],
            attacks=data.get("attacks", []),
            method=data.get("method", "categorizer"),
        )
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="list_ranking_methods",
        description="List available ranking methods for argument evaluation.",
    )
    def list_ranking_methods(self) -> str:
        """Return available ranking method names."""
        from argumentation_analysis.agents.core.logic.ranking_handler import RankingHandler

        return json.dumps(list(RankingHandler.REASONERS.keys()), ensure_ascii=False)
