"""#1759 — real arm of the bounded signature for modal consistency.

The degenerate controls (blocking ⇒ named red fast, slow-but-correct ⇒ green)
live in ``tests/unit/argumentation_analysis/agents/core/logic/
test_modal_consistency_bounded_signature.py`` and prove the WRAPPER mechanism.
This file points the same wrapper at the REAL end-to-end decision path —
the one measured parking in #1783:

    ModalLogicAgent._construct_modal_kb_from_json  (genuine builder, fp11 trick)
    -> TweetyBridge.check_consistency
    -> ModalHandler.is_modal_kb_consistent
    -> SimpleMlReasoner.query  (TWEETY, pure-Java — runs on CI everywhere)

Normally the query decides in well under a second: the test is GREEN and its
assertions on the verdict hold. If the #1783 park (thread parked in GC inside
``reasoner.query``) manifests, ``run_bounded`` raises ``QueryParked``: ONE named
red in ≤ ``BOUNDED_S``, with the parked thread's stack — and, unlike
``--timeout-method=thread``, the run and its junitxml survive. That is the
bounded, reproducible signature the dispatch asked for: observing the blockage
costs this single test, not a 20-min run killed by hand.

Privacy HARD: synthetic propositions only (``rain``/``wet``). 0 corpus content.
"""

import logging
import sys
import threading
import time
import traceback

import pytest

from argumentation_analysis.core.config import settings, ModalSolverChoice
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

# Discriminating bound: a legitimate 2-formula decision is sub-second (even on
# a cold JVM); anything holding longer than this is the parked shape, and the
# bound is far below the lane's own --timeout=900 so the REPORT survives.
BOUNDED_S = 120

CONSISTENT_KB_JSON = {
    "propositions": ["rain", "wet"],
    "modal_formulas": ["[](rain => wet)", "rain"],
}


class QueryParked(AssertionError):
    """Named red: the wrapped call did not return within its bound."""


def run_bounded(fn, *, timeout_s, label):
    """Same harness as the unit degenerate controls (kept self-contained —
    cross-test-tree imports are fragile under differing rootdir configs)."""
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


@pytest.fixture(scope="module")
def modal_bridge():
    """Start the JVM (idempotent) once and build a real ``TweetyBridge``."""
    initialize_jvm()
    return TweetyBridge()


@pytest.fixture(scope="module")
def modal_kb_builder():
    """``ModalLogicAgent`` stub running the genuine ``_construct_modal_kb_from_json``
    code (``__new__`` bypasses the LLM-backed ``__init__`` the builder never
    uses — the fp11 trick, see that file's docstring)."""
    builder = ModalLogicAgent.__new__(ModalLogicAgent)
    builder._agent_logger = logging.getLogger("BoundedSignatureKBBuilder")
    return builder


@pytest.fixture
def tweety_solver():
    """Force the pure-Java default — the always-available, always-deciding
    modal path (no external binary). Pinning ``modal_solver`` alone is NOT
    enough (#1339): when ``modal_prefer_spass_when_available`` is on and a
    vendored SPASS binary is detected (local dev machines), the resolver
    upgrades TWEETY to SPASS and the verdict message names "spass"."""
    previous_solver = settings.modal_solver
    previous_prefer = settings.modal_prefer_spass_when_available
    settings.modal_solver = ModalSolverChoice.TWEETY
    settings.modal_prefer_spass_when_available = False
    try:
        yield
    finally:
        settings.modal_solver = previous_solver
        settings.modal_prefer_spass_when_available = previous_prefer


class TestBoundedSignatureRealArm:
    def test_consistent_kb_decides_within_bound(
        self, modal_bridge, modal_kb_builder, tweety_solver
    ):
        """Lent-mais-correct ⇒ vert : le chemin réel décide sous la borne et le
        verdict authentique (True, tweety) passe au travers du wrapper."""
        kb = modal_kb_builder._construct_modal_kb_from_json(CONSISTENT_KB_JSON)
        start = time.monotonic()
        is_consistent, msg = run_bounded(
            lambda: modal_bridge.check_consistency(kb, "K"),
            timeout_s=BOUNDED_S,
            label="check_consistency(K) -> is_modal_kb_consistent",
        )
        elapsed = time.monotonic() - start
        assert is_consistent is True, (
            f"Consistent modal KB must report consistent; "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert "tweety" in msg.lower()
        # The bound discriminates: green here means the decision returned on
        # its own — never that the bound "passed" a parked call.
        assert elapsed < BOUNDED_S
