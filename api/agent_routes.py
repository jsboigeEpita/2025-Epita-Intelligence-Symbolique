"""REST endpoints for pipeline agent capabilities.

Exposes debate, counter-argument, quality evaluation, and governance
simulation as standalone API endpoints.

Routes:
    POST /api/v1/agents/quality          — Evaluate argument quality (9 virtues)
    POST /api/v1/agents/counter-arguments — Generate counter-arguments
    POST /api/v1/agents/debate           — Run adversarial debate
    POST /api/v1/agents/governance       — Run governance simulation
    POST /api/v1/agents/full-analysis    — Run full unified pipeline
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class TextRequest(BaseModel):
    """Simple text input for analysis."""

    text: str = Field(..., min_length=10, description="Text to analyze")
    max_text: int = Field(5000, ge=100, le=50000, description="Max chars to process")


class QualityScore(BaseModel):
    argument: str
    scores: Dict[str, float] = {}
    overall: float = 0.0


class QualityResponse(BaseModel):
    scores: List[QualityScore] = []
    aggregate: Dict[str, float] = {}
    duration_seconds: float = 0.0


class CounterArgument(BaseModel):
    target: str = ""
    strategy: str = ""
    counter: str = ""


class CounterArgumentResponse(BaseModel):
    parsed: Dict[str, Any] = {}
    strategy: Dict[str, Any] = {}
    llm_counter_arguments: List[CounterArgument] = []
    duration_seconds: float = 0.0


class DebateExchange(BaseModel):
    agent_a_point: str = ""
    agent_b_rebuttal: str = ""
    judge_note: str = ""


class DebateResponse(BaseModel):
    winner: str = ""
    new_insights: List[str] = []
    key_exchanges: List[DebateExchange] = []
    transcript: str = ""
    duration_seconds: float = 0.0


class GovernanceDecision(BaseModel):
    method: str = ""
    winner: str = ""
    scores: Dict[str, float] = {}


class GovernanceResponse(BaseModel):
    decisions: List[GovernanceDecision] = []
    consensus_score: float = 0.0
    summary: str = ""
    duration_seconds: float = 0.0


class FullAnalysisResponse(BaseModel):
    quality: Optional[QualityResponse] = None
    counter_arguments: Optional[CounterArgumentResponse] = None
    debate: Optional[DebateResponse] = None
    governance: Optional[GovernanceResponse] = None
    fields_populated: int = 0
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

agent_router = APIRouter(
    prefix="/api/v1/agents",
    tags=["Pipeline Agents"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_pipeline_phase(
    text: str, capability: str, max_text: int = 5000
) -> Dict[str, Any]:
    """Run a single pipeline capability and return its output + state snapshot."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.unified_pipeline import (
        CAPABILITY_STATE_WRITERS,
        setup_registry,
    )
    from argumentation_analysis.orchestration.workflow_dsl import (
        WorkflowBuilder,
        WorkflowExecutor,
    )

    text = text[:max_text]

    # Build a mini workflow: extract → target capability
    builder = WorkflowBuilder(f"api_{capability}")
    builder.add_phase(name="extract", capability="fact_extraction", depends_on=[])
    if capability != "fact_extraction":
        builder.add_phase(
            name=capability, capability=capability, depends_on=["extract"]
        )
    workflow = builder.build()

    registry = setup_registry()
    executor = WorkflowExecutor(registry)
    state = UnifiedAnalysisState(initial_text=text)

    phase_results = await executor.execute(
        workflow, text, state=state, state_writers=CAPABILITY_STATE_WRITERS
    )

    snapshot = state.get_state_snapshot()
    return {
        "phase_results": phase_results,
        "snapshot": snapshot,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@agent_router.post("/quality", response_model=QualityResponse)
async def evaluate_quality(request: TextRequest):
    """Evaluate argument quality using the 9-virtue evaluator.

    Extracts arguments from the text, then scores each on 9 dimensions:
    clarity, coherence, relevance, sufficiency, accuracy, depth,
    originality, fairness, and persuasiveness.
    """
    start = time.time()
    try:
        result = await _run_pipeline_phase(
            request.text, "argument_quality", request.max_text
        )
    except Exception as e:
        logger.error(f"Quality evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quality evaluation failed: {e}")

    snapshot = result["snapshot"]
    quality_scores = snapshot.get("quality_scores", {})

    scores = []
    for arg_key, arg_scores in quality_scores.items():
        if isinstance(arg_scores, dict):
            overall = sum(arg_scores.values()) / max(len(arg_scores), 1)
            scores.append(
                QualityScore(
                    argument=arg_key, scores=arg_scores, overall=round(overall, 2)
                )
            )

    # Aggregate across arguments
    aggregate = {}
    if scores:
        all_dims = set()
        for s in scores:
            all_dims.update(s.scores.keys())
        for dim in all_dims:
            vals = [s.scores.get(dim, 0) for s in scores if dim in s.scores]
            aggregate[dim] = round(sum(vals) / max(len(vals), 1), 2)

    return QualityResponse(
        scores=scores,
        aggregate=aggregate,
        duration_seconds=round(time.time() - start, 1),
    )


@agent_router.post("/counter-arguments", response_model=CounterArgumentResponse)
async def generate_counter_arguments(request: TextRequest):
    """Generate counter-arguments for the text's main claims.

    Uses 5 rhetorical strategies: reductio ad absurdum, counter-example,
    distinction, reformulation, and concession+pivot.
    """
    start = time.time()
    try:
        result = await _run_pipeline_phase(
            request.text, "counter_argument_generation", request.max_text
        )
    except Exception as e:
        logger.error(f"Counter-argument generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Counter-argument generation failed: {e}"
        )

    snapshot = result["snapshot"]

    # Extract LLM counter-arguments from state
    llm_cas = []
    raw_cas = snapshot.get("llm_counter_arguments", [])
    if isinstance(raw_cas, list):
        for ca in raw_cas:
            if isinstance(ca, dict):
                llm_cas.append(
                    CounterArgument(
                        target=ca.get("target", ""),
                        strategy=ca.get("strategy", ""),
                        counter=ca.get("counter", ca.get("text", "")),
                    )
                )
            elif isinstance(ca, str):
                llm_cas.append(CounterArgument(counter=ca))
    elif isinstance(raw_cas, str) and raw_cas:
        llm_cas.append(CounterArgument(counter=raw_cas))

    return CounterArgumentResponse(
        parsed=snapshot.get("counter_argument_parsed", {}),
        strategy=snapshot.get("counter_argument_strategy", {}),
        llm_counter_arguments=llm_cas,
        duration_seconds=round(time.time() - start, 1),
    )


@agent_router.post("/debate", response_model=DebateResponse)
async def run_debate(request: TextRequest):
    """Run an adversarial debate on the text.

    Agent A defends the strongest arguments, Agent B attacks using
    identified fallacies and counter-arguments. A judge evaluates exchanges.
    """
    start = time.time()
    try:
        result = await _run_pipeline_phase(
            request.text, "adversarial_debate", request.max_text
        )
    except Exception as e:
        logger.error(f"Debate failed: {e}")
        raise HTTPException(status_code=500, detail=f"Debate failed: {e}")

    snapshot = result["snapshot"]
    debate = snapshot.get("debate_transcripts", {})

    exchanges = []
    if isinstance(debate, dict):
        for exc in debate.get("key_exchanges", []):
            if isinstance(exc, dict):
                exchanges.append(
                    DebateExchange(
                        agent_a_point=exc.get("agent_a_point", ""),
                        agent_b_rebuttal=exc.get("agent_b_rebuttal", ""),
                        judge_note=exc.get("judge_note", ""),
                    )
                )

    return DebateResponse(
        winner=debate.get("winner", "") if isinstance(debate, dict) else "",
        new_insights=debate.get("new_insights", []) if isinstance(debate, dict) else [],
        key_exchanges=exchanges,
        transcript=json.dumps(debate, ensure_ascii=False, default=str)[:2000],
        duration_seconds=round(time.time() - start, 1),
    )


@agent_router.post("/governance", response_model=GovernanceResponse)
async def run_governance(request: TextRequest):
    """Run governance simulation on the text.

    Applies 7 voting methods (majority, Borda, Condorcet, approval, etc.)
    to evaluate competing arguments and reach a decision.
    """
    start = time.time()
    try:
        result = await _run_pipeline_phase(
            request.text, "governance_simulation", request.max_text
        )
    except Exception as e:
        logger.error(f"Governance simulation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Governance simulation failed: {e}"
        )

    snapshot = result["snapshot"]
    gov = snapshot.get("governance_decisions", {})

    decisions = []
    if isinstance(gov, dict):
        for method, result_data in gov.items():
            if method in ("summary", "consensus_score"):
                continue
            if isinstance(result_data, dict):
                decisions.append(
                    GovernanceDecision(
                        method=method,
                        winner=str(result_data.get("winner", "")),
                        scores={
                            str(k): float(v)
                            for k, v in result_data.get("scores", {}).items()
                            if isinstance(v, (int, float))
                        },
                    )
                )

    consensus = 0.0
    if isinstance(gov, dict):
        consensus = float(gov.get("consensus_score", 0.0))

    return GovernanceResponse(
        decisions=decisions,
        consensus_score=consensus,
        summary=str(gov.get("summary", "")) if isinstance(gov, dict) else "",
        duration_seconds=round(time.time() - start, 1),
    )


@agent_router.post("/full-analysis", response_model=FullAnalysisResponse)
async def run_full_analysis(request: TextRequest):
    """Run the full unified pipeline on the text.

    Executes all 15 capabilities (fact extraction, fallacy detection,
    quality evaluation, counter-arguments, debate, governance,
    formal logic, etc.) and returns a consolidated result.
    """
    start = time.time()
    try:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
            setup_registry,
        )
        from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor

        # Use the standard workflow (all capabilities)
        from argumentation_analysis.evaluation.run_iteration import (
            ITERATION_CAPABILITIES,
            _build_iteration_workflow,
        )

        all_caps = list(CAPABILITY_STATE_WRITERS.keys())
        workflow = _build_iteration_workflow(13, all_caps)

        registry = setup_registry()
        executor = WorkflowExecutor(registry)
        text = request.text[: request.max_text]
        state = UnifiedAnalysisState(initial_text=text)

        await executor.execute(
            workflow, text, state=state, state_writers=CAPABILITY_STATE_WRITERS
        )

        snapshot = state.get_state_snapshot()
    except Exception as e:
        logger.error(f"Full analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Full analysis failed: {e}")

    duration = round(time.time() - start, 1)

    # Count non-empty fields
    fields_populated = sum(
        1 for v in snapshot.values() if v and v != {} and v != [] and v != "" and v != 0
    )

    return FullAnalysisResponse(
        fields_populated=fields_populated,
        duration_seconds=duration,
    )
