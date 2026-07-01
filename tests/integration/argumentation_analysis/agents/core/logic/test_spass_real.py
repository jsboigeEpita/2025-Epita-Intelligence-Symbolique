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

A third firsthand finding (po-2025 / WSL, 2026-06-23, #1234) added the
``TestRealSpassConsistency`` multi-atom case and the EML→eml adapter:

3. **A genuine SPASS CLI built from source DOES decide modal logic — once the
   Tweety↔SPASS DFG delivery contract is repaired.** Tweety 1.29 emits the DFG
   special-formulae logic token as ``EML`` (uppercase); SPASS 3.9's parser
   requires ``eml`` (lowercase) → "got 'EML', expected special type (eml)",
   SPASS aborts, ``query`` throws "SPASS returned no result which can be
   interpreted" (modal analogue of the eprover #1204 regression). The
   ``spass_eml_adapter.sh`` adapter (registered as
   ``EXTERNAL_TOOL_PATHS['spass']``) rewrites only that keyword case and
   forwards to the real SPASS, which then DECIDES — including the 12-atom KB
   that OOMs ``SimpleMlReasoner`` (``MULTI_ATOM_MODAL_KB`` below). Build:
   ``scripts/setup/build_spass_modal.sh``.

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

# A 12-atom genuinely-modal KB — a necessity chain []( a_i => a_{i+1} ) plus a
# possibility <>( a1 ). This is the #1234 / FP-16 scaling case: ``SimpleMlReasoner``
# enumerates Kripke models and OOMs (``java.lang.OutOfMemoryError``) at this atom
# count, so it CANNOT decide it. SPASS decides it by saturation (no enumeration),
# which is exactly why activating SPASS — not routing around the modal solver — is
# the fix. Privacy HARD: synthetic atoms only.
_MULTI_ATOMS = [f"a{i}" for i in range(1, 13)]
MULTI_ATOM_MODAL_KB = (
    "\n".join(f"type({a})" for a in _MULTI_ATOMS)
    + "\n\n"
    + "\n".join(
        f"[]({_MULTI_ATOMS[i]} => {_MULTI_ATOMS[i + 1]})"
        for i in range(len(_MULTI_ATOMS) - 1)
    )
    + f"\n<>({_MULTI_ATOMS[0]})\n"
)


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

    def test_multi_atom_kb_decides_via_spass_without_oom(
        self, modal_bridge, spass_solver
    ):
        """The #1234 / FP-16 win: a 12-atom genuinely-modal KB that OOMs
        ``SimpleMlReasoner`` (naive Kripke enumeration) must DECIDE via SPASS
        (saturation, no enumeration). Firsthand-verified (2026-06-23) via the
        production ModalHandler under the WSL fol-linux stack: SPASS returns a
        real boolean verdict here where the default reasoner cannot. The KB is
        satisfiable (a reflexive single-world model satisfies the chain and the
        diamond), so the genuine verdict is ``consistent``."""
        is_consistent, msg = modal_bridge.check_consistency(MULTI_ATOM_MODAL_KB, "K")
        assert is_consistent is not None, (
            f"A 12-atom modal KB that OOMs SimpleMlReasoner must still DECIDE via "
            f"SPASS (no enumeration); got ({is_consistent!r}, {msg!r})."
        )
        assert is_consistent is True, (
            f"The necessity-chain + diamond KB is satisfiable; SPASS must report "
            f"consistent. got ({is_consistent!r}, {msg!r})."
        )
        assert (
            "spass" in msg.lower()
        ), f"Verdict must be traceable to the SPASS reasoner; got msg={msg!r}."


# ---------------------------------------------------------------------------
# #1326 — modal sort-name normalization (amont de parseBeliefBase).
# ---------------------------------------------------------------------------
# R519 firsthand: a modal KB whose predicate names contain underscores
# (``type(heavy_rain)``) raised ``ParserException: Illegal characters in
# predicate definition`` → ``is_modal_kb_consistent`` returned ``(None,
# "...parse error...")`` → the axis degraded, never decided. Several producers
# (spectacular-path ``_construct_modal_kb_from_json``, LLM identifiers) emit
# such names. ``ModalHandler`` now normalizes identifiers to MlParser-legal
# PascalCase immediately before ``parseBeliefBase`` (#1326, defense-in-depth).
#
# The anti-theater guard: a KB that USED to parse-fail must now DECIDE via a
# REAL reasoner (verdict traceable to the solver name in ``msg``, not a parse
# error). Privacy HARD: weather-domain synthetic atoms only (no corpus).
UNDERSCORED_CONSISTENT_KB = (
    "type(heavy_rain)\ntype(wet_ground)\n\n"
    "[](heavy_rain => wet_ground)\nheavy_rain\n"
)
UNDERSCORED_INCONSISTENT_KB = "type(heavy_rain)\n\nheavy_rain\n!heavy_rain\n"


class TestUnderscoredKbDecidesViaDefault:
    """The #1326 fix, decided by the DEFAULT pure-Java reasoner (runs on CI
    everywhere — the anti-theater guard). Before #1326 these KBs returned
    ``(None, parse error)``; they must now return a definite boolean."""

    @pytest.fixture
    def tweety_solver(self):
        previous = settings.modal_solver
        settings.modal_solver = ModalSolverChoice.TWEETY
        try:
            yield
        finally:
            settings.modal_solver = previous

    def test_underscored_consistent_kb_decides_true(self, modal_bridge, tweety_solver):
        """A consistent KB with underscored atoms must DECIDE ``True`` via a real
        query (not a parse error). Proves the normalization lets the reasoner
        actually receive and decide the belief set."""
        is_consistent, msg = modal_bridge.check_consistency(
            UNDERSCORED_CONSISTENT_KB, "K"
        )
        assert is_consistent is True, (
            f"Underscored consistent KB must decide True after #1326 "
            f"normalization; got ({is_consistent!r}, {msg!r})."
        )
        assert "tweety" in msg.lower() and "parse" not in msg.lower(), (
            f"Verdict must come from the reasoner, not a parse error; "
            f"got msg={msg!r}."
        )

    def test_underscored_inconsistent_kb_decides_false(self, modal_bridge, tweety_solver):
        """An inconsistent KB (``heavy_rain`` ∧ ``!heavy_rain``) must DECIDE
        ``False``. This proves the symbol map is SOUND: both occurrences of
        ``heavy_rain`` map to the SAME normalized symbol, so the reasoner sees
        the contradiction. An inconsistent map would map them to two different
        atoms and wrongly report consistent."""
        is_consistent, msg = modal_bridge.check_consistency(
            UNDERSCORED_INCONSISTENT_KB, "K"
        )
        assert is_consistent is False, (
            f"Underscored inconsistent KB must decide False (sound symbol map); "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert "tweety" in msg.lower() and "parse" not in msg.lower(), (
            f"Verdict must come from the reasoner, not a parse error; "
            f"got msg={msg!r}."
        )


@pytest.mark.skipif(
    not _spass_runnable(),
    reason="SPASS not runnable — the SPASS DECIDES-firsthand variant of the "
    "#1326 guard runs only where SPASS is a launchable CLI build.",
)
class TestUnderscoredKbDecidesViaSpass:
    """The #1326 fix decided firsthand by SPASS (the coord DoD: genuine solver,
    no theater fallback). The normalized belief set must reach SPASS and DECIDE."""

    @pytest.fixture
    def spass_solver(self):
        previous = settings.modal_solver
        settings.modal_solver = ModalSolverChoice.SPASS
        try:
            yield
        finally:
            settings.modal_solver = previous

    def test_underscored_kb_decides_via_spass(self, modal_bridge, spass_solver):
        is_consistent, msg = modal_bridge.check_consistency(
            UNDERSCORED_CONSISTENT_KB, "K"
        )
        assert is_consistent is True, (
            f"Underscored consistent KB must decide True via SPASS; "
            f"got ({is_consistent!r}, {msg!r})."
        )
        assert "spass" in msg.lower() and "parse" not in msg.lower(), (
            f"Verdict must come from SPASS, not a parse error; got msg={msg!r}."
        )

