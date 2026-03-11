# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.utils.tweety_error_analyzer
Covers TweetyErrorFeedback, TweetyErrorAnalyzer, and utility functions.
"""

import pytest

from argumentation_analysis.utils.tweety_error_analyzer import (
    TweetyErrorFeedback,
    TweetyErrorAnalyzer,
    analyze_tweety_error,
    create_bnf_feedback_for_error,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def analyzer():
    return TweetyErrorAnalyzer()


# ============================================================
# TweetyErrorFeedback dataclass
# ============================================================

class TestTweetyErrorFeedback:
    def test_creation(self):
        fb = TweetyErrorFeedback(
            error_type="syntax_error",
            original_error="unexpected token",
            bnf_rules=["rule ::= head ':-' body '.'"],
            corrections=["Check punctuation"],
            example_fix="rule(X) :- cond(X).",
        )
        assert fb.error_type == "syntax_error"
        assert fb.confidence == 0.8  # default

    def test_custom_confidence(self):
        fb = TweetyErrorFeedback(
            error_type="t", original_error="e",
            bnf_rules=[], corrections=[], example_fix="",
            confidence=0.5,
        )
        assert fb.confidence == 0.5

    def test_fields_accessible(self):
        fb = TweetyErrorFeedback(
            error_type="atom_error", original_error="atom not defined",
            bnf_rules=["r1", "r2"], corrections=["c1"],
            example_fix="fix",
        )
        assert len(fb.bnf_rules) == 2
        assert len(fb.corrections) == 1
        assert fb.example_fix == "fix"


# ============================================================
# TweetyErrorAnalyzer.__init__
# ============================================================

class TestAnalyzerInit:
    def test_error_patterns_populated(self, analyzer):
        assert len(analyzer.error_patterns) > 0

    def test_bnf_rules_populated(self, analyzer):
        assert len(analyzer.bnf_rules) > 0

    def test_corrections_populated(self, analyzer):
        assert len(analyzer.corrections) > 0

    def test_all_error_types_have_bnf(self, analyzer):
        for error_type in analyzer.error_patterns:
            assert error_type in analyzer.bnf_rules, f"Missing BNF for {error_type}"

    def test_all_error_types_have_corrections(self, analyzer):
        for error_type in analyzer.error_patterns:
            assert error_type in analyzer.corrections, f"Missing corrections for {error_type}"


# ============================================================
# _detect_error_type
# ============================================================

class TestDetectErrorType:
    def test_declaration_error(self, analyzer):
        msg = "predicate 'foo' has not been declared"
        assert analyzer._detect_error_type(msg) == "DECLARATION_ERROR"

    def test_declaration_error_french(self, analyzer):
        msg = "le prédicat 'bar' n'a pas été déclaré"
        assert analyzer._detect_error_type(msg) == "DECLARATION_ERROR"

    def test_constant_syntax_error(self, analyzer):
        msg = "error parsing constant(human)"
        assert analyzer._detect_error_type(msg) == "CONSTANT_SYNTAX_ERROR"

    def test_modal_syntax_error(self, analyzer):
        msg = "expected modal operator in formula"
        assert analyzer._detect_error_type(msg) == "MODAL_SYNTAX_ERROR"

    def test_modal_expected_brackets(self, analyzer):
        msg = "expected [] or <> before atom"
        assert analyzer._detect_error_type(msg) == "MODAL_SYNTAX_ERROR"

    def test_json_structure_error(self, analyzer):
        msg = "JSON structure invalid for input"
        assert analyzer._detect_error_type(msg) == "JSON_STRUCTURE_ERROR"

    def test_atom_error(self, analyzer):
        msg = "atom not defined in knowledge base"
        assert analyzer._detect_error_type(msg) == "atom_error"

    def test_rule_error(self, analyzer):
        msg = "rule malformed at line 5"
        assert analyzer._detect_error_type(msg) == "rule_error"

    def test_constraint_error(self, analyzer):
        msg = "constraint violated: integrity constraint"
        assert analyzer._detect_error_type(msg) == "constraint_error"

    def test_variable_error(self, analyzer):
        msg = "variable X unbound in rule"
        assert analyzer._detect_error_type(msg) == "variable_error"

    def test_singleton_variable(self, analyzer):
        msg = "singleton variable Y detected"
        assert analyzer._detect_error_type(msg) == "variable_error"

    def test_syntax_error_generic(self, analyzer):
        msg = "syntax error near token '('"
        assert analyzer._detect_error_type(msg) == "syntax_error"

    def test_unexpected_token(self, analyzer):
        msg = "unexpected token at position 10"
        assert analyzer._detect_error_type(msg) == "syntax_error"

    def test_no_viable_alternative(self, analyzer):
        msg = "no viable alternative at input 'xyz'"
        assert analyzer._detect_error_type(msg) == "syntax_error"

    def test_unknown_error(self, analyzer):
        msg = "something completely unrecognized happened"
        assert analyzer._detect_error_type(msg) == "UNKNOWN_ERROR"

    def test_case_insensitive(self, analyzer):
        msg = "SYNTAX ERROR NEAR TOKEN"
        assert analyzer._detect_error_type(msg) == "syntax_error"


# ============================================================
# analyze_error
# ============================================================

class TestAnalyzeError:
    def test_returns_feedback(self, analyzer):
        fb = analyzer.analyze_error("syntax error near ';'")
        assert isinstance(fb, TweetyErrorFeedback)

    def test_feedback_has_error_type(self, analyzer):
        fb = analyzer.analyze_error("predicate 'foo' has not been declared")
        assert fb.error_type == "DECLARATION_ERROR"

    def test_feedback_preserves_original_error(self, analyzer):
        msg = "atom not defined: bar"
        fb = analyzer.analyze_error(msg)
        assert fb.original_error == msg

    def test_feedback_has_bnf_rules(self, analyzer):
        fb = analyzer.analyze_error("syntax error near token")
        assert len(fb.bnf_rules) > 0

    def test_feedback_has_corrections(self, analyzer):
        fb = analyzer.analyze_error("rule malformed")
        assert len(fb.corrections) > 0

    def test_feedback_has_example_fix(self, analyzer):
        fb = analyzer.analyze_error("variable X unbound")
        assert fb.example_fix != ""

    def test_feedback_has_confidence(self, analyzer):
        fb = analyzer.analyze_error("constraint violated")
        assert 0.0 <= fb.confidence <= 1.0

    def test_unknown_error_low_confidence(self, analyzer):
        fb = analyzer.analyze_error("totally unknown error xyz")
        assert fb.confidence <= 0.5

    def test_with_context(self, analyzer):
        fb = analyzer.analyze_error("syntax error near ':'", context="rule(X) :- body")
        assert isinstance(fb, TweetyErrorFeedback)

    def test_declaration_error_extracts_entity(self, analyzer):
        fb = analyzer.analyze_error("predicate 'is_human' has not been declared")
        assert "is_human" in fb.example_fix

    def test_unknown_fallback_bnf_rules(self, analyzer):
        fb = analyzer.analyze_error("totally unknown issue")
        # Should fall back to syntax_error BNF rules
        assert len(fb.bnf_rules) > 0


# ============================================================
# _generate_example_fix
# ============================================================

class TestGenerateExampleFix:
    def test_syntax_error_example(self, analyzer):
        fix = analyzer._generate_example_fix("syntax_error", "syntax error", None)
        assert "Exemple" in fix or "règle" in fix

    def test_atom_error_with_entity(self, analyzer):
        fix = analyzer._generate_example_fix("atom_error", "atom 'foo' not defined", None)
        assert "foo" in fix

    def test_declaration_error_with_entity(self, analyzer):
        fix = analyzer._generate_example_fix("DECLARATION_ERROR", "predicate 'bar' not declared", None)
        assert "bar" in fix

    def test_unknown_type_default(self, analyzer):
        fix = analyzer._generate_example_fix("UNKNOWN_TYPE", "some error", None)
        assert "documentation" in fix.lower() or "Vérifiez" in fix

    def test_syntax_error_with_missing_context(self, analyzer):
        fix = analyzer._generate_example_fix(
            "syntax_error", "missing something before '.'", "rule(X) :- body"
        )
        assert isinstance(fix, str)

    def test_no_entity_in_error(self, analyzer):
        fix = analyzer._generate_example_fix("atom_error", "atom not defined", None)
        assert "votre_entite" in fix


# ============================================================
# _calculate_confidence
# ============================================================

class TestCalculateConfidence:
    def test_declaration_error_high(self, analyzer):
        conf = analyzer._calculate_confidence("DECLARATION_ERROR", "short msg")
        assert conf >= 0.9

    def test_syntax_error_moderate(self, analyzer):
        conf = analyzer._calculate_confidence("syntax_error", "short msg")
        assert 0.5 <= conf <= 0.85

    def test_unknown_error_low(self, analyzer):
        conf = analyzer._calculate_confidence("UNKNOWN_ERROR", "error")
        assert conf <= 0.5

    def test_unknown_error_with_line_info(self, analyzer):
        conf = analyzer._calculate_confidence("UNKNOWN_ERROR", "error at line 5")
        assert conf == 0.5

    def test_long_message_boost(self, analyzer):
        short_conf = analyzer._calculate_confidence("atom_error", "short")
        long_msg = "a" * 50 + " atom not defined in knowledge base with context"
        long_conf = analyzer._calculate_confidence("atom_error", long_msg)
        assert long_conf >= short_conf

    def test_confidence_capped_at_one(self, analyzer):
        conf = analyzer._calculate_confidence("DECLARATION_ERROR", "x" * 100)
        assert conf <= 1.0

    def test_unmapped_error_type(self, analyzer):
        conf = analyzer._calculate_confidence("TOTALLY_UNKNOWN", "msg")
        assert conf == 0.6  # default


# ============================================================
# generate_bnf_feedback_message
# ============================================================

class TestGenerateBnfFeedbackMessage:
    def test_contains_error_type(self, analyzer):
        fb = TweetyErrorFeedback(
            error_type="syntax_error", original_error="err",
            bnf_rules=["r1"], corrections=["c1"], example_fix="fix",
        )
        msg = analyzer.generate_bnf_feedback_message(fb)
        assert "syntax_error" in msg

    def test_contains_attempt_number(self, analyzer):
        fb = TweetyErrorFeedback(
            error_type="t", original_error="e",
            bnf_rules=[], corrections=[], example_fix="",
        )
        msg = analyzer.generate_bnf_feedback_message(fb, attempt_number=3)
        assert "#3" in msg

    def test_contains_bnf_rules(self, analyzer):
        fb = TweetyErrorFeedback(
            error_type="t", original_error="e",
            bnf_rules=["rule1", "rule2"], corrections=[], example_fix="",
        )
        msg = analyzer.generate_bnf_feedback_message(fb)
        assert "rule1" in msg
        assert "rule2" in msg

    def test_contains_corrections(self, analyzer):
        fb = TweetyErrorFeedback(
            error_type="t", original_error="e",
            bnf_rules=[], corrections=["Fix this", "Fix that"], example_fix="",
        )
        msg = analyzer.generate_bnf_feedback_message(fb)
        assert "Fix this" in msg
        assert "Fix that" in msg

    def test_contains_example_fix(self, analyzer):
        fb = TweetyErrorFeedback(
            error_type="t", original_error="e",
            bnf_rules=[], corrections=[], example_fix="my_example_fix_code",
        )
        msg = analyzer.generate_bnf_feedback_message(fb)
        assert "my_example_fix_code" in msg

    def test_contains_confidence(self, analyzer):
        fb = TweetyErrorFeedback(
            error_type="t", original_error="e",
            bnf_rules=[], corrections=[], example_fix="",
            confidence=0.85,
        )
        msg = analyzer.generate_bnf_feedback_message(fb)
        assert "85" in msg  # 85.0%


# ============================================================
# analyze_tweety_error (top-level function)
# ============================================================

class TestAnalyzeTweetyError:
    def test_returns_string(self):
        result = analyze_tweety_error("syntax error near token")
        assert isinstance(result, str)

    def test_contains_error_info(self):
        result = analyze_tweety_error("predicate 'foo' has not been declared")
        assert "DECLARATION_ERROR" in result

    def test_attempt_number(self):
        result = analyze_tweety_error("syntax error", attempt_number=5)
        assert "#5" in result

    def test_with_context(self):
        result = analyze_tweety_error("syntax error", context="rule(X).")
        assert isinstance(result, str)


# ============================================================
# create_bnf_feedback_for_error (alias function)
# ============================================================

class TestCreateBnfFeedbackForError:
    def test_returns_string(self):
        result = create_bnf_feedback_for_error("syntax error")
        assert isinstance(result, str)

    def test_same_as_analyze(self):
        msg = "predicate 'bar' has not been declared"
        r1 = analyze_tweety_error(msg, attempt_number=2)
        r2 = create_bnf_feedback_for_error(msg, attempt_number=2)
        assert r1 == r2

    def test_with_context_and_attempt(self):
        result = create_bnf_feedback_for_error(
            "atom not defined", context="ctx", attempt_number=3
        )
        assert "#3" in result
