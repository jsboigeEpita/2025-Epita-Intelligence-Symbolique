"""Tests for the synthetic-framework generators and ICCMA ``.af`` parser.

These exercise the surface area used by ``scripts/compare_dung_backends.py``
and the synthetic side of the multi-backend comparison. They are JVM-free
and deterministic.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from abs_arg_dung.backends import (
    generate_classic_examples,
    generate_er,
    generate_sbm,
    parse_iccma_af,
    parse_iccma_af_file,
)


# --- Parser ---

class TestParser:
    def test_basic(self) -> None:
        text = "p af 3\nn a\nn b\nn c\na a b\na b c\n"
        args, atts = parse_iccma_af(text)
        assert args == ["a", "b", "c"]
        assert atts == [("a", "b"), ("b", "c")]

    def test_comments_ignored(self) -> None:
        text = "# header\np af 1\n% another comment\nn x\n"
        args, atts = parse_iccma_af(text)
        assert args == ["x"]
        assert atts == []

    def test_attack_before_n_declared(self) -> None:
        # ICCMA allows `a` lines before `n` — order-free.
        text = "p af 3\na a b\na b c\nn a\nn b\nn c\n"
        args, atts = parse_iccma_af(text)
        assert args == ["a", "b", "c"]
        assert atts == [("a", "b"), ("b", "c")]

    def test_header_required(self) -> None:
        with pytest.raises(ValueError, match="missing mandatory"):
            parse_iccma_af("n a\n")

    def test_duplicate_header(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            parse_iccma_af("p af 1\np af 2\nn a\n")

    def test_undeclared_target(self) -> None:
        with pytest.raises(ValueError, match="not declared"):
            parse_iccma_af("p af 2\nn a\na a b\n")

    def test_count_mismatch(self) -> None:
        with pytest.raises(ValueError, match="declares"):
            parse_iccma_af("p af 5\nn a\nn b\n")

    def test_garbage_line(self) -> None:
        with pytest.raises(ValueError, match="unrecognized"):
            parse_iccma_af("p af 1\nfoo bar\n")

    def test_parse_file(self, tmp_path: Any) -> None:
        path = tmp_path / "ex.af"
        path.write_text("p af 2\nn a\nn b\na a b\n", encoding="utf-8")
        args, atts = parse_iccma_af_file(str(path))
        assert args == ["a", "b"]
        assert atts == [("a", "b")]


# --- Generators ---

class TestSBM:
    def test_block_sizes_sum(self) -> None:
        args, _ = generate_sbm([4, 5, 6], p_in=0.3, p_out=0.05, seed=1)
        assert len(args) == 15

    def test_deterministic(self) -> None:
        a1, _ = generate_sbm([3, 3], p_in=0.3, p_out=0.1, seed=42)
        a2, _ = generate_sbm([3, 3], p_in=0.3, p_out=0.1, seed=42)
        assert a1 == a2

    def test_different_seeds_differ(self) -> None:
        # Compare attack sets (more sensitive than argument order) under
        # high-density SBM where seed-driven divergence is reliable.
        _, a1 = generate_sbm([15, 15], p_in=0.5, p_out=0.3, seed=1)
        _, a2 = generate_sbm([15, 15], p_in=0.5, p_out=0.3, seed=2)
        assert a1 != a2

    def test_arguments_are_strings(self) -> None:
        # Type consistency: arguments and attack endpoints are all strings.
        args, atts = generate_sbm([3, 3], p_in=0.3, p_out=0.1, seed=42)
        assert all(isinstance(a, str) for a in args)
        assert all(isinstance(s, str) and isinstance(t, str) for s, t in atts)

    def test_no_self_loops(self) -> None:
        # SBM with `directed=True` may still produce self-loops; we filter or
        # document. Verify the generator behavior.
        _, atts = generate_sbm([10, 10], p_in=0.3, p_out=0.05, seed=42)
        # networkx `directed=True, selfloops=False` (default in 3.x) — no self.
        assert all(s != t for s, t in atts)


class TestER:
    def test_arg_count(self) -> None:
        args, _ = generate_er(20, p=0.2, seed=42)
        assert len(args) == 20

    def test_deterministic(self) -> None:
        a1, _ = generate_er(15, p=0.3, seed=1)
        a2, _ = generate_er(15, p=0.3, seed=1)
        assert a1 == a2


class TestClassics:
    def test_keys(self) -> None:
        keys = set(generate_classic_examples().keys())
        assert "nixon_diamond" in keys
        assert "odd_cycle_3" in keys
        assert "mutual_attack" in keys
        assert "chain" in keys
        assert "isolated" in keys

    def test_nixon_diamond_args(self) -> None:
        ex = generate_classic_examples()["nixon_diamond"]
        args, _ = ex
        assert args == ["a", "b", "c", "d"]

    def test_isolated_no_attacks(self) -> None:
        _, atts = generate_classic_examples()["isolated"]
        assert atts == []
