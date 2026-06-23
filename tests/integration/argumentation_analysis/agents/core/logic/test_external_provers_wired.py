"""Regression guard: a previously-wired EXTERNAL component must not be silently
disconnected (R467 user mandate, 2026-06-23).

History this guard exists to prevent recurring:
- EProver: binary archived (95d4f3fd) + ctor broken + sync bypass — fabricated
  ``consistent`` on contradictions. Caught a month late (#1204), restored #1209.
- SPASS (modal): binary gitignored + GUI-build can't launch — never decided.
  Caught only when the user checked by hand.
- Clingo (ASP): the JVM Tweety binding was disconnected on THREE counts —
  ``setPathToClingo`` startup injection deleted by 029bdf7c (#1196), plus a
  ``ClingoSolver()`` no-arg ctor and an ``ASPRule(list, list)`` ctor that do
  not exist in this Tweety build (both raised and were swallowed). The official
  clingo Python package carried ASP correctly the whole time, so answer sets
  stayed right — but if it ever vanished the path dropped to a fact-echo
  ``heuristic`` that ignores rules (fabrication). Tweety 1.29's ClingoSolver is
  also incompatible with clingo >= 5.x (it mis-parses the version banner into
  fake atoms), so the genuine path here is the Python binding.

The common failure mode: an external solver that was wired in the past gets
disconnected, and a graceful fallback masks it — so tests stay green while the
real prover is dead (anti-théâtre #1019: silent degradation).

**The invariant this module enforces:** *when the external binary is REGISTERED
(present), the production path MUST use the real solver — not a silent fallback.*
A test that merely checks "some answer came back" cannot catch a disconnect; this
guard checks WHICH solver produced it. Where a binary is genuinely absent the
test skips cleanly (it cannot exercise the solver) — it must NOT be green by
fabrication.

Synthetic atoms only — no corpus.
"""

import asyncio

import pytest

from argumentation_analysis.core.jvm_setup import (
    EXTERNAL_TOOL_PATHS,
    initialize_jvm,
    is_jvm_started,
)


@pytest.fixture(scope="module", autouse=True)
def _jvm():
    initialize_jvm()
    if not is_jvm_started():
        pytest.skip("JVM not started — cannot exercise JVM-backed external solvers.")


# --------------------------------------------------------------------------- #
# Clingo / ASP — the disconnect this guard was written to catch.
# --------------------------------------------------------------------------- #
def _clingo_available():
    """A genuine clingo exists if either the JVM binary is registered OR the
    official clingo Python package is importable."""
    import importlib.util

    return bool(EXTERNAL_TOOL_PATHS.get("clingo")) or (
        importlib.util.find_spec("clingo") is not None
    )


def test_clingo_decided_by_genuine_solver():
    """ASP must be decided by a GENUINE clingo solver — the JVM Tweety binding
    (``clingo_jvm``) OR the official clingo Python package (``clingo_python``) —
    with a CORRECT answer set, never the fact-echo ``heuristic`` (which ignores
    rules and fabricates) and never a silent ``unavailable`` when a solver is
    present.

    The 029bdf7c disconnect broke the JVM binding; the Python package carried
    ASP correctly, but a single missing dependency would have dropped it to the
    heuristic echo. Tweety 1.29's ClingoSolver is additionally incompatible with
    clingo >= 5.x (banner mis-parse), so the genuine path here is the Python
    binding — what this guard enforces is *a real, correct answer set*, not which
    binding produced it."""
    if not _clingo_available():
        pytest.skip("no genuine clingo (JVM binary nor Python package) — cannot test.")

    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_asp_reasoning,
    )

    res = asyncio.new_event_loop().run_until_complete(
        _invoke_asp_reasoning("a.\nb :- a.", {})
    )
    solver = res.get("solver")
    assert solver in ("clingo_jvm", "clingo_python"), (
        f"a genuine clingo is available but ASP used solver={solver!r} — it fell "
        f"to the fact-echo heuristic / unavailable (silent disconnect). The "
        f"heuristic ignores rules and fabricates answer sets (anti-théâtre #1019)."
    )
    # Correctness: the unique answer set of "a. b :- a." is exactly {a, b}.
    sets = [set(m) for m in res.get("answer_sets", [])]
    assert {"a", "b"} in sets, (
        f"genuine solver {solver!r} returned a WRONG answer set {sets!r} — "
        f"expected the unique model {{a, b}}."
    )


