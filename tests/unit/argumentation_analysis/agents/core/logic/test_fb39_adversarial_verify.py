"""FB-39 adversarial cross-verify (po-2023, independent of po-2025's own tests).

Role (per coordinator R422 / #1132): adversarially cross-verify po-2025's FB-39
PL-parsing fix BEFORE it weighs on the #1133 merge (formel = sacre). po-2025
produced the fix + measurement; this file independently stress-tests the
**root-cause claim against REAL Tweety** (JVM), which po-2025's own unit tests do
NOT — they mock jpype (``_pl_parser`` is a MagicMock), so they verify the
canonicalisation *logic* but never that Tweety actually rejects single-form
``&``/``|``. That gap is this file's value-add.

The load-bearing claim under test
---------------------------------
po-2025 reports the FB-39 root cause is NOT paren over-spacing (the standing
R408 note) but a ``&&``-collapse: ``_normalize_formula`` was actively turning
``&&``->``&`` , and Tweety's ``PlParser`` rejects the single form with "General
parsing error". The fix canonicalises any run of ``&``/``|`` to the double form.

This probe feeds known patterns DIRECTLY to Tweety (no normalisation) to confirm
that grammar fact independently, then runs the production path (new
``_normalize_formula`` -> ``parseFormula``) to confirm the fix is real,
non-regressing, and fail-loud for genuinely-illegal logic.

Two probe-expectation corrections (honesty)
-------------------------------------------
An initial probe run surfaced 2 "mismatches" that were MY test-design errors,
not fix defects:
  * raw ``p &&& q`` -> Tweety rejects it (accepts EXACTLY ``&&``, not 3+). This is
    precisely why canonicalisation is needed. Corrected expectation: FAIL.
  * ``xyzzy ???`` -> normalised to ``xyzzy ___`` via the PRE-EXISTING prop-name
    sanitiser (junk punctuation -> underscore, unchanged by FB-39) -> parses as a
    valid proposition. This is pre-existing salvage, NOT a FB-39 regression and
    NOT a swallow. Removed from the illegal-logic controls.
"""

import os

import jpype
import pytest

from argumentation_analysis.agents.core.logic.pl_handler import PLHandler
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

# FB-39 is deterministic (no LLM). These tests probe REAL Tweety, so they need a
# JVM and are skipped in CI (which has no JVM / USE_REAL_JPYPE). Run locally:
#   USE_REAL_JPYPE=true conda run -n projet-is pytest <this file> -m tweety
_REAL_JVM = os.environ.get("USE_REAL_JPYPE") == "true"
skip_no_jvm = pytest.mark.skipif(
    not _REAL_JVM, reason="needs USE_REAL_JPYPE=true (real Tweety, skipped in CI)"
)


@pytest.fixture(scope="module")
def pl_env():
    """Start the JVM once and yield (pl_parser, PLHandler) using the NEW fix."""
    bridge = TweetyBridge.get_instance()
    bridge.initialize_jvm()
    init = bridge.initializer
    yield init.get_pl_parser(), PLHandler(init)


def _raw_parse(pl_parser, formula):
    """Parse with NO normalisation — straight to Tweety. Returns (ok, err)."""
    try:
        pl_parser.parseFormula(jpype.JString(formula))
        return True, ""
    except jpype.JException as e:
        return False, str(e.getMessage())[:80]
    except Exception as e:  # noqa: BLE001
        return False, f"PY:{type(e).__name__}:{str(e)[:60]}"


def _prod_parse(pl_parser, handler, formula):
    """Production path: NEW ``_normalize_formula`` then direct Tweety parse.

    Returns (ok, normalised, err). Exercises po-2025's fix end-to-end.
    """
    norm = handler._normalize_formula(formula)
    try:
        pl_parser.parseFormula(jpype.JString(norm))
        return True, norm, ""
    except jpype.JException as e:
        return False, norm, str(e.getMessage())[:80]
    except Exception as e:  # noqa: BLE001
        return False, norm, f"PY:{type(e).__name__}:{str(e)[:60]}"


# ── Part A: root cause — raw Tweety grammar (the load-bearing claim) ─────────


@skip_no_jvm
@pytest.mark.tweety
class TestRootCauseTweetyGrammar:
    """FB-39 root cause, verified DIRECTLY against Tweety (no normalisation).

    The standing R408 note blamed *paren over-spacing*. po-2025's report claims
    the real cause is single-form ``&``/``|`` rejection. These probes settle it:
    Tweety must accept double-form ``&&``/``||`` (even over-spaced) and reject the
    single form — confirming the ``&&``-collapse was the bug, not the spacing.
    """

    @pytest.mark.parametrize(
        "raw",
        [
            "(p && q) => r",  # compact double-and
            "( p && q ) => r",  # over-spaced parens + double-and — DISPROVES the over-space note
            "p && q",
            "p || q",  # double-or
            "p => q",
            "p <=> q",
            "((p=>q)=>r)=>s",  # deeply nested
        ],
    )
    def test_double_form_accepted(self, pl_env, raw):
        parser, _ = pl_env
        ok, err = _raw_parse(parser, raw)
        assert ok, f"Tweety should ACCEPT double-form '{raw}' but rejected: {err}"

    @pytest.mark.parametrize(
        "raw",
        [
            "(p & q) => r",  # single-and compact
            "( p & q ) => r",  # single-and over-spaced — proves spacing is NOT the cause
            "p & q",
            "p | q",  # single-or
        ],
    )
    def test_single_form_rejected(self, pl_env, raw):
        parser, _ = pl_env
        ok, _ = _raw_parse(parser, raw)
        assert not ok, (
            f"Tweety should REJECT single-form '{raw}' (the FB-39 root cause) but "
            f"accepted it — the &&-collapse bug would be harmless, contradicting po-2025"
        )

    def test_raw_triple_and_rejected(self, pl_env):
        """Raw Tweety accepts EXACTLY '&&', not 3+ amps — this is WHY the fix
        canonicalises runs of & to exactly the double form. (Probe-expectation
        correction: an earlier run wrongly expected raw '&&&' to pass.)"""
        parser, _ = pl_env
        ok, _ = _raw_parse(parser, "p &&& q")
        assert not ok, "raw Tweety should reject '&&&' (only '&&' is valid)"


