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

Three counts appear in this module and they denominate different things —
do not "reconcile" them into one (R807):

- **5 engines** — the list above: the distinct orchestration implementations.
- **9 ``MODE_RUNNERS`` keys** — the ``--modes`` dispatch surface: the 5 engines
  plus 2 pipeline workflow presets (``pipeline_light`` / ``pipeline_full``,
  same engine, different DAG) plus 2 deprecated aliases (``hierarchical``,
  ``pipeline``). ``default_modes()`` is this set minus the aliases — **7**.
  Every default key is exactly the label its runner emits (#1747), so a label
  copied out of a report is a key that dispatches.
- **N ``compute_depth_parity()`` rows** — the modes that have a *measurable*
  structural depth, one row per pipeline preset. The trade-off verdict derives
  its counts from these rows rather than restating a literal.

Usage:
    # Compare all available modes on benchmark texts
    python scripts/compare_orchestration_modes.py

    # Specific modes only
    python scripts/compare_orchestration_modes.py \\
        --modes pipeline_standard hierarchical_bridge hierarchical_delegation

    # Bound the wall-clock of every mode (default 180s)
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
from functools import lru_cache
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, FrozenSet, List, Optional, Tuple

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

# Default wall-time budget (seconds) for EVERY mode. Pre-R653, the
# conversational mode was unbounded and ran >600s on 643-octet input;
# 180s is a reasonable budget that lets a real run reach the Synthesis
# phase on a short corpus without making the harness itself a CI
# bottleneck. Overridable via --max-wall-seconds.
#
# CB #1528 item 3: the name used to carry a "conversational" qualifier and
# the CLI help still said "for the conversational mode". That was drift:
# since CB the budget is threaded to every runner (see ``run_comparison``),
# and the conversational mode is simply the one that used to overshoot it.
DEFAULT_WALL_SECONDS = 180.0


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
        terminated_by_budget — bool: True iff the run was KILLED by the
                            safety-net ``asyncio.wait_for``. This is the
                            MECHANISM, and it is deliberately narrow: a run
                            that stopped ITSELF at its own internal deadline
                            is ``False`` here and carries
                            ``extra_metrics["wall_clock_bounded"]`` instead —
                            two DIFFERENT states, not two witnesses of one
                            (C1 #1500: the graceful stop yields a real partial
                            verdict, the kill does not, and the report renders
                            them ``⏱ budget`` vs ``✅⏱ bounded``).
                            #1752: I read the pair as one state and made this
                            field read ``wall_clock_bounded``, which collapsed
                            the distinction; ``test_internal_bound_maps_to_
                            real_partial_verdict`` (#1480) caught it. What was
                            genuinely missing is the COMPARABILITY predicate —
                            "did this row hit its wall clock at all, so its
                            metrics may not be compared against a run that
                            finished on its own terms" — which is neither
                            field alone: use ``_hit_its_wall_clock(result)``.
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
    # Track CG #1540: these three are Optional with default None ("not
    # written"), NOT a zero default ("measured empty"). Same treatment as
    # `decides` (CA #1529): a runner that does not populate the shared
    # analysis state (hierarchical_bridge / hierarchical_delegation decide by
    # conclusion/verdict_artifact/phases_completed, not by state fill — see
    # _compute_decides DoD-4 #1529) must render "—" in the report, NOT a
    # falsifiable "0.0 % / 0 / 0" indistinguishable from a measured-empty run
    # (leçon #1531 / #1500: a value read from an absent field is
    # indistinguishable from a measured zero). JSON serializes None -> null;
    # downstream readers must treat null as "not applicable", not 0.
    state_fill_rate: Optional[float] = None
    fallacy_count: Optional[int] = None
    argument_count: Optional[int] = None
    phases_completed: int = 0
    phases_total: int = 0
    capabilities_used: List[str] = field(default_factory=list)
    capabilities_missing: List[str] = field(default_factory=list)
    # #1749: the THIRD capability state — "ran and returned nothing". The
    # pipeline removes degraded capabilities from ``capabilities_used`` on
    # purpose (``unified_pipeline._collect_degraded_capabilities``, "so a
    # degraded capability surfaces as degraded, NOT as used" — anti-theater
    # #1019) and emits them in their own list. Reading only two of the three
    # made that capability vanish: neither used nor missing, so a reader
    # counted full coverage on a truncated ledger.
    #
    # Optional[List] with default None, NOT ``[]`` (same convention as
    # ``state_fill_rate``, CG #1540): None = "this mode emits no ledger"
    # (renders ``n/a``); [] = "ledger emitted, nothing degraded" (renders 0).
    # An absent ledger is not an empty one — measured on the return dicts,
    # only pipeline and conversational emit the three keys; the two
    # hierarchical modes and conversation_deterministic emit none.
    capabilities_degraded: Optional[List[str]] = None
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
    # #1753: does ``capabilities_used`` list EVERY capability this run
    # exercised? Only then may a missing producer be read as "never evaluated"
    # (``n/a``). Set at the source by each runner, never inferred at the reader
    # hop. Default False = "cannot demonstrate an absence" — the safe side,
    # which shows the observed count instead of overclaiming.
    perimeter_is_exhaustive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _fmt_fill(rate: Optional[float]) -> str:
    """CG #1540: render state_fill_rate as "—" when not written (None).

    A hierarchical mode that decides by conclusion (not shared state) leaves
    state_fill_rate=None; rendering "—" (not "0.0%") distinguishes "not
    applicable" from "measured empty" (leçon #1531).
    """
    return "—" if rate is None else f"{rate:.1%}"


def _is_filled(value: Any) -> bool:
    """A state field counts as filled iff it carries something."""
    return bool(value) and value not in ([], {}, "", None, 0)


@lru_cache(maxsize=2)
def _construction_baseline_keys(summarize: bool) -> FrozenSet[str]:
    """Keys a pristine ``UnifiedAnalysisState(text)`` fills at CONSTRUCTION.

    #1566: the success paths (``run_pipeline_mode`` / ``run_conversational_mode``)
    hold only a snapshot **dict**, never the state object — so they cannot reuse
    the object-form baseline (``type(state)(raw_text)``). This helper rebuilds
    that baseline from the class, snapshotted in the SAME form as the
    measurement: ``summarize=True`` → the 41-key summarized shape
    (``raw_text`` + ``raw_text_snippet``); ``summarize=False`` → the 51-key raw
    shape (``raw_text`` + ``deanonymized`` + ``stakes_and_stakeholders``).

    A raw baseline subtracted from a summarized snapshot (or the reverse) would
    re-manufacture the drift this helper exists to remove — the ``summarize``
    arg is load-bearing, not decorative. Cached: the set depends only on the
    form, not on any run's text, so it is computed once per form per process.

    Opaque synthetic probe (privacy HARD — never a corpus string here).
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    pristine = UnifiedAnalysisState("baseline_probe_opaque_synthetic")
    snap = pristine.get_state_snapshot(summarize=summarize) or {}
    return frozenset(k for k, v in snap.items() if _is_filled(v))


def _state_fill_rate(
    snapshot_or_state: Any,
    summarize: Optional[bool] = None,
) -> Optional[float]:
    """Fraction of state fields THIS RUN filled in, or None if no state.

    ONE definition, TWO call shapes — a second helper here is how the counters
    in this file drifted before (#1560):

    * **State-object form** (breach paths): ``_state_fill_rate(state)``. The
      fill is not a statistic but the verdict signal itself — it is what
      ``_compute_decides`` reads to decide whether a cut run produced anything.
      The baseline is built from the class via ``type(state)(raw_text)``, so it
      tracks whatever subclass the runner instrumented.

    * **Snapshot-dict form** (#1566 success paths): ``_state_fill_rate(snap,
      summarize=...)``. The success returns hold only the snapshot dict the
      runner emitted (``result["state_snapshot"]``), never the object, so the
      object-form baseline is unreachable. ``summarize`` MUST match the shape
      the runner snapshotted in (pipeline → ``True`` per
      ``unified_pipeline.py``; conversational → ``False``, raw attribute names)
      so the baseline is subtracted in the SAME form as the measurement.

    The construction baseline is SUBTRACTED either way. A freshly built
    ``UnifiedAnalysisState(text)`` is not empty: it already carries
    ``raw_text`` (and ``deanonymized`` / ``stakes_and_stakeholders`` raw, or
    ``raw_text_snippet`` summarized) — ~5-6 % of fields before a phase runs.
    Counting those made an empty run score ``fill > 0``, which on a breach path
    ``_compute_decides`` read as a verdict artifact (the
    ``pipeline_standard | 0/15 phases | 5.9 % | Decides ✅`` row measured at
    R723 — 5.9 % WAS the empty baseline echoed back). On a success path no
    verdict flips (``_compute_decides`` is already carried by
    ``phases_completed > 0``), but the headline percentage was ~5-6 pts high
    and the success/breach columns were not on the same footing. #1566 puts
    them on the same footing. Same family as #1560/#1019 — a number that looks
    like a measurement and is an artifact of the instrument.

    So the numerator counts only fields a pristine state of the same form does
    NOT already fill, and the denominator is the fillable remainder.

    ``None`` (no state instrumented) and ``0.0`` (state instrumented, measured
    empty) are DIFFERENT answers and must stay so — CG #1540 / leçon #1531.
    """
    # Dict form (#1566): snapshot already computed by the runner; ``summarize``
    # selects the baseline form. A dict passed without ``summarize`` is a
    # programming error (the form is ambiguous) → refuse rather than guess.
    if isinstance(snapshot_or_state, dict):
        snapshot = snapshot_or_state
        if summarize is None:
            raise ValueError(
                "_state_fill_rate(dict, summarize=None): the snapshot form is "
                "ambiguous — pass summarize=True (summarized) or False (raw) "
                "so the baseline is subtracted in the same form."
            )
        if not snapshot:
            return 0.0
        baseline = _construction_baseline_keys(bool(summarize))
        fillable = [k for k in snapshot if k not in baseline]
        if not fillable:
            return 0.0
        non_empty = sum(1 for k in fillable if _is_filled(snapshot[k]))
        return round(non_empty / len(fillable), 3)

    # State-object form (breach paths): unchanged since #1565.
    state = snapshot_or_state
    if state is None:
        return None
    try:
        snapshot = state.get_state_snapshot() or {}
    except Exception:
        return None
    if not snapshot:
        return 0.0

    baseline: set = set()
    try:
        pristine = type(state)(getattr(state, "raw_text", "") or "")
        baseline = {
            k for k, v in (pristine.get_state_snapshot() or {}).items() if _is_filled(v)
        }
    except Exception:
        # Baseline unknown → fall back to the raw count rather than guessing.
        # Loud in the sense that matters: it can only OVER-report, and the
        # honest-degrade tests pin the sterile case.
        baseline = set()

    fillable = [k for k in snapshot if k not in baseline]
    if not fillable:
        return 0.0
    non_empty = sum(1 for k in fillable if _is_filled(snapshot[k]))
    return round(non_empty / len(fillable), 3)


def _delegation_task_counts(
    operational_results: List[Dict[str, Any]],
) -> Tuple[int, int, int]:
    """(productive, failed, degraded) task counts for the M3 delegation mode.

    ONE definition shared by the completion path and the wall-clock breach
    path, so a task counts the same way whether the run finished or was cut.

    Status values are ``completed`` / ``completed_with_issues`` / ``failed``
    (rhetorical_tools_adapter.py:147 + delegation_orchestrator.py:213).
    ``completed_with_issues`` produced output ⇒ counts (anti-#1019: honest,
    not punitive). A task carrying ``degraded: True`` ran but produced
    nothing — it keeps ``status: "completed"`` (the call did return) and is
    subtracted (CC #1531 item 1): counting it is what fed a ✅ to a run that
    analysed nothing. The discriminator is the self-declared non-analysis,
    never the emptiness of the output — a clean corpus with zero fallacies is
    a success that found zero.
    """
    completed = sum(
        1
        for r in operational_results
        if isinstance(r, dict) and str(r.get("status", "")).startswith("completed")
    )
    failed = sum(
        1
        for r in operational_results
        if isinstance(r, dict) and str(r.get("status", "")).startswith("failed")
    )
    degraded = sum(
        1 for r in operational_results if isinstance(r, dict) and r.get("degraded")
    )
    return completed - degraded, failed, degraded


def _fmt_count(count: Optional[int]) -> str:
    """CG #1540: render a count (fallacies/args) as "—" when not written."""
    return "—" if count is None else str(count)


# #1740: which capability PRODUCES each count. A count only means something if
# its producer actually ran — see ``_fmt_count_in_perimeter``.
#
# Pinned against ``CAPABILITY_STATE_WRITERS`` by the #1740 tests so these sets
# cannot drift silently when a workflow gains a capability. ⚠ Stated limit: the
# pin keys on the ``*fallacy*`` naming convention, so a fallacy capability
# introduced under an unconventional name would escape it. That hole is far
# narrower than the one being closed (a fabricated 0 on every single run), and
# it is written down rather than hidden.
_FALLACY_PRODUCING_CAPABILITIES: FrozenSet[str] = frozenset(
    {"neural_fallacy_detection", "hierarchical_fallacy_detection"}
)
_ARGUMENT_PRODUCING_CAPABILITIES: FrozenSet[str] = frozenset({"fact_extraction"})


def _hit_its_wall_clock(result: "ModeResult") -> bool:
    """Did this row hit its wall-clock budget, by EITHER route? (#1752)

    Two distinct states share this consequence and neither field spans both:

    * ``terminated_by_budget`` — the safety net fired and KILLED the run. No
      verdict of its own; the report marks it ``⏱ budget``.
    * ``extra_metrics["wall_clock_bounded"]`` — the run stopped ITSELF at its
      internal deadline and recovered a real partial verdict (C1 #1500); the
      report marks it ``✅⏱ bounded``.

    Those two must stay separate wherever the *mechanism* matters — that is
    what #1480 pins, and collapsing them is the mistake this helper exists to
    make unnecessary. But wherever the question is **comparability** ("may I
    put this row's State Fill next to a run that finished on its own terms?"),
    the answer is the same for both and the caller should not have to know
    which route was taken. Callers asking the comparability question use this;
    callers rendering the mechanism read the two fields directly.

    Deliberately NOT a ``ModeResult`` field: a third stored boolean derivable
    from two others is a third thing to keep in sync, and drift between stored
    duplicates is the defect family this instrument exists to detect.
    """
    return bool(result.terminated_by_budget) or bool(
        result.extra_metrics.get("wall_clock_bounded")
    )


def _capability_ledger_lines(result: "ModeResult") -> List[str]:
    """Render the THREE capability states for one row (#1749).

    ``used`` / ``degraded`` / ``missing`` are three states, never two. They
    call for three DIFFERENT actions, which is why folding any pair together
    destroys the actionable content:

    - ``used``     — ran, produced something.
    - ``degraded`` — ran and produced nothing (e.g. an endpoint not configured
      and the provider fails loud). Action: configure the environment.
    - ``missing``  — no provider at all. Action: wire one.

    A mode that emits NO ledger renders ``n/a``, not zeros: "0 degraded" is a
    measurement claim ("I looked and found none") that such a mode never made.
    Measured on the runners' return dicts — pipeline and conversational emit
    all three keys; ``hierarchical_bridge`` / ``hierarchical_delegation`` /
    ``conversation_deterministic`` emit none of them.

    The degraded capabilities are listed BY NAME: the corrective action is
    per-capability, so a bare count would say something is wrong without
    saying what to do about it.
    """
    no_ledger = (
        result.capabilities_degraded is None
        and not result.capabilities_used
        and not result.capabilities_missing
    )
    if no_ledger:
        return [
            f"**{result.mode}** capabilities: n/a "
            f"(mode emits no capability ledger)",
            "",
        ]

    degraded = result.capabilities_degraded
    degraded_part = "n/a" if degraded is None else str(len(degraded))
    lines = [
        f"**{result.mode}** capabilities: {len(result.capabilities_used)} used / "
        f"{degraded_part} degraded / {len(result.capabilities_missing)} missing",
    ]
    if result.capabilities_used:
        lines.append(f"  - used: {', '.join(result.capabilities_used)}")
    if degraded:
        lines.append(f"  - degraded: {', '.join(degraded)}")
    if result.capabilities_missing:
        lines.append(f"  - missing: {', '.join(result.capabilities_missing)}")
    lines.append("")
    return lines


def _fmt_count_in_perimeter(
    count: Optional[int],
    producers: FrozenSet[str],
    capabilities_used: List[str],
    perimeter_is_exhaustive: bool = False,
) -> str:
    """Render a count as ``n/a`` when its PRODUCER never ran (#1740).

    Three states, never two:

    * ``n/a``   — the producing capability is demonstrably outside the executed
      perimeter: never evaluated;
    * ``—``     — inside the perimeter (or perimeter unknown) but not written;
    * ``<int>`` — written.

    **Why this cannot be decided one hop earlier.** ``get_state_snapshot``
    derives every count as ``len()`` over a PRE-DECLARED container
    (``shared_state.py``: ``"fallacy_count": len(self.identified_fallacies)``),
    so the key is *never* absent and the "absent → None → —" convention of
    Track CG #1540 is structurally inert on this field. Three correct fixes at
    the reader hop (#1528 item 3, #1540, #1560) left the symptom untouched for
    exactly that reason — repeated fixes at one hop mean the defect is at
    another. The discriminator therefore has to come from the executed
    perimeter, not from key presence.

    ``capabilities_used`` is built from ``PhaseStatus.COMPLETED`` with degraded
    capabilities removed (``unified_pipeline.py``) — it is the EXECUTED set,
    not the declared one. So a phase cut off by the wall-clock budget reads
    ``n/a`` rather than ``0``, which matters: the #1735 baseline truncated 20
    of 24 runs.

    ⚠ An EMPTY ``capabilities_used`` means the mode reports **no perimeter at
    all** (``conversation_deterministic``), NOT an empty perimeter. Absence
    cannot be demonstrated there, so the count renders as-is — emitting ``n/a``
    would erase a genuine observation, which is the mirror-image of the defect
    being fixed.

    ⚠⚠ #1753: that guard was calibrated on **empty ↔ populated**, and production
    delivers a third shape — **populated but partial**. The conversational mode
    reports two self-declared plugin capabilities and nothing for the agents
    that actually ran, so ``fact_extraction`` is missing from a ledger whose
    run genuinely wrote 4 arguments: a real observation rendered "never
    evaluated". A ``n/a`` claims MORE than a number does — it is an epistemic
    verdict ("do not compare this cell") — so it may only be emitted by a mode
    whose ledger is *exhaustive*. ``perimeter_is_exhaustive`` is set at the
    SOURCE by each runner (never inferred here): the pipeline runners set it
    (their ledger comes from the WorkflowExecutor and is complete); the
    conversational and hierarchical runners do not. Default ``False`` = "I
    cannot demonstrate an absence", which degrades to showing the count.
    """
    if (
        perimeter_is_exhaustive
        and capabilities_used
        and not (set(capabilities_used) & producers)
    ):
        return "n/a"
    return _fmt_count(count)


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
    sterile run stays ``False`` → ``—``: 0/0 phases, 0 messages, and NO state
    written at all (``state_fill_rate is None`` since Track CG #1540 — the
    safety-net branch builds its ``ModeResult`` without those fields, so the
    old "0 % fill" wording here described a measurement that never happens).

    Track CG #1540: ``state_fill_rate`` / ``argument_count`` / ``fallacy_count``
    are now Optional (None = "not written", e.g. hierarchical modes that decide
    by conclusion). ``None`` is NOT an artifact of verdict and must not trigger
    ``True`` (it would manufacture a decision from absence) NOR raise
    (``None > 0`` is a TypeError in Py3). The ``or 0`` coercion makes the check
    None-safe without changing the semantics for real measurements (0 stays 0,
    >0 stays >0).
    """
    if (result.state_fill_rate or 0) > 0:
        return True
    if (result.argument_count or 0) > 0 or (result.fallacy_count or 0) > 0:
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


def _depth_parity_tradeoff_verdict(rows: List[DepthParityRow]) -> str:
    """Render the trade-off verdict with counts DERIVED from ``rows``.

    R807: the counts used to be hardcoded prose ("The 4 modes ... three
    different depth dimensions") while ``compute_depth_parity`` had grown to
    emit more rows — a count that stopped reading the structure it describes
    (the #1019 family in miniature). Deriving them keeps the sentence honest
    when a mode is added or removed; bumping the literal would rot identically.

    The *dimension family* is the nature up to its first parenthesis, so
    ``"delegation"`` / ``"delegation (3-tier depth)"`` count once, as do
    ``"dialogue-depth"`` / ``"dialogue-depth (no LLM)"``.
    """
    n_modes = len(rows)
    families = {r.nature.split(" (")[0].strip() for r in rows}
    n_families = len(families)
    return (
        f"The {n_modes} modes are comparable in interface (all produce a "
        "verdict on the same synthetic input) but NOT in work-perimeter. "
        f"They occupy {n_families} "
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
    lines.append(_depth_parity_tradeoff_verdict(rows))
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
            # CB #1528 item 2: shared with the hierarchical bridge breach path
            # (one definition, two call-sites).
            state_fill_rate=_state_fill_rate(state),
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

    # #1566: the fill is the SAME definition as the breach path (baseline
    # subtracted), via the snapshot-dict form. ``unified_pipeline`` returns
    # ``get_state_snapshot(summarize=True)`` (shared_state.py:358-359), so the
    # baseline must be subtracted in the summarized form — the 41-key shape,
    # not the 51-key raw one.
    # #1560: the counts are MEASURED from the snapshot the pipeline returns.
    # ``result["extra_metrics"]`` has NO producer anywhere in the package, so
    # ``.get("extra_metrics", {}).get("fallacy_count", 0)`` returned its literal
    # default on every run — a 0 indistinguishable from an observed 0 (leçon
    # #1531). What gave it away was invariance: identical 0/0 before AND after
    # #1553 changed the resolution the pipeline uses. Same phantom-key defect as
    # the one already fixed for the conversational runner (CB #1528 item 3).
    #
    # ⚠ INVERSE polarity from that fix: ``unified_pipeline`` returns
    # ``get_state_snapshot(summarize=True)``, whose shape carries ``fallacy_count``
    # / ``argument_count`` FLAT at top level (shared_state.py:358-359) — NOT the
    # raw ``identified_*`` collections the conversational runner reads. Copying
    # that fix verbatim yields None everywhere while looking correct.
    def _summarized_count(key: str) -> Optional[int]:
        value = (snap or {}).get(key)
        # Absent (or drifted to a non-count shape) → None → "—" (Track CG #1540).
        # Never a fabricated 0.
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value

    return ModeResult(
        mode=f"pipeline_{workflow_name}",
        corpus_id=corpus_id,
        success=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=_state_fill_rate(snap, summarize=True),
        fallacy_count=_summarized_count("fallacy_count"),
        argument_count=_summarized_count("argument_count"),
        phases_completed=summary.get("completed", 0),
        phases_total=summary.get("total", 0),
        capabilities_used=result.get("capabilities_used", []),
        capabilities_missing=result.get("capabilities_missing", []),
        # #1749: no ``[]`` default — an absent key must land on None ("no
        # ledger" -> n/a), never on a ``[]`` that would assert "looked, found
        # none". That fabricated-default shape is the phantom-key defect this
        # file has already been bitten by twice (CB #1528 item 3, #1560).
        capabilities_degraded=result.get("capabilities_degraded"),
        # #1753: the pipeline ledger comes from the WorkflowExecutor, which
        # sees every phase — so an absent producer here really does mean "not
        # in the executed perimeter", and ``n/a`` is earned. This is the ONE
        # runner that may claim it; the others cannot.
        perimeter_is_exhaustive=True,
        scope_of_work=scope,
    )


async def run_conversational_mode(
    text: str,
    corpus_id: str,
    max_wall_seconds: float = DEFAULT_WALL_SECONDS,
    room_policy: str = "phase_casting",
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
        f"wall-time-bounded at {max_wall_seconds:g}s, room={room_policy})"
    )
    start = time.time()
    safety_net = _conversational_safety_net_timeout(max_wall_seconds)
    try:
        result = await asyncio.wait_for(
            run_conversational_analysis(
                text=text, max_wall_seconds=max_wall_seconds, room_policy=room_policy
            ),
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
    snapshot = state if isinstance(state, dict) else {}
    # #1566: same fill definition as the breach path (baseline subtracted),
    # via the snapshot-dict form. The conversational snapshot is the raw
    # (non-summarized) one — 51-key shape, raw attribute names — so the
    # baseline is subtracted in the raw form (summarize=False).

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

    # CB #1528 item 3: the counts are MEASURED from the state snapshot the
    # orchestrator returns. ``result["extra_metrics"]`` is a key it NEVER
    # emits, so reading ``.get("extra_metrics", {}).get("fallacy_count", 0)``
    # manufactured a 0 indistinguishable from an observed 0 (leçon #1531), and
    # ``argument_count`` was not read at all — a populated state rendered "—"
    # in the Args column. The snapshot is the non-summarized one (raw attribute
    # names, ``identified_arguments`` / ``identified_fallacies``), NOT the
    # summarized ``*_count`` shape. Absent key → None ("not written", Track CG
    # #1540), never a fabricated 0.
    def _snapshot_count(key: str) -> Optional[int]:
        value = snapshot.get(key)
        if value is None:
            return None
        try:
            return len(value)
        except TypeError:
            return None

    return ModeResult(
        mode="conversational",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 2),
        state_fill_rate=_state_fill_rate(snapshot, summarize=False),
        fallacy_count=_snapshot_count("identified_fallacies"),
        argument_count=_snapshot_count("identified_arguments"),
        phases_completed=len(phases_ran),
        phases_total=len(planned_phases),
        capabilities_used=result.get("capabilities_used", []),
        # #1749: the defect blinds BOTH ledger-emitting modes. Fixing only the
        # pipeline would leave this row silently truncated — and the
        # conversational mode is the one whose ledger is already known to be
        # non-exhaustive (#1753), so a dropped degradation here is the harder
        # one to notice. Same no-default rule as the pipeline runner.
        capabilities_degraded=result.get("capabilities_degraded"),
        # Track CA #1529: `decides` is no longer hand-set here — run_all
        # computes it uniformly from phases_completed + total_messages below.
        # #1752 (CORRECTED): this ``False`` is CORRECT and deliberate, not the
        # constant I first took it for. This runner enforces its bound
        # INTERNALLY and recovers a real partial verdict; the safety net did
        # not fire, so the KILL flag is False while
        # ``extra_metrics["wall_clock_bounded"]`` (set below) records the
        # graceful bound. The tell I misread: every other runner sets this
        # field only on an EXCEPTION path — which is the field's definition,
        # not an anomaly. Readers wanting "hit its wall clock at all" must use
        # ``_hit_its_wall_clock``, not this field.
        terminated_by_budget=False,
        scope_of_work=scope,
        extra_metrics={
            "total_messages": total_messages,
            "duration_seconds_raw": result.get("duration_seconds", 0),
            "wall_clock_bounded": wall_clock_bounded,
            "conversational_status": result.get("status"),
            # CE #1537: which path actually ran. Defensive default is the
            # fallback so an absent field never reads as "agent_group_chat"
            # (anti-#1019 / leçon #1531: absent ≠ measured).
            "execution_path": result.get("execution_path", "round_robin_fallback"),
            # #1760: the steering couple. A fix is judged on BOTH numbers —
            # designations_unresolved must fall AND distinct agents having
            # actually spoken must rise. The first alone goes to zero by
            # forbidding designations, which is the false fix the DoD names.
            "room_policy": room_policy,
            "designations_emitted": budget.get("deliberation_turn_count"),
            "designations_unresolved": len(budget.get("designations_unresolved") or []),
            "distinct_speakers": sorted(
                {
                    m.get("agent")
                    for m in conv_log
                    if isinstance(m, dict) and m.get("agent")
                }
            ),
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
    # #1566 tranche (coord R730 left this 5th site open): the deterministic
    # orchestrator exposes NO UnifiedAnalysisState — it publishes a weighted
    # QUALITY grade (conversation_orchestrator.py:
    # sophistication*0.4 + logical*0.3 + unified*0.3) in ``state.score``.
    # Publishing that grade in the State Fill column put a different QUANTITY
    # under the same name (the metric-named-beyond-its-calculation family).
    # Branch A (kept): state_fill_rate=None (renders "—", CG #1540
    # not-applicable, NOT measured-empty) and the grade moves to
    # extra_metrics["quality_score"]. Branch B (invent a field-fraction for an
    # orchestrator that exposes no UnifiedAnalysisState) = fabrication, rejected.
    quality_score = conv_state.get("state", {}).get("score", 0)

    return ModeResult(
        mode="conversation_deterministic",
        corpus_id=corpus_id,
        success=True,
        terminates=True,
        duration_seconds=round(duration, 3),
        state_fill_rate=None,
        # #1740: absent key → None → "—", never a fabricated 0. This site kept
        # a literal ``0`` default long after the same defect was fixed for the
        # two other runners (#1528 item 3 / #1560) — currently populated, so it
        # was invisible; it would have manufactured a 0 the day the key moved.
        fallacy_count=conv_state.get("state", {}).get("fallacies_detected"),
        phases_completed=3,  # informal + fol + synthesis
        phases_total=3,
        # Track CA #1529: `decides` computed uniformly (phases_completed=3 → True).
        scope_of_work=("ConversationOrchestrator(mode=demo, SimulatedAgent, no LLM)"),
        extra_metrics={
            "messages_count": conv_state.get("messages_count", 0),
            "tools_count": conv_state.get("tools_count", 0),
            "processing_time": conv_state.get("processing_time", 0),
            "quality_score": quality_score,
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

    CB #1528 item 2: when bounded, the runner passes an analysis state BY
    REFERENCE plus a recording ``checkpoint_callback``, exactly as
    ``run_pipeline_mode`` does. The bridge workflow is a strictly SEQUENTIAL
    chain (``objectives_to_workflow`` makes every phase depend on the previous
    one), so both fire once per completed phase — a breach therefore recovers
    what the finished phases produced instead of losing everything with the
    cancelled coroutine. The previous behaviour was documented here as "no
    incremental state exposed → sterile partial"; that was true of the CALL,
    not of the orchestrator, which already accepted the seam one layer down.

    ``max_wall_seconds=None`` (default) = unbounded, unchanged: no state, no
    callback, no writers (anti-pendule — the bound is opt-in and must not
    alter the free-running path).
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

    state = None
    state_writers = None
    checkpoint_callback = None
    # ``planned`` stays None until a completed level reports it. Unlike the
    # pipeline — whose planned total is a deterministic function of the
    # workflow name (``_planned_workflow_phase_count``) — the bridge's phase
    # count depends on the objectives the StrategicManager generates at
    # runtime, so it can only be read off the built workflow, in the context.
    # A breach BEFORE the first phase completes therefore leaves it unknown,
    # and ``phases_total: int`` has no "unknown" value to render: the column
    # shows 0/0. That is the field's pre-existing contract (leçon #1531 would
    # want a "—" here; making that possible means turning phases_total
    # Optional across all 8 runners + both report tables, which is a change to
    # the report schema, not to this bound). Not silently papered over.
    recorded: Dict[str, Any] = {"completed": 0, "planned": None}
    if max_wall_seconds is not None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        state = UnifiedAnalysisState(text)
        state_writers = CAPABILITY_STATE_WRITERS

        def _record_completed(results, ctx):
            # Recording only — never raises (the executor swallows callback
            # errors, so a throw here would be silenced, not surfaced).
            try:
                recorded["completed"] = sum(
                    1
                    for r in results.values()
                    if getattr(getattr(r, "status", None), "name", "") == "COMPLETED"
                )
                planned = (ctx or {}).get("hierarchical_planned_phases")
                if isinstance(planned, int) and not isinstance(planned, bool):
                    recorded["planned"] = planned
            except Exception:
                pass

        checkpoint_callback = _record_completed

    coro = run_hierarchical_analysis(
        text=text,
        capability_registry=registry,
        mode="bridge",
        state=state,
        state_writers=state_writers,
        checkpoint_callback=checkpoint_callback,
    )
    try:
        if max_wall_seconds is not None:
            result = await asyncio.wait_for(coro, timeout=max_wall_seconds)
        else:
            result = await coro
    except asyncio.TimeoutError:
        duration = time.time() - start
        fill = _state_fill_rate(state)
        logger.warning(
            f"hierarchical_bridge on {corpus_id} hit the "
            f"{max_wall_seconds:g}s budget after {duration:.2f}s — recovering "
            f"the partial verdict from the state reference "
            f"({recorded['completed']} completed phase(s), fill="
            f"{'—' if fill is None else f'{fill:.1%}'}; the torn phase is not "
            f"counted)."
        )
        return ModeResult(
            mode="hierarchical_bridge",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            state_fill_rate=fill,
            phases_completed=recorded["completed"],
            phases_total=recorded["planned"] or 0,
            error=f"Wall-clock budget (>={max_wall_seconds:g}s)",
            # `decides` left None → _compute_decides in run_all: a completed
            # phase or a non-empty state IS the partial verdict; nothing
            # recovered stays honestly sterile (— , not a manufactured ✅).
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

    CB #1528 item 2: when bounded, the runner passes a recording
    ``checkpoint_callback`` fired after each completed operational task. The
    T→O loop is strictly sequential, so a breach recovers exactly the tasks
    that finished — the same "accumulated work IS the partial verdict" contract
    as the pipeline, in the shape this mode has (task results, not a shared
    state: it has no ``UnifiedAnalysisState`` surface to fill, which is why
    ``state_fill_rate`` legitimately stays ``—`` here).
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

    checkpoint_callback = None
    recorded: Dict[str, Any] = {"results": [], "planned": None}
    if max_wall_seconds is not None:

        def _record_tasks(results, ctx):
            # Recording only — never raises (the orchestrator guards the call,
            # so a throw here would be swallowed rather than surfaced).
            try:
                recorded["results"] = list(results or [])
                planned = (ctx or {}).get("planned_tasks")
                if isinstance(planned, int) and not isinstance(planned, bool):
                    recorded["planned"] = planned
            except Exception:
                pass

        checkpoint_callback = _record_tasks

    coro = run_hierarchical_analysis(
        text=text,
        capability_registry=registry,
        mode="delegation",
        checkpoint_callback=checkpoint_callback,
    )
    try:
        if max_wall_seconds is not None:
            result = await asyncio.wait_for(coro, timeout=max_wall_seconds)
        else:
            result = await coro
    except asyncio.TimeoutError:
        duration = time.time() - start
        partial = recorded["results"]
        completed, failed, degraded = _delegation_task_counts(partial)
        logger.warning(
            f"hierarchical_delegation on {corpus_id} hit the "
            f"{max_wall_seconds:g}s budget after {duration:.2f}s — recovering "
            f"the partial verdict from the checkpointed task results "
            f"({completed} productive / {len(partial)} finished; the task in "
            f"flight is not counted)."
        )
        return ModeResult(
            mode="hierarchical_delegation",
            corpus_id=corpus_id,
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=round(duration, 2),
            phases_completed=completed,
            phases_total=recorded["planned"] or 0,
            error=f"Wall-clock budget (>={max_wall_seconds:g}s)",
            # `decides` left None → _compute_decides in run_all. No verdict
            # artifact exists at breach (the strategic conclusion is produced
            # AFTER the loop), so the row decides on completed tasks alone —
            # nothing finished ⇒ honestly sterile.
            scope_of_work=scope,
            extra_metrics={
                "tasks_completed": completed,
                "tasks_failed": failed,
                "tasks_degraded": degraded,
                "tasks_finished_before_breach": len(partial),
            },
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
    # completed state. CB #1528 item 2: the counting rules live in
    # ``_delegation_task_counts`` so this path and the wall-clock breach path
    # cannot drift apart (the failure mode of #1560 was exactly a twin
    # call-site left behind).
    phases_total = tasks_created
    phases_completed, tasks_failed, tasks_degraded = _delegation_task_counts(
        operational_results
    )

    # Track CA #1529: ``decides`` is computed UNIFORMLY by run_all via
    # ``_compute_decides``. Post-fold-in it keys on ``phases_completed > 0``
    # (real completed operational tasks) — a genuine signal — in addition to
    # the stashed verdict artifact (the strategic conclusion). NB (CC #1531):
    # pre-CC-fix the conclusion was a false positive on starved input; post-CC
    # (merged dd616d6f) the corpus reaches the operational tier, so the
    # conclusion now reflects real work. ``_compute_decides`` is NOT touched.
    #
    # CC #1531 item 1: when the mode reports itself degraded (no operational
    # task produced anything), its conclusion is a degradation report, not a
    # verdict on the argumentation — so it is NOT offered as a verdict
    # artifact and the row scores ``—``. The conclusion still EXISTS and is
    # still returned by the orchestrator; suppressing it would be the mirror
    # lie the issue explicitly rules out. What changes is only whether it
    # counts as "this mode decided something about the text", which is what
    # the column claims to measure. ``_compute_decides`` itself is untouched:
    # the helper was never wrong, its input was.
    run_degraded = bool(result.get("degraded")) if isinstance(result, dict) else False
    verdict_artifact = None
    if isinstance(result, dict) and not run_degraded:
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
            "tasks_degraded": tasks_degraded,
            "degraded": run_degraded,
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
    # #1747: the CANONICAL key is ``pipeline_standard`` — identical to the label
    # ``run_pipeline_mode`` self-assigns (``mode=f"pipeline_{workflow_name}"``,
    # :852/:900), so a label copied out of a report is a key that works. Before
    # this, ``pipeline`` was the only key whose label was not typable, and it was
    # the flagship mode: reading ``pipeline_standard`` in the baseline and
    # passing it back to ``--modes`` silently produced a report without it.
    "pipeline_standard": lambda text, cid, max_wall_seconds=None: run_pipeline_mode(
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
    # Backward-compat aliases (see deprecation note above).
    "hierarchical": run_hierarchical_mode,
    # #1747: ``pipeline`` kept dispatchable for whoever scripted it, following
    # the convention #1740 established for ``hierarchical`` — same runner as the
    # canonical key, so it emits ``pipeline_standard`` rows either way.
    "pipeline": lambda text, cid, max_wall_seconds=None: run_pipeline_mode(
        text, cid, "standard", max_wall_seconds=max_wall_seconds
    ),
}

# #1740: aliases stay DISPATCHABLE (``--modes hierarchical`` keeps working for
# whoever scripted it) but are excluded from the DEFAULT sweep. Running them by
# default emitted rows the runner self-labels ``hierarchical_bridge`` — strictly
# indistinguishable from the real bridge rows, so the #1735 baseline carried the
# bridge SIX times for three corpora, announced "Modes tested: 7", and anyone
# aggregating that table counted the bridge twice.
#
# #1747 adds ``pipeline`` for the SAME reason: it dispatches the same runner as
# ``pipeline_standard`` and self-labels identically, so leaving both in the
# default sweep would double-count the flagship mode exactly as ``hierarchical``
# double-counted the bridge.
_DEPRECATED_MODE_ALIASES: FrozenSet[str] = frozenset({"hierarchical", "pipeline"})


def default_modes() -> List[str]:
    """The default sweep: every runner except deprecated aliases (#1740)."""
    return [m for m in MODE_RUNNERS if m not in _DEPRECATED_MODE_ALIASES]


# Mode -> human-readable scope-of-work description, for the report table.
# Modes NOT in this map use the value already stored in ``ModeResult.scope_of_work``.
MODE_SCOPE_DESCRIPTIONS = {
    "pipeline": ("UnifiedPipeline DAG (light/standard/full workflows)"),
    "pipeline_standard": "UnifiedPipeline DAG (standard workflow, 15 phases)",
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
      ✅⏱ bounded — a wall-clock-bounded PARTIAL verdict that is REAL (C1 #1500
            + CB #1528 item 2): the run stopped at the bound and left behind
            artifacts the partial state / completed phases carry. Two ways to
            get here, both meaning the same thing for a reader of the table:
            the mode exited cleanly at its own bound (conversational,
            ``extra_metrics["wall_clock_bounded"]``), or it was cut at the
            budget but the accumulated work was recovered (``decides=True``).
      ⏱ terminates=True, terminated_by_budget=True AND nothing recovered — a
            STERILE cut: the budget fired and no verdict artifact survived.
            The discriminator against ``✅⏱`` is ``decides``, i.e. measured
            output — never the mere fact of having been bounded (anti-théâtre:
            relabelling a sterile cut as "bounded" would be the mirror lie).
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
        "| Mode | Corpus | Terminates | Wall-Time | Decides | Phases | Exec Path | Scope |"
    )
    lines.append(
        "|------|--------|------------|-----------|---------|--------|-----------|-------|"
    )

    for r in sorted(results, key=lambda x: (x.mode, x.corpus_id)):
        if r.terminated_by_budget:
            # CB #1528 item 2 (coord R723 "écart de rapport"): a budget cut
            # that recovered a real partial verdict reads ``✅⏱ bounded`` —
            # the legend's own definition of that marker. Before, EVERY budget
            # cut rendered ``⏱ budget``, whose legend says "no verdict
            # produced", so a pipeline row with decides=✅ contradicted its own
            # marker. `decides` is normalised by run_all via _compute_decides
            # (untouched here); `is True` keeps an un-normalised None sterile.
            status = "✅⏱ bounded" if r.decides is True else "⏱ budget"
        elif _hit_its_wall_clock(r):
            # #1752 (CORRECTED): this branch is NOT a reader-hop rescue for the
            # constant above — it renders a DIFFERENT state. A run that stopped
            # itself at its own internal bound produced a real partial verdict
            # (C1 #1500); a run killed by the safety net did not. I first read
            # the two as duplicate witnesses of one state and deleted this
            # branch; ``test_report_marks_bounded_verdict_distinctly`` caught it.
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
        # CE #1537: surface which execution path ran so a conversational line
        # that silently fell back to round-robin cannot be read as a genuine
        # AgentGroupChat run (the exact pre-CD #1534 failure mode). Only the
        # conversational mode records execution_path today; other modes render "—".
        exec_path = r.extra_metrics.get("execution_path")
        if exec_path == "agent_group_chat":
            exec_path_cell = "AgentGroupChat"
        elif exec_path == "round_robin_fallback":
            exec_path_cell = "round-robin ⚠"
        else:
            exec_path_cell = "—"
        lines.append(
            f"| {r.mode} | {r.corpus_id} | {status} | "
            f"{r.duration_seconds:.2f}s | {decides} | "
            f"{r.phases_completed}/{r.phases_total} | {exec_path_cell} | {scope} |"
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
        "Counts (#1740): `n/a` = the producing capability was **not in the "
        "executed perimeter** (never evaluated — not a zero); `—` = in the "
        "perimeter but not written; a number = written."
    )
    lines.append("")
    lines.append(
        "| Mode | Corpus | Success | Duration | State Fill | Fallacies | Args | Phases |"
    )
    lines.append(
        "|------|--------|---------|----------|------------|-----------|------|--------|"
    )

    for r in sorted(results, key=lambda x: (x.mode, x.corpus_id)):
        # #1752: this is the table that carries the COMPARISON metrics (State
        # Fill / Fallacies / Args), so it is the table where a budget-truncated
        # row misleads most — and it was the only one without the marker. A
        # reader comparing 22.0% against 48.7% was comparing a policy to a
        # budget. This is the one defect of the original #1752 report that
        # survived its own correction: here the question is comparability, not
        # mechanism, so both budget routes get the same mark.
        status = "✅" if r.success else "❌"
        if r.success and _hit_its_wall_clock(r):
            status = "✅⏱"
        err = f" ({r.error})" if r.error and len(r.error) < 50 else ""
        lines.append(
            f"| {r.mode} | {r.corpus_id} | {status}{err} | "
            f"{r.duration_seconds:.2f}s | {_fmt_fill(r.state_fill_rate)} | "
            f"{_fmt_count_in_perimeter(r.fallacy_count, _FALLACY_PRODUCING_CAPABILITIES, r.capabilities_used, r.perimeter_is_exhaustive)} | "
            f"{_fmt_count_in_perimeter(r.argument_count, _ARGUMENT_PRODUCING_CAPABILITIES, r.capabilities_used, r.perimeter_is_exhaustive)} | "
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

        # Fill rate comparison — CG #1540: skip None (not written) as well as
        # 0.0; a hierarchical mode that decides by conclusion must not appear
        # here as a 0.0% fill (it would read as "measured empty" — leçon #1531).
        fills = {
            r.mode: r.state_fill_rate
            for r in corpus_results
            if (r.state_fill_rate or 0) > 0
        }
        if fills:
            best_fill = max(fills, key=fills.get)
            lines.append(
                f"**Highest state fill**: `{best_fill}` ({fills[best_fill]:.1%})"
            )
            lines.append("")

        # Capability ledger — all THREE states, side by side (#1749).
        # Previously this block printed only ``capabilities_used``, so a
        # capability that ran and returned nothing appeared nowhere: the row
        # read "14 used / 0 missing" on a run wrong by exactly one capability.
        # The three are rendered together on one line because that is the
        # readable form — "14 used / 1 degraded / 0 missing" is legible,
        # "14 used / 0 missing" plus a footnote is how the state got lost.
        for r in corpus_results:
            lines.extend(_capability_ledger_lines(r))

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
    max_wall_seconds: float = DEFAULT_WALL_SECONDS,
    conv_room_policy: str = "phase_casting",
) -> List[ModeResult]:
    """Run selected modes on selected corpora.

    Args:
        max_wall_seconds: Wall-clock budget (CB #1528) threaded to EVERY
            runner, and every runner now recovers a REAL partial verdict at
            breach (item 2) — pipeline and hierarchical bridge via a state
            reference + recording checkpoint, hierarchical delegation via
            checkpointed task results, conversational via its internal bound
            (C1 #1500). Breach is recorded as a HONEST PARTIAL verdict
            (``terminated_by_budget=True``) — never faked into success
            (anti-#1019), and a cut that recovered nothing still renders
            sterile (``—``) rather than borrowing the bounded marker.
    """
    if modes is None:
        modes = default_modes()
    if corpora is None:
        corpora = list(BENCHMARK_TEXTS.keys())

    # #1747: validate the REQUEST before doing any work. Previously an unknown
    # mode or corpus was a ``logger.warning`` + ``continue``, so the run wrote a
    # complete, well-formed report with exit 0 and the requested mode simply
    # absent — nothing in the ``.md`` or ``.json`` recorded the unhonoured
    # request. For a comparison instrument that is the worst failure shape: an
    # absence in the table becomes indistinguishable from "that mode was never
    # asked for". Fail loud instead (#1019), and name the valid keys so the
    # caller can fix the typo without reading the source.
    #
    # This is a PRE-FLIGHT error, structurally distinct from a runner that
    # raises: the latter is caught below and still yields a ``ModeResult`` with
    # ``success=False``. Failed and skipped stay two different outputs.
    unknown_modes = [m for m in modes if m not in MODE_RUNNERS]
    unknown_corpora = [c for c in corpora if c not in BENCHMARK_TEXTS]
    if unknown_modes or unknown_corpora:
        problems = []
        if unknown_modes:
            problems.append(
                f"unknown mode(s): {', '.join(unknown_modes)}\n"
                f"  valid modes: {', '.join(sorted(MODE_RUNNERS))}"
            )
        if unknown_corpora:
            problems.append(
                f"unknown corpus/corpora: {', '.join(unknown_corpora)}\n"
                f"  valid corpora: {', '.join(sorted(BENCHMARK_TEXTS))}"
            )
        raise ValueError(
            "compare_orchestration_modes: refusing to run a partial sweep.\n"
            + "\n".join(problems)
        )

    if dry_run:
        # Every mode listed here is dispatchable: the pre-flight validation
        # already rejected the unknown ones, so ``--dry-run`` no longer doubles
        # as the only place a typo was reported (#1747).
        print("Dry run — modes that would be tested:")
        for mode in modes:
            alias = " (deprecated alias)" if mode in _DEPRECATED_MODE_ALIASES else ""
            print(f"  {mode}: available{alias}")
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
        # Both lookups are total: the pre-flight validation above rejected every
        # unknown key, so a silent skip is no longer reachable here (#1747).
        text = BENCHMARK_TEXTS[corpus_id]

        for mode in modes:
            runner = MODE_RUNNERS[mode]

            logger.info(f"Running {mode} on {corpus_id} ({len(text)} chars)...")
            try:
                # CB #1528: the wall-clock budget is now threaded to EVERY
                # runner (uniform signature ``runner(text, cid, max_wall_seconds=...)``).
                # Pipeline applies the state-reference trick; conversational
                # its internal bound (C1); hierarchical honest-degrades.
                # #1760: the conversational room policy rides along for the
                # steering measurement rows (ignored by every other runner).
                runner_kwargs = {"max_wall_seconds": max_wall_seconds}
                if mode == "conversational":
                    runner_kwargs["room_policy"] = conv_room_policy
                result = await runner(text, corpus_id, **runner_kwargs)
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
    # verdict, anti-#1019); a genuinely sterile run (cut at the safety-net:
    # 0/0 phases, no state written) stays False → `—`.
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
        default=DEFAULT_WALL_SECONDS,
        help=(
            f"Wall-clock budget in seconds, applied to EVERY mode "
            f"(default {DEFAULT_WALL_SECONDS:g}). "
            f"On breach, the verdict is recorded as PARTIAL HONNÊTE "
            f"(terminated_by_budget=True), never as success=True."
        ),
    )
    parser.add_argument(
        "--conv-room-policy",
        choices=("phase_casting", "truth", "reprompt", "all_agents"),
        default="phase_casting",
        help=(
            "#1760 — conversational only: how the room the PM steers in "
            "relates to its 8-agent capability map. phase_casting is the "
            "baseline; the report's extra_metrics carries the steering couple "
            "(designations_unresolved / distinct_speakers) for every value."
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

    try:
        asyncio.run(
            run_all(
                modes=args.modes,
                corpora=args.corpora,
                output_file=args.output,
                dry_run=args.dry_run,
                max_wall_seconds=args.max_wall_seconds,
                conv_room_policy=args.conv_room_policy,
            )
        )
    except ValueError as exc:
        # #1747: a bad --modes/--corpora request exits non-zero with a readable
        # message instead of a traceback, and — crucially — WITHOUT having
        # written a report that looks complete.
        print(f"\n{exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
