"""#3120 — the LLM egress counter must be one aggregate under pytest-xdist.

Measured on the coordinator's seat (main `23cf6df02`): the same control file
printed 9/1/1 single-process and 0/0/0 under `-n 2`, with "the non-vacuity
control did NOT run in this session" — the controller printed its own empty
counter while the workers, which saw the requests, were never asked. The
canonical ``llm_egress_report.json`` written under ``--junitxml`` carried the
same vacuous zeros, so ``scripts/ci/llm_egress_gate.py`` would read a
measured-looking 0 from any ``-n`` run.

The repair: each worker ships its request records in ``config.workeroutput``
at ``pytest_sessionfinish``; the controller collects them in
``pytest_testnodedown`` and merges them through the same ``snapshot()`` code
path as a single-process run. When no worker snapshot reaches the controller
(a worker died before finishing), the line says UNAVAILABLE instead of
printing a 0 that reads as measured (the issue's option 2, kept as the
degraded branch).

Witnesses:
- pure unit — the merge replays records, sums per-test tallies, and ignores
  foreign shapes;
- end-to-end — the SAME control file under ``-n 2`` prints the same totals as
  single-process, and the canonical report next to each ``--junitxml``
  carries them. Mutation: dropping the worker→controller transfer turns the
  end-to-end witness red (the line falls back to UNAVAILABLE).

Zero spend: the control's requests are httpx ``MockTransport`` doubles,
counted as in-process. The subprocess pytest runs use ``--disable-jvm-session``
so no JVM provisioning is needed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from tests.llm_egress_counter import (
    CLASS_LLM,
    CLASS_NON_LLM,
    CLASS_UNKNOWN,
    LLMEgressCounter,
    merged_snapshot,
)

_REPO = Path(__file__).resolve().parents[2]
_CONTROL = "tests/unit/test_llm_egress_counter.py"

_LINE_RE = re.compile(
    r"LLM egress \(#1787\): (\d+) watched-LLM request\(s\) "
    r"\(gate expectation: 0; (\d+) network, (\d+) in-process double\) · "
    r"(\d+) known non-LLM · (\d+) UNKNOWN host"
)


class TestMergedSnapshot:
    def _record(self, test, host, klass, transport="in_process"):
        return {
            "test": test,
            "host": host,
            "method": "GET",
            "path": "/v1",
            "class": klass,
            "transport": transport,
            "status": 200,
        }

    def test_records_from_every_process_sum_into_one_tally(self):
        worker_1 = {
            "requests": [
                self._record("t_a", "api.openai.com", CLASS_LLM),
                self._record("t_a", "example.com", CLASS_UNKNOWN),
            ]
        }
        worker_2 = {
            "requests": [
                self._record("t_b", "api.openai.com", CLASS_LLM),
                self._record("t_b", "pypi.org", CLASS_NON_LLM),
            ]
        }
        base = {
            "hosts_watched": ["api.openai.com"],
            "transports_patched": ["httpx"],
            "requests": [self._record("(session)", "openrouter.ai", CLASS_LLM)],
        }

        merged = merged_snapshot([worker_1, worker_2], base)

        assert merged["totals_by_class"] == {
            CLASS_LLM: 3,
            CLASS_NON_LLM: 1,
            CLASS_UNKNOWN: 1,
        }
        assert merged["per_test"] == {"(session)": 1, "t_a": 1, "t_b": 1}
        assert merged["per_test_unknown"] == {"t_a": 1}
        assert merged["hosts_watched"] == ["api.openai.com"]
        assert merged["transports_patched"] == [
            "httpx"
        ], "configuration keys describe the process, not the tally"

    def test_foreign_shapes_are_dropped_not_guessed(self):
        payload = {
            "requests": [
                self._record("t", "api.openai.com", CLASS_LLM),
                {"class": "not-a-class", "test": "x"},
                "not-a-dict",
                {"no_class": True},
            ]
        }
        merged = merged_snapshot(
            [payload, "not-a-payload"], {"hosts_watched": [], "requests": []}
        )
        assert merged["totals_by_class"][CLASS_LLM] == 1
        assert sum(merged["totals_by_class"].values()) == 1

    def test_an_empty_worker_list_changes_nothing(self):
        base = {"hosts_watched": [], "transports_patched": [], "requests": []}
        merged = merged_snapshot([], base)
        assert merged["total"] == 0
        assert merged["requests"] == []


class TestTheLineAndTheReportAgreeAcrossProcessCounts:
    """DoD (#3120): the same control file, same totals, whatever ``-n``."""

    @staticmethod
    def _run(
        tmp_path: Path, name: str, *args: str
    ) -> tuple[subprocess.CompletedProcess, dict]:
        out_dir = tmp_path / name
        out_dir.mkdir()
        junit = out_dir / "junit.xml"
        env = os.environ.copy()
        env.pop("PYTEST_CURRENT_TEST", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                _CONTROL,
                "-q",
                "-p",
                "no:cacheprovider",
                "--disable-jvm-session",
                f"--junitxml={junit}",
                *args,
            ],
            cwd=str(_REPO),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        report = json.loads(
            (out_dir / "llm_egress_report.json").read_text(encoding="utf-8")
        )
        return proc, report

    def test_xdist_prints_the_single_process_totals_and_the_report_carries_them(
        self, tmp_path
    ):
        mono_proc, mono_report = self._run(tmp_path, "mono")
        xd_proc, xd_report = self._run(tmp_path, "xd", "-n", "2")

        assert mono_proc.returncode == 0, mono_proc.stdout[-2000:]
        assert xd_proc.returncode == 0, xd_proc.stdout[-2000:]

        mono_line = _LINE_RE.search(mono_proc.stdout)
        xd_line = _LINE_RE.search(xd_proc.stdout)
        assert mono_line, f"no egress line in the mono run:\n{mono_proc.stdout[-2000:]}"
        assert xd_line, (
            "no egress totals line in the -n 2 run — the controller printed "
            f"nothing measurable:\n{xd_proc.stdout[-2000:]}"
        )
        assert (
            "did NOT run" not in xd_proc.stdout
        ), "the merged aggregate must include the control's own rows"
        assert "UNAVAILABLE" not in xd_proc.stdout

        mono_totals = tuple(int(g) for g in mono_line.groups())
        xd_totals = tuple(int(g) for g in xd_line.groups())
        assert xd_totals == mono_totals, (
            "the -n 2 aggregate must equal the single-process measurement "
            f"(mono={mono_totals}, xdist={xd_totals})"
        )

        assert xd_report["totals_by_class"] == mono_report["totals_by_class"]
        assert xd_report["per_test"] == mono_report["per_test"]
        assert (
            xd_report["per_test_llm_network"] == {}
        ), "the controls are in-process doubles; nothing reached a network"
        assert xd_report["totals_by_class"][CLASS_LLM] == mono_totals[0]
