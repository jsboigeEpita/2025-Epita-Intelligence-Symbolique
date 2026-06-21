"""Real (non-mocked) modal consistency integration test — #1205 / #1212.

Two firsthand findings (ai-01, 2026-06-21) reshaped this test from po-2023's
original SPASS-forced draft:

1. **No modal reasoner exposes ``isConsistent``.** Both ``SimpleMlReasoner`` and
   ``SPASSMlReasoner`` only expose ``query``/``queryProof`` (verified via
   ``getMethods()``). ``ModalHandler.is_modal_kb_consistent`` called the
   non-existent ``isConsistent`` → it never decided; fully-mocked unit tests
   masked it (formal theater, modal side of the #1196/#1202 regression class).
   Fixed (#1205): query-based consistency (KB inconsistent iff it entails a
   contradiction ``atom && !atom``).

2. **The vendored ``SPASS.exe`` cannot run here.** It is a GUI/elevation build
   (``CreateProcess error=740``, ``isInstalled()==False``), not a runnable CLI
   theorem prover. So a SPASS-forced verdict is impossible on ai-01 — forcing
   it and asserting a boolean would be re-theater (it would in fact return the
   honest ``None``).

So the **real anti-theater guard** is the DEFAULT modal reasoner
(``SimpleMlReasoner``, pure-Java, query-based): it DECIDES consistency with NO
external binary, hence it RUNS on CI everywhere — not "green by skipping". The
SPASS-specific test is gated on ``isInstalled()`` and skips honestly where SPASS
is not a runnable CLI build (ai-01's GUI binary), so it never green-by-skips a
claim it cannot back.

Production path under test:
``TweetyBridge.check_consistency(bs, "K")`` → ``ModalHandler.is_modal_kb_consistent``
→ active reasoner ``.query(beliefSet, contradiction)``.

Privacy HARD: synthetic propositions only (``Rain``/``Wet``), 0 corpus.
"""

import pytest

from argumentation_analysis.core.config import settings, ModalSolverChoice
from argumentation_analysis.core.jvm_setup import EXTERNAL_TOOL_PATHS, initialize_jvm

# The production path under test.
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

# Valid Tweety MlParser syntax (firsthand-verified): predicates are declared with
# ``type(Pred)`` (0-ary propositions here); modal operators are ``[]``/``<>``.
# An inconsistent KB: a proposition and its negation.
INCONSISTENT_KB = "type(Rain)\n\nRain\n!Rain\n"
# A consistent modal KB exercising the necessity operator: []( Rain => Wet ) and Rain.
CONSISTENT_KB = "type(Rain)\ntype(Wet)\n\n[](Rain => Wet)\nRain\n"


def _spass_runnable() -> bool:
    """True iff the SPASS binary is registered AND actually launchable.

    ``EXTERNAL_TOOL_PATHS['spass']`` being set is NOT enough: the vendored
    ``SPASS.exe`` on ai-01 is a GUI/elevation build that fails to launch
    (``CreateProcess error=740``). Tweety's ``SPASSMlReasoner.isInstalled()``
    probes the actual binary, so it is the honest gate for the SPASS test.
    """
    path = EXTERNAL_TOOL_PATHS.get("spass")
    if not path:
        return False
    try:
        import jpype

        if not jpype.isJVMStarted():
            return False
        SPASSMlReasoner = jpype.JClass(
            "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
        )
        JString = jpype.JClass("java.lang.String")
        return bool(SPASSMlReasoner(JString(path)).isInstalled())
    except Exception:
        return False


@pytest.fixture(scope="module")
def modal_bridge():
    """Start the JVM (idempotent) and build a ``TweetyBridge`` once for the
    module. ``check_consistency(.., "K")`` routes to ``ModalHandler``
    (``is_modal_kb_consistent``), the production entry point for modal
    consistency."""
    initialize_jvm()
    return TweetyBridge()


class TestModalConsistencyDecidesViaDefault:
    """Real, non-mocked modal consistency via the DEFAULT reasoner
    (``SimpleMlReasoner``, pure-Java, query-based). No external binary → this
    RUNS on CI everywhere (the anti-theater guard for the #1205 regression).
    """

    @pytest.fixture
    def tweety_solver(self):
        """Force the pure-Java default (``TWEETY``/``SimpleMlReasoner``) for the
        test. This reasoner decides consistency via ``query`` with no external
        binary — the honest, always-available modal path."""
        previous = settings.modal_solver
        settings.modal_solver = ModalSolverChoice.TWEETY
        try:
            yield
        finally:
            settings.modal_solver = previous

    def test_inconsistent_kb_reports_inconsistent(self, modal_bridge, tweety_solver):
        """An inconsistent modal KB (``Rain`` and ``!Rain``) must yield
        ``is_consistent = False`` via a REAL query-based decision (not a parse
        error: the message must name the solver, proving the verdict came from
        the reasoner)."""
        is_consistent, msg = modal_bridge.check_consistency(INCONSISTENT_KB, "K")
        assert is_consistent is False, (
            f"Inconsistent modal KB must report inconsistent; "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert "tweety" in msg.lower(), (
            f"Verdict must be traceable to the active reasoner (not a parse "
            f"error); got msg={msg!r}."
        )

    def test_consistent_kb_reports_consistent(self, modal_bridge, tweety_solver):
        """A consistent modal KB (``[](Rain => Wet)`` ∧ ``Rain``, exercising the
        necessity operator) must yield ``is_consistent = True`` via a REAL
        query-based decision."""
        is_consistent, msg = modal_bridge.check_consistency(CONSISTENT_KB, "K")
        assert is_consistent is True, (
            f"Consistent modal KB must report consistent; "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert (
            "tweety" in msg.lower()
        ), f"Verdict must be traceable to the active reasoner; got msg={msg!r}."


@pytest.mark.skipif(
    not _spass_runnable(),
    reason="SPASS not runnable (binary unregistered, or not a launchable CLI "
    "build — the vendored SPASS.exe is a GUI/elevation build, err740). "
    "Honest skip: we do not green-by-skip a SPASS verdict we cannot produce.",
)
class TestRealSpassConsistency:
    """Real-binary SPASS modal consistency — runs ONLY where SPASS is a
    launchable CLI build. Where present (a proper CLI SPASS), it must DECIDE the
    same verdicts as the default reasoner; the construction uses the 1-arg
    ``SPASSMlReasoner(path)`` ctor fixed in #1205."""

    @pytest.fixture
    def spass_solver(self):
        previous = settings.modal_solver
        settings.modal_solver = ModalSolverChoice.SPASS
        try:
            yield
        finally:
            settings.modal_solver = previous

    def test_inconsistent_kb_reports_inconsistent_via_spass(
        self, modal_bridge, spass_solver
    ):
        is_consistent, msg = modal_bridge.check_consistency(INCONSISTENT_KB, "K")
        assert is_consistent is False, (
            f"Inconsistent modal KB must report inconsistent via SPASS; "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert (
            "spass" in msg.lower()
        ), f"Verdict must be traceable to the SPASS reasoner; got msg={msg!r}."

    def test_consistent_kb_reports_consistent_via_spass(
        self, modal_bridge, spass_solver
    ):
        is_consistent, msg = modal_bridge.check_consistency(CONSISTENT_KB, "K")
        assert is_consistent is True, (
            f"Consistent modal KB must report consistent via SPASS; "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert (
            "spass" in msg.lower()
        ), f"Verdict must be traceable to the SPASS reasoner; got msg={msg!r}."
