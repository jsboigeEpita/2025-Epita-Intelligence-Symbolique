# -*- coding: utf-8 -*-
"""#2482 on the real JVM and the bundled binaries: Prover9 decides what it is
asked, and the LADR translation keeps every constant a constant.

Measured on ``main``: every Prover9 site sent input the binary rejects (the
belief set's set notation, or Tweety declarations and syntax), so Prover9
never decided anything; and LADR read a constant starting with ``u``-``z`` as
a variable, so Mace4 found no model for a consistent KB. ``fol_query`` raised
under every solver. Synthetic predicates and constants only.
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2482 prover tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

CONSISTENT = ["forall X: (Man(X) => Mortal(X))", "Man(socrates)", "Mortal(plato)"]
INCONSISTENT = ["Man(socrates)", "!Man(socrates)"]


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored.

    ``settings`` is read from the handler module, the object it decides on,
    not re-imported from ``core.config``: a reload of ``core.config`` makes a
    new object that the handler never reads (#1804).
    """
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

    initialize_jvm()
    if not PROVER9_EXECUTABLE.is_file():
        pytest.skip("the bundled Prover9 binary is absent on this seat")
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


def _handler(fol, solver=None):
    """A handler built the way ``TweetyBridge`` builds it, under ``solver``."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    if solver is not None:
        fol.settings.solver = fol.SolverChoice(solver)
    return fol.FOLHandler(TweetyBridge().initializer)


def _belief_set_text(formulas):
    """The belief set the FOL phase builds: its signature, then its formulas."""
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )

    meta = FOLLogicAgent.extract_fol_metadata(formulas)
    return "\n".join(meta["signature_lines"] + [""] + meta["formulas"])


def _belief_set(fol, formulas):
    return _handler(fol).create_belief_set_from_string(_belief_set_text(formulas))


@pytest.mark.parametrize("backend", ["mace4", "prover9"])
@pytest.mark.parametrize(
    "constant",
    ["apple", "umbrella", "window", "zone"],
    ids=["control-a", "u", "w", "z"],
)
def test_the_ladr_translation_keeps_a_constant_a_constant(fol, backend, constant):
    """``{Red(c), !Red(berry)}`` is consistent whatever ``c`` is called. LADR
    reads a free symbol starting with ``u``-``z`` as a variable, so without
    Prolog-style variables ``Red(zone)`` meant "everything is red"."""
    belief_set = _belief_set(fol, [f"Red({constant})", "!Red(berry)"])
    check = getattr(_handler(fol), f"_fol_check_consistency_with_{backend}")

    verdict = asyncio.run(check(belief_set))

    assert verdict[0] is True, verdict


@pytest.mark.parametrize(
    "formulas, expected",
    [(CONSISTENT, True), (INCONSISTENT, False)],
    ids=["consistent", "inconsistent"],
)
def test_the_backend_comparison_hears_prover9(fol, formulas, expected):
    """``compare_fol_backends`` is what the FOL phase calls; on ``main`` it
    reported the bundled Prover9 ``available=False`` on every KB."""
    handler = _handler(fol)
    belief_set = handler.create_belief_set_from_string(_belief_set_text(formulas))

    report = asyncio.run(handler.compare_fol_backends(belief_set))

    prover9 = report["backends"]["prover9"]
    assert prover9["available"] is True, prover9
    assert prover9["verdict"] is expected, prover9
    assert report["decided"]["prover9"] is expected


@pytest.mark.parametrize(
    "formulas, expected",
    [(CONSISTENT, True), (INCONSISTENT, False)],
    ids=["consistent", "inconsistent"],
)
def test_the_consistency_check_runs_prover9_when_configured(fol, formulas, expected):
    """The synchronous check, which the FOL phase uses, honoured EPROVER and
    MACE4 but ran ``SimpleFolReasoner`` when PROVER9 was configured."""
    handler = _handler(fol, "prover9")

    verdict, message = handler.check_consistency(_belief_set_text(formulas))

    assert verdict is expected, message
    assert "(Prover9)" in message, message
    by = handler.check_consistency_by(_belief_set_text(formulas))
    assert by[0] is expected and by[2] == "prover9", by


@pytest.mark.parametrize("solver", ["tweety", "eprover", "prover9", "mace4"])
@pytest.mark.parametrize(
    "goal, expected",
    [("Mortal(socrates)", True), ("Man(plato)", False)],
    ids=["entailed", "not-entailed"],
)
def test_a_query_is_answered_by_the_configured_solver(fol, solver, goal, expected):
    """``fol_query`` raised under every solver on ``main``: the shared parser
    is ``None`` outside TWEETY, and under TWEETY it lacks the KB's signature.
    ``solver_fallback`` is ``False``: the configured solver answered. Under
    MACE4, a model-finder, the in-JVM reasoner answers the query on a handler
    built without the shared parser."""
    if solver == "eprover" and fol._get_eprover_path() is None:
        pytest.skip("the EProver binary is not wired on this seat")
    handler = _handler(fol, solver)
    belief_set = handler.create_belief_set_from_string(_belief_set_text(CONSISTENT))

    assert handler.fol_query(belief_set, goal) == (expected, False)


def _phase(formulas):
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )

    meta = FOLLogicAgent.extract_fol_metadata(formulas)
    return {"formulas": meta["formulas"], "fol_signature": meta["signature_lines"]}


@pytest.mark.parametrize(
    "formulas, expected",
    [(CONSISTENT, True), (INCONSISTENT, False)],
    ids=["consistent", "inconsistent"],
)
def test_the_external_phase_runs_the_solver_it_was_asked_for(
    fol, tmp_path, monkeypatch, formulas, expected
):
    """From a working directory other than the repository root: ``main``
    looked for the binary relative to the CWD."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    monkeypatch.chdir(tmp_path)
    context = {"phase_fol_output": _phase(formulas), "fol_solver": "prover9"}

    result = asyncio.run(_invoke_external_fol_solver("", context))

    assert result["solver"] == "prover9", result
    assert result["consistent"] is expected, result
    assert result["degraded"] is False


