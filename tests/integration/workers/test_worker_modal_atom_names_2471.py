# -*- coding: utf-8 -*-
"""#2471 on the real JVM: the pipeline's modal phase decides a KB whose atoms
need renaming, and decides it right, with either modal solver.

Measured on ``main`` with the TWEETY solver: the three ``renamed-*`` sets were
decided ``False`` (two atoms merged into one) and the ``accented`` set was left
undetermined (``Illegal characters in predicate definition``). The controls
were ``False`` then and stay ``False``. Synthetic atoms only.

The SPASS cases run where the vendored SPASS binary is wired (CI, and seats
with ``ext_tools/spass``): the modal phase routes to it by default there.
"""

import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2471 modal tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]


@pytest.fixture(params=["tweety", "spass"])
def modal_solver(request):
    """Pin the solver the modal phase uses, on the settings object it reads.

    ``settings`` is resolved here, not at import: a test that reloads
    ``core.config`` gives the module a new ``settings`` object and a new
    ``ModalSolverChoice`` class (#1804), and a pin on the old object is inert.
    TWEETY is ``SimpleMlReasoner``; SPASS is the vendored binary, which the
    phase routes to when ``modal_prefer_spass_when_available`` is set.
    """
    from argumentation_analysis.agents.core.logic.modal_handler import (
        _get_spass_path,
    )
    from argumentation_analysis.core import config
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    initialize_jvm()
    if request.param == "spass" and _get_spass_path() is None:
        pytest.skip("the vendored SPASS binary is not wired on this seat")

    settings = config.settings
    previous = settings.modal_solver
    previous_prefer = settings.modal_prefer_spass_when_available
    settings.modal_solver = config.ModalSolverChoice.TWEETY
    object.__setattr__(
        settings, "modal_prefer_spass_when_available", request.param == "spass"
    )
    try:
        yield request.param
    finally:
        settings.modal_solver = previous
        object.__setattr__(
            settings, "modal_prefer_spass_when_available", previous_prefer
        )


def _nl(*formulas):
    return {
        "phase_nl_to_logic_output": {
            "translations": [{"is_valid": True, "formula": f} for f in formulas]
        }
    }


CASES = {
    "renamed-next-to-legal": (
        {
            "formulas": [
                "type(heavy_rain)",
                "type(HeavyRain)",
                "heavy_rain",
                "!HeavyRain",
            ]
        },
        True,
    ),
    "renamed-legal-first": (
        {
            "formulas": [
                "type(HeavyRain)",
                "type(heavy_rain)",
                "!HeavyRain",
                "heavy_rain",
            ]
        },
        True,
    ),
    "renamed-same-stem-nl": (_nl("heavy_rain", "!heavy__rain"), True),
    "accented-next-to-plain": (
        {"formulas": ["type(été)", "type(ete)", "été", "!ete"]},
        True,
    ),
    "control-direct": (
        {"formulas": ["type(heavy_rain)", "heavy_rain", "!heavy_rain"]},
        False,
    ),
    "control-nl": (_nl("heavy_rain", "!heavy_rain"), False),
}


@pytest.mark.parametrize(
    "context, expected", list(CASES.values()), ids=list(CASES.keys())
)
async def test_the_modal_phase_decides_renamed_atoms(context, expected, modal_solver):
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_modal_logic,
    )

    result = await _invoke_modal_logic("ignored", context)
    assert result.get("valid") is expected, result.get("message")
    # Control: the pin took effect, so the verdict is the named solver's.
    assert result.get("solver") == modal_solver
