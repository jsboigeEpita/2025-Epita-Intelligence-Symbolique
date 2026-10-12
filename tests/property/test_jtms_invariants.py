"""Property-based tests for JTMS (Justification-based Truth Maintenance System) invariants.

Uses hypothesis to randomly generate belief networks and verify universal properties:
1. Justification chain consistency: valid beliefs have at least one fully-satisfied justification
2. Retraction cascade: retracting a belief invalidates all dependent beliefs
3. Cycle detection: mutual dependencies (A→B→A) are marked non-monotonic
"""

import itertools

import pytest
from hypothesis import given, settings, assume, seed
from hypothesis import strategies as st

from argumentation_analysis.services.jtms.jtms_core import JTMS

# --- Strategies ---

belief_names = st.lists(
    st.sampled_from([f"b{i}" for i in range(8)]),
    min_size=2,
    max_size=8,
    unique=True,
)


@st.composite
def jtms_network_spec(draw):
    """Draw a raw network spec: belief names, justifications, then a prefix
    of directly-set-valid names. The conclusion may be one of its own
    premises — self-loops (``a ← ¬a``) are part of the surface since #3018,
    they are no longer excluded from the draw."""
    names = draw(belief_names)
    justifications = []
    n_just = draw(st.integers(min_value=1, max_value=6))
    for _ in range(n_just):
        candidates = list(names)
        if len(candidates) < 2:
            continue
        in_list = draw(
            st.lists(
                st.sampled_from(candidates),
                min_size=0,
                max_size=min(3, len(candidates)),
                unique=True,
            )
        )
        remaining = [n for n in candidates if n not in in_list]
        out_list = (
            draw(
                st.lists(
                    st.sampled_from(remaining),
                    min_size=0,
                    max_size=min(2, len(remaining)),
                    unique=True,
                )
            )
            if remaining
            else []
        )
        conclusion = draw(st.sampled_from(candidates))
        justifications.append((in_list, out_list, conclusion))

    valid_count = draw(st.integers(min_value=0, max_value=len(names)))
    return names, justifications, names[:valid_count]


def build_jtms(names, justifications, valid_names=()):
    """Build a JTMS from a spec: beliefs, then justifications, THEN direct
    validity sets — truth values are determined by the network."""
    jtms = JTMS()
    for name in names:
        jtms.add_belief(name)
    for in_list, out_list, conclusion in justifications:
        jtms.add_justification(in_list, out_list, conclusion)
    for name in valid_names:
        jtms.set_belief_validity(name, True)
    return jtms


@st.composite
def jtms_with_justifications(draw):
    names, justifications, valid_names = draw(jtms_network_spec())
    jtms = build_jtms(names, justifications, valid_names)
    return jtms, names, valid_names


# --- Tests ---


class TestJTMSJustificationConsistency:
    """A belief marked valid must have at least one justification where all
    in-beliefs are valid and all out-beliefs are invalid."""

    @given(network=jtms_with_justifications())
    @settings(max_examples=50, deadline=2000)
    @pytest.mark.property
    def test_valid_belief_has_satisfied_justification(self, network):
        jtms, names, valid_names = network
        directly_set = set(valid_names)

        for name in names:
            belief = jtms.beliefs[name]
            if belief.valid is not True:
                continue
            if not belief.justifications:
                continue
            # Beliefs set directly may override justification logic — skip those
            if name in directly_set:
                continue
            # This belief derived validity from propagation — invariant must hold
            has_satisfied = False
            for just in belief.justifications:
                in_ok = all(b.valid is True for b in just.in_list)
                out_ok = all(b.valid is not True for b in just.out_list)
                if in_ok and out_ok:
                    has_satisfied = True
                    break
            assert (
                has_satisfied
            ), f"Belief {name} is valid via propagation but no justification is satisfied"