def test_the_external_phase_reads_the_configured_solver(fol):
    """Without a ``fol_solver`` in the context the phase reads the settings.
    ``main`` compared ``str(settings.solver)``, ``'SolverChoice.PROVER9'``,
    with ``'prover9'``, so no configured solver was ever matched."""
    from argumentation_analysis.core import config
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    if config.settings is not fol.settings:
        pytest.skip("core.config was reloaded; the phase and the handler differ")
    fol.settings.solver = fol.SolverChoice.PROVER9
    context = {"phase_fol_output": _phase(CONSISTENT)}

    result = asyncio.run(_invoke_external_fol_solver("", context))

    assert result["solver"] == "prover9", result
    assert result["consistent"] is True, result


# Prover9 stopped on a resource limit: neither marker is printed.
_UNDECIDED = "\n------ process 1 exit (max_seconds) ------\n"


def test_a_prover9_run_that_decides_nothing_is_no_verdict(fol, monkeypatch):
    """No proof and no exhausted search (a resource limit): the Prover9
    backend gives no verdict, and the phase's check says the in-JVM reasoner
    decided instead. ``main`` read "no THEOREM PROVED" as "consistent"."""
    monkeypatch.setattr(fol, "run_prover9", lambda _input: _UNDECIDED)
    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(_belief_set_text(INCONSISTENT))

    alone = asyncio.run(handler._fol_check_consistency_with_prover9(belief_set))
    verdict, message, solver = handler.check_consistency_by(belief_set)

    assert alone[0] is None, alone
    assert (verdict, solver) == (False, "tweety"), message
    assert message.startswith("Prover9 decided nothing; "), message


def test_input_prover9_refuses_stays_loud(fol, monkeypatch):
    """A fatal error is an error, never a verdict: the Prover9 backend and the
    phase's check both raise with the binary's text.

    #2489: this test used to assert that the phase's check fell back to the
    in-JVM reasoner (``(True, "tweety")``) on a fatal error. That was #2482
    DoD 5 held on the backend only. A refused input is the builder's defect,
    so the check that production calls now raises too; the double raises the
    type the runner raises for a fatal error.
    """
    from argumentation_analysis.core.prover9_runner import Prover9InputRejected

    def refuse(_input):
        raise Prover9InputRejected(
            "Prover9 reported a fatal error (likely malformed input):"
        )

    monkeypatch.setattr(fol, "run_prover9", refuse)
    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(_belief_set_text(CONSISTENT))

    with pytest.raises(Prover9InputRejected, match="fatal error"):
        asyncio.run(handler._fol_check_consistency_with_prover9(belief_set))
    with pytest.raises(Prover9InputRejected, match="fatal error"):
        handler.check_consistency_by(belief_set)