# ── Part B: production path — fix works + non-regression + fail-loud ─────────


@skip_no_jvm
@pytest.mark.tweety
class TestProductionPathFix:
    """The NEW ``_normalize_formula`` (PR #1133) must recover the dropped
    formulas AND preserve everything that parsed before, AND stay fail-loud for
    genuinely-illegal logic (no swallow, R369)."""

    @pytest.mark.parametrize(
        "raw",
        [
            "(p & q) => r",  # the canonical #1132 case — was dropped, now parses
            "p & q",
            "(a | b) => (c & d)",  # mixed & / |
            "(p => q) & (q => r)",  # conjunction of implications
            "!(p & q)",  # negation + grouping
            "p -> q",  # arrow variant -> =>
            "p <-> q",  # biconditional variant -> <=>
        ],
    )
    def test_dropped_formulas_recovered(self, pl_env, raw):
        parser, handler = pl_env
        ok, norm, err = _prod_parse(parser, handler, raw)
        assert ok, (
            f"FB-39 fix should RECOVER '{raw}' (normalised '{norm}') but Tweety "
            f"rejected: {err}"
        )

    @pytest.mark.parametrize(
        "raw",
        [
            "p => q",  # parsed BEFORE the fix too (no & / |)
            "((p=>q)=>r)=>s",
            "p <=> q",
        ],
    )
    def test_no_regression_on_pre_fix_ok(self, pl_env, raw):
        """Non-regression: formulas that already parsed must STILL parse."""
        parser, handler = pl_env
        ok, norm, err = _prod_parse(parser, handler, raw)
        assert ok, f"REGRESSION: '{raw}' (normalised '{norm}') broke: {err}"

    @pytest.mark.parametrize(
        "raw",
        [
            "p =>",  # dangling implication
            "(p && q",  # unbalanced paren
            "&&",  # just operators, no propositions
            "",  # empty
        ],
    )
    def test_illegal_logic_stays_fail_loud(self, pl_env, raw):
        """Genuinely-illegal logic must STAY rejected (dropped + counted). This is
        the R369 anti-fallback guard: the fix adds coverage by canonicalising
        valid operators, NOT by swallowing parse errors. A dangling implication or
        unbalanced paren must still fail-loud."""
        parser, handler = pl_env
        ok, norm, _ = _prod_parse(parser, handler, raw)
        assert not ok, (
            f"illegal '{raw}' (normalised '{norm}') was ACCEPTED — a swallow may "
            f"have been added (R369 violation)"
        )

    def test_canonicalisation_produces_double_form(self, pl_env):
        """The normalised output must contain only the double form (no lone single
        ``&``/``|`` operator that Tweety would reject). Guards the fix itself."""
        _, handler = pl_env
        for raw in ["p & q", "(a | b) & c", "!(p & q) | r"]:
            norm = handler._normalize_formula(raw)
            assert " & " not in norm, f"bare single-& survived in {norm!r}"
            assert " | " not in norm, f"bare single-| survived in {norm!r}"
            assert norm.count("&") % 2 == 0, f"odd '&' count in {norm!r}"
            assert norm.count("|") % 2 == 0, f"odd '|' count in {norm!r}"


# ── Part C: no-JVM invariants (run in CI) — pure function checks ─────────────


class TestCanonicalisationInvariantsNoJVM:
    """No Tweety needed — these verify the ``_normalize_formula`` pure-function
    contract directly (CI-runnable). Independent angle from po-2025's
    ``test_pl_handler_normalize.py`` (different formula set, parity invariants)."""

    def _handler(self):
        """PLHandler with a mocked parser (no JVM) — only _normalize_formula used."""
        from unittest.mock import MagicMock, patch

        with patch("argumentation_analysis.agents.core.logic.pl_handler.jpype"), patch(
            "argumentation_analysis.agents.core.logic.pl_handler.TweetyInitializer"
        ):
            mock_init = MagicMock()
            mock_init.get_pl_parser.return_value = MagicMock()
            return PLHandler(mock_init)

    def test_single_and_canonicalised_to_double(self):
        h = self._handler()
        assert h._normalize_formula("p & q") == "p && q"
        assert h._normalize_formula("(p & q) => r") == "( p && q ) => r"

    def test_single_or_canonicalised_to_double(self):
        h = self._handler()
        assert h._normalize_formula("p | q") == "p || q"

    def test_double_form_idempotent(self):
        """Already-double form must be preserved unchanged (no collapse, no triple)."""
        h = self._handler()
        assert h._normalize_formula("p && q") == "p && q"
        assert h._normalize_formula("p || q") == "p || q"

    def test_biconditional_not_corrupted(self):
        """The =>|<=> regex must not corrupt '<=>'. (My R421 flag of the OLD
        alternation order was a non-bug — confirmed by po-2025 + the raw-Tweety
        probe. Guarded here regardless: '<=>' must round-trip.)"""
        h = self._handler()
        assert h._normalize_formula("p <=> q") == "p <=> q"

    def test_arrow_variants_canonicalised(self):
        h = self._handler()
        assert "=>" in h._normalize_formula("p -> q")
        assert "<=>" in h._normalize_formula("p <-> q")
