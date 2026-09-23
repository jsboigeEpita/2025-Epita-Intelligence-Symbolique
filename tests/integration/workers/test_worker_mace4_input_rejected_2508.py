# -*- coding: utf-8 -*-
"""#2508 on the real JVM and the bundled Mace4: an input Mace4 refuses is a
defect of our builder, never an unavailable Mace4.

Measured on ``main``: ``run_mace4`` raised a plain ``RuntimeError`` on the
binary's ``Fatal error`` marker, so ``check_consistency_by`` answered
``None`` "Mace4 unavailable" and the async check fell back to the in-JVM
reasoner. The Mace4 twin of #2489. Synthetic predicates and constants only.
"""

import asyncio
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2508 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# LADR that Mace4 refuses, as a regression of the builder would produce it.
_MALFORMED = "formulas(assumptions).\nthis is (not ladr.\nend_of_list.\n"
_CONSISTENT = "thing = {a, b}\ntype(Man(thing))\nMan(a)\n!Man(b)"


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.core.mace4_runner import MACE4_EXECUTABLE

    initialize_jvm()
    if not MACE4_EXECUTABLE.is_file():
        pytest.skip("the bundled Mace4 binary is absent on this seat")
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


def _handler(fol):
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    fol.settings.solver = fol.SolverChoice.MACE4
    return fol.FOLHandler(TweetyBridge().initializer)


def test_the_runner_names_a_refused_input(fol):
    """The runner tells an input Mace4 refused from its other failures, at the
    place it reads the binary's marker."""
    from argumentation_analysis.core.mace4_runner import Mace4InputRejected, run_mace4
    from argumentation_analysis.core.prover9_runner import SolverInputDefect

    with pytest.raises(Mace4InputRejected, match="Fatal error") as raised:
        run_mace4(_MALFORMED)
    assert isinstance(raised.value, SolverInputDefect)


def _refused(fol, monkeypatch):
    monkeypatch.setattr(fol, "_belief_set_to_ladr_assumptions", lambda _bs: _MALFORMED)


def test_a_refused_input_is_not_an_unavailable_mace4(fol, monkeypatch):
    """The check the phases call and the async API raise with the binary's
    text. ``main`` answered ``None`` "Mace4 unavailable", and the async check
    let the in-JVM reasoner answer."""
    handler = _handler(fol)
    belief_set = handler.create_belief_set_from_string(_CONSISTENT)
    _refused(fol, monkeypatch)

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        handler.check_consistency_by(belief_set, solver="mace4")
    assert type(raised.value).__name__ == "Mace4InputRejected"
    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        asyncio.run(handler.fol_check_consistency(belief_set))
    assert type(raised.value).__name__ == "Mace4InputRejected"


def test_a_refused_input_fails_the_external_phase(fol, monkeypatch):
    """``_invoke_external_fol_solver`` under Mace4 leaves as an exception, so
    the executor marks the phase FAILED; its error dict would record a
    completed phase."""
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    meta = FOLLogicAgent.extract_fol_metadata(["Man(socrates)", "!Man(plato)"])
    context = {
        "phase_fol_output": {
            "formulas": meta["formulas"],
            "fol_signature": meta["signature_lines"],
        },
        "fol_solver": "mace4",
    }
    _refused(fol, monkeypatch)

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        asyncio.run(_invoke_external_fol_solver("", context))
    assert type(raised.value).__name__ == "Mace4InputRejected"


def test_a_timeout_still_degrades(fol, monkeypatch):
    """Control: a timeout is the environment's failure, not the builder's.
    The check still reads ``None`` with the reason, and the async check still
    falls back to the in-JVM reasoner."""
    from argumentation_analysis.core import mace4_runner

    handler = _handler(fol)
    belief_set = handler.create_belief_set_from_string(_CONSISTENT)
    # The delivery sentinel runs Mace4 once per binary and caches the result:
    # run it for real before the binary starts timing out.
    assert fol._mace4_delivery_is_reliable()

    def hang(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="mace4", timeout=30)

    monkeypatch.setattr(mace4_runner.subprocess, "run", hang)
    verdict, message, backend = handler.check_consistency_by(belief_set, solver="mace4")
    assert (verdict, backend) == (None, "mace4"), message
    assert "timed out" in message, message

    is_consistent, _msg, fallback = asyncio.run(
        handler.fol_check_consistency(belief_set)
    )
    assert (is_consistent, fallback) == (True, True)


def test_the_real_builder_is_decided(fol):
    """Control: the real builder's input, and Mace4 decides."""
    handler = _handler(fol)
    belief_set = handler.create_belief_set_from_string(_CONSISTENT)

    verdict, message, backend = handler.check_consistency_by(belief_set, solver="mace4")

    assert (verdict, backend) == (True, "mace4"), message
