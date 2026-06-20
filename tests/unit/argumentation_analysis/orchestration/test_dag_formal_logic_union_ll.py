"""Tests for the DAG/sequential PL/FOL collapse fix (Track LL #705).

The sequential (DAG) ``spectacular``/``full`` workflows run an ``nl_to_logic``
phase whose whole-text formulas feed ``pl``/``fol``. Those formulas are complex
and frequently fail Tweety, and — critically — their mere presence used to
*short-circuit* the robust 2-pass coordinated generator (Pass 1 atom/signature
inventory → Pass 2 per-argument formulas). The conversational path wins on PL/FOL
precisely because it always runs that 2-pass; the DAG path lost to the zero-shot
baseline (PL 1/1/3, FOL 0/52/0, ``failed_phases=['fol']``) because it didn't.

These tests verify, with the LLM client and TweetyBridge mocked away (no real
API, no JVM), that:

  1. When upstream formulas are present (``context["formulas"]`` — the DAG case),
     ``_invoke_propositional_logic`` / ``_invoke_fol_reasoning`` STILL reach the
     2-pass generator (``_get_openai_client`` is called). Before #705 the upstream
     branch short-circuited and the generator was never invoked.
  2. The upstream formulas are UNIONED into the result rather than being the only
     source (additive, anti-pendulum: we add the robust generator, we don't cap
     the formal phases).
  3. The conversational path (no upstream) is unchanged — still reaches the 2-pass.
"""

from unittest.mock import patch

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod

_LONG_TEXT = "This is a sufficiently long source text for the formal phase. " * 8

_BRIDGE = "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"


class TestDagPlUnionsAndDoesNotShortCircuit:
    """#705: upstream PL formulas no longer skip the 2-pass; they are unioned."""

    async def test_upstream_formulas_still_reach_2pass(self):
        """FP-7 #1199: PL now fails loud (RuntimeError) when all Tweety solvers
        fail (FP-3 #1192/#1019), but the 2-pass generator is STILL reached before
        the solver step — preserving the #705 regression guard against
        short-circuiting. The graceful Python fallback was the theater removed
        by FP-3; we assert fail-loud + 2-pass-reached instead.
        """
        calls = {"client": 0}

        def _fake_client():
            calls["client"] += 1
            return (None, None)  # client unavailable → 2-pass body is a no-op

        with patch.object(
            mod, "_get_openai_client", side_effect=_fake_client
        ), patch(_BRIDGE, side_effect=RuntimeError("no JVM")):
            with pytest.raises(RuntimeError, match="Tweety solvers failed"):
                await mod._invoke_propositional_logic(
                    _LONG_TEXT, {"formulas": ["a", "b"]}
                )

        # Regression: before #705 the upstream branch short-circuited and the
        # generator was never reached — calls["client"] would be 0. The raise
        # happens AFTER the 2-pass, so the client was still called.
        assert calls["client"] >= 1

    async def test_upstream_nl_to_logic_translations_reach_2pass(self):
        """FP-7 #1199: same fail-loud + 2-pass-reached contract for the
        nl_to_logic upstream branch (#705).
        """
        calls = {"client": 0}

        def _fake_client():
            calls["client"] += 1
            return (None, None)

        context = {
            "phase_nl_to_logic_output": {
                "translations": [
                    {
                        "logic_type": "propositional",
                        "is_valid": True,
                        "formula": "p",
                        "original_text": "arg one",
                    }
                ]
            },
            "phase_extract_output": {"arguments": [{"text": "arg one"}]},
        }
        with patch.object(
            mod, "_get_openai_client", side_effect=_fake_client
        ), patch(_BRIDGE, side_effect=RuntimeError("no JVM")):
            with pytest.raises(RuntimeError, match="Tweety solvers failed"):
                await mod._invoke_propositional_logic(_LONG_TEXT, context)

        # The 2-pass generator was reached before the solver raised.
        assert calls["client"] >= 1


class TestDagFolUnionsAndDoesNotShortCircuit:
    """#705: upstream FOL formulas no longer skip the 2-pass; they are unioned."""

    async def test_upstream_formulas_still_reach_2pass(self):
        """FP-7 #1199: FOL reports honest absence (tri-state ``consistent=None``,
        ``solver="none"``) instead of the removed ``fallback="python"`` theater
        (FP-3 #1192/#1019). The #705 regression guard (2-pass reached, upstream
        formulas unioned) is preserved on the honest fail-loud return path.
        """
        calls = {"client": 0}

        def _fake_client():
            calls["client"] += 1
            return (None, None)

        with patch.object(
            mod, "_get_openai_client", side_effect=_fake_client
        ), patch(_BRIDGE, side_effect=RuntimeError("no JVM")):
            out = await mod._invoke_fol_reasoning(
                _LONG_TEXT, {"formulas": ["P(a)", "Q(b)"]}
            )

        # Regression: before #705 the upstream branch short-circuited and the
        # generator was never reached — calls["client"] would be 0.
        assert calls["client"] >= 1
        # Upstream formulas are unioned into the output, not dropped.
        assert "P(a)" in out["formulas"] and "Q(b)" in out["formulas"]
        # FP-3/#1019: no fabricated verdict — honest tri-state None + solver none.
        assert out.get("consistent") is None
        assert out.get("solver") == "none"


class TestConversationalPathUnchanged:
    """No upstream formulas → 2-pass still runs (HH conversational behaviour)."""

    async def test_pl_no_upstream_reaches_2pass(self):
        """FP-7 #1199: conversational path (no upstream) still reaches the 2-pass
        generator, then fails loud on Tweety absence (FP-3 #1192/#1019).
        """
        calls = {"client": 0}

        def _fake_client():
            calls["client"] += 1
            return (None, None)

        with patch.object(
            mod, "_get_openai_client", side_effect=_fake_client
        ), patch(_BRIDGE, side_effect=RuntimeError("no JVM")):
            with pytest.raises(RuntimeError, match="Tweety solvers failed"):
                await mod._invoke_propositional_logic(_LONG_TEXT, {})

        # The 2-pass generator was reached before the solver raised.
        assert calls["client"] >= 1
