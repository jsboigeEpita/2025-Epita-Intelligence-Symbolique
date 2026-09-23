# -*- coding: utf-8 -*-
"""#2491 on the real JVM and the bundled binaries: in the FOL backend
comparison, a defect of our solver input is not an unavailable backend.

Measured on ``main``: ``compare_fol_backends`` recorded every backend
exception as ``{"available": False, "note": "unavailable: …"}``. When Prover9
or Mace4 refused the input our builder made, the comparison said the binary
was missing; when the LADR writer could not write a formula, both LADR
backends read missing and Tweety and EProver were left to agree. Its two
readers kept that reading: the FOL phase published the comparison with the
backend unavailable, and the multi-axis harness reported the whole axis
unavailable. Synthetic predicates and constants only.
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
        reason="#2491 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# LADR the solvers refuse, as a regression of the builder would produce it.
_MALFORMED = "formulas(assumptions).\nthis is (not ladr.\nend_of_list.\n"
_KB = "thing = {a, b}\ntype(Man(thing))\nMan(a)\n!Man(b)"
_FORMULAS = ["forall X: (Man(X) => Mortal(X))", "Man(socrates)", "Mortal(plato)"]


@pytest.fixture
def fol():
    """The handler module, with the JVM up and the solver pin restored."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.core.mace4_runner import MACE4_EXECUTABLE
    from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

    initialize_jvm()
    if not (PROVER9_EXECUTABLE.is_file() and MACE4_EXECUTABLE.is_file()):
        pytest.skip("the bundled Prover9/Mace4 binaries are absent on this seat")
    from argumentation_analysis.agents.core.logic import fol_handler

    previous = fol_handler.settings.solver
    try:
        yield fol_handler
    finally:
        fol_handler.settings.solver = previous


def _compare(fol):
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    handler = fol.FOLHandler(TweetyBridge().initializer)
    return asyncio.run(handler.compare_fol_backends(_KB))


def _prover9_refuses(fol, monkeypatch):
    monkeypatch.setattr(fol, "_prover9_input", lambda *_args: _MALFORMED)


def _mace4_refuses(fol, monkeypatch):
    # The delivery sentinel runs Mace4 once per binary and caches the result:
    # run it for real before Mace4 starts receiving the malformed input.
    assert fol._mace4_delivery_is_reliable()
    real = fol.run_mace4
    monkeypatch.setattr(fol, "run_mace4", lambda *_a, **_k: real(_MALFORMED))


def _writer_refuses(fol, monkeypatch):
    def refuse(*_args):
        raise fol.UnwritableFormula("no LADR text for the term Zed")

    monkeypatch.setattr(fol, "_ladr_text", refuse)


def test_a_refused_prover9_input_is_not_an_unavailable_prover9(fol, monkeypatch):
    """DoD 1. ``main`` reported ``prover9: available False``."""
    _prover9_refuses(fol, monkeypatch)

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        _compare(fol)
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_a_refused_mace4_input_is_not_an_unavailable_mace4(fol, monkeypatch):
    """``main`` reported ``mace4: available False``, next to a decided
    Prover9."""
    _mace4_refuses(fol, monkeypatch)

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        _compare(fol)
    assert type(raised.value).__name__ == "Mace4InputRejected"


def test_an_unwritable_formula_is_not_two_unavailable_backends(fol, monkeypatch):
    """``main`` reported both LADR backends unavailable, and Tweety and
    EProver agreed with each other."""
    _writer_refuses(fol, monkeypatch)

    with pytest.raises(fol.UnwritableFormula, match="Zed"):
        _compare(fol)


def test_an_absent_prover9_is_still_unavailable(fol, monkeypatch, tmp_path):
    """DoD 2, control: a binary that is not there is ``available: False``,
    and the comparison still reports the other backends."""
    from argumentation_analysis.core import prover9_runner

    monkeypatch.setattr(prover9_runner, "PROVER9_EXECUTABLE", tmp_path / "none.bat")

    comparison = _compare(fol)

    prover9 = comparison["backends"]["prover9"]
    assert (prover9["available"], prover9["verdict"]) == (False, None), prover9
    assert "not found" in prover9["note"], prover9
    assert comparison["backends"]["mace4"]["verdict"] is True, comparison


def test_a_mace4_timeout_is_still_unavailable(fol, monkeypatch):
    """Control: a timeout is the environment's failure, not the builder's."""
    from argumentation_analysis.core import mace4_runner

    assert fol._mace4_delivery_is_reliable()

    def hang(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="mace4", timeout=30)

    monkeypatch.setattr(mace4_runner.subprocess, "run", hang)

    comparison = _compare(fol)

    mace4 = comparison["backends"]["mace4"]
    assert (mace4["available"], mace4["verdict"]) == (False, None), mace4
    assert "timed out" in mace4["note"], mace4


