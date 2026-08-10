"""#1646 — pure-Python minimal-retraction computation (the belief-revision insight).

The singular contribution of belief revision (#1646 section A) is the **minimal
retraction** — the smallest set of beliefs whose removal restores consistency
(a minimum correction subset). This is a global cardinality property no other
component computes (PL says UNSAT but not what to give up; the Tweety handler
runs Levi expansion, not a distance-based retraction; an LLM gives local
observations, never a minimal cardinality). The function is a pure SAT
enumeration over the clause base — no JVM, no Tweety reasoner — so it survives
the honest-degraded path where the handler never runs (#1670/#1677), mirroring
``bipolar_insight.py`` (#1645).

These tests pin the algorithm directly (kill-set A: a broken enumeration /
oracle returns wrong cardinality or misses options). The reader-side naming is
pinned in a separate test file (kill-set B) once the insight is wired to the
Acte III reader. Opaque synthetic atoms only.
"""

from argumentation_analysis.agents.core.logic.belief_revision_insight import (
    build_belief_base,
    minimal_retractions,
)


class TestMinimalRetractions:
    def test_consistent_base_needs_no_retraction(self) -> None:
        """A satisfiable base has cardinality 0 — no insight fabricated."""
        assert minimal_retractions([[1], [2], [3]]) == (0, [()])

    def test_single_clause_retraction_cardinality_one(self) -> None:
        """B-1: the canonical case — ONE belief restores consistency (cardinal 1).

        base p1, p1->p2, ¬p2 is UNSAT (p1 ∧ (p1->p2) |= p2 contradicts ¬p2).
        """
        card, opts = minimal_retractions([[1], [-1, 2], [-2]])
        assert card == 1
        # Three cardinal-1 options exist: drop p1, drop p1->p2, drop ¬p2.
        assert len(opts) == 3
        assert all(len(o) == 1 for o in opts)

    def test_no_unique_retraction_insight_b2(self) -> None:
        """B-2: when several cardinal-1 retractions exist, none is privileged.

        This is the figure "there is no unique minimal retraction" — the options
        are all returned, same cardinality, leading to incompatible consistent
        bases.
        """
        card, opts = minimal_retractions([[1], [-1, 2], [-2]])
        assert card == 1
        assert len(opts) >= 2
        # Each option is a distinct singleton retraction.
        flat = {o[0] for o in opts}
        assert len(flat) == len(opts)

    def test_inert_contradiction_insight_b3(self) -> None:
        """B-3 (the most discriminating): a real clash whose minimal retraction
        never touches the conclusion beliefs.

        base p1, ¬p1, r, s — the p1/¬p1 clash is real, but r and s are
        independent conclusions. The minimal retraction isolates the clash and
        leaves r, s intact. No contradiction-detector (PL/UNSAT) can establish
        this, because it never asks what survives.
        """
        base = [[1], [-1], [5], [6]]
        card, opts = minimal_retractions(base)
        assert card == 1
        # Every retraction option touches only the clashing beliefs (idx 0,1),
        # never the conclusions (idx 2,3).
        for opt in opts:
            assert all(i in (0, 1) for i in opt)

    def test_bare_contradiction_two_clauses(self) -> None:
        """p and ¬p: cardinal 1, two options (drop either)."""
        card, opts = minimal_retractions([[1], [-1]])
        assert card == 1
        assert (0,) in opts and (1,) in opts

    def test_two_independent_clashes_need_cardinal_two(self) -> None:
        """Minimality over TWO independent clashes: cardinal 2, not 1.

        base p1, p2, ¬p1, ¬p2 has two disjoint clashes. Removing any single
        clause leaves the other clash intact (still UNSAT), so the minimal
        cardinality is 2 — one retraction per clash. This is the minimality
        guarantee: the search does not stop at a non-restoring cardinal-1 guess.
        """
        card, opts = minimal_retractions([[1], [2], [-1], [-2]])
        assert card == 2
        assert all(len(o) == 2 for o in opts)

    def test_beyond_search_bound_degrades_honestly(self) -> None:
        """A base whose minimal retraction exceeds the search bound returns -1
        (no fabricated minimal set) — fail-loud #1019.

        Five independent clashes need cardinal 5, but the search bound caps at 4,
        so no restoring subset is found within budget.
        """
        five_clashes = [[1], [-1], [2], [-2], [3], [-3], [4], [-4], [5], [-5]]
        card, opts = minimal_retractions(five_clashes)
        assert card == -1
        assert opts == []

    def test_empty_base_is_consistent(self) -> None:
        """An empty belief base is trivially satisfiable (no retraction)."""
        assert minimal_retractions([]) == (0, [()])

    def test_result_is_deterministic(self) -> None:
        """Same input ⇒ same output across calls (no set-ordering leak)."""
        base = [[1], [-1, 2], [-2]]
        first = minimal_retractions(base)
        for _ in range(20):
            assert minimal_retractions(base) == first

    def test_implication_chain_forces_contradiction(self) -> None:
        """p1 -> p2 -> p3, plus ¬p3, plus p1: the chain derives p3, contradicting
        ¬p3. Cardinal 1 — break any link.
        """
        # p1, p1->p2, p2->p3, ¬p3
        card, opts = minimal_retractions([[1], [-1, 2], [-2, 3], [-3]])
        assert card == 1
        assert len(opts) == 4  # p1, p1->p2, p2->p3, ¬p3 each break the chain


