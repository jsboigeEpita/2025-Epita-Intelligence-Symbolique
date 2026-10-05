"""Selecteable Dung-arbitration stage for sophism detection (Track I1 #1501).

A PRODUCTION STAGE — distinct from #1429's ``compare_sophism_backends`` comparison
harness. When ``dung_arbitration`` is enabled, the Dung grounded extension
arbitrates between sophism candidates and ALTERS the detection verdict:
candidates defeated by a defended rival are eliminated (false
positives filtered; surviving candidates reinstated). Off by default
(backward-compat): the detector output is unchanged until the stage is selected.

Anti-fabrication (#1019 / anti-théâtre)
---------------------------------------
The stage never invents an attack. It mechanically turns the conflict policy's
same-span rivalry (#1429 — candidates anchored on the same span attack each
other) into Dung attack edges, then lets the grounded extension decide which
candidates survive. With no rivalry, the enabled stage is honest-absent:
output == input (no fabricated arbitration, no cosmetic flag).

The declared Walton-Krabbe relations channel — ``SpeechAct.REFUTE``/``CHALLENGE``
acts turned into candidate-vs-candidate attacks — was retired (#1649, R1065):
its producer never existed. The DebateAgent emits quality scores, not speech
acts; the act-bearing protocol classes were withdrawn as dead twins (#2137);
and no production writer ever fed the channel. The stage arbitrates on rivalry
alone.

JVM/LLM-free by design
----------------------
Reuses ``neuro_symbolic_arbitrator.arbitrate`` + the pure-python grounded solver
so the stage is unit-testable with synthetic opaque atoms — no JVM, no LLM. Inject
``make_dung_agent_solver()`` for real JVM-backed grounded semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
    ArbitrationResult,
    ConflictPolicy,
    SophismCandidate,
    arbitrate,
    default_conflict_policy,
)


@dataclass(frozen=True)
class ArbitrationVerdict:
    """Formal, traceable outcome of the selectable ``dung_arbitration`` stage.

    The detection pipeline reads ``surviving_ids`` as the arbitrated set of
    fallacies to report; ``eliminated_ids`` carries a machine-checkable reason for
    each dropped candidate, so the verdict is auditable rather than an opaque score
    (#1501 DoD #4). ``enabled=False`` ⇒ passthrough: ``surviving_ids`` == all input
    ids, ``honest_absent=True``, no arbitration performed.
    """

    enabled: bool
    surviving_ids: frozenset[str]
    eliminated_ids: dict[str, str]
    attacks: frozenset[tuple[str, str]]
    honest_absent: bool
    input_count: int
    surviving_count: int


def arbitrate_detections(
    candidates: Sequence[SophismCandidate],
    *,
    dung_arbitration: bool,
    conflict_policy: Optional[ConflictPolicy] = None,
    semantics: str = "grounded",
    solver: Optional[Callable] = None,
) -> ArbitrationVerdict:
    """Selecteable Dung-arbitration stage over sophism candidates (#1501).

    ``dung_arbitration=False`` (default OFF, backward-compat): passthrough — the
    verdict keeps EVERY candidate, performs no arbitration. The detector output is
    unchanged, so wiring the stage off is transparent.

    ``dung_arbitration=True``: build the Dung AF from the conflict policy
    (default: #1429's same-span rivalry), then let the grounded extension decide
    which candidates survive. Candidates defeated by a defended rival are
    eliminated (false-positive filtering); the verdict differs from the
    off-baseline exactly when the symbolic layer has something genuine to
    arbitrate (anti-#1019).

    Args:
        candidates: Sophism candidates as opaque Dung atoms.
        dung_arbitration: Stage selector — OFF by default.
        conflict_policy: Conflict derivation (default: #1429's
            ``default_conflict_policy`` same-span rivalry).
        semantics: Extension semantics label forwarded to ``arbitrate`` (grounded).
        solver: Injected Dung solver (default: pure-python grounded; inject
            ``make_dung_agent_solver()`` for real JVM-backed semantics).

    Returns:
        The formal :class:`ArbitrationVerdict`. When the stage is off OR no attacks
        arise, ``honest_absent`` is True and ``surviving_ids`` == all input ids —
        the stage never fabricates a verdict change.
    """

    candidate_ids = frozenset(c.candidate_id for c in candidates)

    if not dung_arbitration:
        return ArbitrationVerdict(
            enabled=False,
            surviving_ids=candidate_ids,
            eliminated_ids={},
            attacks=frozenset(),
            honest_absent=True,
            input_count=len(candidate_ids),
            surviving_count=len(candidate_ids),
        )

    result: ArbitrationResult = arbitrate(
        candidates,
        solver=solver,
        semantics=semantics,
        conflict_policy=conflict_policy or default_conflict_policy,
    )

    return ArbitrationVerdict(
        enabled=True,
        surviving_ids=result.arbitrated_ids,
        eliminated_ids=dict(result.rejected),
        attacks=result.attacks,
        honest_absent=result.honest_absent,
        input_count=result.neural_count,
        surviving_count=result.arbitrated_count,
    )
