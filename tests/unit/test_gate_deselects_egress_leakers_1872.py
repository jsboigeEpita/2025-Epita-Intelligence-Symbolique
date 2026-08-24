"""Guard #1872: the gate filter must deselect every egress-leaking test.

The #1867 in-position measurement showed that, if ``tests/integration/`` were
added to the gate argv, the five files below fire real LLM POSTs (17 watched
requests, 13 under the real CI key) despite the ``-m "not slow and not
requires_api"`` filter, because none of them carries a deselecting marker:
every test was admitted. This guard re-applies that same gate filter and
asserts the leakers are NOT admitted.

Decisive, not static: it runs the actual filter (``--collect-only -m ...``)
over the five files, so removing a marker from any leaker reddens this test.
``--disable-jvm-session`` keeps the collection fast (no JVM boot) without
changing what the filter admits. The filter does not run the tests, so no LLM
call is made and no egress cost is paid here.

A collection error in one of the non-LLM import-only tests does not count as a
leaker; the guard only requires the collection to have COMPLETED ("N tests
collected") and the leaker ids to be absent. The egress=4 post-fix figure is
the positional measurement (widened argv run), not this guard.
"""

import re
import subprocess
import sys

import pytest

FILES = [
    "tests/integration/test_sherlock_watson_moriarty_real_gpt.py",
    "tests/integration/test_orchestration_agentielle_complete_reel.py",
    "tests/integration/test_realite_pure_jtms.py",
    "tests/integration/test_informal_agent_tool_choice.py",
    "tests/integration/workers/worker_sherlock_watson_moriarty.py",
]

# Every genuine-verdict LLM test in those five files. The #1867 measurement
# attributed a POST to the first three subsets; the siblings are marked with
# the same marker so the gate never runs a half-marked file.
LEAKER_NODEIDS = {
    "tests/integration/test_sherlock_watson_moriarty_real_gpt.py::test_sherlock_watson_moriarty_real_gpt_in_subprocess",
    "tests/integration/test_orchestration_agentielle_complete_reel.py::test_sherlock_jtms_hypotheses",
    "tests/integration/test_orchestration_agentielle_complete_reel.py::test_watson_jtms_validation",
    "tests/integration/test_orchestration_agentielle_complete_reel.py::test_orchestration_collaborative",
    "tests/integration/test_realite_pure_jtms.py::test_interaction_sherlock_reelle",
    "tests/integration/test_realite_pure_jtms.py::test_validation_watson_reelle",
    "tests/integration/test_realite_pure_jtms.py::test_collaboration_orchestration_reelle",
    "tests/integration/test_informal_agent_tool_choice.py::test_informal_agent_forced_tool_choice",
}

# The worker file's tests are collected when the file is named explicitly.
for _name in (
    "TestRealGPTIntegration",
    "TestRealGPTPerformance",
    "TestRealGPTErrorHandling",
    "TestRealGPTAuthenticity",
    "TestRealGPTLoadHandling",
):
    for _tid in (
        "test_real_gpt_kernel_connection",
        "test_real_gpt_sherlock_agent_creation",
        "test_real_gpt_watson_analysis",
        "test_real_gpt_moriarty_revelation",
        "test_real_gpt_complete_workflow",
        "test_real_gpt_response_time",
        "test_real_gpt_token_usage",
        "test_real_gpt_timeout_handling",
        "test_real_gpt_retry_logic",
        "test_real_vs_mock_behavior_comparison",
        "test_real_gpt_oracle_authenticity",
        "test_sequential_requests",
    ):
        LEAKER_NODEIDS.add(
            f"tests/integration/workers/worker_sherlock_watson_moriarty.py::{_name}::{_tid}"
        )

_NODEID_RE = re.compile(r"^\S+::\S+$")


def _admitted_nodeids(out: str):
    return {line.strip() for line in out.splitlines() if _NODEID_RE.match(line.strip())}


def test_gate_filter_deselects_egress_leakers():
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "--disable-jvm-session",
        "-q",
        "-m",
        "not slow and not requires_api",
        *FILES,
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    admitted = _admitted_nodeids(proc.stdout)
    leaked = sorted(LEAKER_NODEIDS & admitted)

    assert "tests collected" in proc.stdout, (
        f"#1872: collect-only did not complete (rc={proc.returncode}); "
        "cannot verify the leakers' deselection.\n"
        f"stderr tail:\n{proc.stderr[-1500:]}"
    )
    assert not leaked, (
        "#1872: egress leakers are ADMITTED by the gate filter "
        "(-m 'not slow and not requires_api'). Their requires_api marker was "
        "likely removed:\n"
        f"  {leaked}\n"
        "Admitted (all):\n"
        f"  {sorted(admitted)}\n"
        f"rc={proc.returncode}"
    )
