"""Neuro-symbolic sophism detection — Dung arbitrage over neural candidates.

Track I1 (#1429, NORTH-STAR). This is a **symbolic arbitrage layer** built on top
of the existing neural sophism detector (``taxonomy_sophism_detector.py``) and
the existing abstract-argumentation solver (``abs_arg_dung/``). It does **not**
re-implement detection, nor the Dung solver — it wires them together so that
overlapping / mutually-exclusive neural candidates are arbitrated by Dung
semantics, with attacks derived from unsatisfied Walton critical questions.

Anti-fabrication posture (#1019 / anti-théâtre)
-----------------------------------------------
The arbitrator never invents a fallacy, a conflict, or a critical-question
failure. It only **mechanically turns declared signals into attacks**:

* A candidate declares the Walton critical questions it fails
  (``failed_critical_questions``) — that declaration is the neural/LLM layer's
  responsibility (bridge wired in PR2, exercised on real text in PR3). Each
  declared failure becomes an unattacked *challenger* argument attacking the
  candidate, so the candidate is defeated under grounded semantics exactly when
  one of its critical questions is genuinely unsatisfied.
* Two candidates anchored on the same evidence span with rival families are in
  declared conflict (the issue's own example: one passage flagged as both *ad
  hominem* and *straw man*). Resolution is mechanical: the strictly more
  confident candidate attacks the less confident one (a tie yields a mutual
  attack → both rejected under grounded).

Honest-absent
-------------
If no candidate declares a failed critical question **and** no two candidates
share a span with rival families, the attack set is empty. The accepted
extension is then the full set of arguments, so the arbitrated output is
identical to the raw neural output — the neuro-symbolic mode is **transparent**
(== neural) when there is nothing genuine to arbitrate. This is mandated by the
issue: no fabricated attacks to "make it symbolic".

JVM-free by design (DI solver)
------------------------------
The Dung solver is an injected callable (``DungSolver`` protocol) so the core
logic is unit-testable with synthetic opaque atoms and **no JVM, no LLM**. The
default solver is a pure-python grounded-extension computation; a thin adapter
(:func:`make_dung_agent_solver`) wraps the real ``abs_arg_dung.DungAgent`` (JVM)
for production use in PR2/PR3. This mirrors the ``compare_*_backends`` DI idiom.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Callable, Optional, Protocol, Sequence, runtime_checkable

from argumentation_analysis.agents.core.debate.argumentation_schemes import (
    ArgumentationScheme,
    classify_scheme,
)

logger = logging.getLogger(__name__)

# Prefix for synthetic challenger arguments standing in for unsatisfied Walton
# critical questions. Caller-supplied candidate ids MUST NOT start with this
# prefix (a guard rejects collisions). Keeping these as first-class arguments
# (rather than implicit attacks) makes the arbitration auditable: every defeat
# traces back to a named critical question.
_CQ_CHALLENGER_PREFIX = "__walton_cq__"


@dataclass(frozen=True)
class SophismCandidate:
    """One neural sophism candidate, modelled as an opaque Dung argument.

    The arbitrator treats ``candidate_id`` / ``family`` / ``span_id`` as opaque
    atoms — it never interprets their meaning, only their declared relations
    (failed critical questions, span overlap). This keeps the symbolic layer
    decoupled from the detector's taxonomy internals and is what makes the unit
    tests JVM/LLM-free.

    Attributes:
        candidate_id: Opaque, unique candidate identifier (e.g. ``"s0"``).
            Must not start with ``__walton_cq__``.
        family: Opaque family label (e.g. ``"ad_hominem"``). Used only to decide
            rivalry between same-span candidates — never interpreted semantically.
        span_id: Opaque evidence-span anchor. Two candidates sharing a span with
            different families are in declared conflict.
        confidence: Neural confidence in ``[0, 1]``. Breaks ties between rival
            same-span candidates (higher attacks lower).
        failed_critical_questions: Walton critical questions the passage fails to
            satisfy for this candidate, as declared by the neural/LLM bridge. Each
            becomes an unattacked challenger attacking this candidate.
    """

    candidate_id: str
    family: str
    span_id: str
    confidence: float
    failed_critical_questions: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.candidate_id.startswith(_CQ_CHALLENGER_PREFIX):
            raise ValueError(
                f"Candidate id {self.candidate_id!r} collides with the reserved "
                f"challenger prefix {_CQ_CHALLENGER_PREFIX!r}."
            )


@dataclass(frozen=True)
class ArbitrationResult:
    """Outcome of arbitrating a batch of neural candidates under Dung semantics.

    ``arbitrated_ids`` is the set of candidate ids that survive the chosen
    semantics. When ``honest_absent`` is ``True`` there were no attacks at all,
    so ``arbitrated_ids`` equals the full input set — the neuro-symbolic mode is
    transparent (identical to neural). Diagnostics (``rejected`` with reasons,
    ``attacks``, challenger map) give PR2/PR3 everything needed to render a
    comparison and a real-corpus report.
    """

    semantics: str
    arbitrated_ids: frozenset[str]
    rejected: dict[str, str]
    attacks: frozenset[tuple[str, str]]
    challenger_for: dict[str, str]
    honest_absent: bool
    neural_count: int
    arbitrated_count: int


@runtime_checkable
class DungSolver(Protocol):
    """Callable contract for an injected Dung extension solver.

    Returns one extension per element of the returned list (grounded ⇒ one
    element, preferred ⇒ several). Arguments and attacks are opaque string ids.
    Implementations must be pure with respect to ``(arguments, attacks)``.
    """

    def __call__(
        self,
        arguments: set[str],
        attacks: set[tuple[str, str]],
        *,
        semantics: str,
    ) -> list[set[str]]: ...


# A conflict policy derives candidate-vs-candidate attack edges from declared
# span overlaps. It must NOT touch critical questions (those are handled by
# :func:`build_dung_framework`). Returning an empty set is always legitimate and
# yields honest-absent behaviour for the conflict dimension.
ConflictPolicy = Callable[[Sequence[SophismCandidate]], set[tuple[str, str]]]


def default_conflict_policy(
    candidates: Sequence[SophismCandidate],
) -> set[tuple[str, str]]:
    """Mechanical same-span / rival-family conflict derivation.

    For each evidence span hosting candidates from **different** families, the
    strictly more confident candidate attacks each less-confident rival; an exact
    confidence tie yields a mutual attack between the rivals (both rejected under
    grounded). No rivalry matrix is invented: "different family on the same span"
    is the only conflict signal, matching the issue's own example.

    Same-span candidates of the **same** family are not in conflict (a passage may
    legitimately surface the same fallacy twice); they produce no edge.
    """

    by_span: dict[str, list[SophismCandidate]] = {}
    for cand in candidates:
        by_span.setdefault(cand.span_id, []).append(cand)

    attacks: set[tuple[str, str]] = set()
    for group in by_span.values():
        # Pairs of candidates on the same span with different families.
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a.family == b.family:
                    continue
                if a.confidence > b.confidence:
                    attacks.add((a.candidate_id, b.candidate_id))
                elif b.confidence > a.confidence:
                    attacks.add((b.candidate_id, a.candidate_id))
                else:
                    # Exact tie — cannot rank; mutual attack (both fall under
                    # grounded). Overridable by supplying another ConflictPolicy.
                    attacks.add((a.candidate_id, b.candidate_id))
                    attacks.add((b.candidate_id, a.candidate_id))
    return attacks


def build_dung_framework(
    candidates: Sequence[SophismCandidate],
    *,
    conflict_policy: Optional[ConflictPolicy] = None,
) -> tuple[set[str], set[tuple[str, str]], dict[str, str]]:
    """Construct the abstract AF (arguments + attacks) for a candidate batch.

    Combines two declared signal sources into one attack set:

    1. **Critical-question challengers** — one unattacked synthetic argument per
       distinct failed Walton CQ, attacking its candidate. The challenger id is
       stable and mapped in the returned ``challenger_for`` dict (challenger →
       candidate it attacks) for auditability.
    2. **Conflict edges** — produced by ``conflict_policy`` (default:
       :func:`default_conflict_policy`).

    Returns ``(arguments, attacks, challenger_for)``.
    """

    policy = conflict_policy or default_conflict_policy
    arguments: set[str] = {c.candidate_id for c in candidates}
    attacks: set[tuple[str, str]] = set(policy(candidates))
    challenger_for: dict[str, str] = {}

    for cand in candidates:
        # Dedup identical critical questions within a candidate so a repeated CQ
        # yields a single challenger (one weakness, one attacker).
        seen: set[str] = set()
        for idx, question in enumerate(cand.failed_critical_questions):
            if question in seen:
                continue
            seen.add(question)
            challenger = f"{_CQ_CHALLENGER_PREFIX}{cand.candidate_id}__{idx}"
            arguments.add(challenger)
            attacks.add((challenger, cand.candidate_id))
            challenger_for[challenger] = cand.candidate_id

    return arguments, attacks, challenger_for


def _grounded_extension_pure(
    arguments: set[str], attacks: set[tuple[str, str]]
) -> frozenset[str]:
    """Least-fixed-point grounded extension in pure python (no JVM).

    Iterates the grounded characteristic function from the empty set: an argument
    is acceptable w.r.t. ``S`` iff every attacker of it is itself attacked by some
    member of ``S``. Converges to the unique grounded extension. Deterministic
    iteration order (sorted) keeps results stable across runs.
    """

    accepted: set[str] = set()
    while True:
        grew = False
        for arg in sorted(arguments):
            if arg in accepted:
                continue
            acceptable = True
            for src, tgt in attacks:
                if tgt != arg:
                    continue
                # `src` attacks `arg`; it must be counter-attacked by some member
                # of the currently accepted set for `arg` to be defended.
                if not any(
                    defender in accepted and (defender, src) in attacks
                    for defender in arguments
                ):
                    acceptable = False
                    break
            if acceptable:
                accepted.add(arg)
                grew = True
        if not grew:
            break
    return frozenset(accepted)


def pure_python_solver(
    arguments: set[str],
    attacks: set[tuple[str, str]],
    *,
    semantics: str,
) -> list[set[str]]:
    """Default injected solver — pure-python grounded extension only.

    Supports ``semantics="grounded"`` (the conservative, single-extension choice
    that best matches "accepted = survives arbitrage"). Other semantics raise
    ``NotImplementedError`` rather than silently approximating: callers wanting
    preferred/stable must inject the real ``abs_arg_dung`` solver via
    :func:`make_dung_agent_solver` (PR2/PR3).
    """

    if semantics != "grounded":
        raise NotImplementedError(
            f"pure_python_solver supports only grounded semantics (got {semantics!r}); "
            "inject make_dung_agent_solver() for preferred/stable/etc."
        )
    return [set(_grounded_extension_pure(arguments, attacks))]


def make_dung_agent_solver() -> DungSolver:
    """Build a ``DungSolver`` backed by the real ``abs_arg_dung.DungAgent`` (JVM).

    Lazy-imports ``abs_arg_dung.agent`` so importing this module never requires
    the JVM; the JVM is only touched when the returned solver is actually called
    (mirroring ``DungAgent.__init__``'s contract). Used in PR2/PR3 production
    wiring; PR1 unit tests inject ``pure_python_solver`` instead.
    """

    def solver(
        arguments: set[str],
        attacks: set[tuple[str, str]],
        *,
        semantics: str,
    ) -> list[set[str]]:
        # Local import: keep the module JVM-free at import time. ``abs_arg_dung``
        # is untyped student code; under the project mypy config this module is
        # not in the strict-override list, so the untyped call is accepted.
        from abs_arg_dung.agent import DungAgent

        agent = DungAgent()  # type: ignore[no-untyped-call]
        for arg in sorted(arguments):
            agent.add_argument(arg)
        for src, tgt in sorted(attacks):
            agent.add_attack(src, tgt)

        if semantics == "grounded":
            return [set(agent.get_grounded_extension())]
        if semantics == "preferred":
            return [set(ext) for ext in agent.get_preferred_extensions()]
        if semantics == "stable":
            return [set(ext) for ext in agent.get_stable_extensions()]
        if semantics == "complete":
            return [set(ext) for ext in agent.get_complete_extensions()]
        if semantics == "ideal":
            return [set(agent.get_ideal_extension())]
        raise ValueError(
            f"Unsupported semantics for abs_arg_dung solver: {semantics!r}"
        )

    return solver


def arbitrate(
    candidates: Sequence[SophismCandidate],
    *,
    solver: Optional[DungSolver] = None,
    semantics: str = "grounded",
    conflict_policy: Optional[ConflictPolicy] = None,
) -> ArbitrationResult:
    """Arbitrate neural candidates under Dung semantics.

    Args:
        candidates: Raw neural sophism candidates as opaque atoms.
        solver: Injected Dung solver (default: pure-python grounded). Inject
            :func:`make_dung_agent_solver` for real JVM-backed semantics.
        semantics: Extension semantics label forwarded to ``solver``.
        conflict_policy: Same-span conflict derivation (default:
            :func:`default_conflict_policy`). Pass a no-op returning ``set()`` to
            disable the conflict dimension and arbitrate on CQs alone.

    Returns:
        The arbitrated candidate set plus full diagnostics. When the framework
        has no attacks (no failed CQ, no same-span rivalry) the result is
        honest-absent: ``arbitrated_ids`` == all candidate ids and
        ``honest_absent`` is ``True``.
    """

    chosen_solver = solver or pure_python_solver
    arguments, attacks, challenger_for = build_dung_framework(
        candidates, conflict_policy=conflict_policy
    )

    extensions = chosen_solver(arguments, attacks, semantics=semantics)
    if not extensions:
        accepted: set[str] = set()
    elif len(extensions) == 1:
        accepted = set(extensions[0])
    else:
        # Multi-extension semantics (e.g. preferred): a candidate "survives
        # arbitration" only if it is skeptically accepted — present in EVERY
        # extension. This is the conservative reading of "definitely accepted".
        accepted = set(extensions[0])
        for ext in extensions[1:]:
            accepted &= set(ext)

    candidate_ids = {c.candidate_id for c in candidates}
    arbitrated_ids = frozenset(candidate_ids & accepted)

    rejected: dict[str, str] = {}
    for cand in candidates:
        if cand.candidate_id in arbitrated_ids:
            continue
        if any(challenger_for.get(a) == cand.candidate_id for a, _ in attacks):
            rejected[cand.candidate_id] = "defeated_by_unsatisfied_critical_question"
        else:
            rejected[cand.candidate_id] = "defeated_by_rival_candidate"

    honest_absent = len(attacks) == 0

    return ArbitrationResult(
        semantics=semantics,
        arbitrated_ids=arbitrated_ids,
        rejected=rejected,
        attacks=frozenset(attacks),
        challenger_for=challenger_for,
        honest_absent=honest_absent,
        neural_count=len(candidate_ids),
        arbitrated_count=len(arbitrated_ids),
    )


# --------------------------------------------------------------------------- #
# PR2 — Walton critical-question bridge + neural/neuro-symbolic comparison    #
# --------------------------------------------------------------------------- #
#
# The arbitrator consumes ``failed_critical_questions`` as an opaque declared
# signal (PR1). PR2 wires the NEURAL→SYMBOLIC bridge that produces that
# declaration honestly: for each candidate, classify the argumentation scheme of
# its evidence span (``classify_scheme``), then ask an injected evaluator which
# of that scheme's *canonical* Walton critical questions are genuinely
# unsatisfied. The bridge only ever propagates questions that are members of the
# classified scheme's canonical set — an evaluator can never inject a question
# the scheme does not actually ask. This is the hard anti-fabrication guard.
#
# The default evaluator declares ZERO unsatisfied questions (honest-absent), so
# without a genuine evaluator (LLM, wired in PR3) the bridge is a no-op and the
# neuro-symbolic pipeline coincides exactly with the neural one. This keeps PR2
# JVM/LLM-free and unit-testable while PR3 supplies the real evaluation.

# Classifies a span's text to its Walton argumentation scheme (or None). DI so
# tests can inject a deterministic classifier; default is the real
# ``argumentation_schemes.classify_scheme``.
SchemeClassifier = Callable[[str], Optional[ArgumentationScheme]]

# Given a span, its scheme, and the candidate under test, returns the critical
# questions the passage genuinely fails to satisfy. The contract is honesty: the
# caller (the bridge) validates the result against the scheme's canonical CQs,
# but the evaluator itself must not fabricate failures — return an empty sequence
# when none are genuinely unsatisfied.
CQEvaluator = Callable[[str, ArgumentationScheme, SophismCandidate], Sequence[str]]


def default_cq_evaluator(
    span_text: str,
    scheme: ArgumentationScheme,
    candidate: SophismCandidate,
) -> Sequence[str]:
    """Declare ZERO unsatisfied critical questions.

    Honest-absent by construction: without a genuine evaluator (LLM in PR3), the
    bridge must not invent any critical-question failure. The neuro-symbolic
    pipeline therefore coincides with the neural one until a real evaluator is
    injected — the anti-théâtre guarantee.
    """

    return ()


def walton_cq_bridge(
    candidates: Sequence[SophismCandidate],
    *,
    span_text_for: Callable[[SophismCandidate], str],
    classifier: Optional[SchemeClassifier] = None,
    cq_evaluator: Optional[CQEvaluator] = None,
) -> tuple[list[SophismCandidate], dict[str, str]]:
    """Enrich candidates with their unsatisfied Walton critical questions.

    For each candidate, classifies the argumentation scheme of its evidence span
    (``span_text_for``), then asks ``cq_evaluator`` which of that scheme's
    canonical critical questions are genuinely unsatisfied. Returns new
    ``SophismCandidate`` instances with ``failed_critical_questions`` set to the
    validated subset.

    Anti-fabrication: only critical questions that are MEMBERS of the classified
    scheme's canonical ``critical_questions`` are propagated — an evaluator can
    never inject a question the scheme does not actually ask. When no scheme is
    classified for a span (``classify_scheme`` returns ``None``), the candidate is
    returned unchanged with no declared CQ.

    Args:
        candidates: Raw neural candidates.
        span_text_for: Yields the evidence-span text for a candidate. Supplied by
            the upstream caller that holds the real text + segmentation (PR3).
        classifier: Scheme classifier (default: ``classify_scheme``).
        cq_evaluator: CQ evaluator (default: :func:`default_cq_evaluator` —
            declares nothing, honest-absent).

    Returns:
        ``(enriched_candidates, span_coverage)`` where ``span_coverage`` maps each
        candidate id to the classified scheme key (``""`` when no scheme matched)
        — useful for PR3's synthesis report.
    """

    cls = classifier or classify_scheme
    evaluator = cq_evaluator or default_cq_evaluator

    enriched: list[SophismCandidate] = []
    coverage: dict[str, str] = {}
    for cand in candidates:
        span_text = span_text_for(cand)
        scheme = cls(span_text)
        coverage[cand.candidate_id] = scheme.key if scheme is not None else ""

        failed: tuple[str, ...] = ()
        if scheme is not None:
            canonical = set(scheme.critical_questions)
            declared = evaluator(span_text, scheme, cand)
            # Hard anti-fabrication guard: keep only declared questions that are
            # genuine members of THIS scheme's canonical critical questions.
            failed = tuple(q for q in declared if q in canonical)

        enriched.append(replace(cand, failed_critical_questions=failed))

    return enriched, coverage


@dataclass(frozen=True)
class SophismComparison:
    """Side-by-side neural vs neuro-symbolic outcome (NORTH-STAR comparable).

    ``neural_ids`` is the raw detector output (all candidates kept);
    ``neuro_symbolic_ids`` is the set that survives Dung arbitrage after the
    Walton CQ bridge. ``eliminated_ids`` = ``neural_ids - neuro_symbolic_ids``
    (the candidates the symbolic layer rejected), and ``arbitrated`` carries the
    full diagnostics (rejected reasons, attacks, challengers) so PR3 can render a
    detailed comparison report. ``span_coverage`` maps each candidate id to the
    Walton scheme key classified on its span (``""`` if none).
    """

    neural_ids: frozenset[str]
    neuro_symbolic_ids: frozenset[str]
    arbitrated: ArbitrationResult
    eliminated_ids: frozenset[str]
    span_coverage: dict[str, str]


def compare_sophism_backends(
    candidates: Sequence[SophismCandidate],
    *,
    span_text_for: Callable[[SophismCandidate], str],
    classifier: Optional[SchemeClassifier] = None,
    cq_evaluator: Optional[CQEvaluator] = None,
    solver: Optional[DungSolver] = None,
    semantics: str = "grounded",
    conflict_policy: Optional[ConflictPolicy] = None,
) -> SophismComparison:
    """Compare the neural-only and neuro-symbolic pipelines on the same batch.

    **Neural** = all candidates kept (raw detector output). **Neuro-symbolic** =
    candidates enriched by :func:`walton_cq_bridge` then arbitrated under Dung
    semantics via :func:`arbitrate`. The comparison surfaces exactly which
    candidates the symbolic layer eliminates and why (through the embedded
    :class:`ArbitrationResult`), realising the NORTH-STAR
    "selectable/comparable" requirement.

    With the default evaluator (no genuine CQ evaluation), the bridge declares no
    failures and the two pipelines coincide — the symbolic layer is transparent
    until there is something genuine to arbitrate. Inject ``cq_evaluator`` (PR3
    wires a real LLM evaluator) and/or ``solver`` to exercise real defeats.

    Args mirror :func:`arbitrate` plus the bridge's ``span_text_for`` /
    ``classifier`` / ``cq_evaluator``.
    """

    neural_ids = frozenset(c.candidate_id for c in candidates)
    enriched, coverage = walton_cq_bridge(
        candidates,
        span_text_for=span_text_for,
        classifier=classifier,
        cq_evaluator=cq_evaluator,
    )
    result = arbitrate(
        enriched,
        solver=solver,
        semantics=semantics,
        conflict_policy=conflict_policy,
    )
    return SophismComparison(
        neural_ids=neural_ids,
        neuro_symbolic_ids=result.arbitrated_ids,
        arbitrated=result,
        eliminated_ids=neural_ids - result.arbitrated_ids,
        span_coverage=coverage,
    )
