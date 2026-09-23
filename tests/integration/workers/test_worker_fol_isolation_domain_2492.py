# -*- coding: utf-8 -*-
"""#2492 on the real JVM: the FOL phase's isolation net checks each formula
over the set's constants.

Measured on ``main``: the net gave a formula checked alone a signature built
from its own constants. A universal rule has none, so its sort was
``thing = {}``, Tweety refused it, and the net dropped the rule as a poison.
Next to one unparsable formula, the inconsistent set
``{forall X: (Man(X) => Mortal(X)), Man(socrates), !Mortal(socrates)}`` was
published consistent and decided, under every solver. Synthetic predicates
and constants only.
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2492 isolation tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

RULE = "forall X: (Man(X) => Mortal(X))"
# Tweety refuses this one, so the combined check degrades and isolation runs.
UNPARSABLE = "Man(socrates"


@pytest.fixture(params=["tweety", "eprover", "prover9"])
def solver(request):
    """The configured FOL solver, with the JVM up and the pin restored.

    ``settings`` is read from the handler module, the object it decides on
    (#1804).
    """
    from argumentation_analysis.core import config
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    initialize_jvm()
    from argumentation_analysis.agents.core.logic import fol_handler

    if config.settings is not fol_handler.settings:
        pytest.skip("core.config was reloaded; the phase and the handler differ")
    if request.param == "eprover" and fol_handler._get_eprover_path() is None:
        pytest.skip("no EProver binary on this seat")
    if request.param == "prover9":
        from argumentation_analysis.core.prover9_runner import PROVER9_EXECUTABLE

        if not PROVER9_EXECUTABLE.is_file():
            pytest.skip("the bundled Prover9 binary is absent on this seat")
    previous = fol_handler.settings.solver
    fol_handler.settings.solver = fol_handler.SolverChoice(request.param)
    try:
        yield request.param
    finally:
        fol_handler.settings.solver = previous


def _run_fol_phase(formulas):
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_fol_reasoning,
    )

    # A short input: the phase's LLM formula generator stays off.
    context = {
        "phase_extract_output": {"arguments": [{"text": "an argument"}]},
        "formulas": list(formulas),
        "_state_object": None,
    }
    return asyncio.run(_invoke_fol_reasoning("text", context))


@pytest.mark.parametrize("poisoned", [False, True], ids=["control", "poisoned"])
def test_a_rule_without_constants_survives_isolation(solver, poisoned):
    """Born red. The control never enters isolation and decides the set
    inconsistent. Poisoned, ``main`` rejected the rule with the poison and
    published ``{Man(socrates), !Mortal(socrates)}`` consistent."""
    formulas = [RULE, "Man(socrates)", "!Mortal(socrates)"]
    if poisoned:
        formulas.append(UNPARSABLE)

    result = _run_fol_phase(formulas)

    assert result["consistent"] is False, result.get("message")
    assert result["fol_status"] == "decided"
    metrics = result["fol_metrics"]
    if poisoned:
        assert metrics["rejected_formulas"] == [UNPARSABLE]
    else:
        assert "rejected_formulas" not in metrics


def test_quantified_formulas_without_constants_survive_isolation(solver):
    """``exists X: (Mortal(X))`` and ``forall X: (!Mortal(X))`` contradict each
    other. ``main`` dropped both and published ``{Man(socrates)}``
    consistent."""
    formulas = [
        "exists X: (Mortal(X))",
        "forall X: (!Mortal(X))",
        "Man(socrates)",
        UNPARSABLE,
    ]

    result = _run_fol_phase(formulas)

    assert result["consistent"] is False, result.get("message")
    assert result["fol_status"] == "decided"
    assert result["fol_metrics"]["rejected_formulas"] == [UNPARSABLE]


def test_an_arity_conflict_is_never_published_consistent(solver):
    """A control on what the net declares per formula. ``Man`` is used with two
    arities, so the set cannot be declared. Checking each formula under the
    set's whole signature charges ``Man/2`` to ``Man(socrates)`` and the rule,
    drops them, and publishes the rest consistent (measured). The formula
    keeps its own predicates and only borrows the set's constants, so no
    formula is dropped for another one's arity. ``main`` dropped the rule."""
    formulas = ["Man(socrates)", "!Mortal(socrates)", RULE, "Man(socrates, plato)"]

    result = _run_fol_phase(formulas)

    assert result["consistent"] is not True, result.get("message")
    assert RULE not in result["fol_metrics"].get("rejected_formulas", [])
    assert "Man(socrates)" not in result["fol_metrics"].get("rejected_formulas", [])
