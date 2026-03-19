"""
Macro workflow definitions composing the full argumentation analysis infrastructure.

Provides pre-built end-to-end pipelines:
- Democratech: democratic deliberation with debate-governance loop
- Debate Tournament: multi-round adversarial debate with scoring
- Fact-Check Pipeline: claim verification via JTMS belief maintenance
- Formal Debate: structured argumentation with ASPIC+, dialogue, ranking
- Belief Dynamics: adversarial testing with AGM belief revision
- Argument Strength: formal ranking + probabilistic evaluation
- Formal Verification: 10-phase pipeline using all logic agents + Tweety
- Comprehensive Analysis: 8-phase LLM-only pipeline (no JVM required)
"""

from argumentation_analysis.workflows.comprehensive_analysis import (
    build_comprehensive_analysis_workflow,
    run_comprehensive_analysis,
)
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
from argumentation_analysis.workflows.formal_debate import (
    build_formal_debate_workflow,
    run_formal_debate,
)
from argumentation_analysis.workflows.belief_dynamics import (
    build_belief_dynamics_workflow,
    run_belief_dynamics,
)
from argumentation_analysis.workflows.argument_strength import (
    build_argument_strength_workflow,
    run_argument_strength,
)
from argumentation_analysis.workflows.formal_verification import (
    build_formal_verification_workflow,
    run_formal_verification,
)

__all__ = [
    "build_comprehensive_analysis_workflow",
    "run_comprehensive_analysis",
    "build_democratech_workflow",
    "run_deliberation",
    "build_debate_tournament_workflow",
    "run_tournament",
    "build_fact_check_workflow",
    "run_fact_check",
    "build_formal_debate_workflow",
    "run_formal_debate",
    "build_belief_dynamics_workflow",
    "run_belief_dynamics",
    "build_argument_strength_workflow",
    "run_argument_strength",
    "build_formal_verification_workflow",
    "run_formal_verification",
]