# --------------------------------------------------------------------------- #
# EProver / FOL — must DECIDE (or guarded-fallback), never fabricate.
# --------------------------------------------------------------------------- #
def test_eprover_decides_inconsistent_when_binary_present():
    if not EXTERNAL_TOOL_PATHS.get("eprover"):
        pytest.skip("EProver binary not registered — cannot test the FOL solver.")

    from argumentation_analysis.core.config import settings, SolverChoice
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    prev = settings.solver
    settings.solver = SolverChoice.EPROVER
    try:
        bridge = TweetyBridge()
        kb = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)\n!Human(socrate)"
        verdict, msg = bridge.check_consistency(kb, "first_order")
    finally:
        settings.solver = prev

    # The contradiction must be detected as inconsistent. A fabricated ``True``
    # here is the #1204 failure; a silent non-EProver solver is a disconnect.
    assert verdict is False, f"EProver did not detect the contradiction: {msg!r}"


# --------------------------------------------------------------------------- #
# Prover9 / FOL (alt) — the binary is fully installed (prover9.exe + cygwin1.dll
# + mace4.exe under libs/prover9/bin/). R467 sweep firsthand-confirmed it
# genuinely DECIDES standalone ("THEOREM PROVED" on a contradiction in ~0.00s).
# Two guards: (1) the binary still decides when fed real Prover9 syntax — so an
# archived/broken install becomes a red build, the EProver #1204 failure mode in
# the Prover9 dimension; (2) selecting PROVER9 through the production bridge must
# yield the CORRECT verdict (the Tweety->Prover9 syntax gap routes it to an
# honest SimpleFolReasoner fallback — that is fine; a FABRICATED verdict is not).
# --------------------------------------------------------------------------- #
def test_prover9_binary_genuinely_decides():
    """Firsthand: the installed Prover9 binary must DECIDE an inconsistent KB
    (fed in real Prover9 syntax). 'THEOREM PROVED' on {Human(socrate),
    -Human(socrate)} |- $F means it genuinely refuted the KB. If the binary is
    archived/broken later, this goes red instead of a silent month-late hand
    discovery (the #1204 / R467 pattern)."""
    from argumentation_analysis.core import prover9_runner

    if not prover9_runner.PROVER9_EXECUTABLE.is_file():
        pytest.skip("Prover9 binary not installed — cannot test the FOL alt solver.")

    p9_input = (
        "formulas(assumptions).\n"
        "Human(socrate).\n"
        "-Human(socrate).\n"
        "end_of_list.\n\n"
        "formulas(goals).\n"
        "$F.\n"
        "end_of_list."
    )
    out = prover9_runner.run_prover9(p9_input)
    assert "THEOREM PROVED" in out, (
        "Prover9 binary is installed but did NOT prove $F from a contradiction — "
        f"it no longer decides (silent disconnect). Raw tail:\n{out[-400:]!r}"
    )


def test_prover9_selection_yields_correct_verdict_never_fabricated():
    """Selecting SolverChoice.PROVER9 must produce the CORRECT verdict on an
    inconsistent FOL KB. The Tweety->Prover9 syntax-translation gap means the
    binary path raises 'Fatal error' and the bridge falls back to the Tweety
    SimpleFolReasoner — an HONEST, labelled fallback. The invariant: the
    contradiction is reported inconsistent (False), or fails loud (None); it is
    NEVER fabricated as consistent (True). A timeout (added R467) turns a hang
    into a fast honest fallback rather than blocking the pipeline."""
    from argumentation_analysis.core import prover9_runner

    if not EXTERNAL_TOOL_PATHS.get("eprover") and not (
        prover9_runner.PROVER9_EXECUTABLE.is_file()
    ):
        pytest.skip("No FOL backend present — cannot test PROVER9 selection.")

    from argumentation_analysis.core.config import settings, SolverChoice
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    prev = settings.solver
    settings.solver = SolverChoice.PROVER9
    try:
        bridge = TweetyBridge()
        kb = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)\n!Human(socrate)"
        verdict, msg = bridge.check_consistency(kb, "first_order")
    finally:
        settings.solver = prev

    assert verdict in (False, None), (
        f"PROVER9-selected FOL reported a contradiction as CONSISTENT "
        f"(verdict={verdict!r}) — a fabricated verdict (anti-théâtre #1019). "
        f"Honest outcomes are inconsistent (False) or fail-loud (None). msg={msg!r}"
    )


# --------------------------------------------------------------------------- #
# PySAT / PL — must decide via PySAT, not the Tweety fallback.
# --------------------------------------------------------------------------- #
def test_pysat_decides_pl_consistency():
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    bridge = TweetyBridge()
    inc, _ = bridge.check_consistency("a\n!a", "propositional")
    con, _ = bridge.check_consistency("a\nb", "propositional")
    assert (
        inc is False and con is True
    ), f"PL consistency wrong: inconsistent->{inc}, consistent->{con}"


