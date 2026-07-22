"""Selecteable Dung-arbitration stage for sophism detection (Track I1 #1501).

A PRODUCTION STAGE — distinct from #1429's ``compare_sophism_backends`` comparison
harness. When ``dung_arbitration`` is enabled, the Dung grounded extension
arbitrates between sophism candidates and ALTERS the detection verdict:
candidates defeated by a defended Walton-Krabbe refutation are eliminated (false
positives filtered; surviving candidates reinstated). Off by default
(backward-compat): the detector output is unchanged until the stage is selected.

Anti-fabrication (#1019 / anti-théâtre)
---------------------------------------
The stage never invents an attack. It mechanically turns DECLARED Walton-Krabbe
antagonistic relations (``SpeechAct.REFUTE`` / ``CHALLENGE`` from
``debate/protocols.py``, produced by the DebateAgent protocol in PR2/PR3) into
Dung attack edges, then lets the grounded extension decide which candidates
survive. With no declared refutations and no same-span rivalry, the enabled stage
is honest-absent: output == input (no fabricated arbitration, no cosmetic flag).

JVM/LLM-free by design
----------------------
Reuses ``neuro_symbolic_arbitrator.arbitrate`` + the pure-python grounded solver
so PR1 is unit-testable with synthetic opaque atoms — no JVM, no LLM. Inject
``make_dung_agent_solver()`` for real JVM-backed grounded semantics (PR2/PR3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from argumentation_analysis.agents.core.debate.protocols import SpeechAct
from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
    ArbitrationResult,
    ConflictPolicy,
    SophismCandidate,
    arbitrate,
    default_conflict_policy,
)

#: Walton-Krabbe speech acts that, when declared from A to B, yield a Dung attack
#: A → B. REFUTE and CHALLENGE are the antagonistic moves in the Walton-Krabbe
#: taxonomy (protocols.py); CONCEDE / SUPPORT / UNDERSTAND are cooperative and do
#: NOT attack. The DebateAgent producer (PR2/PR3) filters its declared relations
#: to these acts before feeding them to the stage.
WALTON_KRABBE_ATTACKING_ACTS: frozenset[SpeechAct] = frozenset(
    {SpeechAct.REFUTE, SpeechAct.CHALLENGE}
)

# Declared Walton-Krabbe relations: for each candidate id, the ids it
# REFUTE/CHALLENGE. Produced by the DebateAgent protocol (PR2/PR3); PR1 passes
# them explicitly to keep the stage JVM/LLM-free and deterministic.
WaltonKrabbeRelations = dict[str, frozenset[str]]


def walton_krabbe_conflict_policy(
    relations: WaltonKrabbeRelations,
) -> ConflictPolicy:
    """ConflictPolicy turning DECLARED Walton-Krabbe refutations into attacks.

    Each declared antagonistic relation (A refutes/challenges B) becomes a Dung
    attack edge (A → B): A is the challenger argument, B the targeted candidate.
    The grounded extension then defeats B exactly when A is itself defended
    (unattacked) — a genuine refutation. This is the candidate-vs-candidate attack
    dimension the #1501 dispatch asks for (DebateAgent as attack source between
    candidates), distinct from #1429's same-span-rival policy and its synthetic
    critical-question challenger.

    Unknown ids, self-loops and cooperative acts are ignored. Returning an empty
    set is always legitimate (honest-absent). The policy never touches critical
    questions (those stay in ``neuro_symbolic_arbitrator.build_dung_framework``).
    """

    def _policy(candidates: Sequence[SophismCandidate]) -> set[tuple[str, str]]:
        known = {c.candidate_id for c in candidates}
        attacks: set[tuple[str, str]] = set()
        for challenger, targets in relations.items():
            if challenger not in known:
                continue
            for target in targets:
                if target in known and target != challenger:
                    attacks.add((challenger, target))
        return attacks

    return _policy


def combine_conflict_policies(*policies: ConflictPolicy) -> ConflictPolicy:
    """Union several ConflictPolicies into one (attacks deduped by set semantics)."""

    def _combined(candidates: Sequence[SophismCandidate]) -> set[tuple[str, str]]:
        attacks: set[tuple[str, str]] = set()
        for policy in policies:
            attacks |= policy(candidates)
        return attacks

    return _combined


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
    walton_krabbe_relations: Optional[WaltonKrabbeRelations] = None,
    conflict_policy: Optional[ConflictPolicy] = None,
    semantics: str = "grounded",
    solver: Optional[Callable] = None,
) -> ArbitrationVerdict:
    """Selecteable Dung-arbitration stage over sophism candidates (#1501).

    ``dung_arbitration=False`` (default OFF, backward-compat): passthrough — the
    verdict keeps EVERY candidate, performs no arbitration. The detector output is
    unchanged, so wiring the stage off is transparent.

    ``dung_arbitration=True``: build the Dung AF from (a) the base conflict policy
    (default: #1429's same-span rivalry) UNION (b) declared Walton-Krabbe
    refutations, then let the grounded extension decide which candidates survive.
    Candidates defeated by a defended refutation are eliminated (false-positive
    filtering); the verdict differs from the off-baseline exactly when the symbolic
    layer has something genuine to arbitrate (anti-#1019).

    Args:
        candidates: Sophism candidates as opaque Dung atoms.
        dung_arbitration: Stage selector — OFF by default.
        walton_krabbe_relations: Declared REFUTE/CHALLENGE relations (DebateAgent
            output in PR2/PR3). Each becomes a candidate-vs-candidate attack.
        conflict_policy: Base conflict derivation (default: #1429's
            ``default_conflict_policy``). Pass a no-op returning ``set()`` to
            arbitrate on Walton-Krabbe refutations alone.
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

    base_policy = conflict_policy or default_conflict_policy
    if walton_krabbe_relations:
        combined = combine_conflict_policies(
            base_policy, walton_krabbe_conflict_policy(walton_krabbe_relations)
        )
    else:
        combined = base_policy

    result: ArbitrationResult = arbitrate(
        candidates,
        solver=solver,
        semantics=semantics,
        conflict_policy=combined,
    )

    surviving = result.arbitrated_ids
    eliminated = dict(result.rejected)
    _annotate_walton_krabbe_eliminations(
        eliminated, surviving, result.attacks, walton_krabbe_relations
    )

    return ArbitrationVerdict(
        enabled=True,
        surviving_ids=surviving,
        eliminated_ids=eliminated,
        attacks=result.attacks,
        honest_absent=result.honest_absent,
        input_count=result.neural_count,
        surviving_count=result.arbitrated_count,
    )


def _annotate_walton_krabbe_eliminations(
    eliminated: dict[str, str],
    surviving: frozenset[str],
    attacks: frozenset[tuple[str, str]],
    relations: Optional[WaltonKrabbeRelations],
) -> None:
    """Refine elimination reasons with the Walton-Krabbe dimension (traceability).

    A candidate eliminated by a DECLARED refuter that itself survived (a genuine,
    defended refutation) is labelled ``defeated_by_walton_krabbe_refutation``
    rather than the generic ``defeated_by_rival_candidate``. Mutates ``eliminated``
    in place. No-op when no relations were declared.
    """

    if not relations:
        return
    refuters = set(relations.keys())
    attackers_of: dict[str, set[str]] = {}
    for src, tgt in attacks:
        attackers_of.setdefault(tgt, set()).add(src)
    for cid in list(eliminated):
        wk_attackers = attackers_of.get(cid, set()) & refuters
        if wk_attackers & surviving:
            eliminated[cid] = "defeated_by_walton_krabbe_refutation"
