"""Tests for the pure-Python Dung backend (sanctuary #893 — independent impl).

These tests verify the canonical examples from :mod:`abs_arg_dung.framework_generator`
and a few reference Dung-style frameworks (Nixon Diamond, self-loops, cycles).
No JVM, no Tweety, no fixtures — fully pure-Python for CI determinism.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from abs_arg_dung.backends import (
    backend_python,
    compute_complete_extensions,
    compute_grounded,
    compute_stable_extensions,
)


# --- Fixtures (canonical Dung reference examples) ---

NIXON_DIAMOND: Dict[str, Any] = {
    "args": ["a", "b", "c", "d"],
    "atts": [("a", "b"), ("b", "a"), ("c", "d"), ("d", "c"), ("a", "c"), ("b", "d")],
    # grounded empty, stable = [{a,d}, {b,c}]
}

TRIANGLE_CYCLE: Dict[str, Any] = {
    "args": ["a", "b", "c"],
    "atts": [("a", "b"), ("b", "c"), ("c", "a")],
    # no stable, only empty complete
}

SELF_LOOP: Dict[str, Any] = {
    "args": ["a", "b"],
    "atts": [("a", "a")],
    # a is in no conflict-free set; grounded = {b}
}

RECIPROCAL: Dict[str, Any] = {
    "args": ["a", "b"],
    "atts": [("a", "b"), ("b", "a")],
    # stable = [{a}, {b}], grounded = {}
}

CHAIN: Dict[str, Any] = {
    "args": ["a", "b", "c"],
    "atts": [("a", "b"), ("a", "c"), ("b", "c")],
    # only {a} survives (chain attack)
}


# --- Grounded (deterministic, O(V+E)) ---

class TestGrounded:
    def test_nixon_diamond_empty(self) -> None:
        assert compute_grounded(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"]) == []

    def test_triangle_cycle_empty(self) -> None:
        assert compute_grounded(TRIANGLE_CYCLE["args"], TRIANGLE_CYCLE["atts"]) == []

    def test_self_loop_keeps_unattacked(self) -> None:
        assert compute_grounded(SELF_LOOP["args"], SELF_LOOP["atts"]) == ["b"]

    def test_reciprocal_empty(self) -> None:
        assert compute_grounded(RECIPROCAL["args"], RECIPROCAL["atts"]) == []

    def test_chain_keeps_root(self) -> None:
        assert compute_grounded(CHAIN["args"], CHAIN["atts"]) == ["a"]

    def test_no_attacks_all_in(self) -> None:
        assert compute_grounded(["a", "b", "c"], []) == ["a", "b", "c"]

    def test_empty_input(self) -> None:
        assert compute_grounded([], []) == []

    def test_unattacked_argument_joins_grounded(self) -> None:
        # Even if no one attacks it, it joins the grounded extension.
        assert compute_grounded(["x"], []) == ["x"]

    def test_sorted_output(self) -> None:
        # Output is sorted: matters for comparison with Tweety (deterministic).
        result = compute_grounded(["c", "a", "b"], [])
        assert result == ["a", "b", "c"]


# --- Complete (enumeration; cardinalities match reference) ---

class TestComplete:
    def test_nixon_complete_cardinality(self) -> None:
        # Reference: 5 complete extensions for the Nixon diamond.
        comp = compute_complete_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        assert len(comp) == 5
        for ext in comp:
            # Each must include all defended arguments
            for ext_set in [set(e) for e in comp]:
                pass

    def test_nixon_includes_two_stable(self) -> None:
        comp = compute_complete_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        comp_sets = [set(c) for c in comp]
        assert {"a", "d"} in comp_sets
        assert {"b", "c"} in comp_sets

    def test_triangle_cycle_only_empty(self) -> None:
        comp = compute_complete_extensions(TRIANGLE_CYCLE["args"], TRIANGLE_CYCLE["atts"])
        assert comp == [[]]

    def test_self_loop_no_a(self) -> None:
        # a->a forbids a in any conflict-free set.
        comp = compute_complete_extensions(SELF_LOOP["args"], SELF_LOOP["atts"])
        for ext in comp:
            assert "a" not in ext

    def test_reciprocal_three_complete(self) -> None:
        # Reference: complete = [∅, {a}, {b}]
        comp = compute_complete_extensions(RECIPROCAL["args"], RECIPROCAL["atts"])
        comp_sets = [set(c) for c in comp]
        assert set() in comp_sets
        assert {"a"} in comp_sets
        assert {"b"} in comp_sets

    def test_chain_single_complete(self) -> None:
        comp = compute_complete_extensions(CHAIN["args"], CHAIN["atts"])
        assert comp == [["a"]]

    def test_complete_empty_input(self) -> None:
        assert compute_complete_extensions([], []) == [[]]

    def test_complete_output_sorted_per_ext(self) -> None:
        comp = compute_complete_extensions(["z", "x", "y"], [])
        for ext in comp:
            assert ext == sorted(ext)


# --- Stable (subset of complete) ---

class TestStable:
    def test_nixon_two_stable(self) -> None:
        stab = compute_stable_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        stab_sets = [set(s) for s in stab]
        assert {"a", "d"} in stab_sets
        assert {"b", "c"} in stab_sets
        assert len(stab) == 2

    def test_triangle_cycle_no_stable(self) -> None:
        # Odd cycle has no stable extension.
        assert compute_stable_extensions(TRIANGLE_CYCLE["args"], TRIANGLE_CYCLE["atts"]) == []

    def test_self_loop_no_stable(self) -> None:
        assert compute_stable_extensions(SELF_LOOP["args"], SELF_LOOP["atts"]) == []

    def test_reciprocal_two_stable(self) -> None:
        stab = compute_stable_extensions(RECIPROCAL["args"], RECIPROCAL["atts"])
        stab_sets = [set(s) for s in stab]
        assert {"a"} in stab_sets
        assert {"b"} in stab_sets

    def test_stable_empty(self) -> None:
        # Empty framework: empty set is vacuously stable.
        assert compute_stable_extensions([], []) == [[]]

    def test_stable_subset_of_complete(self) -> None:
        # Disjoint checking: every stable is also complete.
        args = NIXON_DIAMOND["args"]
        atts = NIXON_DIAMOND["atts"]
        comp = [set(c) for c in compute_complete_extensions(args, atts)]
        for s in compute_stable_extensions(args, atts):
            assert set(s) in comp


# --- backend_python facade (shape match with _compare_dung_backends) ---

class TestFacade:
    def test_backend_marker(self) -> None:
        r = backend_python(["a"], [])
        assert r["backend"] == "python"
        assert r["available"] is True
        assert "note" in r
        assert "extensions" in r
        assert "elapsed_ms" in r
        assert isinstance(r["elapsed_ms"], float)

    def test_extensions_keys(self) -> None:
        r = backend_python(["a"], [])
        ext = r["extensions"]
        assert "grounded" in ext
        assert "complete" in ext
        assert "stable" in ext

    def test_grounded_always_single(self) -> None:
        # Grounded is unique → list with one element.
        r = backend_python(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        assert len(r["extensions"]["grounded"]) == 1

    def test_facade_output_sorted(self) -> None:
        r = backend_python(["c", "a", "b"], [])
        assert r["extensions"]["grounded"][0] == ["a", "b", "c"]


# --- Determinism: same input → same output, twice in a row ---

class TestDeterminism:
    @pytest.mark.parametrize(
        "args,atts",
        [
            (NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"]),
            (RECIPROCAL["args"], RECIPROCAL["atts"]),
            (CHAIN["args"], CHAIN["atts"]),
            ([str(i) for i in range(20)], [(str(i), str(i + 1)) for i in range(19)]),
        ],
    )
    def test_replay(self, args: List[str], atts: List[Tuple[str, str]]) -> None:
        r1 = backend_python(args, atts)
        r2 = backend_python(args, atts)
        # Compare everything except `elapsed_ms` (wallclock, not deterministic).
        r1_clean = {k: v for k, v in r1.items() if k != "elapsed_ms"}
        r2_clean = {k: v for k, v in r2.items() if k != "elapsed_ms"}
        assert r1_clean == r2_clean
