"""Property-based tests for ATMS (Assumption-based Truth Maintenance System) invariants.

Uses hypothesis to randomly generate belief networks and verify universal properties:
1. Contradiction propagation: invalidating an env removes all its supersets from all nodes
2. Environment monotonicity: adding justifications never removes existing environments
3. Nogood enforcement: after a contradiction, no node has an env containing the nogood
4. Hypothesis branching: distinct assumption sets produce distinct environment labels
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from argumentation_analysis.services.jtms.atms_core import ATMS, CONTRADICTION_SYMBOL


# --- Strategies ---

def name_pool(prefix="a", max_names=6):
    return st.lists(
        st.sampled_from([f"{prefix}{i}" for i in range(max_names)]),
        min_size=1,
        max_size=max_names,
        unique=True,
    )


assumption_names = name_pool("a", 6)
derived_names = name_pool("d", 8)


@st.composite
def atms_with_envs(draw):
    """Build an ATMS with assumptions and at least one justification producing environments."""
    atms = ATMS()
    assumptions = draw(assumption_names)
    derived = draw(derived_names)
    assume(len(assumptions) >= 1 and len(derived) >= 1)

    for name in assumptions:
        atms.add_assumption(name)
    for name in derived:
        atms.add_node(name)

    # Add 1-6 justifications
    n_just = draw(st.integers(min_value=1, max_value=6))
    all_names = [n for n in assumptions + derived if n != CONTRADICTION_SYMBOL]
    assume(len(all_names) >= 2)

    for _ in range(n_just):
        in_nodes = draw(st.lists(
            st.sampled_from(all_names), min_size=0, max_size=min(3, len(all_names)),
            unique=True,
        ))
        remaining = [n for n in all_names if n not in in_nodes]
        if remaining:
            out_nodes = draw(st.lists(
                st.sampled_from(remaining),
                min_size=0, max_size=2, unique=True,
            ))
        else:
            out_nodes = []
        candidates = [n for n in all_names if n not in in_nodes and n not in out_nodes]
        if len(candidates) < 1:
            continue
        conclusion = draw(st.sampled_from(candidates))
        try:
            atms.add_justification(in_nodes, out_nodes, conclusion)
        except (KeyError, ValueError):
            pass

    return atms, assumptions, derived


# --- Tests ---


class TestATMSContradictionPropagation:
    """invalidate_environment removes all supersets of the given env from every node."""

    @given(
        n=st.integers(min_value=3, max_value=5),
    )
    @settings(max_examples=30, deadline=2000)
    @pytest.mark.property
    def test_invalidate_removes_supersets_concrete(self, n):
        atms = ATMS()
        assumptions = [f"a{i}" for i in range(n)]
        for name in assumptions:
            atms.add_assumption(name)
        atms.add_node("d0")
        atms.add_justification(assumptions, [], "d0")

        # d0 should have env = union of all assumptions
        envs_before = atms.get_environments("d0")
        assert len(envs_before) > 0

        # Invalidate a subset env
        env_to_kill = frozenset(assumptions[:2])
        atms.invalidate_environment(env_to_kill)

        for name, node in atms.nodes.items():
            for env in node.label:
                assert not env_to_kill.issubset(env), (
                    f"Node {name} still has env {set(env)} superset of killed {set(env_to_kill)}"
                )

    @given(atms_data=atms_with_envs())
    @settings(max_examples=40, deadline=2000)
    @pytest.mark.property
    def test_invalidate_removes_supersets_random(self, atms_data):
        atms, assumptions, derived = atms_data
        if len(assumptions) < 2:
            return

        env_to_kill = frozenset(assumptions[:2])
        atms.invalidate_environment(env_to_kill)

        for name, node in atms.nodes.items():
            for env in node.label:
                assert not env_to_kill.issubset(env), (
                    f"Node {name} still has env {set(env)} superset of killed {set(env_to_kill)}"
                )


class TestATMSEnvironmentMonotonicity:
    """Adding a justification never removes existing environments from any node."""

    @given(
        assumptions=assumption_names,
        derived=derived_names,
    )
    @settings(max_examples=50, deadline=2000)
    @pytest.mark.property
    def test_adding_justification_preserves_environments(
        self, assumptions, derived,
    ):
        assume(len(assumptions) >= 2 and len(derived) >= 1)

        atms = ATMS()
        for name in assumptions:
            atms.add_assumption(name)
        for name in derived:
            atms.add_node(name)

        atms.add_justification([assumptions[0]], [], derived[0])
        labels_before = {
            name: set(node.label) for name, node in atms.nodes.items()
        }

        # Add another justification that won't trigger contradiction
        if len(assumptions) > 1:
            atms.add_justification([assumptions[1]], [], derived[0])

        for name, node in atms.nodes.items():
            for env in labels_before.get(name, set()):
                assert env in node.label, (
                    f"Environment {set(env)} was removed from node {name} "
                    f"after adding a justification"
                )


class TestATMSNogoodEnforcement:
    """After a contradiction is triggered, no node retains an environment that
    is a superset of the contradiction-producing environment."""

    @given(
        a1=st.sampled_from([f"a{i}" for i in range(6)]),
        a2=st.sampled_from([f"a{i}" for i in range(6)]),
    )
    @settings(max_examples=30, deadline=2000)
    @pytest.mark.property
    def test_contradiction_enforces_nogood(self, a1, a2):
        assume(a1 != a2)

        atms = ATMS()
        atms.add_assumption(a1)
        atms.add_assumption(a2)
        atms.add_node("d0")

        # d0 needs both a1 and a2
        atms.add_justification([a1, a2], [], "d0")

        # Now make a1 + a2 a contradiction
        atms.add_justification([a1, a2], [], CONTRADICTION_SYMBOL)

        nogood = frozenset({a1, a2})
        # d0 should NOT have the nogood env (it was invalidated)
        for env in atms.get_environments("d0"):
            assert not nogood.issubset(env), (
                f"d0 still has env {set(env)} containing nogood {set(nogood)}"
            )

        # Assumption nodes retain their singleton envs (not supersets of nogood)
        for name in [a1, a2]:
            for env in atms.get_environments(name):
                assert not nogood.issubset(env), (
                    f"{name} still has env {set(env)} containing nogood {set(nogood)}"
                )


class TestATMSHypothesisBranching:
    """Distinct assumption sets produce distinct environment labels."""

    @given(n=st.integers(min_value=2, max_value=5))
    @settings(max_examples=20, deadline=2000)
    @pytest.mark.property
    def test_distinct_assumptions_give_distinct_singleton_envs(self, n):
        atms = ATMS()
        names = [f"a{i}" for i in range(n)]
        for name in names:
            atms.add_assumption(name)

        for name in names:
            envs = atms.get_environments(name)
            assert envs == {frozenset({name})}

    @given(n=st.integers(min_value=2, max_value=4))
    @settings(max_examples=20, deadline=2000)
    @pytest.mark.property
    def test_derived_env_contains_assumptions(self, n):
        atms = ATMS()
        assumptions = [f"a{i}" for i in range(n)]
        for name in assumptions:
            atms.add_assumption(name)

        atms.add_node("derived")
        atms.add_justification(assumptions, [], "derived")

        envs = atms.get_environments("derived")
        assert len(envs) >= 1
        for env in envs:
            assert any(a in env for a in assumptions)
