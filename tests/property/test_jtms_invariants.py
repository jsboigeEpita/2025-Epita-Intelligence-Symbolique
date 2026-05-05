"""Property-based tests for JTMS (Justification-based Truth Maintenance System) invariants.

Uses hypothesis to randomly generate belief networks and verify universal properties:
1. Justification chain consistency: valid beliefs have at least one fully-satisfied justification
2. Retraction cascade: retracting a belief invalidates all dependent beliefs
3. Cycle detection: mutual dependencies (A→B→A) are marked non-monotonic
"""

import pytest
from hypothesis import given, settings, assume
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
def jtms_with_justifications(draw):
    """Build a JTMS: add beliefs, then justifications, THEN set validity.
    This ensures truth values are determined by the justification network."""
    jtms = JTMS()
    names = draw(belief_names)

    for name in names:
        jtms.add_belief(name)

    # Add 1-6 justifications FIRST
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
        if remaining:
            out_list = draw(
                st.lists(
                    st.sampled_from(remaining),
                    min_size=0,
                    max_size=2,
                    unique=True,
                )
            )
        else:
            out_list = []
        conclusion_candidates = [
            n for n in candidates if n not in in_list and n not in out_list
        ]
        if not conclusion_candidates:
            continue
        conclusion = draw(st.sampled_from(conclusion_candidates))
        jtms.add_justification(in_list, out_list, conclusion)

    # THEN set some beliefs as valid (propagation follows justifications)
    valid_count = draw(st.integers(min_value=0, max_value=len(names)))
    valid_names = names[:valid_count]
    for name in valid_names:
        jtms.set_belief_validity(name, True)

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
            if belief.valid is not True or belief.non_monotonic:
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
    """Mutual dependencies (cycles of length >= 2) are detected and marked non-monotonic.
    Self-loops (A → A) are NOT detected — this is a known limitation."""

    @given(n=st.integers(min_value=2, max_value=4))
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.property
    def test_mutual_dependency_is_non_monotonic(self, n):
        jtms = JTMS()
        names = [f"c{i}" for i in range(n)]
        for name in names:
            jtms.add_belief(name)

        for i in range(n):
            next_i = (i + 1) % n
            jtms.add_justification([names[i]], [], names[next_i])

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
