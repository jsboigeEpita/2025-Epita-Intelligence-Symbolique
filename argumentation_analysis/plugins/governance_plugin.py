"""
Governance SK plugin — wraps governance methods as kernel functions.

Provides @kernel_function methods for voting, conflict detection/resolution,
and consensus metrics. Can be registered in any orchestrator agent's kernel
via kernel.add_plugin().

Integrated from student project 2.1.6 (Multiagent Governance Prototype).
"""

import json
from typing import Any, Dict

from semantic_kernel.functions import kernel_function

from argumentation_analysis.agents.core.governance.conflict_resolution import (
    detect_conflicts,
    resolve_conflict,
)
from argumentation_analysis.agents.core.governance.metrics import (
    consensus_rate,
    fairness_index,
    satisfaction,
    summarize_results,
)


class GovernancePlugin:
    """Semantic Kernel plugin for governance and collective decision-making.

    Wraps governance voting methods, conflict resolution, and consensus
    metrics as @kernel_function methods for use through kernel.invoke().
    """

    @kernel_function(
        name="detect_conflicts",
        description=(
            "Detect conflicts between agent positions. Input: JSON object "
            "mapping agent names to their positions. Returns JSON list of "
            "conflicts with agents and conflict_level."
        ),
    )
    def detect_conflicts_fn(self, positions_json: str) -> str:
        """Detect conflicts between agent positions."""
        positions = json.loads(positions_json)
        conflicts = detect_conflicts(positions)
        return json.dumps(conflicts, ensure_ascii=False)

    @kernel_function(
        name="resolve_conflict",
        description=(
            "Resolve a conflict using a mediation strategy "
            "(collaborative, competitive, or arbitration). "
            "Input: JSON conflict object. Returns JSON resolution."
        ),
    )
    def resolve_conflict_fn(
        self, conflict_json: str, strategy: str = "collaborative"
    ) -> str:
        """Resolve a conflict using specified strategy."""
        conflict = json.loads(conflict_json)
        resolution = resolve_conflict(conflict, strategy=strategy)
        return json.dumps(resolution, ensure_ascii=False, default=str)

    @kernel_function(
        name="compute_consensus_metrics",
        description=(
            "Compute consensus rate, fairness, and satisfaction from "
            "voting results. Input: JSON with 'votes' and 'winner' keys."
        ),
    )
    def compute_consensus_metrics(self, results_json: str) -> str:
        """Compute governance metrics from voting results."""
        results = json.loads(results_json)
        metrics = {
            "consensus_rate": consensus_rate(results),
        }
        try:
            metrics["fairness_index"] = fairness_index(results)
        except Exception:
            metrics["fairness_index"] = None
        try:
            metrics["satisfaction"] = satisfaction(results)
        except Exception:
            metrics["satisfaction"] = None
        return json.dumps(metrics)

    @kernel_function(
        name="list_governance_methods",
        description="List all available governance/voting methods.",
    )
    def list_governance_methods(self) -> str:
        """Return available governance methods as JSON."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            GOVERNANCE_METHODS,
        )

        return json.dumps(
            list(GOVERNANCE_METHODS.keys()), ensure_ascii=False
        )
