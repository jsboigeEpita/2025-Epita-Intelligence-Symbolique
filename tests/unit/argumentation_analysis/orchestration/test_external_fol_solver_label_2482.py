# -*- coding: utf-8 -*-
"""#2482: the external FOL phase names the solver that decided.

``main`` chose the label from its own probe (EProver on ``PATH``), while the
handler finds EProver through ``jvm_setup``'s registry. Measured on a seat
where the two disagree: the result said ``solver: "tweety"`` next to the
handler's own ``FOL consistency check (EProver)``.
"""

import asyncio
from unittest.mock import patch

TWEETY_BRIDGE_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
)


class _Handler:
    """Answers the way ``FOLHandler`` does once EProver has decided."""

    def check_consistency(self, belief_set_input):
        return self.check_consistency_by(belief_set_input)[:2]

    def check_consistency_by(self, belief_set_input, solver=None):
        return True, "FOL consistency check (EProver): consistent", "eprover"


class _Bridge:
    def __init__(self):
        self.fol_handler = _Handler()

    def check_consistency(self, belief_set, logic_type):
        return self.fol_handler.check_consistency(belief_set)


def test_the_double_exposes_nothing_the_handler_lacks():
    from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler

    public = {name for name in dir(_Handler) if not name.startswith("_")}
    assert public - set(dir(FOLHandler)) == set()


def test_the_label_is_the_solver_the_handler_reports():
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_external_fol_solver,
    )

    context = {
        "fol_solver": "eprover",
        "phase_fol_output": {"formulas": ["Man(socrates)"], "fol_signature": []},
    }
    with patch(TWEETY_BRIDGE_PATH, return_value=_Bridge()), patch(
        "shutil.which", return_value=None
    ):
        result = asyncio.run(_invoke_external_fol_solver("", context))

    assert result["solver"] == "eprover", result
    assert "(EProver)" in result["message"]
    assert result["consistent"] is True
