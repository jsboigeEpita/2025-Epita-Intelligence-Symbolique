"""#3050 — exponential AF semantics are computed by a sized method or refused
by name; no unbounded reasoner call is ever submitted.

Born red (base ``f385fa662``, real JVM, offline witness, 2026-10-17): on the
R1090-shaped 40-nodes/1-attack frame, ``preferred``/``grounded``/``stable``/
``complete`` returned instantly but ``admissible`` materialized its 2**39-set
search space until the 2 GB JVM heap died (223 s), taking the process down
before ``conflict_free`` even ran — the executor thread kept enumerating past
its phase deadline (the #2080 shape). The R1077-shaped 7/1 frame returns on
all ten semantics; its verdicts are the anti-regression baseline below.

The sized path decomposes the frame into weakly-connected components. The
per-component counts the decomposition multiplies are themselves grounded in
the base measurement (7/1: conflict_free 96 = 3·2⁵, admissible 64 = 2·2⁵,
naive 2 = 2·1⁵ — pair {a1→a2} contributes 3/2/2, an isolated node 2/2/1), so
the 40/1 expectations are exact arithmetic on measured components, not
predictions.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.agents.core.logic.af_handler import (
    _DUNG_COMPONENT_MAX_NODES,
    _DUNG_ENUMERATION_CEILING,
    AFHandler,
    SEMANTICS_REASONERS,
    weak_components,
)
from argumentation_analysis.agents.core.logic.tweety_initializer import (
    ready_initializer,
)

# --- pure-Python part: the decomposition itself (no JVM) -------------------


class TestWeakComponents:
    def test_isolated_nodes_are_singleton_components(self):
        comps = weak_components(["a", "b", "c"], [])
        assert sorted(comps) == sorted([(["a"], []), (["b"], []), (["c"], [])])

    def test_pair_is_one_component_with_its_edge(self):
        comps = weak_components(["a", "b", "c"], [["a", "b"]])
        assert len(comps) == 2
        pair = next(c for c in comps if len(c[0]) == 2)
        assert pair[0] == ["a", "b"]
        assert pair[1] == [["a", "b"]]

    def test_weak_connectivity_direction_does_not_matter(self):
        # a -> b -> c: one weakly-connected component even though the digraph
        # is a path, not a cycle.
        comps = weak_components(["a", "b", "c"], [["a", "b"], ["b", "c"]])
        assert len(comps) == 1
        assert comps[0][0] == ["a", "b", "c"]

    def test_self_attack_stays_in_its_own_component(self):
        comps = weak_components(["a", "b"], [["a", "a"]])
        assert len(comps) == 2
        solo = next(c for c in comps if c[0] == ["a"])
        assert solo[1] == [["a", "a"]]

    def test_unknown_endpoint_attack_is_skipped_like_build_framework(self):
        # _build_framework skips attacks naming unknown nodes; the components
        # must match the theory that actually gets built.
        comps = weak_components(["a", "b"], [["a", "ghost"], ["a", "b"]])
        assert len(comps) == 1
        assert comps[0][1] == [["a", "b"]]

    def test_first_appearance_order_is_deterministic(self):
        arguments = ["z", "a", "m"]
        comps = weak_components(arguments, [["m", "z"]])
        assert [c[0] for c in comps] == [["z", "m"], ["a"]]


# --- real-JVM part: the sized verdicts --------------------------------------

_JVM = pytest.mark.jpype
_TWEETY = pytest.mark.tweety

_ARGS_7 = [f"a{i}" for i in range(1, 8)]
_ARGS_40 = [f"a{i}" for i in range(1, 41)]

# Base-measured (2026-10-17, Simple* over the WHOLE theory — the fix must
# reproduce these verdicts through the decomposed path).
_BASELINE_7_1 = {
    "preferred": 1,
    "grounded": 1,
    "stable": 1,
    "complete": 1,
    "admissible": 64,
    "conflict_free": 96,
    "semi_stable": 1,
    "stage": 1,
    "ideal": 1,
    "naive": 2,
}


def _handler() -> AFHandler:
    return AFHandler(ready_initializer())


@_JVM
@_TWEETY
class TestSparse40NodesCompletesWithinBudget:
    """The R1090 frame: every semantics computed or refused by name, fast."""

    @pytest.mark.timeout(60)
    def test_full_profile_40_nodes_1_attack(self):
        handler = _handler()
        result = handler.analyze_multi_semantics(
            _ARGS_40, [["a1", "a2"]], list(SEMANTICS_REASONERS)
        )
        extensions = result["extensions"]
        stats = result["statistics"]

        # Enumerated semantics: one extension of the 39 defensible arguments
        # (everything but the defeated a2), plus naive's a1/a2 swap.
        for sem in (
            "preferred",
            "grounded",
            "stable",
            "complete",
            "semi_stable",
            "stage",
            "ideal",
        ):
            assert extensions[sem] == [
                sorted(set(_ARGS_40) - {"a2"})
            ], f"{sem}: {extensions[sem]}"
            assert stats[f"{sem}_count"] == 1
        assert extensions["naive"] == [
            sorted(set(_ARGS_40) - {"a2"}),
            sorted(set(_ARGS_40) - {"a1"}),
        ]
        assert stats["naive_count"] == 2

        # Refused by name, count exact: 3·2**38 conflict-free sets, 2·2**38
        # admissible sets — both far over the ceiling, neither materialized.
        for sem, exact in (
            ("conflict_free", 3 * 2**38),
            ("admissible", 2 * 2**38),
        ):
            refusal = extensions[sem]
            assert isinstance(refusal, dict) and refusal.get("refused") is True
            assert refusal["extensions_count"] == exact
            assert sem in refusal["error"] and "#3050" in refusal["error"]
            assert stats[f"{sem}_count"] == exact

        # No semantics died silently: ten verdicts, none an unnamed error.
        assert len(extensions) == 10
        assert all(
            isinstance(v, list) or (isinstance(v, dict) and "refused" in v)
            for v in extensions.values()
        )

    @pytest.mark.timeout(30)
    def test_oversized_component_refused_before_any_jvm_call(self):
        # A 17-node path (over _DUNG_COMPONENT_MAX_NODES) connected as a chain
        # plus 3 isolated nodes: the chain component is refused by name with
        # its size, before any getModels call — nothing can leak past a
        # deadline because no unbounded call is submitted.
        chain = [f"c{i}" for i in range(1, 18)]
        attacks = [[chain[i], chain[i + 1]] for i in range(16)]
        handler = _handler()
        result = handler.analyze_multi_semantics(
            chain + ["x1", "x2", "x3"], attacks, ["conflict_free"]
        )
        refusal = result["extensions"]["conflict_free"]
        assert isinstance(refusal, dict) and refusal.get("refused") is True
        assert refusal["largest_component_nodes"] == _DUNG_COMPONENT_MAX_NODES + 1
        assert "17 nodes" in refusal["error"]
        # Grounded stays polynomial and direct even on the chain.
        grounded = handler.analyze_multi_semantics(
            chain + ["x1", "x2", "x3"], attacks, ["grounded"]
        )
        assert isinstance(grounded["extensions"]["grounded"], list)


@_JVM
@_TWEETY
class TestR1077ShapeAntiRegression:
    """The 7-nodes/1-attack frame keeps its base verdicts (R1077 shape)."""

    def test_all_ten_semantics_baseline(self):
        handler = _handler()
        result = handler.analyze_multi_semantics(
            _ARGS_7, [["a1", "a2"]], list(SEMANTICS_REASONERS)
        )
        for sem, expected in _BASELINE_7_1.items():
            got = result["extensions"][sem]
            assert isinstance(got, list), f"{sem}: {got}"
            assert len(got) == expected, f"{sem}: {len(got)} != {expected}"


@_JVM
@_TWEETY
class TestDensePairsFamily:
    """The #2930 regime: disjoint mutual pairs multiply under the ceiling."""

    def test_two_pairs_enumerate(self):
        args = ["a1", "a2", "a3", "a4"]
        attacks = [["a1", "a2"], ["a2", "a1"], ["a3", "a4"], ["a4", "a3"]]
        result = _handler().analyze_multi_semantics(args, attacks, ["preferred"])
        exts = result["extensions"]["preferred"]
        assert isinstance(exts, list)
        # Each pair contributes its 2 preferred extensions; the product is 4.
        assert len(exts) == 4

    def test_twelve_pairs_refused_with_exact_count(self):
        args = [f"a{i}" for i in range(1, 25)]
        attacks = [
            e
            for p in range(12)
            for e in ([f"a{2*p+1}", f"a{2*p+2}"], [f"a{2*p+2}", f"a{2*p+1}"])
        ]
        result = _handler().analyze_multi_semantics(args, attacks, ["preferred"])
        refusal = result["extensions"]["preferred"]
        assert isinstance(refusal, dict) and refusal.get("refused") is True
        assert refusal["extensions_count"] == 2**12
        assert refusal["extensions_count"] > _DUNG_ENUMERATION_CEILING
        assert refusal["per_component_counts"] == [2] * 12


