"""#3540 — the native-failure watch reads the batch log against the three triggers.

The three families of #2005, #2080 and #2894 each carry their trigger in
their own thread; a cycle's logs used to be read for the ``Verdict:`` line
only, so a trigger that fired was seen only if someone remembered to grep
for it. The counter below reads ``pipeline.log`` per family, at the end of
a cycle; the page ``docs/guides/NATIVE_FAILURES_WATCH.md`` holds each
signature, its state on ``main``, its unpark/reopen trigger and the grep
that tests it — with ONE source for the patterns (the runner's table, ask
2), checked here.

Free by construction: synthetic logs in ``tmp_path``, one real dump from
the #2080 positive-control child, no key, no network, no corpus. Synthetic
lines carry no document identifier (rule 7): the log bodies are invented,
the tags are the panel's opaque ids.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PAGE = REPO_ROOT / "docs" / "guides" / "NATIVE_FAILURES_WATCH.md"

# The trigger lines, in the shapes the issue pins (exact, case-sensitive):
# a faulthandler dump says "most recent call FIRST", a Python traceback
# says "most recent call last" — the discriminant of case 3.
ARMED = "[doc_A] teardown watchdog armed (60s, pid=1): silence followed"
DUMP_BLOCK = (
    "Timeout (0:01:00)!\n"
    "Thread 0x0000000000001234 (most recent call first):\n"
    '  File "x.py", line 1 in f\n'
)


def _counts(text: str) -> dict:
    """Lazily import the runner's counter and read a synthetic log."""
    from scripts.panel.run_cycle import native_watch

    return native_watch(text)


class TestNativeWatchCounts:
    def test_two_armed_lines_no_dump(self, tmp_path):
        log = tmp_path / "pipeline.log"
        log.write_text(f"{ARMED}\n{ARMED}\n", encoding="utf-8")
        from scripts.panel.run_cycle import native_watch_log

        counts = native_watch_log(log)
        assert counts["teardown_armed"] == 2
        assert counts["teardown_dumps"] == 0

    def test_armed_lines_with_one_dump(self, tmp_path):
        log = tmp_path / "pipeline.log"
        log.write_text(f"{ARMED}\n{ARMED}\n{DUMP_BLOCK}", encoding="utf-8")
        from scripts.panel.run_cycle import native_watch_log

        counts = native_watch_log(log)
        assert counts["teardown_armed"] == 2
        assert counts["teardown_dumps"] == 1

    def test_a_python_traceback_is_not_a_dump(self):
        # The discriminant: a traceback reads "most recent call LAST" — a
        # faulthandler dump alone reads "most recent call first". A pattern
        # matching "most recent call" (the mutation) turns this case red.
        counts = _counts("Traceback (most recent call last):\n  File ...\n")
        assert counts["teardown_dumps"] == 0

    def test_pybind11_signature_counts_once(self):
        counts = _counts("  File ... pybind11::handle::dec_ref() ...\n")
        assert counts["pybind11_signature"] == 1

    def test_the_french_trap_word_is_not_gil(self):
        # A case-insensitive "GIL" grep matches French words of the prompts
        # (#2080 body): "fragilise" must count nothing.
        counts = _counts("le rapport fragilise la lecture\n")
        assert counts["pybind11_signature"] == 0
        assert counts["fatal_abort"] == 0
        assert counts["teardown_dumps"] == 0

    def test_jpype_terminate_counts_once(self):
        counts = _counts("_JTerminate\n")
        assert counts["jpype_terminate"] == 1

    def test_fatal_abort_counts_once(self):
        counts = _counts("Fatal Python error: something\n")
        assert counts["fatal_abort"] == 1

    def test_absent_log_says_absent_not_zero(self, tmp_path):
        from scripts.panel.run_cycle import native_watch_log

        counts = native_watch_log(tmp_path / "does_not_exist.log")
        assert counts["absent"] is True

    def test_end_of_cycle_report_names_the_trigger_issue(self, capsys):
        from scripts.panel.run_cycle import report_native_watch

        report_native_watch({"teardown_armed": 114, "teardown_dumps": 1})
        out = capsys.readouterr().out
        assert "teardown_dumps=1" in out
        assert "#2080" in out

    def test_the_silent_log_prints_nothing(self, capsys):
        from scripts.panel.run_cycle import report_native_watch

        report_native_watch({"teardown_armed": 114, "teardown_dumps": 0})
        out = capsys.readouterr().out
        assert "teardown_dumps=0" not in out
        assert "#2080" not in out


class TestOneSourceOfPatterns:
    def test_every_pattern_appears_on_the_page(self):
        """Ask 2 — the patterns are defined ONCE, in the runner's table; the
        page carries each of them (the grep it prints is the one the code
        runs). A pattern typed twice, diverging, fails this test."""
        from scripts.panel.run_cycle import NATIVE_PATTERNS

        page = PAGE.read_text(encoding="utf-8")
        for name, pattern in NATIVE_PATTERNS.items():
            assert pattern in page, (
                f"pattern {name!r} ({pattern!r}) is not on "
                "docs/guides/NATIVE_FAILURES_WATCH.md — the page must carry "
                "the very string the runner counts"
            )

    def test_the_page_names_the_three_issues(self):
        page = PAGE.read_text(encoding="utf-8")
        for issue in ("#2005", "#2080", "#2894"):
            assert issue in page


class TestPositiveControlRealDump:
    def test_a_real_hang_dump_reads_as_one_dump(self, tmp_path):
        """Not a typed dump: the #2080 child's REAL faulthandler dump of a
        hung teardown must count as teardown_dumps == 1. The child runs a
        plain process: nest_asyncio under pytest skips the teardown
        sequence, so the hang under test cannot exist in-process.

        Measured on that real dump: it lists EVERY thread — 3 thread
        headers each carrying "(most recent call first):", against ONE
        "Timeout (" line. The counter counts the dump EVENT (the one-shot
        Timeout line), never the thread count; the armed line goes to the
        child's stderr, not into this file (armed == 0 here; the armed>0
        cases are the synthetic ones above).
        """
        from tests.unit.scripts.test_teardown_watchdog_2080 import (
            _POSITIVE_CONTROL_CHILD,
        )

        dump_file = tmp_path / "watchdog.log"
        report_file = tmp_path / "control.json"
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                _POSITIVE_CONTROL_CHILD,
                str(REPO_ROOT),
                str(dump_file),
                str(report_file),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert report["elapsed"] >= 3.5, (
            f"teardown returned in {report['elapsed']:.2f}s — no hang, so "
            "the dump under test was never proven real"
        )
        from scripts.panel.run_cycle import native_watch_log

        counts = native_watch_log(dump_file)
        assert counts["teardown_dumps"] == 1
        assert counts["teardown_armed"] == 0
