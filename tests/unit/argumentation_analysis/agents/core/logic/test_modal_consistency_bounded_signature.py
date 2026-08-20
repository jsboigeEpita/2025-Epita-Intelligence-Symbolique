"""#1759 — bounded signature for ``ModalHandler.is_modal_kb_consistent``.

Dispatch R835 volet 2. #1783 measured a whole-tree ``tests/integration`` run
dying at ~48% with a thread parked in GC inside
``modal_handler.py`` ``reasoner.query`` — and observing it costs a ~20 min run
killed by hand. The probe posted on #1759 (issuecomment-5354806466) showed why
``--timeout-method=thread`` (the only pytest-timeout method on Windows) is not
the answer for a *named* red: it aborts the whole run, the junitxml is lost and
subsequent tests never execute.

This file carries the DEGENERATE CONTROLS for the bounded wrapper
(``run_bounded``) used by the real-arm harness in
``tests/integration/argumentation_analysis/agents/core/logic/
test_modal_consistency_bounded_signature.py``:

* a BLOCKING reasoner must convert into a NAMED failure in bounded time,
  carrying the parked thread's stack (which names ``modal_handler.py``'s
  ``reasoner.query`` frame — the measured park site), and
* a SLOW-BUT-CORRECT reasoner must stay GREEN and return its real verdict.

Both must hold, or the bound does not discriminate blocked from slow (#1759
anti-pendule: 3 states, not 2). The wrapper OBSERVES the blockage — it does not
repair it (the dispatch forbids "fixing" ``is_modal_kb_consistent`` here).
"""

import sys
import threading
import time
import traceback
from types import SimpleNamespace
from unittest import mock

import pytest

from argumentation_analysis.agents.core.logic import modal_handler as mh_module
from argumentation_analysis.agents.core.logic.modal_handler import ModalHandler


class QueryParked(AssertionError):
    """Named red: the wrapped call did not return within its bound."""


def run_bounded(fn, *, timeout_s, label):
    """Run ``fn`` in a daemon thread; named-red if it outlives ``timeout_s``.

    Returns ``fn``'s result, or re-raises its exception. If the worker is still
    alive after ``timeout_s`` seconds, raises ``QueryParked`` carrying the
    thread's CURRENT stack — the parked frame is the diagnostic. Unlike
    pytest-timeout's thread method this fails ONE test by name and leaves the
    run (and its report) alive: that is the point of the harness.
    """
    outcome = {}

    def _target():
        try:
            outcome["value"] = fn()
        except BaseException as exc:  # diagnostic harness: capture everything
            outcome["exc"] = exc

    worker = threading.Thread(target=_target, daemon=True, name=f"bounded:{label}")
    worker.start()
    worker.join(timeout_s)
    if worker.is_alive():
        frame = sys._current_frames()[worker.ident]
        stack = "".join(traceback.format_stack(frame))
        raise QueryParked(
            f"{label} did not return within {timeout_s}s (parked) — bounded "
            f"signature #1759. Parked thread stack:\n{stack}"
        )
    if "exc" in outcome:
        raise outcome["exc"]
    return outcome["value"]


def _make_handler(monkeypatch, reasoner):
    """Real ``ModalHandler`` over a stub initializer — no JVM needed.

    The production path stays genuine up to the reasoner call: solver
    resolution, normalization, StringReader/parseBeliefBase, contradiction
    probe, then ``reasoner.query`` — the frame the wrapper's named red must
    show when a reasoner blocks.
    """
    initializer = mock.MagicMock()
    initializer.get_modal_parser.return_value = mock.MagicMock()
    initializer.get_modal_reasoner.return_value = reasoner
    handler = ModalHandler(initializer_instance=initializer)
    monkeypatch.setattr(handler, "_get_active_reasoner", lambda: reasoner)
    monkeypatch.setattr(
        handler, "_build_contradiction_probe", lambda belief_set: object()
    )
    # modal_handler touches jpype.JClass for StringReader and catches
    # jpype.JException; both are stubbed at the MODULE's reference (scoped to
    # modal_handler, restored by monkeypatch — never a global-module patch).
    monkeypatch.setattr(
        mh_module,
        "jpype",
        SimpleNamespace(
            JClass=lambda name: lambda payload: (name, payload),
            JException=type("JException", (Exception,), {}),
        ),
    )
    return handler


class TestBoundedWrapperDegenerateControls:
    """Substitution dégénérée, the two cases the DoD demands."""

    def test_blocking_query_converts_to_named_red_in_bounded_time(self, monkeypatch):
        """Blocked ⇒ rouge NOMMÉ en temps court (pas un run tué à la main)."""

        class BlockingReasoner:
            def query(self, belief_set, formula):
                time.sleep(600)  # degenerate blocker: never returns, never raises

        handler = _make_handler(monkeypatch, BlockingReasoner())
        start = time.monotonic()
        with pytest.raises(QueryParked) as excinfo:
            run_bounded(
                lambda: handler.is_modal_kb_consistent("[](p => q) & p"),
                timeout_s=3,
                label="is_modal_kb_consistent",
            )
        elapsed = time.monotonic() - start
        message = str(excinfo.value)
        assert "is_modal_kb_consistent" in message
        assert "did not return within 3s" in message
        # Bounded: the red arrives in seconds, not after the blocker's 600s.
        assert elapsed < 15
        # The named red carries the parked stack, which names the production
        # park site measured in #1783: modal_handler's reasoner.query call.
        assert "modal_handler" in message
        assert "reasoner.query" in message

    def test_slow_but_correct_query_stays_green_and_decides(self, monkeypatch):
        """Lent-mais-correct ⇒ VERT : la borne rend le verdict réel, pas un rouge."""

        class SlowReasoner:
            def query(self, belief_set, formula):
                time.sleep(2.0)  # slow but terminates with a decision
                return False  # does not entail contradiction -> consistent

        handler = _make_handler(monkeypatch, SlowReasoner())
        is_consistent, message = run_bounded(
            lambda: handler.is_modal_kb_consistent("[](p => q) & p"),
            timeout_s=30,
            label="is_modal_kb_consistent",
        )
        assert is_consistent is True  # tri-state #1636: decided True, not None
        assert "consistent" in message

    def test_wrapper_propagates_the_real_exception(self):
        """The harness re-raises fn's exception — it never swallows failures."""

        def _boom():
            raise ZeroDivisionError("boom")

        with pytest.raises(ZeroDivisionError, match="boom"):
            run_bounded(_boom, timeout_s=5, label="boom")
