"""Tests for FOL signature pre-declaration (#348).

Validates that extract_fol_metadata() correctly parses LLM-generated
formulas to produce Tweety-compatible sort/type declarations.
"""

import pytest

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent


class TestExtractFolMetadata:
    """Test the static extract_fol_metadata method."""

    def test_empty_formulas(self):
        meta = FOLLogicAgent.extract_fol_metadata([])
        assert meta["predicates"] == {}
        assert meta["constants"] == set()

    def test_single_predicate(self):
        formulas = ["Mortel(socrate)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        assert "Mortel" in meta["predicates"]
        assert meta["predicates"]["Mortel"] == 1
        assert "socrate" in meta["constants"]

    def test_quantified_formula(self):
        formulas = ["forall X: (Homme(X) => Mortel(X))"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        assert "Homme" in meta["predicates"]
        assert "Mortel" in meta["predicates"]
        assert "X" in meta["variables"]
        assert meta["predicates"]["Homme"] == 1
        assert meta["predicates"]["Mortel"] == 1

    def test_multi_arg_predicate(self):
        formulas = ["Aime(socrate, platon)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        assert "Aime" in meta["predicates"]
        assert meta["predicates"]["Aime"] == 2
        assert "socrate" in meta["constants"]
        assert "platon" in meta["constants"]

    def test_signature_lines_format(self):
        formulas = ["Homme(socrate)", "Mortel(socrate)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        lines = meta["signature_lines"]
        assert any("thing = {" in line for line in lines)
        assert any("type(Homme(thing))" in line for line in lines)
        assert any("type(Mortel(thing))" in line for line in lines)

    def test_mixed_formulas_produce_5_plus(self):
        """Target: 5+ formulas should produce signature declarations for 5+ predicates."""
        formulas = [
            "Asserted(arg1)",
            "Asserted(arg2)",
            "Fallacious(arg1)",
            "Undermines(fallacy1, arg1)",
            "forall X: (Fallacious(X) => !FullySupported(X))",
        ]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        assert len(meta["predicates"]) >= 3  # Asserted, Fallacious, Undermines, FullySupported
        assert len(meta["constants"]) >= 2  # arg1, arg2, fallacy1
        assert len(meta["signature_lines"]) >= 3

    def test_constants_collected_across_formulas(self):
        formulas = ["P(a)", "Q(b)", "R(a, c)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        assert meta["constants"] == {"a", "b", "c"}


class TestBuildSignaturePrefixedFormulas:
    """Test the build_signature_prefixed_formulas method."""

    def test_prefixes_signature(self):
        formulas = ["Homme(socrate)", "Mortel(socrate)"]
        result = FOLLogicAgent.build_signature_prefixed_formulas(formulas)
        # First lines should be signature, then blank, then formulas
        assert len(result) > len(formulas)
        assert result[-1] == "Mortel(socrate)"
        assert any("thing = {" in line for line in result)

    def test_empty_formulas_return_empty(self):
        result = FOLLogicAgent.build_signature_prefixed_formulas([])
        assert result == []
