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


def _conversational_safety_net_timeout(max_wall_seconds: float) -> float:
    """C1 #1500: safety-net timeout wrapping the internally-bounded call.

    The wall-clock bound is enforced INSIDE ``run_conversational_analysis``
    (clean exit between turns → real partial verdict, anti-#1019). This outer
    ``asyncio.wait_for`` only catches a single in-flight LLM round-trip that
    overshoots the between-turn check. The headroom is the larger of 20 % of
    the budget or 30 s, so the internal bound reliably fires first; if the
    safety net ever fires the verdict is still an honest partial
    (``terminated_by_budget=True``, never faked into success).
    """
    return max(max_wall_seconds * 1.2, max_wall_seconds + 30.0)


def _count_pending_async_tasks() -> int:
    """CB #1528 guard (b): count asyncio tasks still pending (not done).

    A mode killed by ``asyncio.wait_for`` should leave its cancelled coroutine
    fully cleaned up. If this returns >0 immediately after a breached mode, the
    cancellation leaked dangling work (e.g. in-flight HTTP sessions spawned by
    the LLM client) that may inflate the NEXT mode's measured wall-time —
    cross-mode contamination. The count is MEASURED and REPORTED (logged +
    stashed in ``extra_metrics["pending_tasks_after_breach"]``), never masked
    by a convenient mode ordering (coord R709 directive: measure, don't hide).
    """
    try:
        current = asyncio.current_task()
        return sum(1 for t in asyncio.all_tasks() if t is not current and not t.done())
    except RuntimeError:
        # No running loop (called outside a coroutine) → nothing to measure.
        return 0


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
        decides            — Optional[bool]: did the mode produce at least one
                            usable VERDICT ARTIFACT? Computed UNIFORMLY for
                            every mode by :func:`_compute_decides` (Track CA
                            #1529) — never hand-set per runner. A mode decides
                            iff it left behind any of: a non-empty shared state
                            (``state_fill_rate > 0``), an extracted argument or
                            fallacy, an agent dialogue message, a mode-specific
                            conclusion/synthesis (``extra_metrics["verdict_artifact"]``),
                            or a completed workflow phase. ``None`` = not yet
                            computed (a runner that bypassed the helper);
                            ``False`` = computed "no artifact" (e.g. a
                            conversational run cut at the safety-net with 0/0
                            phases — honestly ``—``, anti-#1019: "I checked,
                            nothing" is not "indeterminate"). A budget breach
                            that still produced partial artifacts honestly
                            decides ``True`` (the partial state IS the verdict).
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
    # Track CA #1529: default is None ("not computed"), NOT False ("no"). A
    # runner that forgets the uniform helper shows `—` (indeterminate) rather
    # than asserting a false "no". run_all computes the real value for every
    # result via _compute_decides before the report is rendered.
    decides: Optional[bool] = None
    terminated_by_budget: bool = False
    scope_of_work: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_decides(result: ModeResult) -> bool:
    """The ONE uniform definition of whether a mode *decided* (Track CA #1529).

    A mode decides iff it produced at least one usable **verdict artifact**.
    The signals are read off the common ``ModeResult`` fields every runner
    populates — so the same definition applies to pipeline / conversational /
    hierarchical alike, and no runner hand-sets ``decides`` on a local
    criterion (the BO-4 #1480 defect: three runners, three ad-hoc
    definitions, plus a misleading ``False`` default that painted the
    hardest-working mode — pipeline 15/15 phases — as ``Decides —``).

    Order is irrelevant (short-circuit on the first artifact found):

    * ``state_fill_rate > 0`` — the shared analysis state was populated.
    * ``argument_count > 0`` or ``fallacy_count > 0`` — extracted artifacts.
    * ``extra_metrics["total_messages"] > 0`` — agent dialogue (conversational).
    * ``extra_metrics["verdict_artifact"]`` — a mode-specific conclusion /
      synthesis / strategic decision (e.g. hierarchical_bridge emits a
      ``conclusion`` without filling the shared state — documented as a
      legitimate decide, per DoD-4 #1529).
    * ``phases_completed > 0`` — a completed workflow phase emits its phase's
      artifact by definition.

    Anti-#1019 / anti-pendule: returning ``True`` everywhere would destroy the
    column's discriminating power. The non-regression test is that a genuinely
    sterile run (conversational cut at the safety-net: 0/0 phases, 0 % fill,
    0 messages) stays ``False`` → ``—``.
    """
    if result.state_fill_rate > 0:
        return True
    if result.argument_count > 0 or result.fallacy_count > 0:
        return True
    if result.extra_metrics.get("total_messages", 0) > 0:
        return True
    if result.extra_metrics.get("verdict_artifact"):
        return True
    if result.phases_completed > 0:
        return True
    return False


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
    # C3 #1500: when the depth axis is LLM-derived (delegation), the count is a
    # MEASURED RANGE over ≥3 inputs, not a structural constant. ``measured_range``
    # carries the "min–max (n=K, provenance)" string rendered in place of a bare
    # int. ``depth_count`` holds a representative int (max of range) so any
    # downstream logic that reads the count still gets a usable value.
    measured_range: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# C3 #1500 chiffrage — the delegation mode's strategic tier is LLM-driven, so
# its objective/task count could in principle VARY per input (unlike the
# pipeline's deterministic workflow phase count, which ``compute_depth_parity``
# introspects statically). This constant holds the firsthand-MEASURED range over
# ≥3 benchmark corpora. Injected as a constant + provenance so
# ``render_depth_parity_section`` stays LLM-free at render time (coord R710
# directive: inject a measured constant, do NOT call an LLM from the render
# path). Re-measure after any change to the strategic/tactical tiers and update
# the ranges; the depth-parity tests assert the SHAPE (a measured range with
# provenance), not the exact digits.
#
# Firsthand result R711 (po-2023, env projet-is, post-CC #1531 corpus fix):
# the range is DEGENERATE — all 3 corpora produced exactly 4 objectives
# decomposed into 5 tasks (obj-1 splits into 2), 5/5 completed, rate 1.0. This
# matches the coord's R709 datapoint and documents a NON-DIFFERENTIATION
# finding: on these inputs the LLM-derived delegation tier goes NO DEEPER than
# the 4 hardcoded bridge axes (it produced exactly them). Written as the range
# ``4–4`` rather than the int ``4`` so a reader sees it is a measured
# distribution (that happens to be degenerate), not a structural constant.
DELEGATION_DEPTH_MEASURED = {
    "objectives_range": "4–4",
    "tasks_range": "5–5",
    "n_runs": 3,
    "inputs": "corpus_A/B/C",
    "provenance": "firsthand R711, po-2023 projet-is",
}


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
            depth_dimension="strategic objectives (LLM-derived, measured)",
            # Representative int (max of the measured objective range) so
            # downstream logic reading depth_count gets a usable value; the
            # honest per-input RANGE is carried by ``measured_range`` below.
            depth_count=int(
                DELEGATION_DEPTH_MEASURED["objectives_range"].split("–")[1]
            ),
            nature="delegation (3-tier depth)",
            verdict_dimension="Strategic -> Tactical -> Operational chain",
            measured_range=(
                f"{DELEGATION_DEPTH_MEASURED['objectives_range']} objectives "
                f"-> {DELEGATION_DEPTH_MEASURED['tasks_range']} tasks "
                f"(n={DELEGATION_DEPTH_MEASURED['n_runs']}, "
                f"{DELEGATION_DEPTH_MEASURED['inputs']}, "
                f"{DELEGATION_DEPTH_MEASURED['provenance']})"
            ),
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
        if r.measured_range:
            count = r.measured_range
        elif r.depth_count > 0:
            count = str(r.depth_count)
        else:
            count = "variable (LLM-derived)"
        lines.append(f"| {r.mode} | {r.depth_dimension} | {count} | {r.nature} |")
    lines.append("")
    lines.append(_DEPTH_PARITY_TRADEOFF_VERDICT)
    lines.append("")
    return "\n".join(lines)


# ── Mode runners ─────────────────────────────────────────────────────────


def _planned_workflow_phase_count(workflow_name: str) -> int:
    """C3 #1500: the PLANNED phase total for a workflow_name (deterministic).

    Used at the pipeline budget-breach path so the Phases column reads
    ``completed/planned`` (e.g. 8/15) instead of the nonsensical ``N/0`` the
    pre-C3 breach path left. Same builders ``compute_depth_parity`` introspects
    — read honestly, never fabricated. Returns 0 only if the builder is
    unavailable (e.g. partial import), in which case the column falls back to
    ``completed/0`` rather than inventing a number.
    """
    try:
        from argumentation_analysis.orchestration.workflows import (
            build_full_workflow,
            build_light_workflow,
            build_standard_workflow,
        )

        builders = {
            "light": build_light_workflow,
            "standard": build_standard_workflow,
            "full": build_full_workflow,
        }
        builder = builders.get(workflow_name)
        if builder is None:
            return 0
        return len(builder().phases)
    except Exception:
        return 0


async def run_pipeline_mode(
    text: str,
    corpus_id: str,
    workflow_name: str = "standard",
    max_wall_seconds: Optional[float] = None,
) -> ModeResult:
    """Run UnifiedPipeline (modern workflow engine).

    CB #1528: when ``max_wall_seconds`` is set, the bound is enforced by
    ``asyncio.wait_for`` AROUND ``run_unified_analysis`` — but the analysis
    state is created HERE and passed BY REFERENCE, so a level torn
    mid-``asyncio.gather`` by the cancellation still leaves behind the
    completed levels' artifacts. State writers run per-phase only AFTER each
    level's gather completes (workflow_dsl.py:498 → :788), so the partial
    state is exactly the verdict of the levels that finished — anti-#1019 (a
    real bounded verdict, not a killed coroutine that lost everything). The
    recording ``checkpoint_callback`` counts COMPLETED phases at each level; a
    torn level never reaches its checkpoint, so ``phases_completed`` cannot be
    inflated by a half-finished level (coord R709 guard a).

    ``max_wall_seconds=None`` (default) = unbounded — the original pre-CB
    path. Bounding is opt-in (anti-pendule: bornant ≠ désactiver).
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    scope = "UnifiedPipeline DAG workflow"
    start = time.time()

    # CB #1528: state-reference trick + recording checkpoint (bound only).
    state = None
    last_completed = [0]
    checkpoint_callback = None
    if max_wall_seconds is not None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(text)

        def _record_completed(results, _ctx):
            # Recording only — never raises, so the executor's
            # ``except Exception`` checkpoint swallow (workflow_dsl.py:507)
            # cannot silence it. Fires after each fully-gathered level, so
            # ``last_completed[0]`` = COMPLETED phases from FINISHED levels
            # only — a level torn mid-gather never reaches here (guard a).
            try:
                last_completed[0] = sum(
                    1
                    for r in results.values()
                    if getattr(getattr(r, "status", None), "name", "") == "COMPLETED"
                )
            except Exception:
                pass  # recording must never disturb the pipeline

        checkpoint_callback = _record_completed

    try:
        if max_wall_seconds is not None:
            result = await asyncio.wait_for(
                run_unified_analysis(
                    text=text,
                    workflow_name=workflow_name,
                    state=state,
                    checkpoint_callback=checkpoint_callback,
                ),
                timeout=max_wall_seconds,
            )
        else:
            result = await run_unified_analysis(text=text, workflow_name=workflow_name)
    except asyncio.TimeoutError:
        duration = time.time() - start
        logger.warning(
            f"pipeline_{workflow_name} on {corpus_id} hit the "
            f"{max_wall_seconds:g}s wall-clock budget after {duration:.2f}s "
            f"— recovering partial state from the state reference "
            f"(completed levels only; torn level not counted)."
        )
        snapshot: Dict[str, Any] = {}
        try:
            snapshot = state.get_state_snapshot() or {}
        except Exception:
            snapshot = {}
        total_fields = len(snapshot) if snapshot else 1
        non_empty = sum(
            1 for v in snapshot.values() if v and v not in ([], {}, "", None, 0)
        )
        # C3 #1500 (coord R710 wart): set the PLANNED phase total at breach so
        # the report's Phases column reads ``completed/planned`` (e.g. 8/15),
        # not the nonsensical ``N/0`` left by the pre-C3 breach path. The
        # planned total is deterministic for a given workflow_name (same builder
        # ``compute_depth_parity`` introspects) — read honestly, not fabricated.
        planned_total = _planned_workflow_phase_count(workflow_name)
        return ModeResult(
            mode=f"pipeline_{workflow_name}",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            state_fill_rate=round(non_empty / max(total_fields, 1), 3),
            phases_completed=last_completed[0],
            phases_total=planned_total,
            # `decides` left None → _compute_decides in run_all. A partial
            # state (fill>0) or any completed phase ⇒ True (anti-#1019:
            # the partial state IS the verdict).
            scope_of_work=scope,
        )

    duration = time.time() - start
    summary = result.get("summary", {})
    snap = result.get("state_snapshot", {})

    total_fields = len(snap) if snap else 1
    non_empty = sum(
        1 for v in (snap or {}).values() if v and v not in ([], {}, "", None, 0)
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
        scope_of_work=scope,
    )


async def run_conversational_mode(
    text: str,
    corpus_id: str,
    max_wall_seconds: float = DEFAULT_CONVERSATIONAL_WALL_SECONDS,
) -> ModeResult:
    """Run conversational orchestrator (AgentGroupChat multi-agent).

    C1 #1500: the wall-clock bound is enforced INTERNALLY by
    ``run_conversational_analysis(max_wall_seconds=...)`` — when the deadline
    is reached the orchestrator exits cleanly between turns and the PARTIAL
    state accumulated so far IS the verdict (a real bounded verdict,
    anti-#1019 — not a ``return None`` nor a coroutine killed by
    ``asyncio.wait_for`` that would lose the partial state).

    ``asyncio.wait_for`` is retained only as a safety net at a headroom margin
    (see ``_conversational_safety_net_timeout``); the internal bound is
    expected to fire first.

    Outcomes:
      * Internal bound fired (common on a real LLM): ``success=True``,
        ``terminates=True``, ``decides=True`` (real partial verdict), with
        ``extra_metrics["wall_clock_bounded"]=True`` as the honest nuance.
      * Safety-net timeout (rare — single in-flight call hung past the
        between-turn check): ``success=False``, ``terminates=True``,
        ``terminated_by_budget=True`` (honest partial, never faked into
        success — anti-#1019).
    """
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    scope = (
        "AgentGroupChat multi-agent (3 macro-phases, "
        f"wall-time-bounded at {max_wall_seconds:g}s)"
    )
    start = time.time()
    safety_net = _conversational_safety_net_timeout(max_wall_seconds)
    try:
        result = await asyncio.wait_for(
            run_conversational_analysis(text=text, max_wall_seconds=max_wall_seconds),
            timeout=safety_net,
        )
    except asyncio.TimeoutError:
        duration = time.time() - start
        logger.warning(
            f"Conversational mode on {corpus_id} hit the {safety_net:g}s "
            f"safety-net (internal {max_wall_seconds:g}s bound did not exit "
            f"in time) after {duration:.2f}s — recording honest partial."
        )
        return ModeResult(
            mode="conversational",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            error=f"Safety-net timeout (>={safety_net:g}s)",
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

    budget = result.get("budget", {}) if isinstance(result, dict) else {}
    wall_clock_bounded = bool(budget.get("wall_clock_bounded", False))

    state = result.get("state_snapshot", {})
    total_fields = len(state) if state else 1
    non_empty = sum(
        1 for v in (state or {}).values() if v and v not in ([], {}, "", None, 0)
    )

    planned_phases = result.get("phases", []) if isinstance(result, dict) else []
    conv_log = result.get("conversation_log", []) if isinstance(result, dict) else []
    # Honest phase count: only planned macro-phases that actually produced an
    # agent message. A phase skipped by the wall-clock bound does NOT count
    # (anti-théâtre #1019 — no inflated phases_completed for an empty partial).
    phases_ran = {
        m.get("phase")
        for m in conv_log
        if isinstance(m, dict) and m.get("phase") in planned_phases
    }
    total_messages = result.get("total_messages", 0) if isinstance(result, dict) else 0

    return ModeResult(
        mode="conversational",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=round(non_empty / max(total_fields, 1), 3),
        fallacy_count=result.get("extra_metrics", {}).get("fallacy_count", 0),
        phases_completed=len(phases_ran),
        phases_total=len(planned_phases),
        capabilities_used=result.get("capabilities_used", []),
        # Track CA #1529: `decides` is no longer hand-set here — run_all
        # computes it uniformly from phases_completed + total_messages below.
        terminated_by_budget=False,
        scope_of_work=scope,
        extra_metrics={
            "total_messages": total_messages,
            "duration_seconds_raw": result.get("duration_seconds", 0),
            "wall_clock_bounded": wall_clock_bounded,
            "conversational_status": result.get("status"),
        },
    )


async def run_conversation_deterministic_mode(
    text: str, corpus_id: str, max_wall_seconds: Optional[float] = None
) -> ModeResult:
    """Run ConversationOrchestrator in demo mode (SimulatedAgent, no LLM).

    CB #1528: ``max_wall_seconds`` is accepted for signature uniformity with
    the other runners (so ``run_all`` can thread it to every mode) but is
    IGNORED — this runner is deterministic and LLM-free, so it always
    completes in milliseconds; bounding it would be dead code.
    """
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
        # Track CA #1529: `decides` computed uniformly (phases_completed=3 → True).
        scope_of_work=("ConversationOrchestrator(mode=demo, SimulatedAgent, no LLM)"),
        extra_metrics={
            "messages_count": conv_state.get("messages_count", 0),
            "tools_count": conv_state.get("tools_count", 0),
            "processing_time": conv_state.get("processing_time", 0),
        },
    )


async def run_hierarchical_bridge_mode(
    text: str, corpus_id: str, max_wall_seconds: Optional[float] = None
) -> ModeResult:
    """Run hierarchical analysis via the bridge mode (M2 default).

    The bridge mode short-circuits the 3-tier chain via
    ``objectives_to_workflow`` -> ``WorkflowExecutor`` (Lego/DAG).
    It is the post-#1474 + #1476 + #1478 + #1479 wiring: the harness
    must call the REAL entry-point ``run_hierarchical_analysis`` with a
    populated ``CapabilityRegistry``, NOT the legacy ``HierarchicalOrchestrator().
    analyze()`` (which predates the registry and never distinguishes
    bridge vs delegation).

    CB #1528: ``run_hierarchical_analysis`` exposes NO incremental state, so a
    wall-clock breach cannot recover a partial verdict — the honest degrade is
    a sterile ``terminated_by_budget=True`` result (``decides`` → False → ``—``
    via ``_compute_decides``). This is the structural asymmetry with the
    pipeline (state-reference trick): documented here, not papered over.
    """
    from argumentation_analysis.orchestration.hierarchical.orchestrator import (
        run_hierarchical_analysis,
    )
    from argumentation_analysis.orchestration.registry_setup import (
        setup_registry,
    )

    scope = (
        "Strategic planning -> objectives_to_workflow -> "
        "WorkflowExecutor (Lego/DAG, 4 axes)"
    )
    start = time.time()
    registry = setup_registry(include_optional=True)
    coro = run_hierarchical_analysis(
        text=text,
        capability_registry=registry,
        mode="bridge",
    )
    try:
        if max_wall_seconds is not None:
            result = await asyncio.wait_for(coro, timeout=max_wall_seconds)
        else:
            result = await coro
    except asyncio.TimeoutError:
        duration = time.time() - start
        logger.warning(
            f"hierarchical_bridge on {corpus_id} hit the "
            f"{max_wall_seconds:g}s budget after {duration:.2f}s — honest "
            f"degrade (no incremental state exposed → sterile partial)."
        )
        return ModeResult(
            mode="hierarchical_bridge",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            error=f"Wall-clock budget (>={max_wall_seconds:g}s)",
            scope_of_work=scope,
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
            scope_of_work=scope,
        )
    duration = time.time() - start

    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    phases_completed = summary.get("completed", 0)
    phases_total = summary.get("total", 0)
    # Bridge mode DÉCIDE firsthand via real agents when the registry is
    # populated: it returns a `conclusion` (R644). Track CA #1529: we no longer
    # hand-set `decides` — instead we stash the mode-specific verdict artifact
    # (conclusion / strategic_decision / governance-decoded-firsthand flag)
    # into the uniform `extra_metrics["verdict_artifact"]` channel, and run_all
    # computes `decides` uniformly via `_compute_decides`. This documents that a
    # strategic conclusion counts as deciding EVEN WITHOUT shared-state fill
    # (the DoD-4 #1529 case: bridge 0.0 % fill but Decides ✅ is legitimate).
    verdict_artifact = None
    if isinstance(result, dict):
        verdict_artifact = (
            result.get("conclusion")
            or result.get("strategic_decision")
            or (
                "governance_decided_firsthand"
                if result.get("governance_decided_firsthand") is True
                else None
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
        scope_of_work=(
            "Strategic planning -> objectives_to_workflow -> "
            "WorkflowExecutor (Lego/DAG, 4 axes)"
        ),
        extra_metrics={
            "objectives_count": (
                len(result.get("objectives", [])) if isinstance(result, dict) else 0
            ),
            "verdict_artifact": verdict_artifact,
        },
    )


async def run_hierarchical_delegation_mode(
    text: str, corpus_id: str, max_wall_seconds: Optional[float] = None
) -> ModeResult:
    """Run hierarchical analysis via the delegation mode (M3, RA-10 #1069).

    True strategic -> tactical -> operational delegation driven by
    explicit sequential calls (5/5 tasks when the registry is fully
    populated, per R648+R649+R651+R652). Wired via
    ``run_hierarchical_analysis(..., mode="delegation")``.

    CB #1528: same honest-degrade contract as bridge —
    ``run_hierarchical_analysis`` exposes no incremental state, so a
    wall-clock breach yields a sterile ``terminated_by_budget=True`` result
    (``decides`` → False → ``—``).
    """
    from argumentation_analysis.orchestration.hierarchical.orchestrator import (
        run_hierarchical_analysis,
    )
    from argumentation_analysis.orchestration.registry_setup import (
        setup_registry,
    )

    scope = (
        "Strategic -> Tactical -> Operational (3-tier, "
        "5 tasks via CapabilityRegistry)"
    )
    start = time.time()
    registry = setup_registry(include_optional=True)
    coro = run_hierarchical_analysis(
        text=text,
        capability_registry=registry,
        mode="delegation",
    )
    try:
        if max_wall_seconds is not None:
            result = await asyncio.wait_for(coro, timeout=max_wall_seconds)
        else:
            result = await coro
    except asyncio.TimeoutError:
        duration = time.time() - start
        logger.warning(
            f"hierarchical_delegation on {corpus_id} hit the "
            f"{max_wall_seconds:g}s budget after {duration:.2f}s — honest "
            f"degrade (no incremental state exposed → sterile partial)."
        )
        return ModeResult(
            mode="hierarchical_delegation",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            error=f"Wall-clock budget (>={max_wall_seconds:g}s)",
            scope_of_work=scope,
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
            scope_of_work=scope,
        )
    duration = time.time() - start

    # C3 #1500 fold-in (coord R710 FINDING): read the keys
    # ``DelegationOrchestrator.analyze`` ACTUALLY emits (delegation_orchestrator.
    # py:341-348) — ``objectives`` / ``tasks_created`` / ``operational_results``
    # / ``evaluation`` / ``conclusion``. The previous reader read ``summary`` and
    # ``capabilities_used``, two keys the mode NEVER emits, so the report line
    # showed ``0/0`` phases + ``0.0%`` fill on a run where 5 tasks really
    # executed. Those zeros were UNREAD FIELDS, not measurements. (Bridge mode
    # IS correctly read — it emits ``summary`` via WorkflowExecutor,
    # orchestrator.py:209.) Anti-pendule: the mode already has the data; we read
    # it instead of fabricating a ``summary`` surface orchestrator-side.
    objectives = result.get("objectives", []) if isinstance(result, dict) else []
    tasks_created = result.get("tasks_created", 0) if isinstance(result, dict) else 0
    operational_results = (
        result.get("operational_results", []) if isinstance(result, dict) else []
    )
    evaluation = result.get("evaluation", {}) if isinstance(result, dict) else {}

    # Phases column = the delegation depth axis DoD-3 asks for. Denominator =
    # tactical task count (``tasks_created``); numerator = tasks that reached a
    # completed state. Status values are ``completed`` / ``completed_with_issues``
    # / ``failed`` (operational/adapters/rhetorical_tools_adapter.py:147 +
    # delegation_orchestrator.py:213). ``completed_with_issues`` still produced
    # output → counts as completed (anti-#1019: honest, not punitive).
    def _count_status(results: List[Dict[str, Any]], prefix: str) -> int:
        return sum(
            1
            for r in results
            if isinstance(r, dict) and str(r.get("status", "")).startswith(prefix)
        )

    phases_total = tasks_created
    phases_completed = _count_status(operational_results, "completed")
    tasks_failed = _count_status(operational_results, "failed")

    # Track CA #1529: ``decides`` is computed UNIFORMLY by run_all via
    # ``_compute_decides``. Post-fold-in it keys on ``phases_completed > 0``
    # (real completed operational tasks) — a genuine signal — in addition to
    # the stashed verdict artifact (the strategic conclusion). NB (CC #1531):
    # pre-CC-fix the conclusion was a false positive on starved input; post-CC
    # (merged dd616d6f) the corpus reaches the operational tier, so the
    # conclusion now reflects real work. ``_compute_decides`` is NOT touched.
    verdict_artifact = None
    if isinstance(result, dict):
        verdict_artifact = result.get("conclusion") or result.get("strategic_decision")

    return ModeResult(
        mode="hierarchical_delegation",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 2),
        phases_completed=phases_completed,
        phases_total=phases_total,
        scope_of_work=scope,
        extra_metrics={
            "objectives_count": len(objectives),
            "verdict_artifact": verdict_artifact,
            # Honest signals (C3 #1500): the strategic tier's own evaluation of
            # how much of the delegated work genuinely succeeded + the task
            # status breakdown. Surfaced, not buried in a single 0/0.
            "overall_success_rate": evaluation.get("overall_success_rate"),
            "tasks_completed": phases_completed,
            "tasks_failed": tasks_failed,
        },
    )


# Backward-compat alias kept for downstream scripts that previously
# invoked `hierarchical` as a single-mode runner. The new world has
# TWO comparable sub-modes (bridge + delegation) — point the alias
# at the bridge default for compatibility while documenting the
# deprecation (the issue body of #1480 covers the full migration).
async def run_hierarchical_mode(
    text: str, corpus_id: str, max_wall_seconds: Optional[float] = None
) -> ModeResult:
    """Deprecated alias for ``run_hierarchical_bridge_mode``.

    Kept so that ``--modes hierarchical`` on an old caller does not
    silently break; the alias routes to bridge (the historical default).
    New code should request ``hierarchical_bridge`` or
    ``hierarchical_delegation`` explicitly. Forwards ``max_wall_seconds``
    (CB #1528).
    """
    return await run_hierarchical_bridge_mode(text, corpus_id, max_wall_seconds)


# ── Mode registry ────────────────────────────────────────────────────────
#
# The previous registry listed ``cluedo_baseline`` and ``cluedo_extended``
# as runners; both were dead-code ``success=False`` stubs ("not yet wired
# for text analysis"). Anti-pendule strict: we REMOVE them from the
# harness rather than carry them as fake modes. They are out of scope
# for the comparative trade-off — cluedo is a Sherlock-Watson game, not
# an argumentation-analysis mode comparable to the others.

MODE_RUNNERS: Dict[str, Callable[..., Awaitable[ModeResult]]] = {
    "pipeline": lambda text, cid, max_wall_seconds=None: run_pipeline_mode(
        text, cid, "standard", max_wall_seconds=max_wall_seconds
    ),
    "pipeline_light": lambda text, cid, max_wall_seconds=None: run_pipeline_mode(
        text, cid, "light", max_wall_seconds=max_wall_seconds
    ),
    "pipeline_full": lambda text, cid, max_wall_seconds=None: run_pipeline_mode(
        text, cid, "full", max_wall_seconds=max_wall_seconds
    ),
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
      ✅ terminates=True, success=True (clean completion)
      ✅⏱ bounded — success on a wall-clock-bounded PARTIAL verdict (C1 #1500):
            the conversational mode exited cleanly at the bound and the partial
            state IS the verdict (real, comparable — not a killed coroutine).
      ⏱ terminates=True, terminated_by_budget=True (honest partial — safety-net
            timeout fired, no verdict produced)
      ❌ terminates=False (real failure / exception)

    Decides column (CB #1528 folds-in): ``✅`` produced ≥1 verdict artifact,
    ``—`` computed "no artifact" (e.g. a sterile safety-net cut), ``?``
    indeterminate (a result that bypassed ``_compute_decides`` — should not
    appear via ``run_all``, which normalizes every result).
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
        elif r.extra_metrics.get("wall_clock_bounded"):
            status = "✅⏱ bounded"
        elif r.terminates and r.success:
            status = "✅"
        else:
            status = "❌"
        # CB #1528 folds-in: distinguish the 3 documented `decides` states.
        # `run_all` normalizes every result via `_compute_decides` before
        # reporting, so True/False are the common cases. A direct
        # `generate_report` caller passing un-normalized results would have
        # `decides=None` (indeterminate) — render `?`, NOT `—` (anti-#1019:
        # "I didn't check" is not "I checked, nothing").
        if r.decides is True:
            decides = "✅"
        elif r.decides is False:
            decides = "—"
        else:
            decides = "?"
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
        max_wall_seconds: Wall-clock budget (CB #1528) threaded to EVERY
            runner — pipeline (state-reference trick → real partial verdict),
            conversational (internal bound, C1 #1500), hierarchical (honest
            degrade — no incremental state exposed → sterile ``—``). Breach is
            recorded as a HONEST PARTIAL verdict (``terminated_by_budget=True``)
            — never faked into success (anti-#1019).
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
        print(f"Wall-clock budget (all modes, CB #1528): {max_wall_seconds:g}s")
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
                # CB #1528: the wall-clock budget is now threaded to EVERY
                # runner (uniform signature ``runner(text, cid, max_wall_seconds=...)``).
                # Pipeline applies the state-reference trick; conversational
                # its internal bound (C1); hierarchical honest-degrades.
                result = await runner(
                    text, corpus_id, max_wall_seconds=max_wall_seconds
                )
                results.append(result)
                if result.terminated_by_budget:
                    status = f"BUDGET BREACH ({result.duration_seconds:.2f}s)"
                    # CB #1528 guard (b): measure cross-mode cancellation
                    # contamination. A breached mode's `asyncio.wait_for`
                    # cancels in-flight work; if it leaks dangling tasks they
                    # can inflate the NEXT mode's wall-time. Measured +
                    # reported, NOT masked by re-ordering (coord R709).
                    pending = _count_pending_async_tasks()
                    if pending:
                        logger.warning(
                            f"  → contamination risk: {pending} pending async "
                            f"task(s) survived the {mode} breach on {corpus_id}"
                        )
                        result.extra_metrics["pending_tasks_after_breach"] = pending
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

    # Track CA #1529: compute `decides` UNIFORMLY for every mode from the
    # common ModeResult fields — the single source of truth, so no runner can
    # hand-set it on a local criterion. A budget breach that still produced
    # partial artifacts honestly decides True (the partial state IS the
    # verdict, anti-#1019); a genuinely sterile run (conversational cut at the
    # safety-net: 0/0 phases, 0 % fill) stays False → `—`.
    for r in results:
        r.decides = _compute_decides(r)

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
