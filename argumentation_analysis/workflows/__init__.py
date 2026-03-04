"""
Macro workflow definitions composing the full argumentation analysis infrastructure.

Provides pre-built end-to-end pipelines:
- Democratech: democratic deliberation with debate-governance loop
- Debate Tournament: multi-round adversarial debate with scoring
- Fact-Check Pipeline: claim verification via JTMS belief maintenance
"""

from argumentation_analysis.workflows.democratech import (
    build_democratech_workflow,
    run_deliberation,
)
from argumentation_analysis.workflows.debate_tournament import (
    build_debate_tournament_workflow,
    run_tournament,
)
from argumentation_analysis.workflows.fact_check_pipeline import (
    build_fact_check_workflow,
    run_fact_check,
)

__all__ = [
    "build_democratech_workflow",
    "run_deliberation",
    "build_debate_tournament_workflow",
    "run_tournament",
    "build_fact_check_workflow",
    "run_fact_check",
]