class TestJTMSUnconditionalOnOddLoop:
    """#3013 — the issue's 4-belief counterexample, as an explicit witness.

    Hypothesis found and shrank this table on a fresh database; the CI gate
    draws 50 fresh examples per run and never sees it. Pinned here so the
    gate stops depending on the draw. Born red on main ``2f9cdb9d5``.
    """

    def test_unconditional_belief_is_true_on_odd_loop_and_dependents_follow(self):
        jtms = JTMS()
        for name in ["b0", "b1", "b2", "b3"]:
            jtms.add_belief(name)
        # (in, out -> conclusion), insertion order — the issue's table.
        jtms.add_justification(["b3"], [], "b0")  # J1
        jtms.add_justification([], [], "b1")  # J2
        jtms.add_justification([], [], "b1")  # J3
        jtms.add_justification(["b3"], [], "b2")  # J4
        jtms.add_justification([], ["b0"], "b3")  # J5 — odd loop with J1
        jtms.add_justification([], [], "b3")  # J6 — unconditional

        # b3's unconditional justification (J6) holds whatever b0 is: the odd
        # loop through J5/J1 does not erase it. On main b3 stayed None.
        assert jtms.beliefs["b3"].valid is True
        # The loop is still detected and marked — the flag is a marker, not a
        # label override.
        assert jtms.beliefs["b3"].non_monotonic is True
        assert jtms.beliefs["b0"].non_monotonic is True

        # The property's invariant, made explicit on this network: every
        # belief that is valid has a satisfied justification. On main, b2 kept
        # a stale True from before b3's drop, with J4 unsatisfied.
        for name in ["b0", "b1", "b2", "b3"]:
            belief = jtms.beliefs[name]
            assert belief.valid is True, f"Belief {name} should be True (#3013)"
            has_satisfied = any(
                all(b.valid is True for b in just.in_list)
                and all(b.valid is not True for b in just.out_list)
                for just in belief.justifications
            )
            assert (
                has_satisfied
            ), f"Belief {name} is valid but no justification is satisfied (#3013)"


class TestJTMSWellFoundedLoopLabeling:
    """#3018 — a loop's labels come from a global well-founded computation,
    not from the insertion order: the two issue networks, checked over ALL
    their insertion orders, admit exactly one labeling with zero broken
    beliefs (no True without a satisfied justification). The non-monotonic
    flag is exact: a cycle counts only through an out-list edge, self-loops
    included, positive cycles stay unflagged."""

    def _labels(self, jtms):
        return {name: belief.valid for name, belief in jtms.beliefs.items()}

    def _assert_no_broken_support(self, jtms, order):
        """Label ⇔ support: no belief is True without a satisfied
        justification under the final labels."""
        for name, belief in jtms.beliefs.items():
            if belief.valid is True:
                has_satisfied = any(
                    all(b.valid is True for b in just.in_list)
                    and all(b.valid is not True for b in just.out_list)
                    for just in belief.justifications
                )
                assert has_satisfied, (
                    f"{name} is True without satisfied justification "
                    f"(insertion order {order})"
                )

    def test_odd_loop_pair_one_labeling_over_all_orders(self):
        """`a ← ¬b, b ← a, b ← x` — coordinator-measured 3 labelings / 6
        broken beliefs over the 6 insertion orders on #3016."""
        justifications = [([], ["b"], "a"), (["a"], [], "b"), (["x"], [], "b")]
        labelings = set()
        for order in itertools.permutations(justifications):
            jtms = build_jtms(["a", "b", "x"], order)
            # The well-founded reading: the a↔b loop has no grounded
            # support (x is not a fact), so nobody on it is True.
            for name in ("a", "b", "x"):
                assert (
                    jtms.beliefs[name].valid is None
                ), f"{name}={jtms.beliefs[name].valid} (insertion order {order})"
            self._assert_no_broken_support(jtms, order)
            labelings.add(tuple(sorted(self._labels(jtms).items())))
        assert len(labelings) == 1, "insertion order must not change the labeling"
        # Marking exact: the cycle passes through J1's out-list edge; x
        # is not on it.
        assert jtms.beliefs["a"].non_monotonic is True
        assert jtms.beliefs["b"].non_monotonic is True
        assert jtms.beliefs["x"].non_monotonic is False

    def test_odd_three_cycle_one_labeling_over_all_orders(self):
        """`a ← ¬b, b ← ¬c, c ← ¬a, c ← x` — 4 labelings / 24 broken over
        the 24 insertion orders on #3016."""
        justifications = [
            ([], ["b"], "a"),
            ([], ["c"], "b"),
            ([], ["a"], "c"),
            (["x"], [], "c"),
        ]
        labelings = set()
        for order in itertools.permutations(justifications):
            jtms = build_jtms(["a", "b", "c", "x"], order)
            for name in ("a", "b", "c", "x"):
                assert (
                    jtms.beliefs[name].valid is None
                ), f"{name}={jtms.beliefs[name].valid} (insertion order {order})"
            self._assert_no_broken_support(jtms, order)
            labelings.add(tuple(sorted(self._labels(jtms).items())))
        assert len(labelings) == 1, "insertion order must not change the labeling"
        for name in ("a", "b", "c"):
            assert jtms.beliefs[name].non_monotonic is True
        assert jtms.beliefs["x"].non_monotonic is False

    def test_self_loop_through_out_list_flagged_and_not_true(self):
        """`a ← ¬a` must be flagged (the cycle is its own out-list edge)
        and must not self-support to True."""
        jtms = JTMS()
        jtms.add_justification([], ["a"], "a")
        assert jtms.beliefs["a"].non_monotonic is True
        assert jtms.beliefs["a"].valid is not True

    def test_positive_cycle_not_flagged_and_unknown(self):
        """`a ← b, b ← a` — a positive cycle is monotone: unflagged, and
        without a fact nothing on it is True."""
        jtms = JTMS()
        jtms.add_justification(["b"], [], "a")
        jtms.add_justification(["a"], [], "b")
        assert jtms.beliefs["a"].non_monotonic is False
        assert jtms.beliefs["b"].non_monotonic is False
        assert jtms.beliefs["a"].valid is None
        assert jtms.beliefs["b"].valid is None

    def test_self_supporting_loop_is_unfounded_so_its_negation_decides(self):
        """A belief whose only support runs through itself never counts as
        supported: the loop lands in the unfounded set, so a rule reading
        its negation fires. Three programs, coordinator-measured against
        the WFS definition — the negation stayed None before the
        `_unsupported` fix while `main` labelled it True (#3020 review)."""
        # `a ← b, b ← a, c ← ¬a` — the a↔b loop is its own only support.
        jtms = build_jtms(
            ["a", "b", "c"], [(["b"], [], "a"), (["a"], [], "b"), ([], ["a"], "c")]
        )
        assert jtms.beliefs["c"].valid is True
        assert jtms.beliefs["a"].non_monotonic is False
        assert jtms.beliefs["b"].non_monotonic is False

        # `a ← a, c ← ¬a` — the loop is a self-loop on the in-list side.
        jtms = build_jtms(["a", "c"], [(["a"], [], "a"), ([], ["a"], "c")])
        assert jtms.beliefs["c"].valid is True

        # `x0 ← ¬x1 ; x1 ← x1, ¬x0, ¬x1` — the smallest random
        # counterexample of the coordinator's 20 000-program run.
        jtms = build_jtms(
            ["x0", "x1"], [([], ["x1"], "x0"), (["x1"], ["x0", "x1"], "x1")]
        )
        assert jtms.beliefs["x0"].valid is True


