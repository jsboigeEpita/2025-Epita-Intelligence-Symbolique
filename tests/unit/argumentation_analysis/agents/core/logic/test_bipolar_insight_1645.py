"""#1645 — pure-graph bipolar insights (no JVM, no reasoner).

The bipolar axis's singular contribution (#1645 section A) is the support
relation, whose two distinctive structural properties are both pure graph
theory over the ``supports`` edges — no JVM, no Tweety reasoner — so the
insights survive the honest-degraded path where the handler never runs
(#1670/#1677):

1. **support cycles** (circular authority): arguments backing each other with no
   external anchor (B-insight-2);
2. **articulation points**: an argument that is the SOLE backer of one or more
   others, so removing it collapses their support (B-insight-3).

These tests pin the algorithms directly (disjoint kill-set A: a broken Tarjan or
supporter-count returns wrong/empty results). The reader-side naming is pinned
in ``test_act3_conclusion_plugin.py`` (``TestBipolarSupportCycleInsight`` and
``TestBipolarArticulationPointInsight`` — disjoint kill-set B: the reader).
Opaque synthetic IDs only.
"""

from argumentation_analysis.agents.core.logic.bipolar_insight import (
    detect_support_articulation_points,
    detect_support_cycles,
)


class TestDetectSupportCycles:
    def test_two_node_cycle_detected(self) -> None:
        """The canonical case (#1645 B-insight-2): mutual support, no anchor."""
        assert detect_support_cycles([["prop_a", "prop_b"], ["prop_b", "prop_a"]]) == [
            ["prop_a", "prop_b"]
        ]

    def test_three_node_cycle_detected(self) -> None:
        assert detect_support_cycles(
            [["prop_a", "prop_b"], ["prop_b", "prop_c"], ["prop_c", "prop_a"]]
        ) == [["prop_a", "prop_b", "prop_c"]]

    def test_acyclic_supports_return_empty(self) -> None:
        """No cycle ⇒ no insight fabricated (honest absence)."""
        assert detect_support_cycles([["prop_a", "prop_b"], ["prop_b", "prop_c"]]) == []

    def test_self_loop_detected(self) -> None:
        """An argument supporting itself is the degenerate cycle."""
        assert detect_support_cycles([["prop_a", "prop_a"]]) == [["prop_a"]]

    def test_isolated_acyclic_pair_is_not_a_cycle(self) -> None:
        assert detect_support_cycles([["prop_a", "prop_b"]]) == []

    def test_cycle_plus_acyclic_component(self) -> None:
        """A cycle coexisting with ordinary supports: only the cycle is named."""
        assert detect_support_cycles(
            [["prop_a", "prop_b"], ["prop_b", "prop_a"], ["prop_c", "prop_d"]]
        ) == [["prop_a", "prop_b"]]

    def test_two_disjoint_cycles_both_returned_sorted(self) -> None:
        assert detect_support_cycles(
            [
                ["prop_b", "prop_a"],
                ["prop_a", "prop_b"],
                ["prop_d", "prop_c"],
                ["prop_c", "prop_d"],
            ]
        ) == [["prop_a", "prop_b"], ["prop_c", "prop_d"]]

    def test_malformed_edges_are_dropped(self) -> None:
        """Wrong arity / blank nodes carry no structural meaning."""
        assert detect_support_cycles(
            [
                ["prop_a", "prop_b"],
                ["prop_b", "prop_a"],
                ["only_one"],
                ["", "x"],
                [1, 2, 3],
            ]
        ) == [["prop_a", "prop_b"]]

    def test_empty_input_returns_empty(self) -> None:
        assert detect_support_cycles([]) == []

    def test_result_is_deterministic(self) -> None:
        """Same input ⇒ same output across calls (no set-ordering leak)."""
        supports = [["prop_b", "prop_a"], ["prop_a", "prop_b"]]
        first = detect_support_cycles(supports)
        for _ in range(20):
            assert detect_support_cycles(supports) == first


class TestDetectSupportArticulationPoints:
    """#1645 PR2 — the sole-supporter articulation point (B-insight-3).

    An argument that is the ONLY direct supporter of one or more others. Pure
    supporter-count over the ``supports`` edges (reverse adjacency). Each entry
    is ``{"node": <sole backer>, "dependents": [<targets it backs alone>]}``,
    sorted by node; dependents sorted within an entry. Opaque IDs only.
    """

    def test_sole_backer_is_articulation_point(self) -> None:
        """The canonical case: one backer, one target ⇒ that backer carries it."""
        assert detect_support_articulation_points([["prop_a", "prop_b"]]) == [
            {"node": "prop_a", "dependents": ["prop_b"]}
        ]

    def test_shared_backer_is_not_an_articulation_point(self) -> None:
        """Two backers of the same target ⇒ removing either leaves the other, so
        neither is an articulation point (anti-over-detection).
        """
        assert (
            detect_support_articulation_points(
                [["prop_a", "prop_b"], ["prop_c", "prop_b"]]
            )
            == []
        )

    def test_multi_dependent_grouped_under_one_entry(self) -> None:
        """One sole backer of two targets ⇒ one entry with both dependents."""
        assert detect_support_articulation_points(
            [["prop_a", "prop_b"], ["prop_a", "prop_c"]]
        ) == [{"node": "prop_a", "dependents": ["prop_b", "prop_c"]}]

    def test_self_support_is_not_an_articulation_point(self) -> None:
        """A self-loop is a cycle (B-insight-2), not an articulation: removing
        it does not drop an independent argument. Must not be reported here.
        """
        assert detect_support_articulation_points([["prop_a", "prop_a"]]) == []

    def test_two_articulation_points_returned_sorted(self) -> None:
        """Two distinct sole backers ⇒ two entries, sorted by node."""
        assert detect_support_articulation_points(
            [["prop_b", "dep_one"], ["prop_a", "dep_two"]]
        ) == [
            {"node": "prop_a", "dependents": ["dep_two"]},
            {"node": "prop_b", "dependents": ["dep_one"]},
        ]

    def test_malformed_edges_are_dropped(self) -> None:
        """Wrong arity / blank nodes carry no structural meaning."""
        assert detect_support_articulation_points(
            [
                ["prop_a", "prop_b"],
                ["only_one"],
                ["", "x"],
                [1, 2, 3],
            ]
        ) == [{"node": "prop_a", "dependents": ["prop_b"]}]

    def test_empty_input_returns_empty(self) -> None:
        assert detect_support_articulation_points([]) == []

    def test_result_is_deterministic(self) -> None:
        """Same input ⇒ same output across calls (no dict-ordering leak)."""
        supports = [["prop_b", "dep"], ["prop_a", "dep2"]]
        first = detect_support_articulation_points(supports)
        for _ in range(20):
            assert detect_support_articulation_points(supports) == first