# --- weighted side (#3050): same gate, measured base behaviour --------------

from argumentation_analysis.agents.core.logic.weighted_handler import (  # noqa: E402
    WeightedHandler,
)

# Base-measured whole-theory behaviour (2026-10-17): grounded renders one
# EMPTY extension; preferred/stable/complete/admissible render none;
# conflict_free raises TypeError (a PRE-EXISTING overload defect in the
# weighted module, untouched by #3050 and asserted unchanged here). On the
# 40/1 frame the base grounded call exhausted the heap after 112 s.
_WEIGHTED_BASE_7_1 = {
    "grounded": (1, [0]),
    "preferred": (0, []),
    "stable": (0, []),
    "complete": (0, []),
    "admissible": (0, []),
}


def _weighted() -> WeightedHandler:
    return WeightedHandler(ready_initializer())


@_JVM
@_TWEETY
class TestWeightedSized:
    def test_7_1_verdicts_match_base(self):
        handler = _weighted()
        args = [f"a{i}" for i in range(1, 8)]
        attacks = [("a1", "a2", 0.8)]
        for sem, (count, sizes) in _WEIGHTED_BASE_7_1.items():
            out = handler.analyze_weighted_framework(args, attacks, sem)
            assert out["extensions_count"] == count, f"{sem}: {out}"
            assert sorted({len(e) for e in out["extensions"]}) == sizes, sem

    def test_conflict_free_overload_defect_unchanged(self):
        # The pre-existing TypeError (no matching getModels overload for the
        # weighted conflict_free reasoner) must stay VISIBLE — hiding it
        # behind a refusal would dress an environment defect as a verdict.
        handler = _weighted()
        with pytest.raises(TypeError):
            handler.analyze_weighted_framework(
                [f"a{i}" for i in range(1, 8)], [("a1", "a2", 0.8)],
                "conflict_free",
            )

    @pytest.mark.timeout(30)
    def test_40_nodes_completes_instead_of_oom(self):
        # Base: grounded exhausted the JVM heap after 112 s on this frame.
        # Branch: every loadable semantics returns in milliseconds with the
        # same verdict shape as 7/1.
        handler = _weighted()
        args = [f"a{i}" for i in range(1, 41)]
        attacks = [("a1", "a2", 0.8)]
        for sem, (count, sizes) in _WEIGHTED_BASE_7_1.items():
            out = handler.analyze_weighted_framework(args, attacks, sem)
            assert out["extensions_count"] == count, f"{sem}: {out}"
            assert sorted({len(e) for e in out["extensions"]}) == sizes, sem
            assert not out.get("refused"), sem