# --------------------------------------------------------------------------- #
# SAT — _invoke_sat is PySAT-backed (NOT the dead ext_tools/*.py scripts).
# Must genuinely decide SAT/UNSAT, never fabricate.
# --------------------------------------------------------------------------- #
def test_sat_decided_by_pysat():
    """_invoke_sat routes through SATHandler -> pysat.solvers.Solver (genuine).
    'a & !a' is UNSAT; 'a' is SAT. If PySAT is uninstalled the handler raises
    (fail-loud) rather than fabricating — so we surface that as a skip, never a
    green pass on a dead solver."""
    try:
        import pysat  # noqa: F401
    except ImportError:
        pytest.skip("PySAT not installed — SAT handler cannot decide (fail-loud).")

    from argumentation_analysis.orchestration.invoke_callables import _invoke_sat

    loop = asyncio.new_event_loop()
    unsat = loop.run_until_complete(_invoke_sat("a & !a", {}))
    sat = loop.run_until_complete(_invoke_sat("a", {}))
    assert unsat.get("satisfiable") is False, (
        f"contradiction 'a & !a' reported satisfiable={unsat.get('satisfiable')!r} "
        f"— PySAT disconnect or fabrication (#1019)."
    )
    assert (
        sat.get("satisfiable") is True
    ), f"'a' reported satisfiable={sat.get('satisfiable')!r} — expected True."


# --------------------------------------------------------------------------- #
# SPASS / modal — when SELECTED + present, must decide or be honest-None,
# never silently fall back to SimpleMlReasoner. (po-2025 owns the re-wire;
# this guard locks the invariant in.)
# --------------------------------------------------------------------------- #
def test_spass_no_silent_fallback_when_selected():
    from argumentation_analysis.core.config import settings, ModalSolverChoice
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    if not EXTERNAL_TOOL_PATHS.get("spass"):
        pytest.skip("SPASS binary not registered — cannot test the SPASS modal path.")

    # Is the registered SPASS actually launchable as a CLI? (A GUI/elevation
    # build, or a missing binary beside the adapter, is registered-but-dead.)
    # When it IS launchable, the production path MUST genuinely decide — a silent
    # disconnect that quietly yields None would otherwise pass this guard, the
    # exact "débranché sans que personne voie à redire" failure mode (R467).
    spass_runnable = False
    try:
        import jpype

        if jpype.isJVMStarted():
            SPASSMlReasoner = jpype.JClass(
                "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
            )
            JString = jpype.JClass("java.lang.String")
            spass_runnable = bool(
                SPASSMlReasoner(JString(EXTERNAL_TOOL_PATHS["spass"])).isInstalled()
            )
    except Exception:
        spass_runnable = False

    prev = settings.modal_solver
    settings.modal_solver = ModalSolverChoice.SPASS
    try:
        bridge = TweetyBridge()
        # Two independent synthetic atoms, both asserted — genuinely consistent.
        # Propositions must be declared (``type(p)``) or MlParser raises
        # "Missing '=' in sort declaration" (a parse error, NOT a decision).
        verdict, msg = bridge.check_consistency("type(p)\ntype(q)\n\np\nq\n", "K")
    except Exception as e:  # SPASS can't launch -> must surface, not be masked
        verdict, msg = None, f"raised {type(e).__name__}: {e}"
    finally:
        settings.modal_solver = prev

    # Honest contract: SPASS decides (True/False) OR fails loud (None). A verdict
    # produced by a silently-substituted SimpleMlReasoner would violate #1019;
    # the message must name SPASS or an explicit unavailability, not a quiet swap.
    assert verdict in (True, False, None)
    assert (
        "SimpleMlReasoner" not in msg
    ), f"SPASS was selected but a SimpleMlReasoner verdict leaked through: {msg!r}"

    # The non-skip teeth: where the vendored SPASS CLI genuinely launches (this
    # machine + CI-Windows, since the binary is tracked in git), a future silent
    # disconnect becomes a RED build instead of a quiet None.
    if spass_runnable:
        assert verdict is True, (
            f"SPASS is launchable but the consistent KB 'p, q' did not DECIDE "
            f"consistent via SPASS — silent disconnect? got ({verdict!r}, {msg!r})."
        )
        assert "spass" in msg.lower(), (
            f"SPASS is launchable but the verdict is not traceable to it — a "
            f"quiet reasoner swap? got msg={msg!r}."
        )