class TestJTMSInsertionOrderIndependence:
    """#3018 — the final labeling (and the flags) of a network do not depend
    on the order its justifications were added in."""

    @given(data=st.data())
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.property
    def test_insertion_order_does_not_change_labels_or_flags(self, data):
        names, justifications, valid_names = data.draw(jtms_network_spec())
        permuted = data.draw(st.permutations(justifications))

        base = build_jtms(names, justifications, valid_names)
        other = build_jtms(names, permuted, valid_names)

        labels = lambda j: {n: b.valid for n, b in j.beliefs.items()}
        flags = lambda j: {n: b.non_monotonic for n, b in j.beliefs.items()}
        assert labels(base) == labels(other), (
            f"labels differ between insertion orders:\n"
            f"{labels(base)} vs {labels(other)}"
        )
        assert flags(base) == flags(other)


class TestJTMSRetractionCascade:
    """Retracting a belief invalidates all beliefs whose only justification
    depended on it."""

    @given(n=st.integers(min_value=3, max_value=6))
    @settings(max_examples=30, deadline=2000)
    @pytest.mark.property
    def test_retraction_invalidates_dependents(self, n):
        jtms = JTMS()
        names = [f"x{i}" for i in range(n)]
        for name in names:
            jtms.add_belief(name)

        for i in range(n - 1):
            jtms.add_justification([names[i]], [], names[i + 1])

        jtms.set_belief_validity(names[0], True)

        for name in names:
            assert (
                jtms.beliefs[name].valid is True
            ), f"Expected {name} valid after setting {names[0]}=True"

        jtms.set_belief_validity(names[0], False)

        for name in names:
            belief = jtms.beliefs[name]
            if belief.justifications:
                assert (
                    belief.valid is not True
                ), f"Belief {name} should be invalid after retracting {names[0]}"


