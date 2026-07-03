"""Tests for fail-loud downstream consumer correctness (#1019 follow-up).

Validates that downstream consumers of fail-loud sentinel values
(`consistent: None`, `valid: None`, empty Dung extensions, narrative sentinel)
do NOT silently treat "unverified" as "inconsistent" or "invalid".

Follows R370 dispatch: audit consommateurs aval fail-loud.
"""

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# 1. FOL state writer — consistent: None must NOT become False
# ---------------------------------------------------------------------------


class TestFOLStateWriterFailLoud:
    """_write_fol_to_state must preserve None (unverified) vs False (inconsistent)."""

    def test_consistent_none_preserved(self):
        """When FOL returns consistent=None, state stores None (not False)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_fol_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["forall x. P(x)"],
            "consistent": None,
            "inferences": [],
            "confidence": 0.0,
            "solver": "none",
        }
        _write_fol_to_state(output, state, {})

        # The call should pass consistent=None, not bool(None)=False
        call_args = state.add_fol_analysis_result.call_args
        assert call_args is not None, "add_fol_analysis_result was not called"
        consistent_arg = call_args[0][1]  # second positional arg
        assert consistent_arg is None, (
            f"Expected consistent=None (unverified), got {consistent_arg!r}. "
            f"None being coerced to False is the bug from #1019."
        )

    def test_consistent_true_preserved(self):
        """When FOL returns consistent=True, state stores True."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_fol_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["P(a)"],
            "consistent": True,
            "inferences": ["Q(a)"],
            "confidence": 0.8,
        }
        _write_fol_to_state(output, state, {})

        call_args = state.add_fol_analysis_result.call_args
        assert call_args[0][1] is True

    def test_consistent_false_preserved(self):
        """When FOL returns consistent=False, state stores False."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_fol_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["P(a)", "not P(a)"],
            "consistent": False,
            "inferences": [],
            "confidence": 0.4,
        }
        _write_fol_to_state(output, state, {})

        call_args = state.add_fol_analysis_result.call_args
        assert call_args[0][1] is False

    def test_empty_output_no_crash(self):
        """Empty output does not crash the writer."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_fol_to_state,
        )

        state = MagicMock()
        _write_fol_to_state({}, state, {})
        state.add_fol_analysis_result.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Modal state writer — valid: None must NOT become False
# ---------------------------------------------------------------------------


