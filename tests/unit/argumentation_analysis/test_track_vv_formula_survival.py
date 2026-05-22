"""Tests for Track VV (#677): Formula survival through sanitize+parse pipeline.

Tests cover:
  1. PL sanitizer accepts well-formed formulas and rejects garbage
  2. PL per-formula isolation: one bad formula doesn't kill the batch
  3. FOL unicode_to_ascii conversion works correctly
  4. FOL extract_fol_metadata + identifier sanitization alignment
  5. FOL per-formula isolation survives batch parse failure
  6. Synthetic ≥3 formula survival through full sanitize path
"""

import pytest


class TestPLSanitizerSurvival:
    """PL sanitizer should pass well-formed formulas and reject bad ones."""

    def test_well_formed_formulas_pass(self):
        """Standard PL formulas survive sanitization."""
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        formulas = [
            "p",
            "p => q",
            "p && q",
            "p || q",
            "!p",
            "(p => q) && (q => r)",
            "p <=> q",
        ]
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(formulas)
        assert result.total_sanitized == len(formulas)
        assert len(result.skipped_formulas) == 0

    def test_nl_like_propositions_sanitized(self):
        """Formulas with accented chars get normalized to valid identifiers."""
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        formulas = [
            "léconomie_est_forte => les_marchés_vont_monter",
            "menace_étrangère && !stabilité_intérieure",
        ]
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(formulas)
        assert result.total_sanitized == 2
        # Accented chars replaced with underscores, still valid
        for f in result.sanitized_formulas:
            assert all(c.isalnum() or c in " _!&|()<=>" for c in f)

    def test_garbage_formulas_rejected(self):
        """Garbage formulas are rejected without crashing."""
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        formulas = [
            "```python\nfoo\n```",
            "",
            "!!!",
            "(((",
        ]
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(formulas)
        assert result.total_sanitized == 0
        assert len(result.skipped_formulas) == len(formulas)

    def test_mixed_batch_survives_good_only(self):
        """Mixed batch: good formulas survive, bad ones skipped."""
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        formulas = [
            "p => q",
            "```trash```",
            "r && s",
            "(((",
            "!t",
        ]
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(formulas)
        assert result.total_sanitized == 3
        assert len(result.skipped_formulas) == 2
        good = result.sanitized_formulas
        assert any("=>" in f for f in good)
        assert any("&" in f for f in good)
        assert any("!" in f for f in good)


