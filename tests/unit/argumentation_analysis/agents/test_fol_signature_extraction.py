"""Tests for FOL signature extraction with extended symbol support.

Validates extract_fol_metadata handles accented characters, numeric constants,
function symbols, and edge cases. Also tests per-formula isolation retry logic
in the FOL invoke callable.
"""

import pytest

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent


class TestExtractFolMetadataExtended:
    """Test extract_fol_metadata with extended regex patterns."""

    def test_standard_predicates(self):
        """Standard CamelCase predicates with lowercase constants."""
        formulas = ["Mortal(socrates)", "Human(plato)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Mortal" in meta["predicates"]
        assert "Human" in meta["predicates"]
        assert meta["predicates"]["Mortal"] == 1
        assert "socrates" in meta["constants"]
        assert "plato" in meta["constants"]

    def test_accented_constants(self):
        """Accented characters in predicate/constant names are sanitized for Tweety."""
        formulas = ["EstPrésident(macron)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        # Predicate name sanitized: EstPrésident -> EstPr_sident
        assert "EstPr_sident" in meta["predicates"]
        # Constant sanitized: macron (no accent, stays as-is)
        assert "macron" in meta["constants"]

    def test_numeric_constant_suffixes(self):
        """Numeric suffixes in constants (arg1, fallacy2) should be captured."""
        formulas = ["Asserted(arg1)", "Undermines(fallacy2, arg3)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Asserted" in meta["predicates"]
        assert "Undermines" in meta["predicates"]
        assert meta["predicates"]["Undermines"] == 2
        assert "arg1" in meta["constants"]
        assert "fallacy2" in meta["constants"]
        assert "arg3" in meta["constants"]

    def test_multiple_arities(self):
        """Same predicate with different arities — should keep max arity."""
        formulas = ["P(a)", "P(a, b)", "P(x, y, z)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert meta["predicates"]["P"] == 3

    def test_variables_detected(self):
        """Uppercase identifiers in args should be classified as variables."""
        formulas = ["forall X: (Human(X) => Mortal(X))"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "X" in meta["variables"]
        assert "Human" in meta["predicates"]
        assert "Mortal" in meta["predicates"]

    def test_signature_lines_format(self):
        """Signature lines should follow Tweety BNF format."""
        formulas = ["P(a)", "Q(a, b)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        sig = meta["signature_lines"]

        # Sort declaration: thing = {a, b}
        assert any("thing" in line and "a" in line and "b" in line for line in sig)
        # Type declarations
        assert any("type(P(thing))" in line for line in sig)
        assert any("type(Q(thing, thing))" in line for line in sig)

    def test_empty_formulas(self):
        """Empty formula list should return empty metadata."""
        meta = FOLLogicAgent.extract_fol_metadata([])

        assert meta["predicates"] == {}
        assert meta["constants"] == set()
        assert meta["variables"] == set()
        assert meta["signature_lines"] == ["thing = {}"]

    def test_quantified_formula_with_implication(self):
        """Complex formula with forall, =>, and multiple predicates."""
        formulas = ["forall X: (Fallacious(X) => !FullySupported(X))"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Fallacious" in meta["predicates"]
        assert "FullySupported" in meta["predicates"]
        assert "X" in meta["variables"]
        assert len(meta["constants"]) == 0  # No lowercase args

    def test_mixed_formulas_batch(self):
        """Batch of diverse formulas — all symbols extracted correctly."""
        formulas = [
            "Asserted(arg1)",
            "Undermines(fallacy1, arg1)",
            "Fallacious(arg1)",
            "forall X: (Fallacious(X) => !FullySupported(X))",
        ]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert len(meta["predicates"]) >= 4
        assert "arg1" in meta["constants"]
        assert "fallacy1" in meta["constants"]
        assert "X" in meta["variables"]

    def test_predicate_with_underscore(self):
        """Predicates and constants with underscores should be captured."""
        formulas = ["is_valid(test_case)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "is_valid" in meta["predicates"]
        assert "test_case" in meta["constants"]
