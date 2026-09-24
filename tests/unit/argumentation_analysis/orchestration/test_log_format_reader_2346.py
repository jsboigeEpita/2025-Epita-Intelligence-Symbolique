"""#2346: ``LOG_FORMAT`` is read where a run starts, and the library configures nothing.

Before, only ``get_phase_logger`` read ``LOG_FORMAT``, and no production module
calls it, so the knob changed nothing on a real run. Both entry points
formatted with ``basicConfig``, which never prints the correlation id and phase
name the workflow executor attaches to its ``Starting phase`` lines, and whose
call was a no-op anyway: library modules call ``basicConfig`` at import, and the
first one imported wins. The JSON formatter kept a fixed list of fields and
dropped the others the executor passes. And ``get_phase_logger`` attached a
handler of its own the first time it ran, in the format of the first caller.

The entry points are witnessed in a subprocess that runs the real CLI path, so
every import-time configuration of the real import graph has happened first.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from argumentation_analysis.orchestration.structured_logging import (
    JsonFormatter,
    get_phase_logger,
)

REPO = Path(__file__).resolve().parents[4]
CID = "c2346abc-0000-4000-8000-000000000000"

# Each entry point runs its real __main__ path, then the executor's line is emitted.
ENTRY_POINTS = {
    "run_orchestration": (
        "run_module",
        "argumentation_analysis.run_orchestration",
        ["run_orchestration.py", "--list-workflows"],
    ),
    "compare_orchestration_modes": (
        "run_path",
        "scripts/compare_orchestration_modes.py",
        ["compare_orchestration_modes.py", "--modes", "unknown_mode_2346"],
    ),
}

_WITNESS = """
import logging, runpy, sys
sys.argv = {argv!r}
try:
    runpy.{runner}({target!r}, run_name="__main__")
except SystemExit as stop:
    assert stop.code in (None, 0, 2), stop.code
from argumentation_analysis.orchestration.structured_logging import PhaseLogger
PhaseLogger(
    logging.getLogger("orchestration.workflow_executor"), correlation_id={cid!r}
).info(
    "Starting phase", extra={{"phase_name": "extract", "capability": "fact_extraction"}}
)
"""


def _executor_line(entry, log_format):
    """The executor's ``Starting phase`` line, as a real run of the entry point prints it."""
    runner, target, argv = ENTRY_POINTS[entry]
    env = {k: v for k, v in os.environ.items() if k != "LOG_FORMAT"}
    if log_format is not None:
        env["LOG_FORMAT"] = log_format
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            _WITNESS.format(argv=argv, runner=runner, target=target, cid=CID),
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    lines = [line for line in done.stderr.splitlines() if CID[:8] in line]
    assert len(lines) == 1, (lines, done.stderr[-3000:])
    return lines[0]


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS))
def test_log_format_json_prints_one_json_object_per_line(entry):
    record = json.loads(_executor_line(entry, "json"))
    assert record["logger"] == "orchestration.workflow_executor"
    assert record["correlation_id"] == CID
    assert record["phase_name"] == "extract"
    assert record["capability"] == "fact_extraction"


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS))
def test_the_default_format_names_the_run_and_the_phase(entry):
    line = _executor_line(entry, None)
    assert line.startswith(f"[{CID[:8]}] [extract] "), line
    assert "[orchestration.workflow_executor] Starting phase" in line


def test_json_keeps_every_field_the_executor_passes():
    """The executor's closing line passes lists no fixed field list named."""
    record = logging.LogRecord(
        "orchestration.workflow_executor",
        logging.INFO,
        __file__,
        1,
        "Workflow finished",
        (),
        None,
    )
    record.correlation_id = CID
    record.phases_degraded = ["fol_validate"]
    record.structured_arg_degraded = ["aspic_plus"]
    printed = json.loads(JsonFormatter().format(record))
    assert printed["phases_degraded"] == ["fol_validate"]
    assert printed["structured_arg_degraded"] == ["aspic_plus"]
    assert "args" not in printed and "msg" not in printed


def test_get_phase_logger_leaves_the_logging_configuration_alone():
    get_phase_logger("test_2346", correlation_id=CID)
    own = [
        handler
        for handler in logging.getLogger(
            "argumentation_analysis.orchestration"
        ).handlers
        if handler.formatter is not None
        and type(handler.formatter).__module__.endswith("structured_logging")
    ]
    assert own == []
