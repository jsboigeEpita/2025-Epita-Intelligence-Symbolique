"""Semantic Kernel plugin for AGM belief revision via Tweety.

Wraps BeliefRevisionHandler to expose Dalal and Levi revision,
plus kernel contraction, as @kernel_function methods.
"""

import json
import logging
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class BeliefRevisionPlugin:
    """SK plugin for AGM-style belief revision."""

    @kernel_function(
        name="revise_beliefs",
        description="Revise a propositional belief set with new information. "
        "Input: JSON with 'belief_set' (list of PL formula strings), "
        "'new_belief' (PL formula string), "
        "optional 'method' ('dalal' or 'levi', default: 'dalal').",
    )
    def revise_beliefs(self, revision_json: str) -> str:
        """Revise belief set and return updated beliefs."""
        from argumentation_analysis.agents.core.logic.belief_revision_handler import BeliefRevisionHandler

        data = json.loads(revision_json)
        handler = BeliefRevisionHandler()
        result = handler.revise(
            belief_set=data["belief_set"],
            new_belief=data["new_belief"],
            method=data.get("method", "dalal"),
        )
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="contract_beliefs",
        description="Contract a propositional belief set by removing a formula. "
        "Input: JSON with 'belief_set' (list of PL formula strings), "
        "'formula_to_remove' (PL formula string).",
    )
    def contract_beliefs(self, contraction_json: str) -> str:
        """Contract belief set and return reduced beliefs."""
        from argumentation_analysis.agents.core.logic.belief_revision_handler import BeliefRevisionHandler

        data = json.loads(contraction_json)
        handler = BeliefRevisionHandler()
        result = handler.contract(
            belief_set=data["belief_set"],
            formula_to_remove=data["formula_to_remove"],
        )
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="list_revision_methods",
        description="List available belief revision methods.",
    )
    def list_revision_methods(self) -> str:
        """Return available revision method names."""
        return json.dumps(
            ["dalal", "levi"],
            ensure_ascii=False,
        )
