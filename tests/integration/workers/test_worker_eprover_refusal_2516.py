# -*- coding: utf-8 -*-
"""#2516 on the real JVM and the bundled EProver: an input E refuses is not
a verdict.

Measured on ``main``: Tweety's ``EFOLReasoner.query`` maps every outcome that
is not ``# Proof found!`` to ``false``, an input E refuses (exit status 3)
included. The three EProver sites read that ``false`` as "consistent" or "not
entailed". Two sets the builder writes were refused: a constant named like
the sort (``thing``, which Tweety's TPTP writes as a unary predicate) and a
constant named like a predicate. A predicate named like the sort was not
refused but read as membership of the sort, so E decided ``!thing(c)``
inconsistent. Synthetic predicates and constants only.
"""

import asyncio
import os
import sys
import time
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2516 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# Belief sets as they reached EProver on ``main``: E refuses both.
_REFUSED = {
    "a constant named like the sort": (
        "thing = {thing}\ntype(Man(thing))\n\nforall X: (Man(X))\n!Man(thing)",
        "Man(thing)",
    ),
    "a constant named like a predicate": (
        "thing = {p}\ntype(p(thing))\n\nforall X: (p(X))\n!p(p)",
        "p(p)",
    ),
}
_INCONSISTENT = "thing = {a}\ntype(Man(thing))\n\nforall X: (Man(X))\n!Man(a)"
_CONSISTENT = "thing = {a}\ntype(Man(thing))\n\nforall X: (Man(X))\nMan(a)"


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    initialize_jvm()
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


@pytest.fixture
def eprover(fol):
    if fol._get_eprover_path() is None:
        pytest.skip("the EProver binary is not wired on this seat")
    return fol


def _handler(fol, solver=None):
    """A handler built the way ``TweetyBridge`` builds it, under ``solver``."""
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    if solver is not None:
        fol.settings.solver = fol.SolverChoice(solver)
    return fol.FOLHandler(TweetyBridge().initializer)


@pytest.mark.parametrize("text, query", _REFUSED.values(), ids=list(_REFUSED))
def test_a_refused_input_is_not_a_verdict(eprover, text, query):
    """DoD 1: none of the three EProver sites publishes a verdict; each
    raises with E's message. ``main``: consistent, consistent, not entailed."""
    handler = _handler(eprover, "eprover")
    belief_set = handler.create_belief_set_from_string(text)

    with pytest.raises(eprover.EProverInputRejected, match="exit 3"):
        handler.check_consistency_by(text, solver="eprover")
    with pytest.raises(eprover.EProverInputRejected, match="exit 3"):
        asyncio.run(handler.fol_check_consistency(belief_set))
    with pytest.raises(eprover.EProverInputRejected, match="exit 3"):
        handler.fol_query(belief_set, query)


def test_an_input_e_accepts_is_decided_as_before(eprover):
    """DoD 2, control: green on ``main``."""
    handler = _handler(eprover, "eprover")

    assert handler.check_consistency_by(_INCONSISTENT, solver="eprover")[::2] == (
        False,
        "eprover",
    )
    assert handler.check_consistency_by(_CONSISTENT, solver="eprover")[::2] == (
        True,
        "eprover",
    )
    consistent = handler.create_belief_set_from_string(_CONSISTENT)
    assert asyncio.run(handler.fol_check_consistency(consistent))[0] is True
    assert handler.fol_query(consistent, "Man(a)") == (True, False)
    assert handler.fol_query(consistent, "!Man(a)") == (False, False)


def test_a_run_without_a_verdict_degrades(eprover, monkeypatch):
    """DoD 2: a timeout is no verdict, not a defect of our input. The sync
    check reads ``None``."""

    def timed_out(*_args, **_kwargs):
        raise RuntimeError("EProver timed out after 60s; no verdict (#2516).")

    monkeypatch.setattr(eprover, "run_eprover", timed_out)
    # The sentinel ran through ``run_eprover`` too: keep its verdict cached.
    monkeypatch.setitem(
        eprover._EPROVER_DELIVERY_RELIABLE, str(eprover._get_eprover_path()), True
    )

    verdict, message, _solver = _handler(eprover).check_consistency_by(
        _INCONSISTENT, solver="eprover"
    )

    assert verdict is None, message