class TestJTMSRetractionCascadeTracing:
    """Retraction tracing records cascaded invalidations."""

    @given(
        chain_len=st.integers(min_value=3, max_value=5),
        n_side=st.integers(min_value=0, max_value=2),
    )
    @settings(max_examples=20, deadline=2000)
    @pytest.mark.property
    def test_tracing_records_cascaded_retractions(self, chain_len, n_side):
        jtms = JTMS()
        jtms.enable_tracing()

        chain = [f"chain{i}" for i in range(chain_len)]
        for name in chain:
            jtms.add_belief(name)
        for i in range(chain_len - 1):
            jtms.add_justification([chain[i]], [], chain[i + 1])

        side_nodes = [f"side{i}" for i in range(n_side)]
        for i, name in enumerate(side_nodes):
            jtms.add_belief(name)
            parent_idx = min(i, chain_len - 1)
            jtms.add_justification([chain[parent_idx]], [], name)

        jtms.set_belief_validity(chain[0], True)
        jtms.set_belief_validity(chain[0], False)

        trace = jtms.get_retraction_chain()
        assert len(trace) >= 1
        assert trace[-1]["trigger"] == chain[0]

        all_cascaded = []
        for entry in trace:
            all_cascaded.extend(entry["cascaded"])
        downstream = chain[1:] + side_nodes
        cascaded_set = set(all_cascaded)
        assert len(cascaded_set & set(downstream)) >= 1


class TestJTMSNoCircularSupport:
    """Cycles through an out-list edge (length >= 2 or a self-loop) are
    detected and marked non-monotonic (#3018: the flag is exact — a
    positive cycle, in-list edges only, is monotone and stays unflagged)."""

    @given(n=st.integers(min_value=2, max_value=4))
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.property
    def test_mutual_dependency_is_non_monotonic(self, n):
        jtms = JTMS()
        names = [f"c{i}" for i in range(n)]
        for name in names:
            jtms.add_belief(name)

        for i in range(n - 1):
            jtms.add_justification([names[i]], [], names[i + 1])
        # The closing edge of the cycle goes through an out-list — that is
        # what makes the cycle non-monotonic (#3018).
        jtms.add_justification([], [names[n - 1]], names[0])

        for name in names:
            assert (
                jtms.beliefs[name].non_monotonic is True
            ), f"Cycle member {name} should be non-monotonic"

    @given(
        n=st.integers(min_value=2, max_value=4),
    )
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.property
    def test_non_cyclic_beliefs_are_not_non_monotonic(self, n):
        """A simple chain A → B → C should NOT be non-monotonic."""
        jtms = JTMS()
        names = [f"n{i}" for i in range(n)]
        for name in names:
            jtms.add_belief(name)

        for i in range(n - 1):
            jtms.add_justification([names[i]], [], names[i + 1])

        for name in names:
            assert (
                jtms.beliefs[name].non_monotonic is False
            ), f"Non-cyclic belief {name} should not be non-monotonic"


def _wfs_true_reference(names, justifications, facts_true):
    """Independent well-founded-semantics oracle, written from the
    definition rather than from the implementation's operators: ``gamma(F)``
    is the least model of the reduct assuming exactly ``F`` false (a rule
    fires when every in-premise is derived and every out-premise is in
    ``F``), and the iteration alternates ``T = gamma(F)`` with ``F = atoms
    - gamma(atoms - T)`` — the skeptical reading, where nothing is false
    that survives even when every not-yet-true atom is assumed false.
    Same fixpoint as the implementation, different road (#3020 review)."""
    program = {}
    for in_list, out_list, conclusion in justifications:
        program.setdefault(conclusion, []).append((in_list, out_list))
    atoms = set(names)

    def gamma(assumed_false):
        derived = set(facts_true)
        changed = True
        while changed:
            changed = False
            for head, rules in program.items():
                if head in derived:
                    continue
                for in_list, out_list in rules:
                    if all(p in derived for p in in_list) and all(
                        p in assumed_false for p in out_list
                    ):
                        derived.add(head)
                        changed = True
                        break
        return derived

    false_set = set()
    while True:
        true_set = gamma(false_set)
        next_false = atoms - gamma(atoms - true_set)
        if next_false == false_set:
            break
        false_set = next_false
    return gamma(false_set)


class TestJTMSMatchesWellFoundedSemantics:
    """The labels must agree with the well-founded semantics itself, not
    only with the network's own invariants: an independent oracle — two
    composed gamma operators, no possibly-supported set — recomputes the
    WFS-true set from the raw spec, and every True label must land inside
    it, and nothing outside it may be True. The `_unfounded` one-step gap
    survived every invariant property and died to this one (#3020 review).
    """

    @seed(3018)
    @given(spec=jtms_network_spec())
    @settings(max_examples=200, deadline=5000)
    def test_true_labels_are_exactly_the_wfs_true_set(self, spec):
        names, justifications, valid_names = spec
        jtms = build_jtms(names, justifications, valid_names)
        wfs_true = _wfs_true_reference(names, justifications, set(valid_names))
        mismatches = [
            (name, jtms.beliefs[name].valid, name in wfs_true)
            for name in names
            if (jtms.beliefs[name].valid is True) != (name in wfs_true)
        ]
        assert not mismatches, f"labels disagree with the WFS reference: {mismatches}"