class TestBuildBeliefBase:
    """#1646 base construction (coord ruling R779 ruling 2): derive ¬arg from
    fallacies so the belief base is *genuinely* inconsistent — the precondition
    for minimal_retractions to bite (the D-forensic verdict: _pl_atom sanitizes
    every belief positive → trivially consistent → retraction ∅).

    Convention: a fallacy on argument X adds [-x] alongside [x]. Mirrors
    fallacy_contraction (conversational), which removes the targeted belief.
    Opaque synthetic atoms only.
    """

    def test_no_fallacy_yields_consistent_base(self) -> None:
        """Arguments alone, no fallacy negation → trivially consistent (card 0).

        This is the baseline the D-forensic measured: a base with no negations
        has a minimal retraction of ∅ — no insight. The base construction must
        not fabricate a clash where the upstream detected none.
        """
        base, names = build_belief_base(["x", "y", "z"], [])
        assert base == [[1], [2], [3]]
        assert names == ["x", "y", "z"]
        assert minimal_retractions(base)[0] == 0

    def test_one_fallacy_creates_real_clash(self) -> None:
        """A fallacy on the first argument adds ¬x → base {[x],[y],[-x]} UNSAT.

        The clash is real; minimal_retractions returns cardinal 1. The negation
        clause is labeled ¬x (the reader names the point of rupture).
        """
        base, names = build_belief_base(["x", "y"], [0])
        assert base == [[1], [2], [-1]]
        assert names == ["x", "y", "¬x"]
        card, opts = minimal_retractions(base)
        assert card == 1
        # Each retraction touches only the clash (index 0 = x, or 2 = ¬x), never y.
        for opt in opts:
            assert all(i in (0, 2) for i in opt)
            assert all(names[i] in ("x", "¬x") for i in opt)

    def test_inert_contradiction_leaves_conclusions_intact(self) -> None:
        """B-3 via base construction: a fallacy on x clashes, but y, z survive.

        base {[x],[y],[z],[-x]}: the x/¬x clash is real, cardinal 1, and the
        conclusion beliefs y, z never appear in any retraction option — the
        discriminating figure no contradiction-detector (PL/UNSAT) produces.
        """
        base, names = build_belief_base(["x", "y", "z"], [0])
        card, opts = minimal_retractions(base)
        assert card == 1
        for opt in opts:
            # Only the clash beliefs (x at 0, ¬x at 3) are ever retracted.
            assert all(i in (0, 3) for i in opt)
            assert all(names[i] not in ("y", "z") for i in opt)

    def test_two_fallacies_on_distinct_args_need_cardinal_two(self) -> None:
        """Two fallacies on two distinct arguments → two independent clashes.

        base {[x],[y],[-x],[-y]}: removing one clause leaves the other clash,
        so the minimal cardinality is 2 — one retraction per clash (the
        minimality guarantee).
        """
        base, names = build_belief_base(["x", "y"], [0, 1])
        assert base == [[1], [2], [-1], [-2]]
        card, opts = minimal_retractions(base)
        assert card == 2
        assert all(len(o) == 2 for o in opts)

    def test_out_of_range_index_ignored(self) -> None:
        """An ungrounded target (index out of range) is ignored, not asserted.

        #1019: an attack we cannot ground is an attack we do not assert. A
        fallacy whose target resolves outside the argument list adds no clause.
        """
        base, names = build_belief_base(["x"], [0, 1, 5, -1])
        # Only index 0 is in range → one negation; the rest are dropped.
        assert base == [[1], [-1]]
        assert names == ["x", "¬x"]

    def test_repeated_fallacy_same_arg_adds_one_negation(self) -> None:
        """Several fallacies on the same argument yield one clash, not many.

        A negated belief is one clause ``[-x]`` regardless of how many fallacies
        target x — the belief-not-tenable is a single belief, not one-per-fallacy
        (deduplication; otherwise the reader would name phantom alternatives).
        """
        base, _names = build_belief_base(["x"], [0, 0, 0])
        assert base == [[1], [-1]]
        card, opts = minimal_retractions(base)
        assert card == 1
        # Two singletons: drop x (index 0) or drop ¬x (index 1).
        assert sorted(opts) == [(0,), (1,)]

    def test_construction_is_deterministic(self) -> None:
        """Same arguments + same indices ⇒ same (base, names) every call."""
        first = build_belief_base(["a", "b", "c"], [1])
        for _ in range(20):
            assert build_belief_base(["a", "b", "c"], [1]) == first
