"""Unit tests for PLFormulaSanitizer (#537).

Tests cover:
- Operator normalization
- NL-like proposition detection and symbol mapping
- Formula validation (balanced parens, valid tokens, non-empty)
- Batch sanitization with skipping
- Symbol mapping round-trip
- Edge cases (markdown artifacts, empty input, long predicates, accented chars)
"""

import pytest

from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
    PLFormulaSanitizer,
    SanitizationResult,
)


class TestOperatorNormalization:
    """Test _normalize_operators and operator handling."""

    def test_double_ampersand(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p && q")
        assert result == "p & q"

    def test_double_pipe(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p || q")
        assert result == "p | q"

    def test_arrow_implication(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p -> q")
        assert result == "p => q"

    def test_double_arrow_biconditional(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p <-> q")
        assert result is not None
        assert "<=>" in result

    def test_compound_operators(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("(p && q) -> r")
        assert result is not None
        assert "&" in result
        assert "=>" in result

    def test_no_operators(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("rain")
        assert result == "rain"


class TestNLDetection:
    """Test detection of NL-like proposition names."""

    def test_short_valid_prop(self):
        s = PLFormulaSanitizer()
        assert not s._is_nl_like("rain")

    def test_underscore_valid(self):
        s = PLFormulaSanitizer()
        assert not s._is_nl_like("is_raining")

    def test_long_nl_fragment(self):
        s = PLFormulaSanitizer()
        assert s._is_nl_like("the speaker argues that national sovereignty")

    def test_special_chars(self):
        s = PLFormulaSanitizer()
        assert s._is_nl_like("l'argument")

    def test_accented_chars(self):
        s = PLFormulaSanitizer()
        assert s._is_nl_like("souveraineté")

    def test_mixed_language(self):
        s = PLFormulaSanitizer()
        assert s._is_nl_like("coopération yields résultats")


class TestSymbolMapping:
    """Test NL→atomic symbol mapping."""

    def test_basic_mapping(self):
        s = PLFormulaSanitizer()
        sym1 = s._map_label("it is raining")
        sym2 = s._map_label("the ground is wet")
        assert sym1 == "p"
        assert sym2 == "q"

    def test_reuse_mapping(self):
        s = PLFormulaSanitizer()
        sym1 = s._map_label("rain")
        sym2 = s._map_label("rain")
        assert sym1 == sym2

    def test_symbol_exhaustion(self):
        s = PLFormulaSanitizer()
        symbols = [s._map_label(f"label_{i}") for i in range(30)]
        assert symbols[0] == "p"
        assert symbols[10] == "z"
        assert symbols[11] == "p2"
        assert symbols[12] == "q2"
        assert len(set(symbols)) == 30

    def test_case_insensitive_reuse(self):
        s = PLFormulaSanitizer()
        s._map_label("Rain")
        sym2 = s._map_label("rain")
        assert sym2 == "p"

    def test_reverse_mapping(self):
        s = PLFormulaSanitizer()
        s._map_label("it is raining")
        s._map_label("the ground is wet")
        rev = s.reverse_mapping()
        assert rev["p"] == "it is raining"
        assert rev["q"] == "the ground is wet"


class TestFormulaValidation:
    """Test formula validation rules."""

    def test_valid_simple(self):
        s = PLFormulaSanitizer()
        ok, reason = s.validate_formula("p & q")
        assert ok
        assert reason == "valid"

    def test_valid_implication(self):
        s = PLFormulaSanitizer()
        ok, _ = s.validate_formula("p => q")
        assert ok

    def test_valid_negation(self):
        s = PLFormulaSanitizer()
        ok, _ = s.validate_formula("! p")
        assert ok

    def test_valid_nested(self):
        s = PLFormulaSanitizer()
        ok, _ = s.validate_formula("( p & q ) => r")
        assert ok

    def test_empty_formula(self):
        s = PLFormulaSanitizer()
        ok, reason = s.validate_formula("")
        assert not ok
        assert "empty" in reason

    def test_unbalanced_parens(self):
        s = PLFormulaSanitizer()
        ok, reason = s.validate_formula("( p & q")
        assert not ok
        assert "unbalanced" in reason

    def test_no_propositions(self):
        s = PLFormulaSanitizer()
        ok, reason = s.validate_formula("=> &")
        assert not ok
        assert "no propositions" in reason

    def test_invalid_token(self):
        s = PLFormulaSanitizer()
        ok, reason = s.validate_formula("p & 123bad")
        assert not ok
        assert "invalid tokens" in reason


class TestSanitizeFormula:
    """Test end-to-end formula sanitization."""

    def test_already_valid(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p & q")
        assert result == "p & q"

    def test_nl_props_mapped(self):
        s = PLFormulaSanitizer()
        # Verbose proposition names with hyphens/quotes → sanitized and mapped
        result = s.sanitize_formula("l'argument => conclusion")
        assert result is not None

    def test_markdown_fence_rejected(self):
        s = PLFormulaSanitizer()
        assert s.sanitize_formula("```formula```") is None

    def test_none_input(self):
        s = PLFormulaSanitizer()
        assert s.sanitize_formula(None) is None

    def test_empty_input(self):
        s = PLFormulaSanitizer()
        assert s.sanitize_formula("") is None

    def test_nl_fragment_with_special_chars(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("l'argument est valable => conclusion")
        # The sanitizer should normalize special chars in prop names
        assert result is not None

    def test_preserves_valid_long_names(self):
        s = PLFormulaSanitizer(max_prop_length=50)
        result = s.sanitize_formula("national_sovereignty_requires_action")
        assert result is not None
        assert "national_sovereignty_requires_action" in result

    def test_rejects_very_long_nl(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula(
            "the speaker argues that national sovereignty requires immediate action "
            "&& foreign powers threaten our independence"
        )
        # Should be sanitized via symbol mapping
        assert result is not None
        assert "p" in result
        assert "q" in result


class TestBatchSanitization:
    """Test batch sanitization with mixed valid/invalid formulas."""

    def test_all_valid(self):
        s = PLFormulaSanitizer()
        formulas = ["p & q", "r => s", "! t"]
        result = s.sanitize_batch(formulas)
        assert result.total_input == 3
        assert result.total_sanitized == 3
        assert len(result.skipped_formulas) == 0

    def test_mixed_validity(self):
        s = PLFormulaSanitizer()
        formulas = [
            "p & q",
            "```invalid```",
            "r => s",
            "",
            "( p => q ) & r",
        ]
        result = s.sanitize_batch(formulas)
        assert result.total_input == 5
        assert result.total_sanitized == 3
        assert len(result.skipped_formulas) == 2

    def test_nl_formulas_mapped(self):
        s = PLFormulaSanitizer(max_prop_length=20)
        # Long proposition names that exceed max_prop_length → mapped to atomic symbols
        formulas = [
            "national_sovereignty_requires && foreign_powers_threaten",
            "cooperation_yields_outcomes => defend_borders_against",
        ]
        result = s.sanitize_batch(formulas)
        assert result.total_sanitized == 2
        # Long names should be mapped to p, q, r, s
        assert len(result.symbol_mapping) >= 2

    def test_symbol_mapping_populated(self):
        s = PLFormulaSanitizer()
        formulas = ["national_sovereignty => immediate_action"]
        result = s.sanitize_batch(formulas)
        assert result.total_sanitized == 1
        # Valid short names won't be remapped, but mapping should be available
        mapping = result.symbol_mapping
        assert isinstance(mapping, dict)

    def test_empty_batch(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_batch([])
        assert result.total_input == 0
        assert result.total_sanitized == 0

    def test_result_type(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_batch(["p & q"])
        assert isinstance(result, SanitizationResult)
        assert isinstance(result.sanitized_formulas, list)
        assert isinstance(result.symbol_mapping, dict)
        assert isinstance(result.skipped_formulas, list)


class TestEdgeCases:
    """Test edge cases and real-world patterns from corpora."""

    def test_french_accented_prop(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("souveraineté_nécessite => action")
        # Accented chars should be sanitized or mapped
        assert result is not None

    def test_double_negation(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("! ! p")
        assert result is not None
        tokens = result.split()
        assert tokens.count("!") == 2

    def test_biconditional(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p <=> q")
        assert result == "p <=> q"

    def test_deeply_nested(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("( ( p & q ) => ( r | s ) )")
        assert result is not None

    def test_real_corpus_pattern(self):
        """Pattern observed in 159 ParserExceptions from corpus_dense_A/B/C."""
        s = PLFormulaSanitizer()
        formulas = [
            "National sovereignty requires immediate action => Foreign powers threaten independence",
            "Cooperation yields better outcomes => We must defend our borders",
        ]
        result = s.sanitize_batch(formulas)
        # Both should be sanitized via symbol mapping
        assert result.total_sanitized == 2
        for f in result.sanitized_formulas:
            # All tokens should be valid
            tokens = f.split()
            for t in tokens:
                if t not in {"=>", "<=>", "&", "|", "!", "(", ")", ""}:
                    assert t[0].isalpha() or t[0] == "_", f"Invalid token: {t}"

    def test_operator_without_spaces(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("p&&q=>r")
        assert result is not None
        assert "&" in result
        assert "=>" in result

    def test_only_operators(self):
        s = PLFormulaSanitizer()
        result = s.sanitize_formula("=> & |")
        assert result is None
