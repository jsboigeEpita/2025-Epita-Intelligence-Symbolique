"""Modern Sherlock Orchestrator for Spectacular Rhetorical Analysis (#357).

Investigation-style orchestrator wiring >=5 agents via existing invoke
callables. Uses the investigation metaphor:

- Arguments = "claims" by the author/speaker
- Fallacies = "inconsistencies" in the argumentation
- Quality scores = "reliability ratings"
- Counter-arguments = "cross-examination"
- JTMS = belief propagation through evidence chains
- ATMS = hypothesis branching with alternative interpretations
- Narrative synthesis = solution with reasoning chain
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

logger = logging.getLogger(__name__)


@dataclass
class InvestigationStep:
    """Single step in the investigation trace."""

    step: int
    phase: str
    agent: str
    findings: Dict[str, Any] = field(default_factory=dict)
    conclusion: str = ""


@dataclass
class InvestigationResult:
    """Complete investigation result."""

    trace: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_chain: List[str] = field(default_factory=list)
    agents_used: List[str] = field(default_factory=list)
    agent_count: int = 0
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    solution: str = ""
    state_snapshot: Optional[Dict[str, Any]] = None


class SherlockModernOrchestrator:
    """Investigation orchestrator using >=5 existing agents.

    Agents wired (7 total):
      1. ExtractAgent — claim identification
      2. InformalAnalysisAgent — fallacy detection (inconsistencies)
      3. QualityScoringPlugin — reliability assessment
      4. CounterArgumentAgent — cross-examination
      5. JTMS — belief propagation
      6. ATMS — hypothesis branching
      7. NarrativeSynthesisPlugin — solution synthesis

    Works without LLM calls — invoke callables use template-based
    fallbacks when services are unavailable.
    """

    MIN_AGENTS = 5

    def __init__(self, state: Optional[UnifiedAnalysisState] = None):
        self.state = state
        self._trace: List[InvestigationStep] = []
        self._agents: List[str] = []
        self._hypotheses: List[Dict[str, Any]] = []
        self._ctx: Dict[str, Any] = {}

    def _add_step(self, phase: str, agent: str, findings: Dict, conclusion: str):
        self._trace.append(
            InvestigationStep(
                step=len(self._trace) + 1,
                phase=phase,
                agent=agent,
                findings=findings,
                conclusion=conclusion,
            )
        )
        if agent not in self._agents:
            self._agents.append(agent)

    async def investigate(self, discourse: str, context: Optional[Dict] = None) -> InvestigationResult:
        """Run full investigation on discourse text."""
        self._ctx = dict(context or {})
        if self.state is None:
            self.state = UnifiedAnalysisState(discourse)

        await self._phase_extraction(discourse)
        await self._phase_fallacy_detection(discourse)
        await self._phase_quality(discourse)
        await self._phase_cross_examination(discourse)
        await self._phase_belief_tracking(discourse)
        await self._phase_hypothesis_branching(discourse)
        await self._phase_solution_synthesis()

        return self._build_result()

    # ── Phase implementations ───────────────────────────────────────────

    async def _phase_extraction(self, text: str):
        """Phase 1: Identify claims in the discourse."""
        result = await self._invoke_safe(
            "_invoke_extract", text,
            fallback={"extracts": [], "arguments": [], "claims": []},
        )
        self._ctx["phase_extract_output"] = result

        claims = result.get("extracts", result.get("claims", []))
        args = result.get("arguments", [])
        total = len(claims) + len(args)

        self._add_step(
            phase="extraction",
            agent="ExtractAgent",
            findings={"claims_found": len(claims), "arguments_found": len(args)},
            conclusion=f"Identified {total} element(s) for investigation "
            f"({len(claims)} claims, {len(args)} arguments).",
        )

    async def _phase_fallacy_detection(self, text: str):
        """Phase 2: Detect argumentative inconsistencies."""
        result = await self._invoke_safe(
            "_invoke_hierarchical_fallacy", text,
            fallback={"fallacies": {}, "total": 0},
        )
        self._ctx["phase_hierarchical_fallacy_output"] = result

        fallacies = result.get("fallacies", [])
        if isinstance(fallacies, dict):
            count = len(fallacies)
            types = list(set(v.get("type", "") for v in fallacies.values() if isinstance(v, dict)))
        elif isinstance(fallacies, list):
            count = len(fallacies)
            types = list(set(f.get("type", "") for f in fallacies if isinstance(f, dict)))
        else:
            count = result.get("total", 0)
            types = []

        self._add_step(
            phase="fallacy_detection",
            agent="InformalAnalysisAgent",
            findings={"fallacy_count": count, "types": types},
            conclusion=(
                f"Detected {count} argumentative inconsistency(es)"
                + (f" ({', '.join(types[:3])})" if types else "")
                + "."
            ),
        )

    async def _phase_quality(self, text: str):
        """Phase 3: Evaluate argument reliability."""
        result = await self._invoke_safe(
            "_invoke_quality_evaluator", text,
            fallback={"per_argument_scores": {}, "note_finale": 0.0},
        )
        self._ctx["phase_quality_output"] = result

        scores = result.get("per_argument_scores", {})
        overall = result.get("note_finale", 0.0)

        self._add_step(
            phase="quality_evaluation",
            agent="QualityScoringPlugin",
            findings={
                "overall_score": overall,
                "arguments_evaluated": len(scores),
            },
            conclusion=(
                f"Reliability assessment: {overall:.1f}/10 across "
                f"{len(scores)} argument(s)."
            ),
        )

    async def _phase_cross_examination(self, text: str):
        """Phase 4: Cross-examine via counter-arguments."""
        result = await self._invoke_safe(
            "_invoke_counter_argument", text,
            fallback={"counter_arguments": [], "suggested_strategy": {}},
        )
        self._ctx["phase_counter_output"] = result

        counters = result.get("counter_arguments", [])
        strategy = result.get("suggested_strategy", {})
        strat_name = strategy.get("strategy_name", "general") if isinstance(strategy, dict) else "general"

        self._add_step(
            phase="cross_examination",
            agent="CounterArgumentAgent",
            findings={
                "counter_arguments": len(counters),
                "strategy": strat_name,
            },
            conclusion=(
                f"Cross-examination via '{strat_name}' strategy produced "
                f"{len(counters)} counter-argument(s)."
            ),
        )

    async def _phase_belief_tracking(self, text: str):
        """Phase 5: Track belief propagation via JTMS."""
        result = await self._invoke_safe(
            "_invoke_jtms", text,
            fallback={"beliefs": {}, "retraction_chain": []},
        )
        self._ctx["phase_jtms_output"] = result

        beliefs = result.get("beliefs", {})
        retraction_chain = result.get("retraction_chain", [])
        valid = sum(1 for v in beliefs.values() if isinstance(v, dict) and v.get("valid") is True)
        invalid = sum(1 for v in beliefs.values() if isinstance(v, dict) and v.get("valid") is False)

        self._add_step(
            phase="belief_tracking",
            agent="JTMS",
            findings={
                "beliefs_total": len(beliefs),
                "beliefs_valid": valid,
                "beliefs_invalid": invalid,
                "retractions": len(retraction_chain),
            },
            conclusion=(
                f"Evidence chain maintains {len(beliefs)} belief(s): "
                f"{valid} upheld, {invalid} retracted"
                + (f", {len(retraction_chain)} cascade(s)" if retraction_chain else "")
                + "."
            ),
        )

    async def _phase_hypothesis_branching(self, text: str):
        """Phase 6: Branch hypotheses via ATMS."""
        result = await self._invoke_safe(
            "_invoke_atms", text,
            fallback={"atms_contexts": [], "has_contradictions": False},
        )
        self._ctx["phase_atms_output"] = result

        contexts = result.get("atms_contexts", [])
        has_contradictions = result.get("has_contradictions", False)
        coherent = sum(1 for c in contexts if isinstance(c, dict) and c.get("coherent"))
        incoherent = len(contexts) - coherent

        # Build hypothesis descriptions for the investigation
        self._hypotheses = []
        for ctx in contexts:
            if isinstance(ctx, dict):
                self._hypotheses.append({
                    "id": ctx.get("hypothesis_id", "unknown"),
                    "coherent": ctx.get("coherent", False),
                    "assumptions": ctx.get("assumptions", []),
                })

        self._add_step(
            phase="hypothesis_branching",
            agent="ATMS",
            findings={
                "hypotheses_tested": len(contexts),
                "coherent": coherent,
                "incoherent": incoherent,
                "has_contradictions": has_contradictions,
            },
            conclusion=(
                f"Tested {len(contexts)} hypothesis/branch(es): "
                f"{coherent} coherent, {incoherent} incoherent."
            ),
        )

    async def _phase_solution_synthesis(self):
        """Phase 7: Synthesize investigation solution."""
        result = await self._invoke_safe(
            "_invoke_narrative_synthesis", "",
            fallback={"narrative": "", "paragraph_count": 0},
        )
        self._ctx["phase_narrative_synthesis_output"] = result

        narrative = result.get("narrative", "")
        if not narrative:
            narrative = self._build_template_solution()

        self._add_step(
            phase="solution_synthesis",
            agent="NarrativeSynthesisPlugin",
            findings={"paragraph_count": result.get("paragraph_count", 1)},
            conclusion="Investigation synthesis complete.",
        )

        self._solution = narrative

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _invoke_safe(self, func_name: str, text: str, fallback: Dict) -> Dict:
        """Try to invoke a callable, return fallback on failure."""
        try:
            from argumentation_analysis.orchestration import invoke_callables as ic

            func = getattr(ic, func_name, None)
            if func is not None:
                return await func(text, self._ctx)
        except Exception as e:
            logger.debug("invoke_safe(%s) fallback: %s", func_name, e)
        return dict(fallback)

    def _build_template_solution(self) -> str:
        """Build a template investigation solution from trace data."""
        lines = ["Investigation Summary\n"]
        for step in self._trace:
            lines.append(f"Step {step.step} [{step.phase}]: {step.conclusion}")
        if self._hypotheses:
            lines.append("\nHypotheses:")
            for h in self._hypotheses:
                status = "COHERENT" if h.get("coherent") else "INCOHERENT"
                lines.append(f"  - {h['id']}: {status} (assumptions: {h.get('assumptions', [])})")
        return "\n".join(lines)

    def _build_result(self) -> InvestigationResult:
        """Build the final investigation result."""
        trace_dicts = [
            {"step": s.step, "phase": s.phase, "agent": s.agent,
             "findings": s.findings, "conclusion": s.conclusion}
            for s in self._trace
        ]
        reasoning = [s.conclusion for s in self._trace if s.conclusion]
        snapshot = None
        try:
            snapshot = self.state.get_state_snapshot(summarize=True)
        except Exception:
            pass

        return InvestigationResult(
            trace=trace_dicts,
            reasoning_chain=reasoning,
            agents_used=list(self._agents),
            agent_count=len(self._agents),
            hypotheses=list(self._hypotheses),
            solution=getattr(self, "_solution", ""),
            state_snapshot=snapshot,
        )


def build_sherlock_modern_workflow():
    """Build a WorkflowDefinition for the Sherlock Modern investigation.

    Provided as a convenience for the workflow catalog — the
    SherlockModernOrchestrator class is the primary entry point.
    """
    try:
        from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

        return (
            WorkflowBuilder("sherlock_modern")
            .add_phase("extract", capability="fact_extraction")
            .add_phase(
                "hierarchical_fallacy",
                capability="hierarchical_fallacy_detection",
                depends_on=["extract"],
                optional=True,
            )
            .add_phase("quality", capability="argument_quality", depends_on=["extract"])
            .add_phase(
                "counter",
                capability="counter_argument_generation",
                depends_on=["quality"],
            )
            .add_phase(
                "jtms",
                capability="belief_maintenance",
                depends_on=["counter"],
                optional=True,
            )
            .add_phase(
                "atms",
                capability="atms_hypothesis_testing",
                depends_on=["jtms"],
                optional=True,
            )
            .add_phase(
                "narrative_synthesis",
                capability="narrative_synthesis",
                depends_on=["atms"],
                optional=True,
            )
            .build()
        )
    except Exception:
        return None
