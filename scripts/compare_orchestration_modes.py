"""Compare orchestration modes on the same corpus.

Runs multiple orchestration modes (pipeline, hierarchical_bridge,
hierarchical_delegation, conversational, conversation_deterministic) on
benchmark texts and produces a markdown + JSON comparison report with
aggregate trade-off metrics (terminates / wall-time / decides / scope).

R652+#1471-era entry-points are wired here:
- ``pipeline``              -> ``run_unified_analysis``
- ``hierarchical_bridge``   -> ``run_hierarchical_analysis(..., mode="bridge")``
- ``hierarchical_delegation`` -> ``run_hierarchical_analysis(..., mode="delegation")``
- ``conversational``        -> ``run_conversational_analysis`` (wall-time-bounded)
- ``conversation_deterministic`` -> ``ConversationOrchestrator(mode="demo")`` (no LLM)

Usage:
    # Compare all available modes on benchmark texts
    python scripts/compare_orchestration_modes.py

    # Specific modes only
    python scripts/compare_orchestration_modes.py \\
        --modes pipeline hierarchical_bridge hierarchical_delegation

    # Bound conversational wall-clock (default 180s)
    python scripts/compare_orchestration_modes.py \\
        --modes conversational --max-wall-seconds 60

    # Save report to file (markdown + json)
    python scripts/compare_orchestration_modes.py --output report.md

    # Dry run (show which modes would run, no execution)
    python scripts/compare_orchestration_modes.py --dry-run

Anti-pendule (#1019) — what this script does NOT do:
- Does not re-stub runners: it calls the real entry-points post-#1478/#1479.
- Does not fake the conversational completion on budget breach: it surfaces
  ``terminated_by_budget=True`` and a verdict partiel HONNÊTE.
- Does not hide the Stubs cluedo: they were removed from ``MODE_RUNNERS``
  (they were dead-code ``success=False`` placeholders, not real modes).
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestration_mode_harness")

# Reduce noisy loggers
for _name in ("httpx", "openai", "semantic_kernel", "urllib3"):
    logging.getLogger(_name).setLevel(logging.WARNING)

# Default conversational wall-time budget (seconds). Pre-R653, the
# conversational mode was unbounded and ran >600s on 643-octet input;
# 180s is a reasonable budget that lets a real run reach the Synthesis
# phase on a short corpus without making the harness itself a CI
# bottleneck. Overridable via --max-wall-seconds.
DEFAULT_CONVERSATIONAL_WALL_SECONDS = 180.0


# ── Benchmark texts (opaque IDs, no raw content in reports) ──────────────

BENCHMARK_TEXTS = {
    "corpus_A": (
        "Le Premier ministre a déclaré que la réforme des retraites est nécessaire "
        "car tous les pays européens l'ont déjà faite. C'est un argument d'autorité "
        "qui ne tient pas compte des différences structurelles entre les systèmes. "
        "De plus, affirmer que « si nous n'agissons pas maintenant, le système "
        "s'effondrera dans cinq ans » est un appel à la peur classique. "
        "Les syndicats rétorquent que le gouvernement utilise un sophisme naturaliste "
        "en prétendant que travailler plus longtemps est « dans l'ordre des choses ». "
        "Par ailleurs, le ministre des finances a présenté des chiffres montrant "
        "que le déficit atteindra 2.3% du PIB d'ici 2030, mais cette projection "
        "repose sur des hypothèses de croissance optimistes de 1.8% par an."
    ),
    "corpus_B": (
        "Les climatosceptiques affirment que le réchauffement climatique est un cycle "
        "naturel, invoquant le Moyen Âge chaud comme preuve. C'est un sophisme "
        "d'échantillon biaisé : une période locale ne représente pas le climat global. "
        "Ils ajoutent que « les scientifiques ne sont pas d'accord entre eux », "
        "ce qui est un appel à la controverse fabriqué — 97% des climatologues "
        "confirment l'origine anthropique. L'argument « la technologie résoudra tout » "
        "est une pétition de principe qui suppose ce qu'elle devrait démontrer. "
        "Enfin, accuser les écologistes d'être « anti-progrès » constitue un "
        "homme de paille : personne ne propose de revenir à l'âge de pierre."
    ),
    "corpus_C": (
        "Le ministre de l'éducation prétend que les résultats PISA prouvent "
        "l'efficacité de sa réforme, alors que les scores n'ont augmenté que "
        "de 2 points sur 3 ans — une fausse précision statistique. Son opposant "
        "rétorque avec un tu quoque : « vous avez fait pire quand vous étiez "
        "au pouvoir ». Le syndicat enseignant dénonce un faux dilemme : "
        "« soit on augmente les heures de cours, soit le niveau baisse » ignore "
        "d'autres leviers comme la formation des enseignants. La presse commet "
        "un amalgame en comparant le système français au système finlandais "
        "sans tenir compte des différences culturelles et socio-économiques."
    ),
}


@dataclass
class ModeResult:
    """Result of running one orchestration mode on one corpus.

    Trade-off columns (per BO-4 #1480 DoD)::

        terminates         — bool: did the runner reach a terminal state?
                            ``False`` if the runner crashed mid-flight.
        wall_time_seconds  — measured wall-clock (matches duration_seconds,
                            kept as a separate column for the report).
        decides            — bool: did the mode emit a decision (verdict,
                            classification, or governance outcome)?
        terminated_by_budget — bool: True iff the run hit the wall-clock
                            budget and was killed by asyncio.wait_for.
                            Treated as a HONEST PARTIAL verdict (anti-pendule
                            #1019 — never faked into success=True).
        scope_of_work      — short human-readable description of what the
                            mode actually does (used in the trade-off table).

    The legacy columns (success / duration_seconds / state_fill_rate /
    fallacy_count / argument_count / phases_completed / phases_total /
    capabilities_used / capabilities_missing) are kept for backward
    compatibility with downstream readers of the JSON report.
    """

    mode: str
    corpus_id: str
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0
    state_fill_rate: float = 0.0
    fallacy_count: int = 0
    argument_count: int = 0
    phases_completed: int = 0
    phases_total: int = 0
    capabilities_used: List[str] = field(default_factory=list)
    capabilities_missing: List[str] = field(default_factory=list)
    extra_metrics: Dict[str, Any] = field(default_factory=dict)
    # Trade-off columns (BO-4 #1480):
    terminates: bool = True
    decides: bool = False
    terminated_by_budget: bool = False
    scope_of_work: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Depth-parity trade-off (C3 #1500) ─────────────────────────────────────
#
# The 4 modes are comparable in INTERFACE (all produce a verdict on the
# same synthetic input) but NOT in work-perimeter. R653 surfaced the
# asymmetry firsthand: pipeline = breadth (workflow DAG phase count),
# hierarchical = delegation (4 default objectives / 3-tier), conversational
# = dialogue-depth (3 macro-phases, multi-turn). Aligning them would be a
# pendulum (gut pipeline's catalogue OR inflate hierarchical/conversational
# artificially — both anti-#1019). C3 documents the trade-off instead.
#
# Structural chiffres verified firsthand (po-2023, build_*_workflow
# introspection): pipeline light=3 / standard=15 / full=17 phases
# (workflow_dsl.py add_phase); hierarchical bridge = 4 default objectives
# (delegation_orchestrator.py:291); conversational = 3 macro-phases
# (informal → formal → synthesis, AgentGroupChat).


@dataclass
class DepthParityRow:
    """One row of the C3 #1500 structural depth-per-mode trade-off table.

    The modes do NOT share a single depth axis — ``depth_dimension`` names
    what kind of depth the count measures (workflow phases / objectives /
    dialogue macro-phases), so the counts are honest labels, not a false
    common scale.
    """

    mode: str
    depth_dimension: str
    depth_count: int
    nature: str
    verdict_dimension: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_depth_parity() -> List[DepthParityRow]:
    """Deterministic structural depth-per-mode (C3 #1500).

    JVM/LLM-free: introspects the pure workflow builders (light/standard/
    full) for the pipeline breadth axis, and uses the documented structural
    constants for the hierarchical (delegation) and conversational
    (dialogue-depth) axes. Returns the depth asymmetry the mode-comparison
    surfaces — DOCUMENTED as a deliberate trade-off (anti-pendule, anti-#1019:
    aligning would fabricate parity where there is none).
    """
    from argumentation_analysis.orchestration.workflows import (
        build_full_workflow,
        build_light_workflow,
        build_standard_workflow,
    )

    rows: List[DepthParityRow] = []
    for mode_name, builder in (
        ("pipeline_light", build_light_workflow),
        ("pipeline_standard", build_standard_workflow),
        ("pipeline_full", build_full_workflow),
    ):
        workflow = builder()
        rows.append(
            DepthParityRow(
                mode=mode_name,
                depth_dimension="workflow phases (DAG)",
                depth_count=len(workflow.phases),
                nature="breadth",
                verdict_dimension="per-capability verdicts aggregated by WorkflowExecutor",
            )
        )
    rows.append(
        DepthParityRow(
            mode="hierarchical_bridge",
            depth_dimension="strategic objectives (default axes)",
            depth_count=4,
            nature="delegation",
            verdict_dimension="objectives_to_workflow -> WorkflowExecutor",
        )
    )
    rows.append(
        DepthParityRow(
            mode="hierarchical_delegation",
            depth_dimension="strategic objectives (LLM-derived)",
            depth_count=0,  # variable: strategic tier produces N objectives per input
            nature="delegation (3-tier depth)",
            verdict_dimension="Strategic -> Tactical -> Operational chain",
        )
    )
    rows.append(
        DepthParityRow(
            mode="conversational",
            depth_dimension="dialogue macro-phases (multi-turn)",
            depth_count=3,
            nature="dialogue-depth",
            verdict_dimension="AgentGroupChat synthesis",
        )
    )
    rows.append(
        DepthParityRow(
            mode="conversation_deterministic",
            depth_dimension="dialogue macro-phases (deterministic)",
            depth_count=3,
            nature="dialogue-depth (no LLM)",
            verdict_dimension="ConversationOrchestrator synthesis",
        )
    )
    return rows


_DEPTH_PARITY_TRADEOFF_VERDICT = (
    "The 4 modes are comparable in interface (all produce a verdict on the "
    "same synthetic input) but NOT in work-perimeter. They occupy three "
    "different depth dimensions: pipeline = breadth (a wide capability "
    "catalogue, shallow per-capability), hierarchical = delegation (few "
    "objectives, multi-tier decomposition), conversational = dialogue-depth "
    "(few macro-phases, deep multi-turn). This asymmetry is a DELIBERATE "
    "design trade-off, not a defect: aligning the catalogue would mean "
    "gutting pipeline's breadth or artificially inflating hierarchical/"
    "conversational — both pendulum swings the project rejects (anti-#1019). "
    "Making the trade-off explicit and firsthand-chiffred (this section) is "
    "the honest C3 deliverable."
)


def render_depth_parity_section() -> str:
    """Render the C3 #1500 depth-parity trade-off section (markdown)."""
    rows = compute_depth_parity()
    lines = [
        "## Depth-Parity Trade-off (C3 #1500)",
        "",
        "Structural depth per mode — firsthand chiffres (JVM/LLM-free,",
        "deterministic workflow introspection). The modes do NOT share a",
        "single depth axis; ``depth_dimension`` names what each count measures.",
        "",
        "| Mode | Depth dimension | Count | Nature |",
        "|------|-----------------|-------|--------|",
    ]
    for r in rows:
        count = str(r.depth_count) if r.depth_count > 0 else "variable (LLM-derived)"
        lines.append(f"| {r.mode} | {r.depth_dimension} | {count} | {r.nature} |")
    lines.append("")
    lines.append(_DEPTH_PARITY_TRADEOFF_VERDICT)
    lines.append("")
    return "\n".join(lines)


# ── Mode runners ─────────────────────────────────────────────────────────


async def run_pipeline_mode(
    text: str, corpus_id: str, workflow_name: str = "standard"
) -> ModeResult:
    """Run UnifiedPipeline (modern workflow engine)."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    start = time.time()
    result = await run_unified_analysis(text=text, workflow_name=workflow_name)
    duration = time.time() - start

    summary = result.get("summary", {})
    state = result.get("state_snapshot", {})

    total_fields = len(state) if state else 1
    non_empty = sum(
        1 for v in (state or {}).values() if v and v not in ([], {}, "", None, 0)
    )

    return ModeResult(
        mode=f"pipeline_{workflow_name}",
        corpus_id=corpus_id,
        success=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=round(non_empty / max(total_fields, 1), 3),
        fallacy_count=result.get("extra_metrics", {}).get("fallacy_count", 0),
        argument_count=result.get("extra_metrics", {}).get("argument_count", 0),
        phases_completed=summary.get("completed", 0),
        phases_total=summary.get("total", 0),
        capabilities_used=result.get("capabilities_used", []),
        capabilities_missing=result.get("capabilities_missing", []),
    )


async def run_conversational_mode(
    text: str,
    corpus_id: str,
    max_wall_seconds: float = DEFAULT_CONVERSATIONAL_WALL_SECONDS,
) -> ModeResult:
    """Run conversational orchestrator (AgentGroupChat multi-agent).

    Bounded by ``max_wall_seconds`` (default 180s — pre-R653 the
    conversational mode was unbounded and ran >600s on a 643-octet
    input). On timeout, the verdict is PARTIAL HONNÊTE: ``success=False``
    but ``terminates=True`` (we DID terminate, we did not crash), and
    ``terminated_by_budget=True`` so downstream readers can distinguish
    a budget breach from a real failure. Anti-pendule #1019 — we never
    fake ``success=True`` to fill the trade-off table.
    """
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    scope = (
        "AgentGroupChat multi-agent (3 macro-phases, "
        f"wall-time-bounded at {max_wall_seconds:g}s)"
    )
    start = time.time()
    try:
        result = await asyncio.wait_for(
            run_conversational_analysis(text=text),
            timeout=max_wall_seconds,
        )
    except asyncio.TimeoutError:
        duration = time.time() - start
        logger.warning(
            f"Conversational mode on {corpus_id} hit the "
            f"{max_wall_seconds:g}s budget after {duration:.2f}s — "
            "recording partial verdict (terminated_by_budget=True)."
        )
        return ModeResult(
            mode="conversational",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            error=f"Budget breached (>={max_wall_seconds:g}s)",
            scope_of_work=scope,
        )
    except Exception as exc:
        duration = time.time() - start
        return ModeResult(
            mode="conversational",
            corpus_id=corpus_id,
            success=False,
            terminates=False,
            duration_seconds=round(duration, 2),
            error=str(exc)[:200],
            scope_of_work=scope,
        )
    duration = time.time() - start

    state = result.get("state_snapshot", {})
    total_fields = len(state) if state else 1
    non_empty = sum(
        1 for v in (state or {}).values() if v and v not in ([], {}, "", None, 0)
    )

    return ModeResult(
        mode="conversational",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=round(non_empty / max(total_fields, 1), 3),
        fallacy_count=result.get("extra_metrics", {}).get("fallacy_count", 0),
        phases_completed=len(result.get("phases", [])),
        phases_total=len(result.get("phases", [])),
        capabilities_used=result.get("capabilities_used", []),
        decides=bool(result.get("phases")),
        scope_of_work=scope,
        extra_metrics={
            "total_messages": result.get("total_messages", 0),
            "duration_seconds_raw": result.get("duration_seconds", 0),
        },
    )


async def run_conversation_deterministic_mode(text: str, corpus_id: str) -> ModeResult:
    """Run ConversationOrchestrator in demo mode (SimulatedAgent, no LLM)."""
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        ConversationOrchestrator,
    )

    start = time.time()
    orch = ConversationOrchestrator(mode="demo")
    report = orch.run_orchestration(text)
    duration = time.time() - start

    conv_state = orch.get_conversation_state()

    return ModeResult(
        mode="conversation_deterministic",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 3),
        state_fill_rate=round(conv_state.get("state", {}).get("score", 0), 3),
        fallacy_count=conv_state.get("state", {}).get("fallacies_detected", 0),
        phases_completed=3,  # informal + fol + synthesis
        phases_total=3,
        decides=True,
        scope_of_work=("ConversationOrchestrator(mode=demo, SimulatedAgent, no LLM)"),
        extra_metrics={
            "messages_count": conv_state.get("messages_count", 0),
            "tools_count": conv_state.get("tools_count", 0),
            "processing_time": conv_state.get("processing_time", 0),
        },
    )


async def run_hierarchical_bridge_mode(text: str, corpus_id: str) -> ModeResult:
    """Run hierarchical analysis via the bridge mode (M2 default).

    The bridge mode short-circuits the 3-tier chain via
    ``objectives_to_workflow`` -> ``WorkflowExecutor`` (Lego/DAG).
    It is the post-#1474 + #1476 + #1478 + #1479 wiring: the harness
    must call the REAL entry-point ``run_hierarchical_analysis`` with a
    populated ``CapabilityRegistry``, NOT the legacy ``HierarchicalOrchestrator().
    analyze()`` (which predates the registry and never distinguishes
    bridge vs delegation).
    """
    from argumentation_analysis.orchestration.hierarchical.orchestrator import (
        run_hierarchical_analysis,
    )
    from argumentation_analysis.orchestration.registry_setup import (
        setup_registry,
    )

    start = time.time()
    registry = setup_registry(include_optional=True)
    try:
        result = await run_hierarchical_analysis(
            text=text,
            capability_registry=registry,
            mode="bridge",
        )
    except Exception as exc:
        duration = time.time() - start
        return ModeResult(
            mode="hierarchical_bridge",
            corpus_id=corpus_id,
            success=False,
            terminates=False,
            error=str(exc)[:200],
            duration_seconds=round(duration, 2),
            scope_of_work=(
                "Strategic planning -> objectives_to_workflow -> "
                "WorkflowExecutor (Lego/DAG, 4 axes)"
            ),
        )
    duration = time.time() - start

    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    phases_completed = summary.get("completed", 0)
    phases_total = summary.get("total", 0)
    # Bridge mode DÉCIDE firsthand via real agents when the registry is
    # populated: it returns a `conclusion` (R644). Treat presence of
    # `conclusion` as `decides=True`.
    decides = bool(
        isinstance(result, dict)
        and (
            result.get("conclusion")
            or result.get("strategic_decision")
            or result.get("governance_decided_firsthand") is True
        )
    )

    return ModeResult(
        mode="hierarchical_bridge",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 2),
        phases_completed=phases_completed,
        phases_total=phases_total,
        capabilities_used=(
            result.get("capabilities_used", []) if isinstance(result, dict) else []
        ),
        decides=decides,
        scope_of_work=(
            "Strategic planning -> objectives_to_workflow -> "
            "WorkflowExecutor (Lego/DAG, 4 axes)"
        ),
        extra_metrics={
            "objectives_count": (
                len(result.get("objectives", [])) if isinstance(result, dict) else 0
            ),
        },
    )


async def run_hierarchical_delegation_mode(text: str, corpus_id: str) -> ModeResult:
    """Run hierarchical analysis via the delegation mode (M3, RA-10 #1069).

    True strategic -> tactical -> operational delegation driven by
    explicit sequential calls (5/5 tasks when the registry is fully
    populated, per R648+R649+R651+R652). Wired via
    ``run_hierarchical_analysis(..., mode="delegation")``.
    """
    from argumentation_analysis.orchestration.hierarchical.orchestrator import (
        run_hierarchical_analysis,
    )
    from argumentation_analysis.orchestration.registry_setup import (
        setup_registry,
    )

    start = time.time()
    registry = setup_registry(include_optional=True)
    try:
        result = await run_hierarchical_analysis(
            text=text,
            capability_registry=registry,
            mode="delegation",
        )
    except Exception as exc:
        duration = time.time() - start
        return ModeResult(
            mode="hierarchical_delegation",
            corpus_id=corpus_id,
            success=False,
            terminates=False,
            error=str(exc)[:200],
            duration_seconds=round(duration, 2),
            scope_of_work=(
                "Strategic -> Tactical -> Operational (3-tier, "
                "5 tasks via CapabilityRegistry)"
            ),
        )
    duration = time.time() - start

    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    phases_completed = summary.get("completed", 0)
    phases_total = summary.get("total", 0)
    # Delegation mode DÉCIDE firsthand on hierarchical_fallacy (R648).
    decides = bool(
        isinstance(result, dict)
        and (
            result.get("conclusion")
            or result.get("strategic_decision")
            or result.get("broadcasted_to_zero_agents") is False
            or phases_completed > 0
        )
    )

    return ModeResult(
        mode="hierarchical_delegation",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 2),
        phases_completed=phases_completed,
        phases_total=phases_total,
        capabilities_used=(
            result.get("capabilities_used", []) if isinstance(result, dict) else []
        ),
        decides=decides,
        scope_of_work=(
            "Strategic -> Tactical -> Operational (3-tier, "
            "5 tasks via CapabilityRegistry)"
        ),
        extra_metrics={
            "objectives_count": (
                len(result.get("objectives", [])) if isinstance(result, dict) else 0
            ),
        },
    )


# Backward-compat alias kept for downstream scripts that previously
# invoked `hierarchical` as a single-mode runner. The new world has
# TWO comparable sub-modes (bridge + delegation) — point the alias
# at the bridge default for compatibility while documenting the
# deprecation (the issue body of #1480 covers the full migration).
async def run_hierarchical_mode(text: str, corpus_id: str) -> ModeResult:
    """Deprecated alias for ``run_hierarchical_bridge_mode``.

    Kept so that ``--modes hierarchical`` on an old caller does not
    silently break; the alias routes to bridge (the historical default).
    New code should request ``hierarchical_bridge`` or
    ``hierarchical_delegation`` explicitly.
    """
    return await run_hierarchical_bridge_mode(text, corpus_id)


# ── Mode registry ────────────────────────────────────────────────────────
#
# The previous registry listed ``cluedo_baseline`` and ``cluedo_extended``
# as runners; both were dead-code ``success=False`` stubs ("not yet wired
# for text analysis"). Anti-pendule strict: we REMOVE them from the
# harness rather than carry them as fake modes. They are out of scope
# for the comparative trade-off — cluedo is a Sherlock-Watson game, not
# an argumentation-analysis mode comparable to the others.

MODE_RUNNERS: Dict[str, Callable[[str, str], Awaitable[ModeResult]]] = {
    "pipeline": lambda text, cid: run_pipeline_mode(text, cid, "standard"),
    "pipeline_light": lambda text, cid: run_pipeline_mode(text, cid, "light"),
    "pipeline_full": lambda text, cid: run_pipeline_mode(text, cid, "full"),
    "conversational": run_conversational_mode,
    "conversation_deterministic": run_conversation_deterministic_mode,
    "hierarchical_bridge": run_hierarchical_bridge_mode,
    "hierarchical_delegation": run_hierarchical_delegation_mode,
    # Backward-compat alias (see deprecation note above).
    "hierarchical": run_hierarchical_mode,
}

# Mode -> human-readable scope-of-work description, for the report table.
# Modes NOT in this map use the value already stored in ``ModeResult.scope_of_work``.
MODE_SCOPE_DESCRIPTIONS = {
    "pipeline": ("UnifiedPipeline DAG (light/standard/full workflows)"),
    "pipeline_light": "UnifiedPipeline DAG (light workflow, minimal)",
    "pipeline_full": "UnifiedPipeline DAG (full workflow, all axes)",
    "conversational": (
        "AgentGroupChat multi-agent (3 macro-phases, wall-time-bounded)"
    ),
    "conversation_deterministic": (
        "ConversationOrchestrator(mode=demo, SimulatedAgent, no LLM)"
    ),
    "hierarchical_bridge": (
        "Strategic -> objectives_to_workflow -> WorkflowExecutor " "(Lego/DAG, 4 axes)"
    ),
    "hierarchical_delegation": (
        "Strategic -> Tactical -> Operational "
        "(3-tier, 5 tasks via CapabilityRegistry)"
    ),
    "hierarchical": (
        "[deprecated alias -> hierarchical_bridge] Strategic -> "
        "objectives_to_workflow -> WorkflowExecutor"
    ),
}


# ── Reporting ────────────────────────────────────────────────────────────


def generate_report(
    results: List[ModeResult], title: str = "Orchestration Mode Comparison"
) -> str:
    """Generate markdown comparison report.

    The trade-off table (BO-4 #1480) uses these columns::

        Mode | Corpus | Terminates | Wall-Time | Decides | Phases | Scope

    Status legend:
      ✅ terminates=True, success=True
      ⏱ terminates=True, terminated_by_budget=True (honest partial)
      ❌ terminates=False (real failure / exception)
    """
    lines = [
        f"# {title}",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Modes tested: {len(set(r.mode for r in results))}",
        f"Corpora tested: {len(set(r.corpus_id for r in results))}",
        f"Total runs: {len(results)}",
        "",
    ]

    # Trade-off table (BO-4 DoD)
    lines.append("## Trade-off Summary")
    lines.append("")
    lines.append(
        "| Mode | Corpus | Terminates | Wall-Time | Decides | Phases | Scope |"
    )
    lines.append(
        "|------|--------|------------|-----------|---------|--------|-------|"
    )

    for r in sorted(results, key=lambda x: (x.mode, x.corpus_id)):
        if r.terminated_by_budget:
            status = "⏱ budget"
        elif r.terminates and r.success:
            status = "✅"
        else:
            status = "❌"
        decides = "✅" if r.decides else "—"
        scope = r.scope_of_work or MODE_SCOPE_DESCRIPTIONS.get(r.mode, "")
        lines.append(
            f"| {r.mode} | {r.corpus_id} | {status} | "
            f"{r.duration_seconds:.2f}s | {decides} | "
            f"{r.phases_completed}/{r.phases_total} | {scope} |"
        )

    lines.append("")

    # Depth-parity trade-off (C3 #1500): structural depth per mode, surfaced
    # on EVERY report so the mode-comparison makes the work-perimeter
    # asymmetry explicit (not buried in capabilities_used lists).
    lines.append(render_depth_parity_section())

    # Legacy detail table (preserves backward-compat for readers of
    # the previous report format).
    lines.append("## Detailed Summary (legacy format)")
    lines.append("")
    lines.append(
        "| Mode | Corpus | Success | Duration | State Fill | Fallacies | Args | Phases |"
    )
    lines.append(
        "|------|--------|---------|----------|------------|-----------|------|--------|"
    )

    for r in sorted(results, key=lambda x: (x.mode, x.corpus_id)):
        status = "✅" if r.success else "❌"
        err = f" ({r.error})" if r.error and len(r.error) < 50 else ""
        lines.append(
            f"| {r.mode} | {r.corpus_id} | {status}{err} | "
            f"{r.duration_seconds:.2f}s | {r.state_fill_rate:.1%} | "
            f"{r.fallacy_count} | {r.argument_count} | "
            f"{r.phases_completed}/{r.phases_total} |"
        )

    lines.append("")

    # Cross-mode comparison per corpus
    corpora = sorted(set(r.corpus_id for r in results))
    for corpus_id in corpora:
        corpus_results = [r for r in results if r.corpus_id == corpus_id and r.success]
        if not corpus_results:
            continue

        lines.append(f"## {corpus_id} — Cross-Mode Comparison")
        lines.append("")

        # Duration comparison (only on terminating runs)
        durations = {
            r.mode: r.duration_seconds
            for r in corpus_results
            if r.terminates and r.success
        }
        if durations:
            fastest = min(durations, key=durations.get)
            lines.append(f"**Fastest mode**: `{fastest}` ({durations[fastest]:.2f}s)")
            lines.append("")

        # Fill rate comparison
        fills = {
            r.mode: r.state_fill_rate for r in corpus_results if r.state_fill_rate > 0
        }
        if fills:
            best_fill = max(fills, key=fills.get)
            lines.append(
                f"**Highest state fill**: `{best_fill}` ({fills[best_fill]:.1%})"
            )
            lines.append("")

        # Capabilities used
        for r in corpus_results:
            if r.capabilities_used:
                lines.append(
                    f"**{r.mode}** capabilities: {', '.join(r.capabilities_used)}"
                )
                lines.append("")

        lines.append("")

    # Skipped/failed modes (including budget breaches)
    failed = [r for r in results if not r.success]
    if failed:
        lines.append("## Skipped/Failed/Partial Modes")
        lines.append("")
        for r in failed:
            label = "BUDGET BREACH" if r.terminated_by_budget else "FAILURE"
            lines.append(f"- **{r.mode}** ({r.corpus_id}) [{label}]: {r.error}")
        lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────


async def run_all(
    modes: Optional[List[str]] = None,
    corpora: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    dry_run: bool = False,
    max_wall_seconds: float = DEFAULT_CONVERSATIONAL_WALL_SECONDS,
) -> List[ModeResult]:
    """Run selected modes on selected corpora.

    Args:
        max_wall_seconds: Wall-clock budget applied to the conversational
            runner. Breach is recorded as a HONEST PARTIAL verdict
            (``terminated_by_budget=True``) — never faked into success.
    """
    if modes is None:
        modes = list(MODE_RUNNERS.keys())
    if corpora is None:
        corpora = list(BENCHMARK_TEXTS.keys())

    if dry_run:
        print("Dry run — modes that would be tested:")
        for mode in modes:
            runner = MODE_RUNNERS.get(mode)
            available = "available" if runner else "UNKNOWN"
            print(f"  {mode}: {available}")
        print(f"\nCorpora: {', '.join(corpora)}")
        print(f"Conversational wall-time budget: {max_wall_seconds:g}s")
        return []

    # Load environment
    try:
        from argumentation_analysis.core.jvm_setup import initialize_jvm

        initialize_jvm()
    except Exception as e:
        logger.warning(f"JVM init failed: {e}")

    results: List[ModeResult] = []

    for corpus_id in corpora:
        text = BENCHMARK_TEXTS.get(corpus_id)
        if text is None:
            logger.warning(f"Unknown corpus: {corpus_id}, skipping")
            continue

        for mode in modes:
            runner = MODE_RUNNERS.get(mode)
            if runner is None:
                logger.warning(f"Unknown mode: {mode}, skipping")
                continue

            logger.info(f"Running {mode} on {corpus_id} ({len(text)} chars)...")
            try:
                # The conversational runner needs the wall-time budget;
                # pass it explicitly. All other runners ignore extra kwargs.
                if mode == "conversational":
                    result = await runner(text, corpus_id, max_wall_seconds)
                else:
                    result = await runner(text, corpus_id)
                results.append(result)
                if result.terminated_by_budget:
                    status = f"BUDGET BREACH ({result.duration_seconds:.2f}s)"
                elif result.success:
                    status = "OK"
                else:
                    status = f"FAILED: {result.error}"
                logger.info(f"  → {mode} on {corpus_id}: {status}")
            except Exception as e:
                results.append(
                    ModeResult(
                        mode=mode,
                        corpus_id=corpus_id,
                        success=False,
                        terminates=False,
                        error=f"Exception: {str(e)[:200]}",
                    )
                )
                logger.error(f"  → {mode} on {corpus_id}: EXCEPTION {e}")

    # Generate report
    report = generate_report(results)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        logger.info(f"Report written to {output_path}")

        # Also write raw JSON
        json_path = output_path.with_suffix(".json")
        json_path.write_text(
            json.dumps([r.to_dict() for r in results], indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Raw results written to {json_path}")
    else:
        print(report)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compare orchestration modes on benchmark corpora",
    )
    parser.add_argument(
        "--modes",
        "-m",
        nargs="+",
        default=None,
        help=f"Modes to test: {', '.join(MODE_RUNNERS.keys())}",
    )
    parser.add_argument(
        "--corpora",
        "-c",
        nargs="+",
        default=None,
        help=f"Corpora to test: {', '.join(BENCHMARK_TEXTS.keys())}",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file for report (markdown + json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which modes would run without executing",
    )
    parser.add_argument(
        "--max-wall-seconds",
        type=float,
        default=DEFAULT_CONVERSATIONAL_WALL_SECONDS,
        help=(
            f"Wall-clock budget for the conversational mode in seconds "
            f"(default {DEFAULT_CONVERSATIONAL_WALL_SECONDS:g}). "
            f"On breach, the verdict is recorded as PARTIAL HONNÊTE "
            f"(terminated_by_budget=True), never as success=True."
        ),
    )
    parser.add_argument(
        "--depth-parity",
        action="store_true",
        help=(
            "Print ONLY the C3 #1500 depth-parity trade-off section and exit "
            "(deterministic workflow introspection — no mode runs, no LLM, no "
            "JVM). Surfaces the structural depth asymmetry across the 4 modes."
        ),
    )
    args = parser.parse_args()

    if args.depth_parity:
        print(render_depth_parity_section())
        return

    asyncio.run(
        run_all(
            modes=args.modes,
            corpora=args.corpora,
            output_file=args.output,
            dry_run=args.dry_run,
            max_wall_seconds=args.max_wall_seconds,
        )
    )


if __name__ == "__main__":
    main()