def _pigeonhole(n):
    """``n + 1`` pigeons in ``n`` holes: unsatisfiable, and beyond E's reach in
    seconds for ``n = 9``."""
    lines = [
        f"fof(p{i}, axiom, " + " | ".join(f"h{i}_{j}" for j in range(n)) + ")."
        for i in range(n + 1)
    ]
    count = 0
    for j in range(n):
        for i in range(n + 1):
            for k in range(i + 1, n + 1):
                lines.append(f"fof(c{count}, axiom, ~h{i}_{j} | ~h{k}_{j}).")
                count += 1
    lines.append("fof(q, conjecture, $false).")
    return "\n".join(lines) + "\n"


def _eprover_pids():
    import psutil

    return {
        p.pid
        for p in psutil.process_iter(["name"])
        if (p.info["name"] or "").lower().startswith("eprover")
    }


def test_a_timeout_kills_every_e_process(eprover):
    """DoD 2: the runner stops a runaway search, and ``--auto-schedule``'s
    child goes with its parent (killing the parent alone leaves it running,
    measured on Windows)."""
    from argumentation_analysis.core.eprover_runner import run_eprover

    before = _eprover_pids()

    with pytest.raises(RuntimeError, match="timed out") as raised:
        run_eprover(_pigeonhole(9), eprover._get_eprover_path(), timeout=3)

    assert not isinstance(raised.value, eprover.EProverInputRejected)
    deadline = time.monotonic() + 10
    while _eprover_pids() - before and time.monotonic() < deadline:
        time.sleep(0.5)
    assert not _eprover_pids() - before


@pytest.mark.parametrize("solver", ["tweety", "eprover", "prover9", "mace4"])
@pytest.mark.parametrize(
    "formulas, expected",
    [
        (["forall X: (Man(X))", "!Man(thing)"], False),
        (["forall X: (p(X))", "!p(p)"], False),
        (["!thing(c)"], True),
        (["Man(thing)", "thing(thing)"], True),
    ],
    ids=[
        "a constant named thing",
        "a constant named like a predicate",
        "a predicate named thing",
        "both named thing",
    ],
)
def test_the_builder_names_nothing_like_the_sort_or_a_predicate(
    fol, solver, formulas, expected
):
    """DoD 3: the builder's sets are decided, and alike under every solver.
    ``main``: EProver answered consistent, consistent, inconsistent,
    consistent."""
    from argumentation_analysis.agents.core.logic.fol_logic_agent import (
        FOLLogicAgent,
    )
    from argumentation_analysis.core.mace4_runner import MACE4_EXECUTABLE
    from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

    if solver == "eprover" and fol._get_eprover_path() is None:
        pytest.skip("the EProver binary is not wired on this seat")
    if solver == "prover9" and not PROVER9_EXECUTABLE.is_file():
        pytest.skip("the bundled Prover9 binary is absent on this seat")
    if solver == "mace4" and not MACE4_EXECUTABLE.is_file():
        pytest.skip("the bundled Mace4 binary is absent on this seat")
    meta = FOLLogicAgent.extract_fol_metadata(formulas)
    text = "\n".join(meta["signature_lines"] + [""] + meta["formulas"])

    verdict, message, decided_by = _handler(fol).check_consistency_by(
        text, solver=solver
    )

    assert (verdict, decided_by) == (expected, solver), message


def test_the_eprover_path_is_absolute_where_the_runner_starts_it(eprover):
    """The runner starts E from an argument list, which needs a path the OS
    resolves without the shell."""
    assert os.path.isabs(str(eprover._get_eprover_path()))
