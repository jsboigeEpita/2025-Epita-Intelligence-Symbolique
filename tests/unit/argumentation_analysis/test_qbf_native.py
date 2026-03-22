"""Tests for pure-Python QBF solver and argumentation-to-QBF conversion.

Tests the JVM-free fallback implementation in qbf_native.py.
"""

import pytest

from argumentation_analysis.agents.core.logic.qbf_native import (
    Var,
    Not,
    And,
    Or,
    Implies,
    ForAll,
    Exists,
    parse_formula,
    check_qbf,
    analyze_qbf,
    credulous_acceptance_qbf,
    skeptical_acceptance_qbf,
    example_simple_validity,
    example_simple_satisfiability,
    example_mixed_quantifiers,
    example_argumentation_acceptance,
)


class TestFormulaEvaluation:
    """Test basic formula AST evaluation."""

    def test_variable(self):
        x = Var("x")
        assert x.evaluate({"x": True}) is True
        assert x.evaluate({"x": False}) is False
        assert x.evaluate({}) is False  # default False

    def test_negation(self):
        not_x = Not(Var("x"))
        assert not_x.evaluate({"x": True}) is False
        assert not_x.evaluate({"x": False}) is True

    def test_conjunction(self):
        f = And(Var("x"), Var("y"))
        assert f.evaluate({"x": True, "y": True}) is True
        assert f.evaluate({"x": True, "y": False}) is False

    def test_disjunction(self):
        f = Or(Var("x"), Var("y"))
        assert f.evaluate({"x": False, "y": False}) is False
        assert f.evaluate({"x": True, "y": False}) is True

    def test_implication(self):
        f = Implies(Var("x"), Var("y"))
        assert f.evaluate({"x": True, "y": True}) is True
        assert f.evaluate({"x": True, "y": False}) is False
        assert f.evaluate({"x": False, "y": False}) is True  # vacuously true


class TestQuantifiers:
    """Test universal and existential quantification."""

    def test_forall_tautology(self):
        """∀x. (x | !x) is valid."""
        f = ForAll(["x"], Or(Var("x"), Not(Var("x"))))
        assert f.evaluate({}) is True

    def test_forall_non_tautology(self):
        """∀x. x is not valid."""
        f = ForAll(["x"], Var("x"))
        assert f.evaluate({}) is False

    def test_exists_satisfiable(self):
        """∃x. x is satisfiable."""
        f = Exists(["x"], Var("x"))
        assert f.evaluate({}) is True

    def test_exists_contradiction(self):
        """∃x. (x & !x) is not satisfiable."""
        f = Exists(["x"], And(Var("x"), Not(Var("x"))))
        assert f.evaluate({}) is False

    def test_mixed_quantifiers(self):
        """∀x. ∃y. (x => y) is valid (choose y=True)."""
        f = ForAll(["x"], Exists(["y"], Implies(Var("x"), Var("y"))))
        assert f.evaluate({}) is True

    def test_mixed_quantifiers_invalid(self):
        """∃y. ∀x. (x => y) is not valid (y=True works but y=False doesn't)."""
        # Actually ∃y.∀x.(x=>y) means: exists y such that for all x, x implies y
        # If y=True: ∀x.(x=>True) = True. So this IS valid.
        f = Exists(["y"], ForAll(["x"], Implies(Var("x"), Var("y"))))
        assert f.evaluate({}) is True

    def test_strict_invalid_mixed(self):
        """∀y. ∃x. (x & !y) — for y=True, need ∃x.(x & False) = False."""
        f = ForAll(["y"], Exists(["x"], And(Var("x"), Not(Var("y")))))
        assert f.evaluate({}) is False


class TestParser:
    """Test formula parsing."""

    def test_parse_variable(self):
        f = parse_formula("x")
        assert isinstance(f, Var)
        assert f.evaluate({"x": True}) is True

    def test_parse_negation(self):
        f = parse_formula("!x")
        assert isinstance(f, Not)
        assert f.evaluate({"x": True}) is False

    def test_parse_conjunction(self):
        f = parse_formula("x & y")
        assert f.evaluate({"x": True, "y": True}) is True
        assert f.evaluate({"x": True, "y": False}) is False

    def test_parse_implication(self):
        f = parse_formula("x => y")
        assert f.evaluate({"x": True, "y": False}) is False
        assert f.evaluate({"x": False, "y": False}) is True


