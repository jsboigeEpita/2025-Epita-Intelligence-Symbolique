# -*- coding: utf-8 -*-
"""#2471 on the real JVM: the pipeline's modal phase decides a KB whose atoms
need renaming, and decides it right.

Measured on ``main`` with the TWEETY solver: the three ``renamed-*`` sets were
decided ``False`` (two atoms merged into one) and the ``accented`` set was left
undetermined (``Illegal characters in predicate definition``). The controls
were ``False`` then and stay ``False``. Synthetic atoms only.
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

from argumentation_analysis.core.config import ModalSolverChoice, settings  # noqa: E402


@pytest.fixture
def tweety_solver():
    """Pin the pure-Java solver (SimpleMlReasoner), as #1219's test does."""
    previous = settings.modal_solver
    previous_prefer = settings.modal_prefer_spass_when_available
    settings.modal_solver = ModalSolverChoice.TWEETY
    object.__setattr__(settings, "modal_prefer_spass_when_available", False)
    try:
        yield
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
async def test_the_modal_phase_decides_renamed_atoms(context, expected, tweety_solver):
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_modal_logic,
    )

    initialize_jvm()
    result = await _invoke_modal_logic("ignored", context)
    assert result.get("valid") is expected, result.get("message")
    assert result.get("solver") == "tweety"
