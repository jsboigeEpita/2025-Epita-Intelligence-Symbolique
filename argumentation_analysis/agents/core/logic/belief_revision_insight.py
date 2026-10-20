"""JVM-free minimal-retraction computation over a propositional belief base.

The singular contribution of belief revision (#1646 section A) is the **minimal
retraction**: the *smallest* set of beliefs whose removal restores the
consistency of the base. This is a global cardinality property — "the minimal
retraction is of cardinal 1, and it is Z" — that no other component of the chain
produces:

- an LLM asked to "find contradictions" gives local observations
  ("the speaker contradicts themselves between X and Y"), never a global
  minimal-retraction cardinality;
- the PL solver says UNSAT (the base is inconsistent), but not *what to give up*
  nor *how little suffices*;
- the Tweety-bound ``BeliefRevisionHandler`` runs the **Levi pattern**
  (contraction of ``¬new`` + expansion of ``new``), which is an *expansion* when
  the base does not contain ``¬new`` — it never computes a distance-based
  minimal retraction (Tweety 1.28 exposes no ``DalalRevision`` operator; the
  handler docstring says so).

So the insight lives HERE, as a pure function, not in the JVM-bound handler —
the same architectural lesson as ``bipolar_insight.py`` (#1645): a structural
insight that lives inside a JVM-bound handler dies on the honest-degraded path
where the handler never runs (#1670/#1677).

The computation is a **minimum correction subset** (MCS): enumerate removal
subsets of the clause base by increasing size and return the smallest whose
removal makes the conjunction satisfiable. The base is first split into its
**connected components** — clauses linked by the atoms they share. A
component's atoms are disjoint from every other component's, so the base is
consistent iff every component is, and the minimum correction subset
decomposes exactly: the cardinality sums over the unsatisfiable components and
the option set is their cartesian product. #3088: #3014 grew the population to
40 units, where the flat sweep walked C(40, k) and exhausted its subset budget
at k=8 on every real run since.
A pure-Python SAT oracle (``python-sat``, a pinned dep) is used — **no JVM, no
Tweety reasoner**.

Each entry of ``belief_base`` is one belief expressed as a CNF clause (a list of
signed integer literals). A belief ``p1 -> p2`` is the clause ``[-1, 2]``; a
positive belief ``p1`` is ``[1]``; a negation ``¬p2`` is ``[-2]``. Retraction is
at the **belief** granularity (one clause = one belief), so the reader can name
which belief is the point of rupture (insight B-1) and how many alternatives of
the same cardinality exist (insight B-2). The discriminating case (insight B-3,
"inert contradiction") reads directly off the result: a real inconsistency whose
minimal retraction touches only a clashing belief while the conclusion beliefs
never appear in any retraction option.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Any, Dict, List, Optional, Sequence, Tuple

# A belief, here, is one CNF clause: a list of signed integer literals.
#   [1]       = positive belief in atom 1
#   [-2]      = belief ¬(atom 2)
#   [-1, 2]   = belief (atom 1 -> atom 2)
Clause = List[int]
BeliefBase = List[Clause]

#: Upper bound on the retraction cardinality we search for, PER unsatisfiable
#: component (#3088: the components are independent, so this cap applies to a
#: component's cardinality, not to the summed one). Real corpus runs (measured
#: 2026-09-19, doc_0 spectacular): 8 fallacy targets -> 8 independent clash
#: pairs -> minimal retraction of cardinality **8** — the old fixed cap of 4 sat
#: below every real-run cardinality, so the insight degraded to -1 on each real
#: run while the planted texts (cardinal 1-2) stayed green. The cap now covers
#: real-run cardinalities (fallacy counts bound it); beyond it, the component is
#: deeply inconsistent and the search refuses BY NAME (``refusal="search_k"``),
#: never fabricating a minimal set.
_MAX_SEARCH_K = 12

#: Cumulative-subset budget across the whole k-sweep — the pathology guard.
#: It is drawn from by every component's sweep, so a dense component cannot
#: spend it forever. The original calibration ("doc_0: ~127k subsets; a
#: 10-target doc: ~616k") held for a 7-unit window: on the 40-unit population
#: #3014 introduced, the FLAT sweep passed it at k=8 and returned -1 after a
#: ~36 s churn on every real run (#3088, measured). The decomposition now keeps
#: per-component sweeps small; a component that still exhausts the budget
#: refuses BY NAME (``refusal="subset_budget"``) with the figures.
_MAX_SUBSET_BUDGET = 700_000

#: Stored-options cap for the state entry (see ``shape_minimal_retraction``):
#: real-run bases yield combinatorially many minimal options; the exact count
#: rides along as the int ``options_total``.
_OPTIONS_STORED_CAP = 64


def _is_satisfiable(clauses: BeliefBase) -> bool:
    """True iff the conjunction of ``clauses`` is SAT (Glucose3 oracle)."""
    # Local import: python-sat is a hard pinned dep (1.9.dev8). Keeping it
    # inside the function means a missing dep degrades THIS insight honestly
    # (the function raises) rather than poisoning the module import for callers
    # that only want, e.g., a future non-SAT helper in this module.
    from pysat.solvers import Glucose3

    if not clauses:
        return True
    with Glucose3(bootstrap_with=clauses) as solver:
        return bool(solver.solve())


@dataclass(frozen=True)
class RetractionResult:
    """The retraction search's verdict — a refusal always names its bound.

    ``cardinality == -1`` iff ``refusal`` is set: the search stopped AT a bound
    instead of churning, and the reason rides with the figure (#3088 item 4 —
    the silent ``-1`` that followed a ~36 s sweep is what the issue opened on).
    ``options`` stores at most ``_OPTIONS_STORED_CAP`` minimal options, as index
    tuples into the base; ``options_total`` is the EXACT multiplicity, obtained
    by product over the components and never materialized. ``touched`` holds
    every clause index appearing in SOME minimal option — exact, computed over
    the components rather than derived from the stored head.
    """

    cardinality: int
    options: List[Tuple[int, ...]]
    options_total: int
    touched: Tuple[int, ...] = ()
    refusal: Optional[str] = None
    refusal_detail: str = ""

    @property
    def degraded(self) -> bool:
        """True iff the search refused at a bound (never for a computed result)."""
        return self.refusal is not None


def _clause_components(belief_base: BeliefBase) -> List[List[int]]:
    """Clause indices grouped by the atoms they share (insertion-ordered).

    Two clauses are linked when a chain of shared atoms connects them, so the
    groups' atom sets are pairwise disjoint — which is exactly what makes the
    retraction decompose (see :func:`minimal_retractions`). An empty clause is
    always false and shares no atom: it forms a component of its own.
    """
    parent: Dict[int, int] = {}

    def find(node: int) -> int:
        parent.setdefault(node, node)
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for index, clause in enumerate(belief_base):
        atoms = {abs(literal) for literal in clause}
        if not atoms:
            find(-(index + 1))  # a node of its own — no atom can collide with it
            continue
        anchor = min(atoms)
        for atom in atoms:
            union(anchor, atom)

    groups: "Dict[int, List[int]]" = {}
    for index, clause in enumerate(belief_base):
        atoms = {abs(literal) for literal in clause}
        root = find(min(atoms)) if atoms else find(-(index + 1))
        groups.setdefault(root, []).append(index)
    return list(groups.values())


def _sweep_component(
    component: BeliefBase, budget: int
) -> "Tuple[int, List[Tuple[int, ...]], int, Optional[str], str]":
    """The bounded increasing-k sweep over ONE unsatisfiable component.

    Returns ``(cardinality, options, budget, refusal, detail)``; ``refusal`` is
    set (with ``cardinality == -1``) when a bound stopped the sweep, and the
    detail carries the figures — never a bare ``-1``.
    """
    n = len(component)
    for k in range(1, min(_MAX_SEARCH_K, n) + 1):
        winners: List[Tuple[int, ...]] = []
        for drop in combinations(range(n), k):
            budget -= 1
            if budget < 0:
                return (
                    -1,
                    [],
                    budget,
                    "subset_budget",
                    f"subset budget {_MAX_SUBSET_BUDGET} exhausted in a "
                    f"component of {n} clauses during the k={k} pass",
                )
            kept = [component[i] for i in range(n) if i not in drop]
            if _is_satisfiable(kept):
                winners.append(drop)
        if winners:
            return (k, winners, budget, None, "")
    return (
        -1,
        [],
        budget,
        "search_k",
        f"no retraction of cardinality <= {_MAX_SEARCH_K} restores a component "
        f"of {n} clauses",
    )


def minimal_retractions(belief_base: BeliefBase) -> RetractionResult:
    """Minimum correction subsets of a propositional belief base (#1646, #3088).

    Returns a :class:`RetractionResult`. ``cardinality`` 0 (with one empty
    option) means the base is already consistent. ``cardinality == -1`` comes
    WITH a named ``refusal`` and the measured reason — the search stopped at a
    bound rather than churn silently. Otherwise ``cardinality`` is the exact
    minimum and ``options_total`` the exact number of equally-minimal options.

    Exactness over a large base: the clauses split into connected components
    with pairwise-disjoint atoms, so the base is consistent iff every component
    is, and a minimum correction subset repairs each unsatisfiable component
    independently. Hence ``cardinality`` is the sum over the unsatisfiable
    components and ``options_total`` their product; a satisfiable component
    contributes to neither. The singular contribution of belief revision — the
    global minimal cardinality, which no other component computes — is
    preserved: the decomposition is an identity on the answer, not an
    approximation. 40 independent clash pairs therefore cost 40 single-pair
    sweeps instead of C(40, k), which exhausted the subset budget at k=8 on
    every real run since #3014 grew the population to 40 units (#3088).

    Examples (opaque synthetic atoms):

        A single belief restores consistency (insight B-1, "cardinal 1")::

            >>> base = [[1], [-1, 2], [-2]]  # p1, p1->p2, ¬p2  => UNSAT
            >>> result = minimal_retractions(base)
            >>> result.cardinality
            1
            >>> result.options_total  # three cardinal-1 options
            3

        No unique minimal retraction (insight B-2) — same base, >1 option::

            >>> len(minimal_retractions([[1], [-1, 2], [-2]]).options) >= 2
            True

        An inert contradiction (insight B-3): the clash is real but its minimal
        retraction never touches the conclusion beliefs (atoms 5, 6)::

            >>> base = [[1], [-1], [5], [6]]  # p1/¬p1 clash, r & s independent
            >>> result = minimal_retractions(base)
            >>> result.cardinality
            1
            >>> all(5 not in base[i] and 6 not in base[i]
            ...     for opt in result.options for i in opt)
            True

        A consistent base needs no retraction::

            >>> minimal_retractions([[1], [2], [3]]).cardinality
            0
    """
    if _is_satisfiable(belief_base):
        return RetractionResult(0, [()], 1)

    cardinality = 0
    per_component: "List[List[Tuple[int, ...]]]" = []
    touched: "set[int]" = set()
    budget = _MAX_SUBSET_BUDGET
    for component_indices in _clause_components(belief_base):
        component = [belief_base[i] for i in component_indices]
        if _is_satisfiable(component):
            continue
        card, local_options, budget, refusal, detail = _sweep_component(
            component, budget
        )
        if refusal is not None:
            return RetractionResult(-1, [], 0, (), refusal, detail)
        cardinality += card
        global_options: List[Tuple[int, ...]] = []
        for local in local_options:
            mapped = tuple(component_indices[j] for j in local)
            global_options.append(mapped)
            touched.update(mapped)
        per_component.append(global_options)

    if not per_component:
        # UNSAT overall while every component reads SAT: the oracle contradicts
        # itself. Refuse by name rather than fabricate a cardinality (#1019).
        return RetractionResult(
            -1,
            [],
            0,
            (),
            "decomposition_mismatch",
            "the base is UNSAT while every connected component is SAT",
        )

    options_total = 1
    for options in per_component:
        options_total *= len(options)
    # The stored head is the first ``_OPTIONS_STORED_CAP`` combinations in
    # component order — sorted for a stable reading. The full set is NEVER
    # materialized: on a decomposable base it can be astronomically larger than
    # any store (40 clash pairs: 2**40), and the exact figure already rides in
    # ``options_total``.
    stored: List[Tuple[int, ...]] = []
    for combination in product(*per_component):
        stored.append(tuple(sorted(i for option in combination for i in option)))
        if len(stored) >= _OPTIONS_STORED_CAP:
            break
    stored.sort()
    return RetractionResult(cardinality, stored, options_total, tuple(sorted(touched)))


def shape_minimal_retraction(
    result: RetractionResult, names: List[str]
) -> Dict[str, Any]:
    """Shape a retraction result for the ``belief_revision_results`` state entry.

    Shared by both mode-exclusive producers (the pipeline
    ``_invoke_belief_revision`` and the conversational
    ``_run_belief_revision_from_state``). Real-run bases yield combinatorially
    many equally-minimal retractions (doc_0: 8 clash pairs -> 2**8 = 256
    options; the #3088 shape: 2**10 = 1024), so the stored ``options`` list is
    capped while the exact ``options_total`` rides along — the Acte III reader
    names the TRUE multiplicity (insight B-2), never the storage cap.
    ``options_total`` is an int: nothing textual to scrub (sanitize_state leaves
    non-list leaves of ``minimal_retraction`` untouched).

    A refusal (``cardinality == -1`` at a bound) is shaped WITH its name and the
    measured reason (``refusal``/``refusal_detail``) and ``degraded`` True: the
    reader can name which bound stopped the search instead of reading a bare -1
    (#3088 item 4).
    """
    if result.refusal is not None:
        return {
            "cardinality": -1,
            "options": [],
            "options_total": 0,
            "base_size": len(names),
            "touched_count": 0,
            "degraded": True,
            "refusal": result.refusal,
            "refusal_detail": result.refusal_detail,
        }
    stored = [[names[i] for i in opt] for opt in result.options]
    return {
        "cardinality": result.cardinality,
        "options": stored,
        "options_total": result.options_total,
        "base_size": len(names),
        "touched_count": len(result.touched),
        "degraded": False,
    }


def build_belief_base(
    arguments: Sequence[str],
    negated_indices: Sequence[int],
) -> Tuple[BeliefBase, List[str]]:
    """Build a CNF belief base where fallacies introduce real contradictions.

    This is the **base construction** for ``minimal_retractions`` (#1646, coord
    ruling R779 ruling 2 — "derive ¬arg from fallacies"). It turns the pipeline's
    extracted arguments + the fallacies that undermine them into a belief base
    that is *genuinely inconsistent*, which is the precondition for the
    minimal-retraction insight to bite (without it, ``_pl_atom`` sanitizes every
    belief to a positive atom and the base is trivially consistent — the D-forensic
    verdict, 3 locks).

    **Derivation convention** (documented per the coord's guard): a detected
    fallacy targeting argument X establishes that belief X is **not tenable**.
    Argument X is the positive unit clause ``[x]`` (the belief as the speaker
    advanced it); the fallacy adds the negation ``[-x]``. The base
    ``{[x], [-x]}`` is a real clash, and ``minimal_retractions`` isolates it —
    naming which belief must be given up. This mirrors the conversational path's
    ``fallacy_contraction`` (which *removes* the targeted belief; here we *negate*
    it, creating the clash the retraction computation resolves) and the pipeline's
    own ``new_belief = NOT(target)`` counter-argument intent (l.3982), which
    ``_pl_atom`` was silently laundering back to a positive atom.

    The fallacy must undermine the *tenability* of the belief it targets for the
    negation to be honest. All targeted fallacies in this repo's taxonomy
    (ad hominem, petitio principii, false cause, …) attack tenability — that is
    precisely the ``fallacy_contraction`` contract. A per-type granularity (which
    fallacy *negates* vs merely *weakens*) is a documented follow-up, not a
    precondition; the convention here matches the existing contraction path
    rather than inventing a new taxonomy call.

    Atom ``i+1`` ↔ ``arguments[i]`` (the 1-based signed-int convention of this
    module). Indices out of range are **ignored** (#1019: an ungrounded target is
    not asserted — we do not invent a clash where the upstream did not ground one).

    Args:
        arguments: the belief labels, in order. Each becomes a positive unit
            clause; the label names the point of rupture for the reader.
        negated_indices: 0-based indices into ``arguments`` of the beliefs a
            fallacy negates (already resolved from ``arg_N`` identifiers by the
            producer — see ``_resolve_target_argument_index``).

    Returns:
        ``(base, names)`` where ``base[i]`` is clause ``i`` and ``names[i]`` is
        its label (the argument, or ``"¬arg"`` for a fallacy-negation clause).

    Examples (opaque synthetic atoms):

        No fallacy ⇒ consistent base (cardinal 0, the D-forensic baseline)::

            >>> base, names = build_belief_base(["x", "y", "z"], [])
            >>> base
            [[1], [2], [3]]
            >>> minimal_retractions(base).cardinality
            0

        One fallacy on the first argument ⇒ a real clash (cardinal 1)::

            >>> base, names = build_belief_base(["x", "y"], [0])
            >>> base
            [[1], [2], [-1]]
            >>> result = minimal_retractions(base)
            >>> result.cardinality
            1
            >>> all(names[i] in ("x", "¬x")
            ...     for opt in result.options for i in opt)
            True
    """
    n = len(arguments)
    base: BeliefBase = [[i + 1] for i in range(n)]
    names: List[str] = list(arguments)
    seen: set[int] = set()
    for idx in negated_indices:
        if isinstance(idx, int) and 0 <= idx < n and idx not in seen:
            seen.add(idx)
            base.append([-(idx + 1)])
            names.append(f"¬{arguments[idx]}")
    return base, names
