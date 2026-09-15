"""Né-rouge guards for #2096 residual anomalies #3, #4, #5.

Measured on the pristine tree (base ``045edcb9``):

- #3: the ``generate_counter_argument`` docstring advertised
  "reductio ad absurdum, counter-example, distinction, reformulation,
  and concession" — three of those five terms exist in NEITHER enum of
  ``agents/core/counter_argument/definitions.py``, and the generation
  surface is driven by ``RhetoricalStrategy`` (``strategies.py`` maps
  every strategy to its prompt), whose five values are none of
  "distinction" / "reformulation" / "concession".
- #4: ``scripts/testing/run_mcp_tests.ps1`` invokes pytest on
  ``tests/unit/services/test_mcp_server.py`` — a path that does not
  exist (the living file is under
  ``tests/unit/argumentation_analysis/services/``; the old location
  survives only as ``tests/unit/services/_archived/``).
- #5: the v2 registration ``except`` (``main.py:_register_v2_tools``)
  logs the exception but not the consequence — a reader of the log
  cannot tell the server is running degraded on base tools only.
"""

import re
from pathlib import Path

from argumentation_analysis.agents.core.counter_argument.definitions import (
    RhetoricalStrategy,
)
from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
    register_specialized_tools,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
REAL_STRATEGIES = {s.value for s in RhetoricalStrategy}


class _ToolRecorder:
    """Stand-in for the FastMCP instance: captures decorated tools."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def _docstring_of(tool_name: str) -> str:
    recorder = _ToolRecorder()
    register_specialized_tools(recorder, get_registry=lambda: None)
    doc = recorder.tools[tool_name].__doc__
    assert doc, f"tool {tool_name} must keep a docstring"
    return doc


def test_generate_counter_argument_docstring_lists_real_strategies():
    doc = _docstring_of("generate_counter_argument")
    match = re.search(r"Strategies include ([^.]+)\.", doc)
    assert match, "docstring must enumerate its strategies"
    listed = set()
    for term in match.group(1).split(","):
        term = re.sub(r"^and\s+", "", term.strip())
        if term:
            listed.add(term.replace(" ", "_").lower())
    assert listed == REAL_STRATEGIES, (
        f"docstring strategies {sorted(listed)} != RhetoricalStrategy "
        f"{sorted(REAL_STRATEGIES)}"
    )


def test_run_mcp_tests_ps1_targets_existing_paths():
    ps1 = REPO_ROOT / "scripts" / "testing" / "run_mcp_tests.ps1"
    body = ps1.read_text(encoding="utf-8", errors="replace")
    targets = re.findall(r"([\w./-]+\.py)\b", body)
    assert targets, "the runner must reference at least one test path"
    for target in targets:
        assert (
            REPO_ROOT / target
        ).exists(), f"dead path in run_mcp_tests.ps1: {target}"


def test_v2_registration_warning_names_the_degradation():
    src = (
        REPO_ROOT / "argumentation_analysis" / "services" / "mcp_server" / "main.py"
    ).read_text(encoding="utf-8", errors="replace")
    warnings = re.findall(r'V2 tools not registered[^"]*', src)
    assert warnings, "v2 registration except must keep its warning"
    for message in warnings:
        assert re.search(r"base tools|degraded", message), (
            "the warning must name the consequence: server degraded to "
            f"base tools only — got: {message!r}"
        )
