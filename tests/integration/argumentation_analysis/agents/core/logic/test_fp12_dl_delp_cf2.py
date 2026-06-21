"""FP-12 #1215 — DL/DeLP/CF2 wiring: DECIDE or honest fail-loud (REAL, no mock).

Three reasoners that *seemed* wired but never actually decided (the #1019
theater family, sibling of the modal/DL/DeLP bugs):

1. **DL ``is_consistent`` hardcoded True** — ``dl_handler`` computed
   ``reasoner.query(kb, ⊤)`` then ignored the result and unconditionally
   returned ``(True, "consistent")``. Worse than "degraded": a fabricated
   verdict. ``NaiveDlReasoner`` exposes only ``query`` (no ``isConsistent``,
   same gap as the modal reasoners #1212), so the deciding procedure is
   **bottom-entailment**: a KB is consistent iff it does NOT entail ⊥. Assert
   ``(witness: ⊥)`` and query — an inconsistent KB entails everything (incl. ⊥),
   a consistent one does not. Firsthand-verified (po-2025).

2. **DeLP fed raw prose to ``DelpParser``** — ``_invoke_delp`` defaulted
   ``program_text`` to ``input_text[:500]`` when no program was in context.
   DeLP syntax (facts / strict / defeasible rules) is not prose → guaranteed
   parse failure AND a corpus-text leak into the parser (privacy). Fix is
   subtraction: drop the raw-text default, fail-loud ``unavailable``.

3. **CF2 announced but class absent** — ``CF2Reasoner`` is NOT shipped in the
   vendored Tweety build (introspected firsthand: the FQN raises
   ClassNotFoundException in both 1.28 and 1.29; no SimpleCF2Reasoner /
   prover.* variant). Advertising cf2 as supported while the class is absent
   was a false promise. Honest gate-out: cf2 is removed from
   ``SEMANTICS_REASONERS`` → ``_get_reasoner("cf2")`` raises ``ValueError``
   (not a silent empty result dressed as "decided").

Privacy HARD: synthetic atoms only (``human``/``john``). 0 corpus content.
"""

import pytest

from argumentation_analysis.core.jvm_setup import initialize_jvm


@pytest.fixture(scope="module")
def tweety_bridge():
    """Start the JVM (idempotent) once and build a ``TweetyBridge`` whose
    initializer has all Tweety components loaded (DLHandler/AFHandler require
    ``is_jvm_ready()`` = JVM started AND classes loaded)."""
    initialize_jvm()
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    return TweetyBridge()


class TestDLDecidesViaBottomEntailment:
    """DL ``is_consistent`` must DECIDE via the real NaiveDlReasoner — the
    hardcoded-True theater is gone; the verdict comes from bottom-entailment."""

    def test_consistent_kb_decides_true(self, tweety_bridge):
        from argumentation_analysis.agents.core.logic.dl_handler import DLHandler

        handler = DLHandler(tweety_bridge.initializer)
        # KB: john is human (no contradiction) -> consistent.
        kb = handler._DlBeliefSet()
        john = handler._Individual("john")
        human = handler._AtomicConcept("human")
        kb.add(handler._ConceptAssertion(john, human))

        result, msg = handler.is_consistent(kb)
        assert (
            result is True
        ), f"Consistent DL KB must decide True; got ({result!r}, {msg!r})."
        assert "consistent" in msg.lower()

    def test_inconsistent_kb_decides_false(self, tweety_bridge):
        from argumentation_analysis.agents.core.logic.dl_handler import DLHandler

        handler = DLHandler(tweety_bridge.initializer)
        # KB: john is human AND john is ¬human -> john cannot be both -> inconsistent.
        kb = handler._DlBeliefSet()
        john = handler._Individual("john")
        human = handler._AtomicConcept("human")
        kb.add(handler._ConceptAssertion(john, human))
        kb.add(handler._ConceptAssertion(john, handler._Complement(human)))

        result, msg = handler.is_consistent(kb)
        assert result is False, (
            f"Inconsistent DL KB must decide False (previously hardcoded True); "
            f"got ({result!r}, {msg!r})."
        )
        assert "inconsistent" in msg.lower()


class TestDeLPNoRawTextFailLoud:
    """DeLP must NOT feed raw text to DelpParser. No program -> honest
    ``unavailable``, never a parse-failure-on-prose (correctness + privacy)."""

    async def test_no_program_returns_unavailable(self):
        from argumentation_analysis.orchestration.invoke_callables import _invoke_delp

        result = await _invoke_delp("some raw prose that is not a program", {})
        assert (
            result["status"] == "unavailable"
        ), f"No program in context must fail-loud unavailable; got {result!r}."
        assert "program" in result["message"].lower()

    async def test_raw_text_never_reaches_parser(self):
        """Privacy guard (#1215): the ``input_text[:500]`` default is gone — a
        raw corpus-like input must NOT be forwarded to the parser; it must be
        rejected upstream as ``unavailable``."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_delp

        secret = "SECRET_CORPUS_LEAK_" + "x" * 200
        result = await _invoke_delp(secret, {})
        assert result["status"] == "unavailable"
        # The raw input must not appear anywhere in the result (no leak).
        assert "SECRET_CORPUS_LEAK" not in str(result)

    async def test_explicit_program_is_forwarded(self):
        """Sanity: when a program IS supplied, the callable proceeds past the
        fail-loud guard (the handler may still raise on JVM issues, but the
        raw-text default no longer interferes)."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_delp

        # A minimal valid DeLP program (a strict fact). We only assert the
        # guard did not short-circuit: result is NOT the "unavailable" dict.
        try:
            result = await _invoke_delp(
                "", {"program": "bird(tweety).", "queries": ["bird(tweety)"]}
            )
        except RuntimeError:
            # JVM unavailable in this env is acceptable — the point is the
            # guard did not fire (which would return a dict, not raise).
            return
        assert result.get("status") != "unavailable" or "program" not in str(
            result.get("message", "")
        ), "An explicit program must not trigger the no-program fail-loud."


class TestCF2HonestGateOut:
    """CF2 is not shipped in the vendored Tweety build. The fix is honest
    gate-out (removed from SEMANTICS_REASONERS), not a silent empty result."""

    def test_cf2_not_advertised_as_supported(self):
        from argumentation_analysis.agents.core.logic.af_handler import (
            AFHandler,
            SEMANTICS_REASONERS,
        )

        assert "cf2" not in SEMANTICS_REASONERS
        assert "cf2" not in AFHandler.supported_semantics()
        # The other 10 are still there.
        assert len(SEMANTICS_REASONERS) == 10

    def test_cf2_request_raises_valueerror(self, tweety_bridge):
        """Asking for cf2 must fail loudly (ValueError), not silently produce
        an empty result dressed as 'decided'."""
        from argumentation_analysis.agents.core.logic.af_handler import AFHandler

        handler = AFHandler(tweety_bridge.initializer)
        with pytest.raises(ValueError, match="Unsupported semantics"):
            handler._get_reasoner("cf2")
