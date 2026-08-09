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
removal makes the conjunction satisfiable. For the small bases the pipeline
produces (8-12 clauses on real runs, measured #1646 D) this is trivially cheap.
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

from typing import List, Tuple

# A belief, here, is one CNF clause: a list of signed integer literals.
#   [1]       = positive belief in atom 1
#   [-2]      = belief ¬(atom 2)
#   [-1, 2]   = belief (atom 1 -> atom 2)
Clause = List[int]
BeliefBase = List[Clause]

#: upper bound on the retraction cardinality we search for. The pipeline bases
#: are small (<= ~12 clauses on real runs); a retraction beyond this would mean
#: the base is deeply inconsistent and the insight degrades honestly (no
#: fabricated minimal set).
_MAX_SEARCH = 4


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


def minimal_retractions(belief_base: BeliefBase) -> Tuple[int, List[Tuple[int, ...]]]:
    """Minimum correction subsets of a proposional belief base (#1646).

    Returns ``(cardinality, options)`` where ``options`` is the list of minimal
    retraction sets (as index-tuples into ``belief_base``). ``cardinality == 0``
    with ``options == [()]`` means the base is already consistent (no retraction
    needed). ``cardinality == -1`` means no retraction within ``_MAX_SEARCH``
    restores consistency (deeply inconsistent base; the insight degrades
    honestly rather than fabricate).

    The minimal retraction is the smallest set of beliefs to give up so the rest
    holds together — the singular contribution of belief revision. Enumerating
    by increasing size guarantees the *minimal* cardinality (a greedy or
    single-shot removal would not). For the small pipeline bases this is cheap;
    the search bound keeps it bounded on pathological inputs.

    Examples (opaque synthetic atoms):

        A single belief restores consistency (insight B-1, "cardinal 1")::

            >>> base = [[1], [-1, 2], [-2]]  # p1, p1->p2, ¬p2  => UNSAT
            >>> card, opts = minimal_retractions(base)
            >>> card
            1
            >>> len(opts)  # three cardinal-1 options (p1, p1->p2, ¬p2)
            3

        No unique minimal retraction (insight B-2) — same base, >1 option::

            >>> card, opts = minimal_retractions([[1], [-1, 2], [-2]])
            >>> len(opts) >= 2
            True

        An inert contradiction (insight B-3): the clash is real but its minimal
        retraction never touches the conclusion beliefs (atoms 5, 6)::

            >>> base = [[1], [-1], [5], [6]]  # p1/¬p1 clash, r & s independent
            >>> card, opts = minimal_retractions(base)
            >>> card
            1
            >>> all(5 not in base[i] and 6 not in base[i]
            ...     for opt in opts for i in opt)
            True

        A consistent base needs no retraction::

            >>> minimal_retractions([[1], [2], [3]])
            (0, [()])
    """
    if _is_satisfiable(belief_base):
        return (0, [()])

    n = len(belief_base)
    from itertools import combinations

    for k in range(1, min(_MAX_SEARCH, n) + 1):
        winners: List[Tuple[int, ...]] = []
        for drop in combinations(range(n), k):
            kept = [belief_base[i] for i in range(n) if i not in drop]
            if _is_satisfiable(kept):
                winners.append(drop)
        if winners:
            return (k, winners)
    return (-1, [])
