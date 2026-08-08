"""#1645 — pure-graph support-cycle detection (the bipolar axis's distinctive insight).

The bipolar axis's singular contribution (#1645 section A) is the support
relation, whose most distinctive structural property is the support cycle
(circular authority): arguments that back each other with no external anchor.
This is pure graph theory over the ``supports`` edges — no JVM, no Tweety
reasoner — so the insight survives the honest-degraded path where the handler
never runs (#1670/#1677).

These tests pin the algorithm directly (disjoint kill-set A: a broken Tarjan
returns wrong/empty groups). The reader-side naming is pinned in
``test_act3_conclusion_plugin.py::TestBipolarSupportCycleInsight`` (disjoint
kill-set B: the reader). Opaque synthetic IDs only.
"""

from argumentation_analysis.agents.core.logic.bipolar_insight import (
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
