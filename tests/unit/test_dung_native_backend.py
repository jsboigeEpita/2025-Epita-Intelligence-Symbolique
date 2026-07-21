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
    # grounded empty, complete = [[], [a,d], [b,c]], stable = [{a,d}, {b,c}]
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


# --- Asymmetric regression fixtures (Track I5 #1502 résidu) ---
# Symmetric frameworks (nixon_diamond, a↔b, triangle) MASK the direction
# inversion bug. The asymmetrics below expose it.

ASYMMETRIC_CHAIN: Dict[str, Any] = {
    "args": ["a", "b", "c"],
    "atts": [("a", "b"), ("b", "c")],
    # grounded = {a, c} (a defends nothing of b's attackers → b dropped,
    # c unattacked → trivially defended). complete = [[], [a, c]].
}

ASYMMETRIC_DIAMOND: Dict[str, Any] = {
    "args": ["a", "b", "c", "d"],
    "atts": [("a", "b"), ("b", "c"), ("a", "d"), ("d", "c")],
    # grounded = {a, c}: a defended (no attacker); b attacked by a (in
    # attack_range of {a}); c defended (b ∈ attack_range of {a}); d
    # attacked by a (in attack_range).
}

ASYMMETRIC_VS: Dict[str, Any] = {
    "args": ["x", "y", "z"],
    "atts": [("x", "y"), ("y", "x")],
    # NOT the same as RECIPROCAL (which is symmetric). Same shape here, so
    # we test it for parity with RECIPROCAL.
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
        # Correct nixon_diamond complete count = 3: [[], {a, d}, {b, c}].
        # {c} and {d} alone are NOT admissible (c attacked by a, d attacked
        # by b — neither {c} nor {d} contains their defender).
        # Reference: Dung 1995, computed via manual enumeration.
        comp = compute_complete_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        assert len(comp) == 3

    def test_nixon_includes_two_stable(self) -> None:
        comp = compute_complete_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        comp_sets = [set(c) for c in comp]
        assert {"a", "d"} in comp_sets
        assert {"b", "c"} in comp_sets

    def test_nixon_includes_empty(self) -> None:
        # Empty is trivially admissible + complete when no self-attacks.
        comp = compute_complete_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        assert [] in comp

    def test_nixon_excludes_singletons(self) -> None:
        # {c} alone: a attacks c, {c} contains no defender of c → not
        # admissible. Same for {d}. Regression for #1502 résidu.
        comp = compute_complete_extensions(NIXON_DIAMOND["args"], NIXON_DIAMOND["atts"])
        for ext in comp:
            assert ext not in (["c"], ["d"])

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


# --- Asymmetric regression tests (Track I5 #1502 résidu) ---
# These frameworks are NOT symmetric. Symmetric frameworks (nixon, RECIPROCAL,
# TRIANGLE) MASK the direction inversion in `_attacked_by` + the backward
# relation in `compute_grounded.attack_range`. The chains/diamonds below
# expose any direction bug immediately.

class TestAsymmetricRegression:
    def test_grounded_asymmetric_chain(self) -> None:
        # a → b → c : a is unattacked, attacks b; b attacks c. Grounded = {a, c}
        # (a survives trivially, b is attacked by a in attack_range, c is
        # unattacked AND attacked by b which is in attack_range of {a}).
        assert compute_grounded(
            ASYMMETRIC_CHAIN["args"], ASYMMETRIC_CHAIN["atts"]
        ) == ["a", "c"]

    def test_complete_asymmetric_chain(self) -> None:
        # complete = [{a, c}]: empty is NOT complete (a has no attacker, so
        # empty defends a — fixpoint condition forces a into the set). Only
        # {a, c} survives (b attacked by a, undefended).
        comp = compute_complete_extensions(
            ASYMMETRIC_CHAIN["args"], ASYMMETRIC_CHAIN["atts"]
        )
        comp_sets = [set(c) for c in comp]
        assert {"a", "c"} in comp_sets
        assert set() not in comp_sets  # a is undefended → empty incomplete
        assert {"b"} not in comp_sets
        assert {"c"} not in comp_sets  # c undefended but isolated; not complete alone
        assert {"a"} not in comp_sets  # c undefended, must be in fixpoint
        assert len(comp_sets) == 1

    def test_stable_asymmetric_chain(self) -> None:
        # Stable subset: same as complete for this AF.
        stab = compute_stable_extensions(
            ASYMMETRIC_CHAIN["args"], ASYMMETRIC_CHAIN["atts"]
        )
        stab_sets = [set(s) for s in stab]
        assert {"a", "c"} in stab_sets

    def test_grounded_asymmetric_diamond(self) -> None:
        # a → b → c, a → d → c : b and d each attacked by a. Grounded = {a, c}.
        assert compute_grounded(
            ASYMMETRIC_DIAMOND["args"], ASYMMETRIC_DIAMOND["atts"]
        ) == ["a", "c"]

    def test_complete_asymmetric_diamond(self) -> None:
        # complete = [{a, c}] only. Empty is not complete (a undefended →
        # must be in fixpoint). b, d each attacked by a, undefended alone.
        comp = compute_complete_extensions(
            ASYMMETRIC_DIAMOND["args"], ASYMMETRIC_DIAMOND["atts"]
        )
        comp_sets = [set(c) for c in comp]
        assert {"a", "c"} in comp_sets
        assert set() not in comp_sets
        assert {"b"} not in comp_sets
        assert {"d"} not in comp_sets
        assert {"c"} not in comp_sets  # c undefended → fixpoint forces a in
        assert len(comp_sets) == 1

    def test_grounded_simple_path(self) -> None:
        # Smallest direction-exposing case: a → b. Grounded = {a}.
        # (b attacked by a, a unattacked.)
        assert compute_grounded(["a", "b"], [("a", "b")]) == ["a"]

    def test_grounded_three_step_path(self) -> None:
        # a → b → c → d. Grounded = {a, c}: a undefended, b attacked by a,
        # c attacked by b which IS in attack_range of {a}, d attacked by c
        # which is in attack_range of {a, c} — so d drops.
        assert compute_grounded(
            ["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")]
        ) == ["a", "c"]


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
