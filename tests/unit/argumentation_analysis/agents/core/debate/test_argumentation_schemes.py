"""Tests for the restored 10-scheme dialogical engine (G8 #1184, Epic #1165).

The trunk debate had no active scheme matcher (``FormalArgument.scheme`` was
never populated). G8 restores the engine adapted faithfully from the student
deliverable ``argumentation_engine._load_argumentation_schemes``, adding the
canonical Walton critical questions. ``classify_scheme`` is a DETERMINISTIC
lexical matcher that fails loud (None) when no scheme fits — never a fabricated
label (#1019).
"""

from __future__ import annotations

from argumentation_analysis.agents.core.debate.argumentation_schemes import (
    ArgumentationScheme,
    _load_argumentation_schemes,
    classify_scheme,
    schemes_as_prompt_context,
)


class TestSchemeTable:
    def test_ten_schemes_loaded(self):
        schemes = _load_argumentation_schemes()
        assert len(schemes) == 10

    def test_student_keys_preserved(self):
        """The 10 scheme keys match the student deliverable verbatim."""
        schemes = _load_argumentation_schemes()
        expected = {
            "modus_ponens",
            "expert_opinion",
            "analogy",
            "cause_effect",
            "consensus",
            "empirical_evidence",
            "economic_argument",
            "precautionary_principle",
            "moral_argument",
            "historical_precedent",
        }
        assert set(schemes.keys()) == expected

    def test_each_scheme_has_critical_questions(self):
        """G8 addition: every scheme carries canonical Walton critical questions."""
        schemes = _load_argumentation_schemes()
        for key, s in schemes.items():
            assert isinstance(s, ArgumentationScheme)
            assert len(s.critical_questions) >= 1, f"{key} has no critical question"

    def test_strength_values_are_students(self):
        """Faithful restoration: strength values are the student engine's."""
        schemes = _load_argumentation_schemes()
        assert schemes["modus_ponens"].strength == 1.0
        assert schemes["empirical_evidence"].strength == 0.9
        assert schemes["consensus"].strength == 0.85


class TestClassifyScheme:
    def test_expert_opinion_matched(self):
        s = classify_scheme("Selon un expert du domaine, la thèse tient.")
        assert s is not None
        assert s.key == "expert_opinion"

    def test_economic_argument_matched(self):
        s = classify_scheme("Le coût est élevé mais le bénéfice est plus grand.")
        assert s is not None
        assert s.key == "economic_argument"

    def test_empirical_evidence_matched(self):
        s = classify_scheme("Les données montrent P sur un échantillon représentatif.")
        assert s is not None
        assert s.key == "empirical_evidence"

    def test_no_match_returns_none_fail_loud(self):
        """Fail-loud (#1019): neutral text yields None, never a fabricated label."""
        assert classify_scheme("Le ciel est bleu aujourd'hui.") is None

    def test_empty_returns_none(self):
        assert classify_scheme("") is None
        assert classify_scheme(None) is None  # type: ignore[arg-type]

    def test_no_fabricated_scheme_label(self):
        """Anti-pendule: the matcher never invents a scheme that isn't in the table."""
        s = classify_scheme("Selon un expert du domaine.")
        if s is not None:
            table = _load_argumentation_schemes()
            assert s.key in table


class TestPromptContext:
    def test_renders_all_schemes_with_questions(self):
        ctx = schemes_as_prompt_context()
        assert "expert" in ctx.lower()
        assert "question" in ctx.lower()
        # 10 numbered lines
        assert ctx.count("\n") >= 9
