"""FP-6 #1197 — FOL invoke-callable must propagate the handler's fail-loud tri-state.

FP-3 (#1192/#1195) made the FOL *handler* (``fol_handler.check_consistency``)
return ``None`` on reasoner OOM / failure — an honest "could not compute". But the
*invoke callable* ``_invoke_fol_reasoning`` re-castrated that honesty one layer up:

  - main path:  ``"consistent": bool(is_consistent)`` → ``bool(None) == False``
                fabricated a definite "KB is inconsistent" verdict (confidence 0.4);
  - isolation:  hardcoded ``"consistent": True`` after only checking each formula
                *parses* — never a consistency check on the combined KB.

This is the R405 "determinization is structural" pattern: théâtre killed at the
handler instantly regrows above it. These tests pin the tri-state contract so the
fail-loud ``None`` reaches the state unchanged (and is never fabricated into a
verdict). The LLM client is mocked away (no API) and the TweetyBridge is mocked
(no JVM) — the formulas are injected via ``context["formulas"]`` (the DAG path).
"""

from unittest.mock import MagicMock, patch

import argumentation_analysis.orchestration.invoke_callables as mod

_LONG_TEXT = "This is a sufficiently long source text for the FOL formal phase. " * 8

_BRIDGE = "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"


def _no_llm_client():
    """Client unavailable → 2-pass generator is a no-op; KB comes from context."""
    return (None, None)


class TestFolFailLoudTriState:
    """#1197: the handler's None/True/False tri-state must survive the invoke callable."""

    async def test_handler_none_propagates_as_none_not_false(self):
        """Reasoner returns None (OOM/degraded) ⇒ output consistent=None, confidence=0.0.

        Regression: before FP-6, ``bool(None)`` fabricated ``consistent=False`` and
        ``confidence=0.4`` — a reader would see "FOL decided the KB is inconsistent"
        when in truth FOL could not compute a verdict.
        """
        bridge = MagicMock()
        # The FP-3 handler returns (None, msg) when the reasoner OOMs / fails.
        bridge.check_consistency.return_value = (None, "OutOfMemoryError → degraded")

        with patch.object(mod, "_get_openai_client", side_effect=_no_llm_client), patch(
            _BRIDGE, return_value=bridge
        ):
            out = await mod._invoke_fol_reasoning(
                _LONG_TEXT,
                {"formulas": ["Human(socrates)", "Mortal(socrates)"]},
            )

        assert out["consistent"] is None, "None must not be coerced to False"
        assert out["confidence"] == 0.0, "unverified ⇒ confidence 0.0, not 0.4"

    async def test_handler_true_maps_to_consistent_true(self):
        """A real positive verdict is preserved (True ⇒ confidence 0.8)."""
        bridge = MagicMock()
        bridge.check_consistency.return_value = (True, "consistent")

        with patch.object(mod, "_get_openai_client", side_effect=_no_llm_client), patch(
            _BRIDGE, return_value=bridge
        ):
            out = await mod._invoke_fol_reasoning(
                _LONG_TEXT,
                {"formulas": ["Human(socrates)", "Mortal(socrates)"]},
            )

        assert out["consistent"] is True
        assert out["confidence"] == 0.8

    async def test_handler_false_is_a_real_inconsistency_verdict(self):
        """A real negative verdict is preserved and distinguishable from None."""
        bridge = MagicMock()
        bridge.check_consistency.return_value = (False, "inconsistent")

        with patch.object(mod, "_get_openai_client", side_effect=_no_llm_client), patch(
            _BRIDGE, return_value=bridge
        ):
            out = await mod._invoke_fol_reasoning(
                _LONG_TEXT,
                {"formulas": ["P(a)", "!P(a)"]},
            )

        assert out["consistent"] is False
        assert out["confidence"] == 0.4

    async def test_isolation_retry_does_not_fabricate_true(self):
        """When the batch check raises, the per-formula isolation path must run a real
        combined consistency check — not hardcode ``consistent: True`` from parse-success.

        Here the first batch ``check_consistency`` raises (forcing the isolation
        branch); per-formula parse checks succeed; the combined re-check returns the
        degraded ``None``. Output must be ``consistent=None``, never the old ``True``.
        """
        bridge = MagicMock()
        calls = {"n": 0}

        def _check(belief_set, logic_type):
            calls["n"] += 1
            if calls["n"] == 1:
                # First (batch) call raises → drives the except-isolation branch.
                raise RuntimeError("batch parse failed")
            # Per-formula parse checks + final combined re-check.
            # Return the degraded tri-state for the combined re-check.
            return (None, "combined degraded")

        bridge.check_consistency.side_effect = _check

        with patch.object(mod, "_get_openai_client", side_effect=_no_llm_client), patch(
            _BRIDGE, return_value=bridge
        ):
            out = await mod._invoke_fol_reasoning(
                _LONG_TEXT,
                {"formulas": ["Human(socrates)", "Mortal(socrates)"]},
            )

        assert out.get("isolation_retry") is True, "expected the isolation branch"
        assert out["consistent"] is None, "isolation must not fabricate True"
        assert out["confidence"] == 0.0
