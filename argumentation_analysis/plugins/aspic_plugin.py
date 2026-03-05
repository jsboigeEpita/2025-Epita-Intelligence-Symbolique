"""Semantic Kernel plugin for ASPIC+ structured argumentation via Tweety.

Wraps ASPICHandler to expose structured argumentation analysis
with strict and defeasible inference rules as @kernel_function methods.
"""

import json
import logging
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class ASPICPlugin:
    """SK plugin for ASPIC+ structured argumentation."""

    @kernel_function(
        name="analyze_aspic",
        description="Analyze an ASPIC+ framework with strict and defeasible rules. "
        "Input: JSON with 'strict_rules' (list of {head, body}), "
        "'defeasible_rules' (list of {head, body, name?}), "
        "optional 'axioms' (list of strings), "
        "optional 'reasoner_type' ('simple' or 'directional').",
    )
    def analyze_aspic(self, framework_json: str) -> str:
        """Analyze ASPIC+ framework and return extensions."""
        from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

        data = json.loads(framework_json)
        handler = ASPICHandler()
        result = handler.analyze_aspic_framework(
            strict_rules=data.get("strict_rules", []),
            defeasible_rules=data.get("defeasible_rules", []),
            axioms=data.get("axioms"),
            reasoner_type=data.get("reasoner_type", "simple"),
        )
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="list_aspic_reasoner_types",
        description="List available ASPIC+ reasoner types.",
    )
    def list_aspic_reasoner_types(self) -> str:
        """Return available reasoner type names."""
        return json.dumps(["simple", "directional"], ensure_ascii=False)
