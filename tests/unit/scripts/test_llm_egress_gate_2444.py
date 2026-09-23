"""#2444: the CI gate fails when a test reaches an LLM over the network.

``scripts/ci/llm_egress_gate.py`` reads the report ``tests/llm_egress_counter.py``
writes. Its reports here are built by the real counter (``observe_request``,
then the network-transport mark), not written by hand, so a rename of the
field on the producer side reddens these tests.

Born red on real data: replayed on the egress report of CI run 35819591775
(``main`` ``748e1ad0``), the gate exits 1 and names the four tests that sent
16 requests to ``api.openai.com``.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.ci.llm_egress_gate import (  # noqa: E402
    CONTROL_MODULE,
    EXIT_LEAK,
    EXIT_NOT_MEASURED,
    EXIT_OK,
    main,
)
from tests.llm_egress_counter import (  # noqa: E402
    _CURRENT_ENTRY,
    LLMEgressCounter,
)

LEAKER = "tests/unit/x/test_leak.py::test_reaches_the_model"
CONTROL = CONTROL_MODULE + "test_counter_sees_raw_openai_sdk_request"
URL = "https://api.openai.com/v1/chat/completions"


def _observe(counter: LLMEgressCounter, test: str, network: bool) -> None:
    counter.current_test = test
    entry = counter.observe_request(URL, "POST")
    if network:
        token = _CURRENT_ENTRY.set(entry)
        try:
            counter.observe_network_transport()
        finally:
            _CURRENT_ENTRY.reset(token)
    counter.current_test = None


def _report(tmp_path: Path, rows) -> Path:
    counter = LLMEgressCounter(frozenset({"api.openai.com"}))
    for test, network in rows:
        _observe(counter, test, network)
    path = tmp_path / "llm_egress_report.json"
    path.write_text(json.dumps(counter.snapshot()), encoding="utf-8")
    return path


def test_a_network_request_fails_the_gate_and_names_the_test(tmp_path, capsys):
    path = _report(tmp_path, [(CONTROL, False), (LEAKER, True), (LEAKER, True)])

    assert main([str(path)]) == EXIT_LEAK
    out = capsys.readouterr().out
    assert f"    2  {LEAKER}" in out
    assert "api.openai.com" in out


def test_in_process_doubles_pass_the_gate(tmp_path, capsys):
    """The non-vacuity controls answer in-process (#2422): not a leak."""
    path = _report(tmp_path, [(CONTROL, False), (LEAKER, False)])

    assert main([str(path)]) == EXIT_OK
    assert "0 watched-LLM requests reached the network" in capsys.readouterr().out


def test_a_report_without_control_rows_is_not_measured(tmp_path, capsys):
    """A counter that saw nothing reads 0, like a clean run: refuse it."""
    path = _report(tmp_path, [])

    assert main([str(path)]) == EXIT_NOT_MEASURED
    assert "NOT MEASURED" in capsys.readouterr().out


def test_a_missing_report_is_not_measured(tmp_path, capsys):
    assert main([str(tmp_path / "absent.json")]) == EXIT_NOT_MEASURED
    assert "does not exist" in capsys.readouterr().out


@pytest.mark.parametrize("content", ["{not json", "[]"])
def test_an_unreadable_report_is_not_measured(tmp_path, content):
    path = tmp_path / "llm_egress_report.json"
    path.write_text(content, encoding="utf-8")

    assert main([str(path)]) == EXIT_NOT_MEASURED


def test_a_report_without_the_network_field_is_not_measured(tmp_path, capsys):
    """If the counter stops writing the field, the gate must not read 0."""
    path = _report(tmp_path, [(CONTROL, False)])
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["per_test_llm_network"]
    path.write_text(json.dumps(data), encoding="utf-8")

    assert main([str(path)]) == EXIT_NOT_MEASURED
    assert "per_test_llm_network" in capsys.readouterr().out