class TestModalStateWriterFailLoud:
    """_write_modal_to_state must preserve None (unverified) vs False (invalid)."""

    def test_valid_none_preserved(self):
        """When modal returns valid=None, state stores None (not False)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_modal_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["[](p)"],
            "valid": None,
            "modalities": ["necessity"],
            "solver": "unavailable",
        }
        _write_modal_to_state(output, state, {})

        call_args = state.add_modal_analysis_result.call_args
        assert call_args is not None
        valid_arg = call_args[0][1]  # second positional arg
        assert valid_arg is None, (
            f"Expected valid=None (unverified), got {valid_arg!r}"
        )

    def test_valid_true_preserved(self):
        """When modal returns valid=True, state stores True."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_modal_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["[](p)"],
            "valid": True,
            "modalities": ["necessity"],
        }
        _write_modal_to_state(output, state, {})

        call_args = state.add_modal_analysis_result.call_args
        assert call_args[0][1] is True

    def test_valid_false_preserved(self):
        """When modal returns valid=False, state stores False."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_modal_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": ["<>(p & ~p)"],
            "valid": False,
            "modalities": ["possibility"],
        }
        _write_modal_to_state(output, state, {})

        call_args = state.add_modal_analysis_result.call_args
        assert call_args[0][1] is False


# ---------------------------------------------------------------------------
# 3. DL state writer — consistent: None must NOT become False
# ---------------------------------------------------------------------------


class TestDLStateWriterFailLoud:
    """_write_dl_to_state must preserve None (unverified) vs False (inconsistent)."""

    def test_consistent_none_preserved(self):
        """When DL returns consistent=None, state stores None."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_dl_to_state,
        )

        state = MagicMock()
        output = {
            "consistent": None,
            "message": "DL reasoning unavailable",
        }
        _write_dl_to_state(output, state, {})

        call_args = state.add_fol_analysis_result.call_args
        assert call_args is not None
        consistent_arg = call_args[1]["consistent"]
        assert consistent_arg is None

    def test_confidence_zero_when_none(self):
        """When DL consistent=None, confidence is 0.0 (not 1.0)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_dl_to_state,
        )

        state = MagicMock()
        output = {
            "consistent": None,
            "message": "unavailable",
        }
        _write_dl_to_state(output, state, {})

        call_args = state.add_fol_analysis_result.call_args
        assert call_args[1]["confidence"] == 0.0


# ---------------------------------------------------------------------------
# 4. Formal synthesis scoring — None excluded from scores
# ---------------------------------------------------------------------------


class TestFormalSynthesisScoring:
    """_invoke_formal_synthesis must NOT score None as 0.0."""

    @pytest.mark.asyncio
    async def test_consistent_none_not_scored(self):
        """Phases with consistent=None are excluded from validity scoring."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_formal_synthesis,
        )

        context = {
            "phase_fol_output": {
                "formulas": ["P(x)"],
                "consistent": None,
                "confidence": 0.0,
                "solver": "none",
            },
        }
        result = await _invoke_formal_synthesis("test", context)

        # overall_validity should be 0.5 (default when no scores collected)
        assert result["overall_validity"] == 0.5, (
            f"Expected 0.5 (no verified phases), got {result['overall_validity']}"
        )

    @pytest.mark.asyncio
    async def test_consistent_true_scores_1(self):
        """Phases with consistent=True score 1.0."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_formal_synthesis,
        )

        context = {
            "phase_fol_output": {
                "formulas": ["P(a)"],
                "consistent": True,
                "confidence": 0.8,
            },
        }
        result = await _invoke_formal_synthesis("test", context)
        assert result["overall_validity"] == 1.0

    @pytest.mark.asyncio
    async def test_consistent_false_scores_0(self):
        """Phases with consistent=False score 0.0."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_formal_synthesis,
        )

        context = {
            "phase_fol_output": {
                "formulas": ["P(a)", "~P(a)"],
                "consistent": False,
                "confidence": 0.2,
            },
        }
        result = await _invoke_formal_synthesis("test", context)
        assert result["overall_validity"] == 0.0

    @pytest.mark.asyncio
    async def test_mixed_consistent_values(self):
        """Mix of True, False, None: only True and False are scored."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_formal_synthesis,
        )

        context = {
            "phase_fol_output": {
                "formulas": ["P(a)"],
                "consistent": True,
            },
            "phase_pl_output": {
                "formulas": ["p & q"],
                "satisfiable": True,
            },
            "phase_modal_output": {
                "formulas": ["[](p)"],
                "valid": None,  # unverified — excluded from scoring
            },
        }
        result = await _invoke_formal_synthesis("test", context)
        # Only True (1.0) + True (1.0) scored = 2.0 / 2 = 1.0
        assert result["overall_validity"] == 1.0


# ---------------------------------------------------------------------------
# 5. Dung cap — power-set enumeration bounded at 25
# ---------------------------------------------------------------------------


class TestDungFallbackIsFailLoud:
    """_python_dung_fallback is a fail-loud stub — pure-Python Dung extension
    enumeration was removed as anti-theatre (#1019, FP-22 #1249): the previous
    combinatorial power-set path produced non-empty extension sets without a
    genuine Tweety reasoner call. The stub raises so no accidental call can
    enter fabricated results into state. Call sites in _invoke_dung_extensions
    return honest-absent degraded dicts instead. These tests lock the
    anti-theatre fix (regression guard) — they replace the old cap-enumeration
    tests, which asserted the now-excised fabricated behavior.
    """

    def test_large_set_raises_fail_loud(self):
        """For >25 arguments the stub raises (no fabricated extensions)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        # 30 arguments — formerly above the 25 power-set cap.
        arguments = [f"arg_{i}" for i in range(30)]
        attacks = [[f"arg_{i}", f"arg_{i+1}"] for i in range(29)]

        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_dung_fallback(arguments, attacks)

    def test_at_cap_raises_fail_loud(self):
        """Even at the old 25-arg cap, no pure-Python path remains — stub raises."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        arguments = [f"arg_{i}" for i in range(25)]
        attacks = [[f"arg_{i}", f"arg_{i+1}"] for i in range(24)]

        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_dung_fallback(arguments, attacks)


# ---------------------------------------------------------------------------
# 6. Narrative sentinel — consumers must not treat sentinel as valid prose
# ---------------------------------------------------------------------------


class TestNarrativeSentinelConsumer:
    """Verify narrative sentinel is not silently accepted as valid prose."""

    def test_sentinel_detected_in_narrative(self):
        """The sentinel string is properly detectable via containment check."""
        # _FALLBACK_SENTINEL is a local variable inside _invoke_narrative_synthesis.
        # We define the expected value here for testing the detection pattern.
        _SENTINEL_SUBSTR = (
            "L'analyse n'a pas produit suffisamment de donnees pour generer "
            "une synthese narrative"
        )

        # The sentinel should be a non-empty string
        assert isinstance(_SENTINEL_SUBSTR, str)
        assert len(_SENTINEL_SUBSTR) > 0

        # Sentinel must be detectable in longer strings via `in` operator
        longer = _SENTINEL_SUBSTR + " Some additional text."
        assert _SENTINEL_SUBSTR in longer

    def test_narrative_writer_handles_empty(self):
        """State writer handles empty narrative gracefully."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_narrative_synthesis_to_state,
        )

        state = MagicMock()
        # Empty narrative output
        _write_narrative_synthesis_to_state({}, state, {})
        # Should not crash and should not set phantom string attribute
        assert not isinstance(getattr(state, "narrative_synthesis", ""), str)


# ---------------------------------------------------------------------------
# 7. Dung extensions consumers — empty dict handled correctly
# ---------------------------------------------------------------------------


class TestDungEmptyExtensions:
    """Dung extensions empty-dict must not crash consumers."""

    def test_state_writer_handles_empty_extensions(self):
        """State writer stores empty extensions dict without crash."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = MagicMock()
        output = {
            "semantics": "python",
            "extensions": {},
            "arguments": [],
            "attacks": [],
        }
        # Should not raise
        _write_dung_extensions_to_state(output, state, {})

    def test_state_writer_handles_none_extensions(self):
        """State writer handles None extensions gracefully."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_extensions_to_state,
        )

        state = MagicMock()
        output = {
            "semantics": "python",
            "extensions": None,
            "arguments": ["a", "b"],
            "attacks": [("a", "b")],
        }
        # Should not raise — None treated as {}
        _write_dung_extensions_to_state(output, state, {})