# #2489: LADR that Prover9 refuses, as a regression of ``_prover9_input`` would
# produce it. The real binary answers ``Fatal error:  sread_term error``.
_MALFORMED = "formulas(assumptions).\nthis is (not ladr.\nend_of_list.\n"


def test_the_runner_names_a_refused_input(fol):
    """The runner tells an input Prover9 refused from its other failures, at
    the place it reads the binary's fatal-error marker."""
    from argumentation_analysis.core.prover9_runner import (
        Prover9InputRejected,
        run_prover9,
    )

    with pytest.raises(Prover9InputRejected, match="Fatal error"):
        run_prover9(_MALFORMED)


def test_a_timeout_is_not_a_refused_input(fol, monkeypatch):
    """A timeout is the environment's failure, not the builder's: the runner
    raises a plain ``RuntimeError``, and the phase's check still falls back to
    the in-JVM reasoner, naming why."""
    import subprocess

    from argumentation_analysis.core import prover9_runner

    def hang(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="prover9", timeout=60)

    monkeypatch.setattr(prover9_runner.subprocess, "run", hang)
    with pytest.raises(RuntimeError, match="timed out") as raised:
        prover9_runner.run_prover9("formulas(assumptions).\nend_of_list.\n")
    assert not isinstance(raised.value, prover9_runner.Prover9InputRejected)

    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(_belief_set_text(CONSISTENT))
    monkeypatch.setattr(fol, "run_prover9", prover9_runner.run_prover9)
    verdict, message, solver = handler.check_consistency_by(belief_set)

    assert (verdict, solver) == (True, "tweety"), message
    assert message.startswith("Prover9 failed (Prover9 timed out"), message