class TestQBFSolver:
    """Test the check_qbf and analyze_qbf functions."""

    def test_tautology_valid(self):
        """∀x. (x | !x) should be valid."""
        result, msg = check_qbf(
            [{"type": "forall", "vars": ["x"]}],
            "x | !x",
        )
        assert result is True
        assert "VALID" in msg

    def test_contradiction_invalid(self):
        """∃x. (x & !x) should be invalid."""
        result, msg = check_qbf(
            [{"type": "exists", "vars": ["x"]}],
            "x & !x",
        )
        assert result is False
        assert "INVALID" in msg

    def test_analyze_returns_statistics(self):
        analysis = analyze_qbf(
            [{"type": "forall", "vars": ["x", "y"]}],
            "x | y | !x",
        )
        assert "statistics" in analysis
        assert analysis["statistics"]["variable_count"] == 2
        assert analysis["statistics"]["search_space"] == 4
        assert analysis["statistics"]["handler"] == "qbf_native"


class TestArgumentationToQBF:
    """Test argumentation framework to QBF conversion."""

    def test_credulous_simple(self):
        """a attacks b, b attacks a — both credulously accepted."""
        result = credulous_acceptance_qbf(
            arguments=["a", "b"],
            attacks=[["a", "b"], ["b", "a"]],
            target="a",
        )
        assert result["accepted"] is True
        assert "a" in result["witness_extension"]

    def test_credulous_attacked(self):
        """a attacks b, no defense — b not credulously accepted (self-defended)."""
        # Actually b IS attacked by a, and b doesn't counter-attack
        # But {b} is conflict-free. Is it admissible?
        # a attacks b, b is in {b}, a attacks b and a ∉ {b}
        # b must defend against a: needs someone in {b} to attack a
        # b doesn't attack a → {b} not admissible
        result = credulous_acceptance_qbf(
            arguments=["a", "b"],
            attacks=[["a", "b"]],
            target="b",
        )
        assert result["accepted"] is False

    def test_credulous_unattacked(self):
        """Unattacked argument is always credulously accepted."""
        result = credulous_acceptance_qbf(
            arguments=["a", "b"],
            attacks=[["a", "b"]],
            target="a",
        )
        assert result["accepted"] is True

    def test_credulous_nonexistent(self):
        """Non-existent argument returns False."""
        result = credulous_acceptance_qbf(
            arguments=["a"],
            attacks=[],
            target="z",
        )
        assert result["accepted"] is False

    def test_skeptical_unattacked(self):
        """Unattacked argument should be skeptically accepted."""
        result = skeptical_acceptance_qbf(
            arguments=["a", "b"],
            attacks=[["a", "b"]],
            target="a",
        )
        assert result["accepted"] is True

    def test_skeptical_mutual_attack(self):
        """In mutual attack, neither is skeptically accepted."""
        result = skeptical_acceptance_qbf(
            arguments=["a", "b"],
            attacks=[["a", "b"], ["b", "a"]],
            target="a",
        )
        # a is in {a} preferred ext but not in {b} preferred ext
        assert result["accepted"] is False

    def test_nixon_diamond(self):
        """Classic Nixon diamond: mutual attack between a and b."""
        result = credulous_acceptance_qbf(
            arguments=["a", "b", "c"],
            attacks=[["a", "b"], ["b", "a"]],
            target="c",
        )
        assert result["accepted"] is True  # c is unattacked


class TestExamples:
    """Test the example functions."""

    def test_example_validity(self):
        result = example_simple_validity()
        assert result["valid"] is True

    def test_example_satisfiability(self):
        result = example_simple_satisfiability()
        assert result["valid"] is False

    def test_example_mixed(self):
        result = example_mixed_quantifiers()
        assert result["valid"] is True

    def test_example_argumentation(self):
        result = example_argumentation_acceptance()
        assert result["accepted"] is True
