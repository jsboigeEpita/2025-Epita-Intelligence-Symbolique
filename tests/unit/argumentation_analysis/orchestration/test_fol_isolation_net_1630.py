"""#1630 — FOL per-formula isolation net: reachable AND effective.

Two independent defects had made the net dead code in
``_invoke_fol_reasoning`` (invoke_callables.py):

  1. **Unreachable on the real failure mode.** The handler
     (``fol_handler.check_consistency``, FP-3 #1192) signals a parse / reasoner
     failure by RETURNING ``(None, "Degraded ...")`` — not by raising. The
     combined check therefore completes without exception, so the ``except``
     isolation branch never armed. The net only triggered on genuine Tweety
     *exceptions*, never on the None-verdict that is the actual degraded signal.
  2. **Empty when it ran.** The per-formula loop triaged on absence-of-exception
     (``try ... valid_formulas.append``), which accepted every formula under the
     None-return mode (the handler returns, it doesn't raise) →
     ``valid_formulas == formulas`` → the net caught nothing.

The fix:
  - trigger the net on the combined-check None-verdict too (not only on a raise);
  - triage on the RETURNED verdict — None ⇒ the poison, True/False ⇒ kept;
  - name the rejected formulas in ``fol_metrics`` (DoD item 4), not only at
    ``logger.debug``.

Anti-pendules (coordinator dispatch #1630):
  - the handler is NOT made to raise — the #1192 tri-state contract is correct;
    it is the downstream guard that must read the returned value;
  - the survivors' combined check passes the tri-state through (FP-6 #1197):
    parsing ≠ deciding, never fabricate True from parse-success;
  - the existing ``except`` branch stays (DoD item 2): both modes coexist.

Falsifiability — two degenerate substitutions with disjoint kill-sets:
  - Sub A (defect 2): the per-formula triage reverts to absence-of-exception
    (accept on any non-raising return). Kills the naming/survivors/exception
    tests; SPARES the pure reachability test (the loop still runs).
  - Sub B (defect 1): the None-trigger is removed. Kills the reachability +
    naming/survivors tests (isolation never runs on the None mode); SPARES the
    exception-path test (the ``except`` branch is untouched).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

TWEETY_BRIDGE_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
)

# Opaque, deterministic atoms. The poison is a distinctive predicate the mock can
# match inside the belief-set string; it models a formula the reasoner cannot
# parse (returns None per #1192) while the genuine formulas parse fine.
_GOOD_FORMULAS = [
    "forall X: (Human(X) => Mortal(X))",
    "forall X: (Cat(X) => Animal(X))",
]
_POISON_FORMULA = "BadPoison(X)"
_POISON_TOKEN = "BadPoison"


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _ctx(formulas: list) -> dict:
    """Context carrying pre-formed FOL formulas via context['formulas'] (unioned
    into the belief set, bypassing NL translation)."""
    return {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": formulas,
        "_state_object": None,
    }


def _verdict_reject_poison(belief_set_str: str, _logic_type: str):
    """Models the #1192 degraded signal: the poison (single or in a batch)
    returns a None verdict — the reasoner could not compute; the genuine
    formulas return a definite True verdict."""
    if _POISON_TOKEN in belief_set_str:
        return (None, f"Degraded: parse error on {_POISON_TOKEN} (#1192)")
    return (True, "FOL consistency check: consistent.")


def _combined_raises_poison_none(belief_set_str: str, _logic_type: str):
    """Models a genuine Tweety EXCEPTION on the combined batch (it cannot reason
    about the full set with the poison), while the poison ALONE returns the #1192
    None-verdict and the genuine formulas return True. This exercises the except
    branch with a poison whose individual failure mode is the None-return, so the
    per-formula triage (defect 2) — not only the per-formula except — decides its
    fate."""
    if _POISON_TOKEN in belief_set_str:
        # Combined batch (genuine formulas + poison) → genuine raise → except.
        if "Human" in belief_set_str or "Cat" in belief_set_str:
            raise RuntimeError(
                f"Tweety parse error on combined batch with {_POISON_TOKEN}"
            )
        # Single poison → None verdict (#1192 degraded, not a raise).
        return (None, f"Degraded: {_POISON_TOKEN} (#1192)")
    return (True, "FOL consistency check: consistent.")


# ---------------------------------------------------------------------------
# DoD item 1 — reachability: the None-verdict reaches the net
# ---------------------------------------------------------------------------


class TestNoneVerdictReachesIsolation:
    """Pre-fix the combined None-verdict fell through to the silent 'unverified'
    main return without ever running isolation (the handler returns None, it
    doesn't raise → the except never armed). Post-fix the None-verdict REACHES
    the net."""

    def test_isolation_reached_on_combined_none(self):
        """Every formula returns None individually (total reasoner failure).
        The reachability signal: ``isolation_rejected_count`` is present in the
        metrics — isolation ran. (Sub B, which removes the None-trigger, makes
        this key absent → this test fails; Sub A spares it, the loop still
        runs.)"""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _ctx(list(_GOOD_FORMULAS))
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (
            None,
            "Degraded: reasoner could not compute (#1192)",
        )
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        metrics = result["fol_metrics"]
        # Reachability: isolation ran and recorded a rejection count. Pre-fix
        # (no None-trigger) this key is absent.
        assert "isolation_rejected_count" in metrics
        # No fabricated verdict: combined None ⇒ unverified, never True (#1019).
        assert result["consistent"] is None
        assert result["fol_status"] == "unverified"


# ---------------------------------------------------------------------------
# DoD item 4 — rejected formulas named in the metrics artefact
# ---------------------------------------------------------------------------


class TestRejectedFormulasNamedInMetrics:
    """The rejected formulas must be NAMED in fol_metrics (not only at
    logger.debug), so a parse-poison is diagnosable without a re-run."""

    def test_all_rejected_formulas_listed_by_name(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _ctx(list(_GOOD_FORMULAS))
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (
            None,
            "Degraded: reasoner could not compute (#1192)",
        )
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        metrics = result["fol_metrics"]
        # Every injected formula was rejected (None verdict) and named.
        assert metrics["isolation_rejected_count"] == len(_GOOD_FORMULAS)
        rejected = metrics["rejected_formulas"]
        assert isinstance(rejected, list)
        assert len(rejected) == len(_GOOD_FORMULAS)
        # The names survive sanitization recognizably (Human / Cat predicates).
        rejected_text = " ".join(rejected)
        assert "Human" in rejected_text
        assert "Cat" in rejected_text


# ---------------------------------------------------------------------------
# DoD item 3 — N-1 survive + combined verdict (synthetic, no corpus)
# ---------------------------------------------------------------------------


class TestPoisonIsolatedSurvivorsCarryVerdict:
    """A KB of N formulas whose combined belief set returns None (the batch
    cannot be reasoned about) but where only ONE formula is the poison: the
    N-1 genuine formulas survive and carry a real combined verdict."""

    def test_poison_rejected_and_survivors_decided(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        # N = 2 genuine + 1 poison = 3; expect N-1 = 2 survivors.
        context = _ctx(list(_GOOD_FORMULAS) + [_POISON_FORMULA])
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.side_effect = _verdict_reject_poison
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        # DoD item 3: N-1 survive, the poison is rejected.
        assert result["isolation_retry"] is True
        assert len(result["formulas"]) == len(_GOOD_FORMULAS)
        assert not any(_POISON_TOKEN in f for f in result["formulas"])
        # A real combined verdict on the survivors (FP-6 #1197: decided, not
        # fabricated from parse-success).
        assert result["fol_status"] == "decided"
        assert result["consistent"] is True
        # DoD item 4: the poison is named in the metrics.
        rejected = result["fol_metrics"]["rejected_formulas"]
        assert any(_POISON_TOKEN in f for f in rejected)
        assert result["fol_metrics"]["isolation_survivors"] == len(_GOOD_FORMULAS)


# ---------------------------------------------------------------------------
# DoD item 2 — the except branch stays reachable AND effective
# ---------------------------------------------------------------------------


class TestExceptionPathStillIsolates:
    """The existing except branch (genuine Tweety exception on the combined
    check) still isolates the survivors after the refactor — both failure modes
    coexist, the except is NOT removed."""

    def test_combined_exception_isolates_survivors(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        # The combined check raises (genuine Tweety exception on the full batch);
        # the poison alone returns the #1192 None-verdict; the genuine formulas
        # parse and are consistent. So the poison's fate in the except branch is
        # decided by the per-formula VERDICT triage (defect 2), not by a raise.
        context = _ctx(list(_GOOD_FORMULAS) + [_POISON_FORMULA])
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.side_effect = _combined_raises_poison_none
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = _run(_invoke_fol_reasoning("text", context))

        # The except branch isolated the survivors — same contract as the
        # None-trigger path, reached via a genuine exception instead.
        assert result["isolation_retry"] is True
        assert len(result["formulas"]) == len(_GOOD_FORMULAS)
        assert not any(_POISON_TOKEN in f for f in result["formulas"])
        assert result["fol_status"] == "decided"
        assert result["consistent"] is True
