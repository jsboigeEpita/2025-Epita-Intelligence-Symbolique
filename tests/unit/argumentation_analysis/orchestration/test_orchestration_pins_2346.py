"""#2346: two orchestration invariants that nothing pinned.

- ``ProgressMonitor.detect_critical_issues`` reports a task as late once its
  elapsed time *reaches* its estimate (``>=``). That comparison was corrected
  from ``>`` and no test held the boundary, so it could slip back silently.
- ``state_writers`` keeps three module-level tables per structured formalism:
  input keys, display name, absent reason. Each is read with ``.get`` and a
  fallback, so a formalism missing from one table degrades silently. For the
  input keys, the fallback ``()`` files genuine input as absent.
"""

import ast
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from argumentation_analysis.orchestration import state_writers
from argumentation_analysis.orchestration.hierarchical.tactical import monitor as mon
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)

START = datetime(2026, 1, 1, 12, 0, 0)
ESTIMATE = 600


class _FrozenClock(datetime):
    frozen = START

    @classmethod
    def now(cls, tz=None):
        return cls.frozen


def _delayed_after(monkeypatch, elapsed_seconds):
    monkeypatch.setattr(mon, "datetime", _FrozenClock)
    monkeypatch.setattr(
        _FrozenClock, "frozen", START + timedelta(seconds=elapsed_seconds)
    )
    state = TacticalState()
    state.add_task(
        {
            "id": "t1",
            "description": "Task t1",
            "objective_id": "obj1",
            "start_time": START.isoformat(),
            "estimated_duration": ESTIMATE,
        },
        status="in_progress",
    )
    state.task_progress["t1"] = 0.5
    issues = mon.ProgressMonitor(tactical_state=state).detect_critical_issues()
    return [i for i in issues if i["type"] == "delayed_task"]


class TestOverdueBoundary:
    def test_a_task_that_reaches_its_estimate_is_late(self, monkeypatch):
        assert len(_delayed_after(monkeypatch, ESTIMATE)) == 1

    def test_a_task_one_second_short_of_its_estimate_is_not_late(self, monkeypatch):
        """Control: the frozen clock drives the comparison."""
        assert _delayed_after(monkeypatch, ESTIMATE - 1) == []


def _recorded_formalisms():
    """The capabilities passed to ``_record_structured_arg_status`` in the module."""
    tree = ast.parse(
        Path(state_writers.__file__).read_text(encoding="utf-8-sig"),
    )
    recorded = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_record_structured_arg_status"
        ):
            capability = node.args[1]
            assert isinstance(capability, ast.Constant) and isinstance(
                capability.value, str
            ), ast.dump(capability)
            recorded.add(capability.value)
    assert recorded, "no call to _record_structured_arg_status was found"
    return recorded


@pytest.mark.parametrize(
    "table",
    [
        "_STRUCTURED_ARG_INPUT_KEYS",
        "_STRUCTURED_ARG_FORMALISM_NAME",
        "_STRUCTURED_ARG_ABSENT_REASON",
    ],
)
def test_every_recorded_formalism_has_an_entry_in_each_table(table):
    assert set(getattr(state_writers, table)) == _recorded_formalisms()
