"""#2346 (Fragile, the section's most serious item): ``TracedAgent`` used to
configure the **root** logger with ``logging.basicConfig(force=True)``.

Wrapping one agent removed every handler the application had installed,
sent the whole process's logging into that agent's trace file, and a second
traced agent truncated the first one's file and took the root over again.
A trace now writes to its own file through its own logger and leaves the
logging configuration of the process alone.
"""

import logging
from types import SimpleNamespace

from argumentation_analysis.agents.utils.tracer import TracedAgent


def _agent(name):
    return SimpleNamespace(name=name)


def _read(path):
    return path.read_text(encoding="utf-8")


def _close(traced):
    # Tolerates the pre-#2346 class, which had no ``close``: the born-red run
    # then fails on the logging behaviour itself, not on a missing method.
    getattr(traced, "close", lambda: None)()


def test_root_logging_configuration_is_left_alone(tmp_path):
    root = logging.getLogger()
    marker = logging.NullHandler()
    root.addHandler(marker)
    handlers_before = list(root.handlers)
    level_before = root.level
    try:
        traced = TracedAgent(_agent("A"), str(tmp_path / "a.log"))
        try:
            assert root.handlers == handlers_before
            assert root.level == level_before
        finally:
            _close(traced)
    finally:
        root.removeHandler(marker)


def test_application_logs_stay_out_of_the_trace(tmp_path):
    trace = tmp_path / "a.log"
    traced = TracedAgent(_agent("A"), str(trace))
    try:
        logging.getLogger("some.application.module").warning("APP_LINE")
    finally:
        _close(traced)
    content = _read(trace)
    assert "TracedAgent for 'A' enabled" in content
    assert "APP_LINE" not in content


def test_two_traces_keep_their_own_files(tmp_path):
    first, second = tmp_path / "a.log", tmp_path / "b.log"
    a = TracedAgent(_agent("A"), str(first))
    b = TracedAgent(_agent("B"), str(second))
    try:
        a._logger.info("LINE_FROM_A")
        b._logger.info("LINE_FROM_B")
    finally:
        _close(a)
        _close(b)
    assert "LINE_FROM_A" in _read(first) and "LINE_FROM_B" not in _read(first)
    assert "LINE_FROM_B" in _read(second) and "LINE_FROM_A" not in _read(second)
    assert "TracedAgent for 'A' enabled" in _read(first)


def test_trace_file_is_rewritten_per_run(tmp_path):
    """Control: a trace file holds one run, as before (mode ``w``)."""
    trace = tmp_path / "a.log"
    trace.write_text("STALE\n", encoding="utf-8")
    traced = TracedAgent(_agent("A"), str(trace))
    _close(traced)
    assert "STALE" not in _read(trace)