def test_the_real_builder_is_decided_by_both_ladr_backends(fol):
    """Control: with the real builder, Prover9 and Mace4 decide."""
    comparison = _compare(fol)

    assert comparison["decided"].get("prover9") is True, comparison
    assert comparison["decided"].get("mace4") is True, comparison


def _fol_phase_context(fol):
    from argumentation_analysis.core import config

    if config.settings is not fol.settings:
        pytest.skip("core.config was reloaded; the phase and the handler differ")
    # The primary check stays in-JVM, so only the comparison meets the refusal.
    fol.settings.solver = fol.SolverChoice.TWEETY
    return {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(_FORMULAS),
        "_state_object": None,
        "compare_backends": True,
    }


def test_a_refused_input_fails_the_fol_phase(fol, monkeypatch):
    """DoD 3. The phase that publishes ``fol_backend_comparison`` ends FAILED
    with the binary's text. ``main`` completed it and published Prover9
    unavailable in the comparison."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )
    from argumentation_analysis.orchestration.workflow_dsl import (
        PhaseStatus,
        WorkflowBuilder,
        WorkflowExecutor,
    )

    context = _fol_phase_context(fol)
    _prover9_refuses(fol, monkeypatch)
    provider = MagicMock()
    provider.name = "fol_reasoning"
    provider.invoke = _invoke_fol_reasoning
    registry = MagicMock()
    registry.find_for_capability = lambda _cap: [provider]
    workflow = WorkflowBuilder("t2491").add_phase("fol", capability="fol").build()

    results = asyncio.run(
        WorkflowExecutor(registry).execute(workflow, input_data="text", context=context)
    )

    assert results["fol"].status == PhaseStatus.FAILED, results["fol"]
    assert "Fatal error" in (results["fol"].error or ""), results["fol"]


def test_the_fol_phase_still_publishes_an_absent_prover9(fol, monkeypatch, tmp_path):
    """Control for DoD 3: an absent binary is still published in the phase's
    comparison, and the phase completes."""
    from argumentation_analysis.core import prover9_runner
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    context = _fol_phase_context(fol)
    monkeypatch.setattr(prover9_runner, "PROVER9_EXECUTABLE", tmp_path / "none.bat")

    result = asyncio.run(_invoke_fol_reasoning("text", context))

    prover9 = result["fol_backend_comparison"]["backends"]["prover9"]
    assert prover9["available"] is False, prover9


def test_a_failing_comparison_still_leaves_the_fol_phase_its_verdict(fol, monkeypatch):
    """Control for DoD 3: any other comparison failure is still best-effort.
    The phase completes with its primary verdict and publishes no
    comparison."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    context = _fol_phase_context(fol)

    async def broken(self, _belief_set):
        raise RuntimeError("comparison down")

    monkeypatch.setattr(fol.FOLHandler, "compare_fol_backends", broken)

    result = asyncio.run(_invoke_fol_reasoning("text", context))

    assert "fol_backend_comparison" not in result, result
    assert result["consistent"] is True, result


def test_a_refused_input_is_not_an_unavailable_axis(fol, monkeypatch):
    """The multi-axis harness lets the defect through; ``main`` reported the
    FOL axis unavailable."""
    from argumentation_analysis.orchestration.invoke_callables import (
        compare_all_axes,
    )

    _prover9_refuses(fol, monkeypatch)

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        asyncio.run(compare_all_axes(axes=["fol"], fol_belief_set=_KB))
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_a_refused_input_fails_the_multi_axis_phase(fol, monkeypatch):
    """The phase that runs the harness (``multi_axis_compare``) does not catch
    it either, so the executor fails the phase; ``main`` completed it with the
    FOL axis unavailable."""
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_multi_axis_compare,
    )

    _prover9_refuses(fol, monkeypatch)
    context = {"multi_axis": {"axes": ["fol"], "fol_belief_set": _KB}}

    with pytest.raises(RuntimeError, match="Fatal error") as raised:
        asyncio.run(_invoke_multi_axis_compare("text", context))
    assert type(raised.value).__name__ == "Prover9InputRejected"


def test_a_failing_comparator_is_still_an_unavailable_axis():
    """Control: any other comparator failure still reads as an unavailable
    axis, and the harness does not raise."""
    from argumentation_analysis.orchestration.invoke_callables import (
        compare_all_axes,
    )

    async def broken(_belief_set):
        raise RuntimeError("comparator down")

    report = asyncio.run(
        compare_all_axes(axes=["fol"], fol_belief_set=_KB, fol_compare_fn=broken)
    )

    axis = report["axes"]["fol"]
    assert (axis["available"], axis["note"]) == (False, "unavailable: comparator down")