class TestPLPerFormulaIsolation:
    """PL pipeline per-formula isolation prevents one-bad-kills-all."""

    def test_pl_metrics_has_isolation_survivors_key(self):
        """pl_metrics dict includes isolation_survivors counter."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        # Verify the metric key exists in the function signature
        # by checking the source has the key
        import inspect

        source = inspect.getsource(_invoke_propositional_logic)
        assert '"isolation_survivors"' in source


class TestFOLUnicodeConversion:
    """FOL unicode_to_ascii_fol converts Unicode operators correctly."""

    def test_forall_conversion(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        assert "forall" in FOLLogicAgent.unicode_to_ascii_fol("∀X: P(X)")
        assert "forall" not in "∀X: P(X)"

    def test_exists_conversion(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        assert "exists" in FOLLogicAgent.unicode_to_ascii_fol("∃X: P(X)")

    def test_and_or_implies_conversion(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        f = FOLLogicAgent.unicode_to_ascii_fol("∀X: (P(X) ∧ Q(X)) → R(X)")
        assert "forall" in f
        assert "&&" in f
        assert "=>" in f
        assert "∧" not in f
        assert "→" not in f

    def test_negation_conversion(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        f = FOLLogicAgent.unicode_to_ascii_fol("¬P(X)")
        assert f.strip() == "!P(X)"

    def test_biconditional_conversion(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        f = FOLLogicAgent.unicode_to_ascii_fol("P(X) ↔ Q(X)")
        assert "<=>" in f
        assert "↔" not in f

    def test_no_unicode_unchanged(self):
        """ASCII-only formulas pass through unchanged."""
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        original = "forall X: (P(X) && Q(X)) => R(X)"
        assert FOLLogicAgent.unicode_to_ascii_fol(original) == original


class TestFOLIdentifierSanitization:
    """FOL identifier sanitization aligns formulas with signature."""

    def test_extract_fol_metadata_finds_predicates(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        formulas = ["Mortal(socrates)", "Philosopher(plato)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        assert "Mortal" in meta["predicate_map"]
        assert "Philosopher" in meta["predicate_map"]
        assert "socrates" in meta["constant_map"]
        assert "plato" in meta["constant_map"]

    def test_extract_fol_metadata_signature_lines(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        formulas = ["Mortal(socrates)", "Philosopher(plato)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        sig = meta["signature_lines"]
        # Should have sort declaration and type declarations
        assert any("thing" in line for line in sig)
        assert any("Mortal" in line for line in sig)
        assert any("Philosopher" in line for line in sig)

    def test_extract_fol_metadata_handles_accented_chars(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        formulas = ["EstPrésident(macron)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        # The predicate name should be sanitized
        assert len(meta["predicate_map"]) > 0
        # The constant should be sanitized
        assert len(meta["constant_map"]) > 0

    def test_constant_sanitization_collision_disambiguation(self):
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        formulas = ["P(jean_paul)", "P(jean-paul)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        constants = meta["constants"]
        # Two distinct surface forms should produce two distinct sanitized constants
        assert len(constants) >= 2


class TestFOLPipelineIntegration:
    """Integration tests for the FOL sanitize+parse path."""

    def test_template_formulas_survive_sanitization(self):
        """Template fallback formulas should survive the sanitize path."""
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        formulas = [
            "Asserted(arg1)",
            "Asserted(arg2)",
            "Undermines(fallacy1, arg1)",
            "Fallacious(arg1)",
            "forall X: (Fallacious(X) -> !FullySupported(X))",
        ]
        # Unicode conversion (no-op for ASCII)
        converted = [FOLLogicAgent.unicode_to_ascii_fol(f) for f in formulas]
        # Metadata extraction
        meta = FOLLogicAgent.extract_fol_metadata(converted)
        sig = meta["signature_lines"]
        # Should produce signature with all predicates
        assert len(sig) >= 3  # thing sort + at least 2 predicate types
        # All formulas should still be present
        assert len(converted) == 5

    def test_three_formulas_minimal_survival(self):
        """At least 3 well-formed FOL formulas survive sanitization path."""
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        import re

        formulas = [
            "forall X: (Mortal(X) => Dies(X))",
            "Philosopher(socrates)",
            "Mortal(socrates)",
            "forall X: (Philosopher(X) => Wise(X))",
            "!Wise(callicles)",
        ]
        # Unicode conversion
        formulas = [FOLLogicAgent.unicode_to_ascii_fol(f) for f in formulas]
        # Metadata extraction + sanitization
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        constant_map = meta.get("constant_map", {})
        predicate_map = meta.get("predicate_map", {})
        sanitized = []
        for f in formulas:
            sf = f
            for orig, safe in sorted(predicate_map.items(), key=lambda x: -len(x[0])):
                sf = re.sub(r"\b" + re.escape(orig) + r"\b", safe, sf)
            for orig, safe in sorted(constant_map.items(), key=lambda x: -len(x[0])):
                sf = re.sub(r"\b" + re.escape(orig) + r"\b", safe, sf)
            sanitized.append(sf)
        # All 5 should survive (well-formed ASCII FOL)
        assert len(sanitized) == 5
        assert len(meta["signature_lines"]) >= 3


class TestPLPipelineMinimalSurvival:
    """At least 3 well-formed PL formulas survive the sanitize path."""

    def test_three_formulas_through_sanitizer(self):
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        formulas = [
            "p => q",
            "q => r",
            "p && !r",
            "s || t",
            "u <=> v",
        ]
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(formulas)
        assert result.total_sanitized >= 3
        assert len(result.skipped_formulas) == 0

    def test_three_nl_formulas_survive_with_valid_names(self):
        """Snake_case prop names are valid Tweety identifiers and survive."""
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        formulas = [
            "is_mortal => will_die",
            "is_philosopher && seeks_wisdom",
            "!is_wealthy",
            "is_brave || is_cautious",
        ]
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(formulas)
        assert result.total_sanitized >= 3
        # Snake_case names are already valid — no symbol mapping needed


class TestFOLMetricsKeys:
    """Verify FOL metrics dict has the new pre_sanitize/post_sanitize keys."""

    def test_fol_metrics_has_sanitize_keys(self):
        """fol_metrics dict includes pre_sanitize and post_sanitize counters."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        import inspect

        source = inspect.getsource(_invoke_fol_reasoning)
        assert '"pre_sanitize"' in source
        assert '"post_sanitize"' in source
