"""Unit tests for PLHandler._normalize_formula and parse_pl_formula (#1132).

FB-39 root cause: Tweety's PlParser requires the DOUBLE-form conjunction/
disjunction ("&&", "||"); the previous normalization collapsed them to single
"&"/"|", which Tweety rejects with "General parsing error" — dropping ~58 valid
formulas/run of formal coverage. These tests guard the canonicalisation
(no-JVM, runs in CI) and the negative controls (genuinely-illegal formulas stay
rejected). End-to-end Tweety parsing is covered by the tweety-marked class.
"""
import os

import pytest
from unittest.mock import patch, MagicMock


def _make_handler():
    """Instantiate a PLHandler with mocked jpype (no JVM needed).

    Mirrors the pattern in test_sat_handler.TestPLHandlerSATDispatch.
    """
    with patch(
        "argumentation_analysis.agents.core.logic.pl_handler.jpype"
    ) as mock_jpype, patch(
        "argumentation_analysis.agents.core.logic.pl_handler.TweetyInitializer"
    ):
        mock_jpype.JClass.return_value = MagicMock
        mock_jpype.JString.return_value = "mock"
        mock_jpype.JException = Exception
        mock_init = MagicMock()
        mock_init.get_pl_parser.return_value = MagicMock()
        from argumentation_analysis.agents.core.logic.pl_handler import PLHandler

        return PLHandler(mock_init)


class TestNormalizeFormulaCanonicalisation:
    """FB-39 (#1132): & / | runs MUST canonicalise to the double-form && / ||."""

    @pytest.mark.parametrize(
        "raw",
        [
            "p && q",                 # already double — preserved
            "p & q",                  # single-& — canonicalised UP to &&
            "(p && q) => r",          # issue #1132 canonical example
            "(p => q) & (q => r)",    # conjunction of implications
            "!(p & q)",               # negation + grouping
            "(a | b) => (c & d)",     # mixed or/and
        ],
    )
    def test_conjunction_canonicalised(self, raw):
        h = _make_handler()
        out = h._normalize_formula(raw)
        # every '&' must be part of a '&&' pair (no lone single-& operator that
        # Tweety would reject)
        assert out.count("&") % 2 == 0, f"odd '&' count in {out!r} for {raw!r}"
        # no bare " & " operator survives (only " && ")
        assert " & " not in out, f"bare single-& operator in {out!r} for {raw!r}"

    @pytest.mark.parametrize("raw", ["p || q", "p | q", "(a | b) => r", "p <=> q | r"])
    def test_disjunction_canonicalised(self, raw):
        h = _make_handler()
        out = h._normalize_formula(raw)
        assert out.count("|") % 2 == 0, f"odd '|' count in {out!r} for {raw!r}"
        assert " | " not in out, f"bare single-| operator in {out!r} for {raw!r}"

    def test_implication_preserved(self):
        h = _make_handler()
        assert "=>" in h._normalize_formula("p => q")

    def test_arrow_variant_canonicalised(self):
        h = _make_handler()
        assert h._normalize_formula("p -> q").count("=>") == 1

    def test_biconditional_preserved(self):
        # The =>|<=> regex alternation must NOT corrupt "<=>" (the latent bug
        # po-2023 flagged — confirmed non-bug, but guarded here).
        h = _make_handler()
        out = h._normalize_formula("p <=> q")
        assert "<=>" in out
        assert out.strip() == "p <=> q"

    def test_biconditional_variant_canonicalised(self):
        h = _make_handler()
        out = h._normalize_formula("p <-> q")
        assert "<=>" in out
        assert "<->" not in out

    def test_deep_nesting_preserved(self):
        h = _make_handler()
        out = h._normalize_formula("((p => q) => r) => s")
        assert out.count("=>") == 3  # all three implications survive
        assert out.count("&") == 0   # no conjunction introduced

    def test_not_string_returns_empty(self):
        h = _make_handler()
        assert h._normalize_formula(None) == ""
        assert h._normalize_formula(123) == ""


class TestParsePlFormulaNegativeControls:
    """Genuinely-illegal formulas stay rejected (no error-swallowing, #1132 R369)."""

    def test_unbalanced_parens_rejected(self):
        # The sanitizer pre-validation rejects unbalanced parens -> None.
        h = _make_handler()
        assert h.parse_pl_formula("(p && q") is None
        assert h.parse_pl_formula("p && q)") is None

    def test_markdown_fence_rejected(self):
        h = _make_handler()
        assert h.parse_pl_formula("```p && q```") is None

    def test_empty_rejected(self):
        h = _make_handler()
        assert h.parse_pl_formula("") is None


@pytest.mark.tweety
class TestParsePlFormulaTweetyIntegration:
    """End-to-end Tweety parsing (FB-39 #1132). Skipped unless a real JVM is up.

    These reproduce the diagnostic: valid nested formulas that previously failed
    ("General parsing error") now reach the solver; genuinely-illegal formulas
    still raise ValueError (fail-loud).
    """

    _PATTERNS_SHOULD_PARSE = [
        "p && q",
        "(p && q) => r",
        "(p => q) && (q => r)",
        "!(p && q)",
        "((p => q) => r) => s",
        "p <=> q",
        "(a || b) => (c && d)",
    ]
    # Sanitizer pre-validation rejects these -> parse_pl_formula returns None.
    _PATTERNS_SANITIZER_REJECTS = [
        "(p && q",     # unbalanced parens
        "p && q)",     # unbalanced parens
        "```p && q```",  # markdown fence
    ]
    # These pass the sanitizer but Tweety rejects them -> ValueError (fail-loud).
    _PATTERNS_TWEETY_REJECTS = [
        "p =>",        # missing rhs
    ]

    @pytest.fixture(autouse=True)
    def _require_jvm(self):
        if os.environ.get("USE_REAL_JPYPE") != "true":
            pytest.skip("set USE_REAL_JPYPE=true to exercise real Tweety parsing")
        from argumentation_analysis.core.jvm_setup import initialize_jvm
        import jpype  # noqa: F401
        initialize_jvm()
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        from argumentation_analysis.agents.core.logic.pl_handler import PLHandler
        bridge = TweetyBridge.get_instance()
        try:
            bridge.initialize_jvm()
        except RuntimeError:
            pass
        init = bridge.initializer
        init.initialize_pl_components()
        self.handler = PLHandler(init)

    @pytest.mark.parametrize("formula", _PATTERNS_SHOULD_PARSE)
    def test_valid_nested_parses(self, formula):
        f = self.handler.parse_pl_formula(formula)
        assert f is not None, f"valid formula {formula!r} failed to parse"

    @pytest.mark.parametrize("formula", _PATTERNS_SANITIZER_REJECTS)
    def test_sanitizer_rejects_return_none(self, formula):
        # Sanitizer pre-validation drops these (returns None) — no exception.
        assert self.handler.parse_pl_formula(formula) is None

    @pytest.mark.parametrize("formula", _PATTERNS_TWEETY_REJECTS)
    def test_tweety_rejects_raise(self, formula):
        # Passes the sanitizer but Tweety rejects -> ValueError (fail-loud, no
        # silent swallowing per #1132 R369).
        with pytest.raises(ValueError):
            self.handler.parse_pl_formula(formula)
