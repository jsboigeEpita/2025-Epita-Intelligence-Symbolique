"""
Formal Verification Workflow (#71) — Full pipeline using all logic agents + Tweety handlers.

10-phase pipeline:
  1. Extraction: heuristic claim extraction from text
  2. PL Analysis: propositional logic satisfiability check
  3. FOL Analysis: first-order logic consistency check (parallel with PL)
  4. Modal Analysis: modal logic necessity/possibility detection (optional)
  5. Dung Extensions: argument framework + extension computation
  6. ASPIC+ Analysis: structured argumentation via ASPIC+
  7. Ranking: formal argument ranking semantics
  8. JTMS Tracking: belief maintenance for consistency monitoring
  9. Belief Revision: AGM-style revision if inconsistency detected (conditional)
 10. Formal Synthesis: aggregate all formal results into unified validity report

Use cases: legal contract analysis, formal spec verification, scientific reasoning audit.
"""

from typing import Dict, Any

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)


DEFAULT_INCONSISTENCY_THRESHOLD = 0.5


def _has_inconsistency(ctx: Dict[str, Any]) -> bool:
    """Trigger belief revision only if upstream phases found inconsistency."""
    # Check FOL analysis
    fol_output = ctx.get("phase_fol_analysis_output")
    if isinstance(fol_output, dict) and fol_output.get("consistent") is False:
        return True
    # Check PL analysis
    pl_output = ctx.get("phase_pl_analysis_output")
    if isinstance(pl_output, dict) and pl_output.get("satisfiable") is False:
        return True
    # Check JTMS for retracted beliefs
    jtms_output = ctx.get("phase_jtms_tracking_output")
    if isinstance(jtms_output, dict):
        beliefs = jtms_output.get("beliefs", {})
        if isinstance(beliefs, dict):
            retracted = sum(1 for v in beliefs.values() if v == "False")
            if retracted > 0:
                return True
    return False


def build_formal_verification_workflow() -> WorkflowDefinition:
    """Build the 10-phase formal verification workflow.

    Phase dependencies form a diamond pattern:
        extraction
         /     \\
    pl_analysis  fol_analysis
         |          |    \\
         |     modal(opt) jtms_tracking
         \\       /           |
      dung_analysis    belief_revision(cond)
       /        \\          /
    aspic    ranking       /
       \\       |         /
      formal_synthesis
    """
    return (
        WorkflowBuilder("formal_verification")
        .add_phase("extraction", capability="fact_extraction")
        .add_phase(
            "pl_analysis",
            capability="propositional_logic",
            depends_on=["extraction"],
        )
        .add_phase(
            "fol_analysis",
            capability="fol_reasoning",
            depends_on=["extraction"],
        )
        .add_phase(
            "modal_analysis",
            capability="modal_logic",
            depends_on=["fol_analysis"],
            optional=True,
        )
        .add_phase(
            "dung_analysis",
            capability="dung_extensions",
            depends_on=["pl_analysis"],
        )
        .add_phase(
            "aspic_analysis",
            capability="aspic_plus_reasoning",
            depends_on=["dung_analysis"],
        )
        .add_phase(
            "ranking",
            capability="ranking_semantics",
            depends_on=["dung_analysis"],
        )
        .add_phase(
            "jtms_tracking",
            capability="belief_maintenance",
            depends_on=["fol_analysis"],
        )
        .add_conditional_phase(
            "belief_revision",
            capability="belief_revision",
            condition=_has_inconsistency,
            depends_on=["jtms_tracking"],
        )
        .add_phase(
            "formal_synthesis",
            capability="formal_synthesis",
            depends_on=["ranking", "aspic_analysis", "belief_revision"],
        )
        .set_metadata("domain", "formal_verification")
        .set_metadata("version", "1.0")
        .set_metadata("issue", "#71")
        .build()
    )


async def run_formal_verification(text: str, **kwargs) -> Dict[str, Any]:
    """Convenience wrapper for running the formal verification workflow."""
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    return await run_unified_analysis(
        text, workflow_name="formal_verification", **kwargs
    )
