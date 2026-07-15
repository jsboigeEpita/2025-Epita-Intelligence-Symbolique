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

import hashlib
import logging
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional, Protocol, Sequence, runtime_checkable

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
    neural_reachable: bool = True


def compare_sophism_backends(
    candidates: Sequence[SophismCandidate],
    *,
    span_text_for: Callable[[SophismCandidate], str],
    classifier: Optional[SchemeClassifier] = None,
    cq_evaluator: Optional[CQEvaluator] = None,
    solver: Optional[DungSolver] = None,
    semantics: str = "grounded",
    conflict_policy: Optional[ConflictPolicy] = None,
    neural_reachable: bool = True,
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

    ``neural_reachable`` (GE-3 #1456) records whether the NEURAL tier genuinely
    decided. When ``False`` (no LLM configured / detection failed) the comparison
    is unilateral theatre — the caller MUST surface it as ``degraded``, never as a
    genuine comparison (anti-théâtre #1019). A reachable tier that detected zero
    fallacies stays ``True``: an empty-but-reachable neural verdict is an honest
    negative, not a degraded failure.
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
        neural_reachable=neural_reachable,
    )


# --------------------------------------------------------------------------- #
# PR3 — Real LLM cq_evaluator (production wiring of the bridge)               #
# --------------------------------------------------------------------------- #
#
# PR2 keeps the bridge honest-absent by default: the default evaluator declares
# ZERO unsatisfied critical questions. PR3 supplies a real evaluator that asks
# the LLM (OpenAI / OpenRouter via ``invoke_callables`` helpers) which of a
# candidate's scheme's canonical Walton critical questions are genuinely
# unsatisfied for that span.
#
# The mirror is exact of the TR-1/TR-2 structured_arg_translator pattern:
#   * lazy import of invoke_callables helpers (avoids any module-load cycle),
#   * no API key ⇒ returns () so the call fails-soft to honest-absent,
#   * JSON-mode response parsed by ``_parse_json_from_llm``,
#   * validations: ``failed`` keys must be MEMBERS of the scheme's canonical
#     critical_questions (the bridge re-validates against the same canonical
#     set, so this is double-belt-and-braces anti-fabrication).
#
# Exposed as :func:`make_llm_cq_evaluator` returning a ``CQEvaluator``-compatible
# async-callable. The CQEvaluator protocol is sync today — PR3 keeps the sync
# shape (the bridge does NOT await), wrapping the async LLM call synchronously
# via ``asyncio.run`` from the probe side, mirroring how ``compare_sophism_backends``
# is called from synchronous PR3 probe code.

# Async signature of the LLM-backed CQ evaluator. The synchronous CQEvaluator
# used by :func:`walton_cq_bridge` is the production entry point; the async form
# lets the probe ``await`` it once per candidate without spinning a thread.
AsyncCQEvaluator = Callable[[str, ArgumentationScheme, SophismCandidate], "Any"]


async def _llm_cq_evaluator_async(
    span_text: str, scheme: ArgumentationScheme, candidate: SophismCandidate
) -> Sequence[str]:
    """Ask the LLM which canonical critical questions this span genuinely fails.

    Mirrors :func:`_llm_extract_relations` (TR-1/TR-2 pattern): lazy imports,
    no-API-key honest-absent, JSON-mode parse, fail-soft exception handling.
    Validates against the scheme's canonical CQ set as a defence-in-depth guard
    on top of the bridge's same check.

    Returns an empty tuple on any failure path — the bridge's anti-fabrication
    posture means a failure to evaluate MUST stay transparent, not invent CQ
    failures. PR3 probe surfaces the failure mode (key missing, parse, etc.) via
    the caller's own logging.
    """

    # Lazy import: invoke_callables imports the informal modules lazily from the
    # handlers, so importing its helpers here is safe at call time (no cycle).
    from argumentation_analysis.orchestration.invoke_callables import (
        _get_determinism_params,
        _get_openai_client,
        _guarded_chat_completion,
        _parse_json_from_llm,
    )

    canonical_cqs = list(scheme.critical_questions)
    if not canonical_cqs:
        return ()

    client, model_id = _get_openai_client()
    if client is None:
        logger.info("LLM cq_evaluator: no API key configured — staying honest-absent.")
        return ()

    canonical_list = "; ".join(f"- {q}" for q in canonical_cqs)
    system_content = (
        "You are an expert in Walton-style argumentation schemes. "
        "For the given passage and its classified argumentation scheme, decide "
        "which of the scheme's canonical critical questions are GENUINELY "
        "unsatisfied by the passage — i.e. which CQ, if asked of the passage, "
        "would expose a real weakness. Report a CQ ONLY when the passage "
        "genuinely fails to satisfy it. If none are genuinely unsatisfied, "
        "return an empty list. Do NOT invent failures. "
        f"Candidate id: {candidate.candidate_id} (opaque, ignore its meaning). "
        f"Canonical critical questions of scheme « {scheme.label} »: "
        f"{canonical_list}. "
        "Respond with ONLY a JSON object of shape: "
        '{"failed": ["verbatim CQ text 1", ...]}'
    )
    user_content = (
        f"Scheme key: {scheme.key}\n"
        f"Passage (the candidate's evidence span):\n{span_text[:3000]}\n\n"
        "Return the JSON."
    )

    det_params = _get_determinism_params()
    llm_kwargs: dict[str, Any] = dict(det_params)
    llm_kwargs["response_format"] = {"type": "json_object"}
    try:
        response = await _guarded_chat_completion(
            client,
            model=model_id,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            **llm_kwargs,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft: any LLM error → honest-absent
        logger.info("LLM cq_evaluator: call failed (%s); staying honest-absent.", exc)
        return ()

    raw = response.choices[0].message.content or ""
    try:
        data = _parse_json_from_llm(raw)
    except Exception as exc:  # noqa: BLE001
        logger.info("LLM cq_evaluator: parse failed (%s); staying honest-absent.", exc)
        return ()

    declared = data.get("failed") if isinstance(data, dict) else None
    if not isinstance(declared, list):
        return ()
    canonical_set = set(canonical_cqs)
    return tuple(q for q in declared if isinstance(q, str) and q in canonical_set)


# --------------------------------------------------------------------------- #
# GE-3 (#1456, Epic #1448) — genuinely-reachable NEURAL tier                   #
# --------------------------------------------------------------------------- #
#
# ``compare_sophism_backends`` is bilateral only when the NEURAL side genuinely
# decides. The cluster's existing neural entry point (``_invoke_camembert_fallacy``)
# depends on the SELF_HOSTED_LLM_* endpoint, which is not configured here → it
# returns ``status="unavailable"`` and the axis stays honest-absent (constat C3:
# the "comparison" is unilateral theatre). This detector routes through
# ``_get_openai_client()`` (the configured OpenAI/OpenRouter client) so the neural
# tier is reachable wherever the main LLM is — exactly like ``_llm_cq_evaluator``
# does for the symbolic CQ side (PR3).


async def llm_neural_detect_async(
    input_text: str, *, max_candidates: int = 25
) -> "tuple[list[SophismCandidate], Callable[[SophismCandidate], str], bool]":
    """LLM-backed neural sophism detection producing genuine ``SophismCandidate``s.

    Asks the configured LLM to detect the fallacies genuinely present in the
    text, then maps each to an opaque candidate. Mirrors ``_llm_cq_evaluator``
    (PR3): lazy imports, no-API-key honest-absent, JSON-mode, fail-soft.

    Returns ``(candidates, span_text_for, reachable)``:

    * ``candidates`` — ``SophismCandidate`` list (opaque ids ``s0..sN``, family
      from the LLM label, span_id from a deterministic hash of the span text so
      two detections on the same span with rival families are declared rivals
      under :func:`default_conflict_policy`, confidence clamped to ``[0, 1]``);
    * ``span_text_for`` — accessor feeding the Walton-CQ bridge;
    * ``reachable`` — ``False`` when no key is configured OR the call/parse
      failed (the axis MUST then surface as ``degraded``, never as a genuine
      comparison — anti-théâtre #1019). ``True`` when the LLM genuinely ran
      (even if it returned zero fallacies: a reachable negative is honest, not
      degraded — see :func:`compare_sophism_backends` semantics).
    """

    # Lazy import (same no-cycle rationale as the CQ evaluator above).
    from argumentation_analysis.orchestration.invoke_callables import (
        _get_determinism_params,
        _get_openai_client,
        _guarded_chat_completion,
        _parse_json_from_llm,
    )

    client, model_id = _get_openai_client()
    if client is None:
        logger.info(
            "LLM neural detect: no API key configured — neural tier "
            "unreachable (degraded, #1456)."
        )
        return [], lambda c: "", False

    system_content = (
        "You are an expert at detecting informal fallacies in argumentative text. "
        "Identify the GENUINE fallacies present — report a fallacy ONLY when the "
        "passage really commits it. Do NOT invent fallacies. For each one give: "
        "a short family label (e.g. ad_hominem, straw_man, appeal_to_authority, "
        "false_dilemma, hasty_generalization, slippery_slope, circular_reasoning, "
        "equivocation, appeal_to_emotion, red_herring), the exact span text that "
        "commits it (verbatim, <= 400 chars), and a confidence in [0,1]. "
        "Respond with ONLY a JSON object of shape: "
        '{"fallacies": [{"family": "...", "span_text": "...", "confidence": 0.0}]}'
    )
    user_content = (
        f"Analyse the following text for fallacies:\n\n{input_text[:8000]}\n\n"
        "Return the JSON."
    )

    det_params = _get_determinism_params()
    llm_kwargs: dict[str, Any] = dict(det_params)
    llm_kwargs["response_format"] = {"type": "json_object"}
    try:
        response = await _guarded_chat_completion(
            client,
            model=model_id,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            **llm_kwargs,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft: any LLM error → degraded
        logger.info(
            "LLM neural detect: call failed (%s); neural tier unreachable "
            "(degraded, #1456).",
            exc,
        )
        return [], lambda c: "", False

    raw = response.choices[0].message.content or ""
    try:
        data = _parse_json_from_llm(raw)
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "LLM neural detect: parse failed (%s); neural tier unreachable "
            "(degraded, #1456).",
            exc,
        )
        return [], lambda c: "", False

    raw_fallacies = data.get("fallacies") if isinstance(data, dict) else None
    if not isinstance(raw_fallacies, list):
        # Reachable, but nothing structured to detect — a reachable negative.
        return [], lambda c: "", True

    span_by_id: dict[str, str] = {}
    candidates: list[SophismCandidate] = []
    seen_ids: set[str] = set()
    for i, f in enumerate(raw_fallacies[:max_candidates]):
        if not isinstance(f, dict):
            continue
        family = str(f.get("family", "unknown")).strip() or "unknown"
        span_text = str(f.get("span_text", "")).strip()[:400]
        if not span_text:
            continue
        try:
            confidence = float(f.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        # Deterministic, opaque span anchor: same span text ⇒ same span_id, so
        # rival-family detections on one passage are declared conflicts.
        span_id = "span_" + hashlib.md5(span_text.encode("utf-8")).hexdigest()[:8]
        cid = f"s{i}"
        while cid in seen_ids:  # defensive: never collide with a challenger id
            cid = f"s{i}_{len(seen_ids)}"
        seen_ids.add(cid)
        span_by_id[cid] = span_text
        candidates.append(
            SophismCandidate(
                candidate_id=cid,
                family=family,
                span_id=span_id,
                confidence=confidence,
            )
        )

    def span_text_for(c: SophismCandidate) -> str:
        return span_by_id.get(c.candidate_id, "")

    logger.info(
        "LLM neural detect: %d genuine candidate(s); neural tier reachable (#1456).",
        len(candidates),
    )
    return candidates, span_text_for, True


def make_llm_cq_evaluator() -> CQEvaluator:
    """Build a synchronous ``CQEvaluator`` wrapping the async LLM-backed one.

    The bridge's :func:`walton_cq_bridge` consumes a sync callable. The returned
    ``CQEvaluator`` runs the async LLM call to completion via
    ``asyncio.run`` — safe from the PR3 probe (sync entry point that runs once
    per candidate). If called from an already-running event loop (e.g. inside
    another async context), the call fails soft: returns () so the bridge stays
    honest-absent for that candidate rather than crashing the run.

    Lazy-imports the async helper so importing this module stays LLM-free (no
    network calls at import time, no module-load cycle with ``invoke_callables``).
    """

    def _sync(
        span_text: str, scheme: ArgumentationScheme, candidate: SophismCandidate
    ) -> Sequence[str]:
        try:
            import asyncio

            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to drive the async helper synchronously.
            try:
                return asyncio.run(
                    _llm_cq_evaluator_async(span_text, scheme, candidate)
                )
            except Exception as exc:  # noqa: BLE001 — fail-soft
                logger.info(
                    "LLM cq_evaluator (sync wrapper): run failed (%s); "
                    "staying honest-absent.",
                    exc,
                )
                return ()
        # Already inside an event loop — cannot asyncio.run. Fail soft.
        logger.info(
            "LLM cq_evaluator: sync wrapper called from a running loop; "
            "staying honest-absent. Use _llm_cq_evaluator_async directly."
        )
        return ()

    return _sync