def test_a_refused_input_turns_the_phase_check_red(fol, monkeypatch):
    """#2489, born red on the real binary: when the builder produces LADR that
    Prover9 refuses, the check the FOL phase calls raises with the binary's
    text. ``main`` let the in-JVM reasoner decide, labelled ``tweety``, and a
    builder regression stayed invisible."""
    monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)
    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(_belief_set_text(CONSISTENT))

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        handler.check_consistency_by(belief_set)
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_a_refused_input_fails_the_external_phase(fol, monkeypatch):
    """#2489, the phase production runs, born red on the real binary: a
    refused input leaves ``_invoke_external_fol_solver`` as an exception, so
    the executor marks the phase FAILED with the binary's text. Neither the
    in-JVM verdict (``main``) nor the phase's error dict, which the executor
    records as a completed phase, may stand in for it."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)
    context = {"phase_fol_output": _phase(CONSISTENT), "fol_solver": "prover9"}

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        asyncio.run(_invoke_external_fol_solver("", context))
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_a_refused_input_is_not_an_unavailable_solver(fol, monkeypatch):
    """#2489, the handler's async API, born red: ``fol_check_consistency``
    under Prover9 raises on a refused input. ``main`` read the refusal as an
    unavailable solver and answered with the in-JVM reasoner."""
    monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)
    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(_belief_set_text(CONSISTENT))

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        asyncio.run(handler.fol_check_consistency(belief_set))
    assert type(raised.value).__name__ == "Prover9InputRejected"


@pytest.mark.parametrize("refused", [False, True], ids=["control", "refused"])
def test_the_fol_phase_under_prover9(fol, monkeypatch, refused):
    """#2489, the main FOL phase with Prover9 configured, born red.

    Control: the real builder, and the phase decides. Refused: the phase
    raises, so the executor marks it FAILED with the binary's text. ``main``
    answered with the in-JVM reasoner; with only the handler repaired, the
    phase read the refusal as a Tweety parse failure and dropped every
    formula in isolation.
    """
    from argumentation_analysis.core import config
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    if config.settings is not fol.settings:
        pytest.skip("core.config was reloaded; the phase and the handler differ")
    fol.settings.solver = fol.SolverChoice.PROVER9
    if refused:
        monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)
    # A short input: the phase's LLM formula generator stays off.
    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(CONSISTENT),
        "_state_object": None,
    }

    if refused:
        with pytest.raises(RuntimeError, match="Fatal error") as raised:
            asyncio.run(_invoke_fol_reasoning("text", context))
        assert type(raised.value).__name__ == "Prover9InputRejected"
    else:
        result = asyncio.run(_invoke_fol_reasoning("text", context))
        assert result["consistent"] is True, result.get("message")
        assert "Prover9" in result.get("message", ""), result.get("message")


# Ground formulas only: the isolation net rejects a universal formula checked
# alone (its sort has no constant), a defect of its own (#2492).
_GROUND = ["Man(socrates)", "Mortal(plato)"]
# Tweety refuses this one, so the combined check degrades and isolation runs.
_UNPARSABLE = "Man(socrates"


def _run_fol_phase(fol, formulas):
    from argumentation_analysis.core import config
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    if config.settings is not fol.settings:
        pytest.skip("core.config was reloaded; the phase and the handler differ")
    fol.settings.solver = fol.SolverChoice.PROVER9
    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(formulas),
        "_state_object": None,
    }
    return asyncio.run(_invoke_fol_reasoning("text", context))


def test_a_refused_input_is_not_retried_formula_by_formula(fol, monkeypatch):
    """#2489: the combined check's refusal leaves the phase at once. Read as a
    Tweety parse failure, it sent every formula to isolation, one Prover9 run
    each, before the first of them raised."""
    built = []

    def refused(*args):
        built.append(args)
        return _MALFORMED

    monkeypatch.setattr(fol, "_prover9_input", refused)
    with pytest.raises(RuntimeError, match="Fatal error"):
        _run_fol_phase(fol, _GROUND)
    assert len(built) == 1


def test_isolation_does_not_drop_a_refused_formula(fol, monkeypatch):
    """#2489: when isolation runs (the combined set does not parse), a formula
    Prover9 refuses is not Tweety's poison: the phase raises. Dropped as
    "rejected by Tweety", every formula went, and the phase published an
    undecided set with no trace of the builder."""
    monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)
    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        _run_fol_phase(fol, _GROUND + [_UNPARSABLE])
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_isolation_does_not_degrade_a_refused_combined_set(fol, monkeypatch):
    """#2489: a builder defect that shows only on several formulas together.
    Each survivor passes alone; the check of the survivors together raises
    instead of publishing them unverified."""
    real = fol._prover9_input

    def refuses_sets(belief_set, *rest):
        if belief_set.size() > 1:
            return _MALFORMED
        return real(belief_set, *rest)

    monkeypatch.setattr(fol, "_prover9_input", refuses_sets)
    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        _run_fol_phase(fol, _GROUND + [_UNPARSABLE])
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_isolation_under_prover9_control(fol):
    """Control: the real builder, the same formulas. Isolation rejects the
    unparsable formula by name and Prover9 decides on the survivors."""
    result = _run_fol_phase(fol, _GROUND + [_UNPARSABLE])

    assert result["consistent"] is True, result.get("message")
    assert result["fol_metrics"]["rejected_formulas"] == [_UNPARSABLE]
    assert "Prover9" in result.get("message", ""), result.get("message")


def test_a_refused_query_input_is_not_a_fallback(fol, monkeypatch):
    """#2489, the query path, born red on the real binary: ``fol_query`` under
    Prover9 raises on a refused input. ``main`` rewrapped the refusal and
    answered with the in-JVM reasoner (``solver_fallback=True``)."""
    monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)
    handler = _handler(fol, "prover9")
    belief_set = handler.create_belief_set_from_string(_belief_set_text(CONSISTENT))

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        handler.fol_query(belief_set, "Mortal(socrates)")
    assert type(raised.value).__name__ == "Prover9InputRejected"
