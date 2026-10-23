"""Guard #1872 DoD-3: a nested pytest session cannot clobber the gate report.

``tests/llm_egress_counter.write_report`` writes ``llm_egress_report.json``
into the junitxml directory. A worker spawned by a launcher is a second,
unfiltered pytest session with no ``--junitxml``; it wrote to the SAME
canonical name and overwrote the gate's tally — the instrument lost its
measurement at the exact moment it became positive (#1867).

By construction the gate session always passes ``--junitxml``; a session
without one is nested. ``write_report`` must therefore write a per-process
distinct path for the no-junitxml case, and the parent's canonical file must
keep the parent's CONTENT (verified by reading it back, not just its mtime).

#3194 adds the second half of the guard: the nested file leaves the checkout.
It goes to the session's scratch directory (here, a stand-in basetemp), and
the current directory receives nothing — the 803 files the seat accumulated
in nine days came from that write.
"""

import json
import os
from pathlib import Path

import pytest

from tests.llm_egress_counter import LLMEgressCounter, write_report

PARENT_TEST = "tests/unit/some_test.py::test_gate_control"
CHILD_TEST = "tests/integration/workers/worker_x.py::test_leak"


class _Opt:
    def __init__(self, xmlpath):
        self.xmlpath = xmlpath


class _Factory:
    """Stand-in for pytest's ``_tmp_path_factory`` (the session scratch dir)."""

    def __init__(self, basetemp: Path) -> None:
        self._basetemp = basetemp

    def getbasetemp(self) -> Path:
        return self._basetemp


class _Cfg:
    def __init__(self, xmlpath, basetemp):
        self.option = _Opt(xmlpath)
        self._tmp_path_factory = _Factory(basetemp)


def _counter_with(test_name, host="api.openai.com"):
    counter = LLMEgressCounter(frozenset({"api.openai.com"}))
    counter.current_test = test_name
    counter.observe_request("https://api.openai.com/v1/chat/completions", "POST")
    counter.current_test = None
    return counter


def test_child_session_writes_distinct_path(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    parent = _counter_with(PARENT_TEST)
    parent_path = write_report(
        parent, _Cfg(str(tmp_path / "pytest_report.xml"), scratch)
    )
    assert parent_path is not None
    assert parent_path.name == "llm_egress_report.json"
    assert parent_path.parent == tmp_path

    monkeypatch.chdir(tmp_path)
    child = _counter_with(CHILD_TEST)
    child_path = write_report(child, _Cfg(None, scratch))
    assert child_path is not None
    assert child_path.name != "llm_egress_report.json", (
        "child (no --junitxml) must not write the canonical gate filename — " "#1872"
    )
    assert child_path.name.startswith("llm_egress_report.")
    assert child_path.resolve() != parent_path.resolve()
    assert (
        not (tmp_path / "llm_egress_report.json")
        .read_text(encoding="utf-8")
        .count(CHILD_TEST)
    ), "canonical file must not carry the child tally"
    # #3194: the nested report leaves the current directory.
    assert child_path.parent == scratch
    assert not list(
        tmp_path.glob("llm_egress_report.*.json")
    ), "a nested report must not land in the checkout/current directory (#3194)"
    assert child_path.exists()


def test_parent_report_content_survives_child_write(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    parent = _counter_with(PARENT_TEST)
    write_report(parent, _Cfg(str(tmp_path / "pytest_report.xml"), scratch))

    monkeypatch.chdir(tmp_path)
    child = _counter_with(CHILD_TEST)
    write_report(child, _Cfg(None, scratch))

    parent_report = json.loads(
        (tmp_path / "llm_egress_report.json").read_text(encoding="utf-8")
    )
    # Content, not mtime: the canonical file must still tally the PARENT.
    assert parent_report["total"] == 1
    assert PARENT_TEST in parent_report["per_test"]
    assert CHILD_TEST not in parent_report["per_test"]
    assert (scratch / f"llm_egress_report.{os.getpid()}.json").exists()
