"""#1645 — bipolar invoke distinguishes JVM-absent (honest-absent) from
handler-failure (fail loud with the real cause). Three states, never two.

Pre-fix ``_invoke_bipolar`` (invoke_callables.py l.3591) had TWO defects of the
#1634 family, both flagged in the coordinator's review of the #1645 checkpoint:

  1. **Diagnostic fabricated.** The ``except Exception`` caught *everything* —
     ``ImportError``, ``TypeError``, a real Tweety reasoning error, or the JVM
     simply being absent — and relabeled all of it
     ``"JVM/Tweety required, install JVM"``. Three genuinely different
     situations (no JVM / handler broken / analysis failed) were made
     indistinguishable downstream, always toward the most reassuring reading
     ("it's the environment"). The cause was *rewritten*, not reported.
  2. **The message contradicted the flow.** It announced
     ``"Reporting unverified status"`` (i.e. "I continue and signal") and the
     very next line ``raise``d — the message documented an intent it abandoned.

The fix introduces THREE states:
  - JVM absent (``jpype.isJVMStarted() is False``) ⇒ honest-absent: return a
    degraded dict (``extensions: None``, tri-state), the phase continues. Mirrors
    ``_invoke_sat``'s solver-absence boundary (l.4045).
  - JVM up + the handler/analysis raises ⇒ fail loud with the REAL cause
    (preserved via ``raise ... from e``), never relabeled "JVM required".

Anti-pendule (coordinator DoD): do NOT swap the raise for a silent ``return {}``
— that would trade this defect for its mirror (#1019: a crash turned into a mute
session). Three states, never two; honest-absent on one side, fail-loud on the
other.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BRIDGE_BIPOLAR = (
    "argumentation_analysis.agents.core.logic.bipolar_handler.BipolarHandler"
)

_FABRICATED = "JVM/Tweety required"  # the old relabeled diagnostic — must be GONE
_INSTALL_HINT = "Install JVM"  # likewise


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _ctx() -> dict:
    """Minimal context reaching the BipolarHandler construction."""
    return {"arguments": ["arg_A", "arg_B"], "supports": [], "attacks": []}


# ---------------------------------------------------------------------------
# State 1 — JVM absent ⇒ honest-absent degraded dict (phase continues)
# ---------------------------------------------------------------------------


class TestJvmAbsentIsHonestAbsent:
    """When the JVM is not started, bipolar returns a degraded dict instead of
    raising — the phase continues, the axis is recorded absent, no verdict is
    fabricated (#1019)."""

    def test_returns_dict_not_raises(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_bipolar,
        )

        # BipolarHandler() construct + JClass would raise with no JVM; patch the
        # handler to raise so the except path is exercised, AND force
        # isJVMStarted False so the fix routes to honest-absent.
        with patch(_BRIDGE_BIPOLAR, side_effect=RuntimeError("no JVM")), patch(
            "jpype.isJVMStarted", return_value=False
        ):
            result = _run(_invoke_bipolar("text", _ctx()))

        assert isinstance(result, dict)
        assert result.get("degraded") is True
        assert result.get("absent_reason") == "jvm_not_started"
        # tri-state None = not computed, never a fabricated empty extension set
        # (which would read as "consistent sur vide", #1019).
        assert result.get("extensions") is None

    def test_absent_dict_carries_no_fabricated_diagnostic(self):
        """The honest-absent path must not relabel the cause as 'JVM required' —
        it records the real underlying signal in ``error``."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_bipolar,
        )

        with patch(_BRIDGE_BIPOLAR, side_effect=RuntimeError("no JVM")), patch(
            "jpype.isJVMStarted", return_value=False
        ):
            result = _run(_invoke_bipolar("text", _ctx()))

        # The fabricated relabeling of the old code is gone from this path.
        assert _FABRICATED not in result.get("message", "")
        assert _INSTALL_HINT not in result.get("message", "")
        # The REAL signal is preserved (not rewritten to "environment gap").
        assert "no JVM" in result.get("error", "")


# ---------------------------------------------------------------------------
# State 2 — JVM up + handler/analysis failure ⇒ fail loud with the REAL cause
# ---------------------------------------------------------------------------


class TestJvmUpHandlerFailureFailsLoudRealCause:
    """When the JVM is up but the handler/analysis raises, the failure is ours,
    not the environment's. Fail loud with the real cause; do NOT relabel it
    'JVM/Tweety required' (that fabrication was the #1634 defect)."""

    def test_raises_with_real_cause_not_relabeled(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_bipolar,
        )

        # A TypeError inside the analysis with the JVM up — a genuine code bug,
        # nothing to do with a missing JVM.
        real_cause = TypeError("bad argument shape in analyze")
        mock_handler = MagicMock()
        mock_handler.analyze_bipolar_framework.side_effect = real_cause
        with patch(_BRIDGE_BIPOLAR, return_value=mock_handler), patch(
            "jpype.isJVMStarted", return_value=True
        ):
            with pytest.raises(RuntimeError) as exc_info:
                _run(_invoke_bipolar("text", _ctx()))

        msg = str(exc_info.value)
        # The REAL cause is named (type + message), preserved via `from e`.
        assert "TypeError" in msg
        assert "bad argument shape in analyze" in msg
        # The fabricated environment-relabeled diagnostic is GONE.
        assert _FABRICATED not in msg
        assert _INSTALL_HINT not in msg
        # The chained original exception is preserved (not swallowed).
        assert exc_info.value.__cause__ is real_cause

    def test_real_cause_not_reassuring_env_label(self):
        """A Tweety reasoning error (JVM up) must surface as a reasoning error,
        not as 'install a JVM'."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_bipolar,
        )

        mock_handler = MagicMock()
        mock_handler.analyze_bipolar_framework.side_effect = ValueError(
            "Tweety rejected the support relation"
        )
        with patch(_BRIDGE_BIPOLAR, return_value=mock_handler), patch(
            "jpype.isJVMStarted", return_value=True
        ):
            with pytest.raises(RuntimeError) as exc_info:
                _run(_invoke_bipolar("text", _ctx()))

        assert "Tweety rejected the support relation" in str(exc_info.value)
        # Crucially, it must NOT tell the user to install a JVM — the JVM is up.
        assert _INSTALL_HINT not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Relation — translator's supports must survive the degraded branch to the writer
# ---------------------------------------------------------------------------


class TestTranslatorWorkSurvivesDegradedState:
    """When the translator produced supports but the JVM is absent, the degraded
    dict MUST echo those supports so ``_write_bipolar_to_state`` persists them.

    Pre-fix the degraded branch returned ``"supports": []`` — the relation the
    translator had just established (translation needs NO JVM) was erased at the
    exact moment of writing. ``supports`` is the ONLY non-empty payload of the
    two mode-3 axes on the 8 real artefacts, and it is exactly what
    ``_write_bipolar_to_state`` (state_writers.py l.823) and the #1667 presence
    channel read FROM the result dict. This test pins the relation
    translator → handler-skip → writer so the echo cannot silently re-regress.
    """

    def test_writer_persists_translator_supports_not_empty(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )
        from argumentation_analysis.orchestration.state_writers import (
            _write_bipolar_to_state,
        )

        # The translator runs BEFORE the try (no JVM needed) and produces 2
        # genuine support pairs.
        translator_outcome = MagicMock()
        translator_outcome.relations = [
            ("corpus_A", "prop_1"),
            ("corpus_B", "prop_2"),
        ]
        translator_outcome.cause = "ok"
        translator_outcome.error = ""

        # ctx WITHOUT supports ⇒ _invoke_bipolar calls the translator itself.
        ctx = {"arguments": ["corpus_A", "corpus_B"]}

        with patch(
            "argumentation_analysis.orchestration.structured_arg_translator.translate_to_bipolar_supports",
            new=AsyncMock(return_value=translator_outcome),
        ), patch(
            "argumentation_analysis.core.jvm_setup.is_jvm_started",
            return_value=False,
        ), patch(
            _BRIDGE_BIPOLAR,
            side_effect=RuntimeError("JVM absent: BipolarHandler ctor failed"),
        ):
            output = _run(_invoke_bipolar("opaque text", ctx))

        # Degraded dict, supports echoed as 2 pairs — NOT zeroed to [].
        assert output["degraded"] is True
        assert output["extensions"] is None  # tri-state, Dung reasoning skipped
        assert output["supports"] == [
            ["corpus_A", "prop_1"],
            ["corpus_B", "prop_2"],
        ]

        # The writer reads supports FROM the dict → it must persist the 2 pairs.
        state = MagicMock()
        with patch(
            "argumentation_analysis.orchestration.state_writers._record_structured_arg_status"
        ):
            _write_bipolar_to_state(output, state, ctx)

        state.add_bipolar_result.assert_called_once()
        call_args = state.add_bipolar_result.call_args.args
        # signature: add_bipolar_result(fw_type, arguments, supports)
        persisted_supports = call_args[2]
        assert persisted_supports == [
            ["corpus_A", "prop_1"],
            ["corpus_B", "prop_2"],
        ], "writer must persist the translator's supports, not []"

