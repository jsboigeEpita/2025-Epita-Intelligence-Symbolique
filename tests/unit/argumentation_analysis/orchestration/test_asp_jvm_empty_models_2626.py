"""#2626: an empty answer-set list from Tweety's ClingoSolver is a verdict
only when clingo itself printed ``UNSATISFIABLE``.

``ClingoSolver.getModels`` returns an empty list in three cases: the program is
unsatisfiable, the binary failed, or its output did not parse (clingo >= 5.5
prints ``Answer: 1 (Time: ...)``). ``_invoke_asp_reasoning`` took the JVM path
first and returned that empty list as ``solver="clingo_jvm"``, zero models,
for a satisfiable program. Its guard rejected only atoms outside the program's
vocabulary, which an empty list never has.

The outputs below are measured, not written by hand: clingo 5.4.0 (the
``settings.jvm.clingo_version`` binary) through Tweety's ``getOutput()``,
pyclingo 5.8.0 on the command line, and the usage error of a binary that is
not clingo. Only the temporary file path is replaced.
"""

import asyncio
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

from argumentation_analysis.core import jvm_setup

SATISFIABLE_PROGRAM = "a.\nb :- a."
UNSATISFIABLE_PROGRAM = "a.\n:- a."

CLINGO_540_SAT = (
    "clingo version 5.4.0\nReading from prog.lp\nSolving...\nAnswer: 1\na b\n"
    "SATISFIABLE\n\nModels       : 1\nCalls        : 1\n"
    "Time         : 0.002s (Solving: 0.00s 1st Model: 0.00s Unsat: 0.00s)\n"
    "CPU Time     : 0.016s\n"
)
CLINGO_540_UNSAT = (
    "clingo version 5.4.0\nReading from prog.lp\nSolving...\nUNSATISFIABLE\n\n"
    "Models       : 0\nCalls        : 1\n"
    "Time         : 0.001s (Solving: 0.00s 1st Model: 0.00s Unsat: 0.00s)\n"
    "CPU Time     : 0.000s\n"
)
CLINGO_580_SAT = (
    "pyclingo version 5.8.0\nReading from stdin\nSolving...\n"
    "Answer: 1 (Time: 0.003s)\na b\nSATISFIABLE\n\nModels       : 1+\n"
    "Calls        : 1\n"
    "Time         : 0.003s (Solving: 0.00s 1st Model: 0.00s Unsat: 0.00s)\n"
    "CPU Time     : 0.000s\n"
)
NOT_CLINGO_USAGE = (
    "Unknown option: -n\n"
    "usage: clingo [option] ... [-c cmd | -m mod | file | -] [arg] ...\n"
    "Try `python -h' for more information.\n"
)


def _run(program):
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_asp_reasoning,
    )

    return asyncio.new_event_loop().run_until_complete(
        _invoke_asp_reasoning(program, {})
    )


def _python_clingo_available():
    try:
        import clingo  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.parametrize(
    "output, unsatisfiable",
    [
        (CLINGO_540_UNSAT, True),
        (CLINGO_540_SAT, False),
        (CLINGO_580_SAT, False),
        (NOT_CLINGO_USAGE, False),
        ("", False),
        (None, False),
    ],
    ids=["540-unsat", "540-sat", "580-sat", "not-clingo", "empty", "none"],
)
def test_only_clingos_unsatisfiable_line_is_a_verdict(output, unsatisfiable):
    """``SATISFIABLE`` is a substring of ``UNSATISFIABLE``: the check is on the
    whole line, so a satisfiable output never reads as unsatisfiable."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _clingo_reported_unsatisfiable,
    )

    assert _clingo_reported_unsatisfiable(output) is unsatisfiable


@pytest.fixture
def not_clingo_dir(tmp_path):
    """A directory whose ``clingo`` is not clingo: it exits 2 with a usage
    error. Tweety's ClingoSolver runs it and returns an empty list."""
    if os.name == "nt":
        # A copy of this interpreter rejects Tweety's ``-n`` option. Its
        # DLLs go with it so that it starts outside its own directory.
        exe_dir = Path(sys.executable).parent
        shutil.copy2(sys.executable, tmp_path / "clingo.exe")
        for dll in exe_dir.glob("*.dll"):
            shutil.copy2(dll, tmp_path / dll.name)
    else:
        script = tmp_path / "clingo"
        script.write_text(
            "#!/bin/sh\necho 'Unknown option: -n' >&2\nexit 2\n", encoding="utf-8"
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return tmp_path


def test_empty_models_from_a_failed_binary_are_not_a_verdict(
    not_clingo_dir, monkeypatch
):
    """The JVM path runs a binary that fails. ``main`` returned
    ``solver="clingo_jvm"`` with zero models for a satisfiable program."""
    if not jvm_setup.is_jvm_started():
        pytest.skip("the JVM is not started: the clingo_jvm path is not taken")
    monkeypatch.setitem(jvm_setup.EXTERNAL_TOOL_PATHS, "clingo", str(not_clingo_dir))

    res = _run(SATISFIABLE_PROGRAM)

    assert res["solver"] != "clingo_jvm", res
    assert res.get("jvm_refused", "").startswith("ClingoJvmEmptyModels"), res
    if _python_clingo_available():
        assert res["solver"] == "clingo_python", res
        assert {"a", "b"} in [set(m) for m in res["answer_sets"]], res
        assert res["satisfiable"] is True, res


def test_python_binding_states_unsatisfiable(monkeypatch):
    """Without the JVM path, an unsatisfiable program is an explicit verdict,
    not only an empty list."""
    if not _python_clingo_available():
        pytest.skip("the clingo Python package is not installed")
    monkeypatch.setattr(jvm_setup, "is_jvm_started", lambda: False)

    res = _run(UNSATISFIABLE_PROGRAM)

    assert (res["solver"], res["answer_sets"], res["satisfiable"]) == (
        "clingo_python",
        [],
        False,
    ), res
    assert "jvm_refused" not in res, res


def _real_clingo_registered():
    path = jvm_setup.EXTERNAL_TOOL_PATHS.get("clingo")
    return bool(path) and jvm_setup.is_jvm_started()


@pytest.mark.parametrize(
    "program, answer_sets, satisfiable",
    [
        (SATISFIABLE_PROGRAM, [{"a", "b"}], True),
        (UNSATISFIABLE_PROGRAM, [], False),
    ],
    ids=["sat", "unsat"],
)
def test_real_clingo_binary_decides_on_the_jvm_path(program, answer_sets, satisfiable):
    """Control: with a working clingo registered, the JVM path keeps deciding,
    and an unsatisfiable program stays a ``clingo_jvm`` verdict. Runs only
    where ``ext_tools/clingo`` is provisioned (gitignored, absent in CI)."""
    if not _real_clingo_registered():
        pytest.skip("no clingo binary registered in EXTERNAL_TOOL_PATHS")

    res = _run(program)

    assert res["solver"] == "clingo_jvm", res
    assert [set(m) for m in res["answer_sets"]] == answer_sets, res
    assert res["satisfiable"] is satisfiable, res
    assert "jvm_refused" not in res, res
