#!/usr/bin/env python
"""Fail the CI gate when a test reached an LLM over the network (#2444).

The unit gate runs under ``-m "not slow and not requires_api"``, so an LLM
request that leaves the machine during it is a leak by construction
(#1591/#1787). ``tests/llm_egress_counter.py`` counts those requests and
prints "gate expectation: 0", but it only observes: nothing failed when the
count was not 0. Run 35819591775 on ``main`` ``748e1ad0`` was green with 16
network requests to ``api.openai.com`` from four tests. This script is the
check that was missing. It reads the egress report and exits non-zero when
``per_test_llm_network`` is not empty, naming each test.

It reads the report the counter writes, not the terminal summary. Requests
answered by an in-process double (``MockTransport``, an ASGI app) are not
leaks and do not count here (#2422).

Exit codes:

* ``0``: the report is present, the counter is proven live, and no watched
  LLM request reached a network transport.
* ``1``: at least one did. The tests are listed, most requests first.
* ``2``: not measured. The report is missing or unreadable, lacks the field
  this script reads, or has no row from the counter's non-vacuity controls
  (``tests/unit/test_llm_egress_counter.py``). A 0 from a counter that saw
  nothing cannot be told from an unwired one.

Usage::

    python scripts/ci/llm_egress_gate.py llm_egress_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

EXIT_OK = 0
EXIT_LEAK = 1
EXIT_NOT_MEASURED = 2

# The field ``LLMEgressCounter.snapshot`` writes (#2422). The unit test of this
# script builds its report with the real counter, so a rename reddens there.
NETWORK_FIELD = "per_test_llm_network"
# The non-vacuity controls the gate itself runs. Their rows prove the session
# counter was installed and saw requests.
CONTROL_MODULE = "tests/unit/test_llm_egress_counter.py::"


def evaluate(report: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Return ``(exit_code, lines)`` for an already-loaded report."""
    network = report.get(NETWORK_FIELD)
    if not isinstance(network, dict):
        return EXIT_NOT_MEASURED, [
            f"NOT MEASURED (#2444): the report has no '{NETWORK_FIELD}' mapping. "
            "The counter no longer writes the field this gate reads."
        ]
    per_test = report.get("per_test")
    controls = [
        test
        for test in (per_test if isinstance(per_test, dict) else {})
        if test.startswith(CONTROL_MODULE)
    ]
    if not controls:
        return EXIT_NOT_MEASURED, [
            "NOT MEASURED (#2444): no row from the counter's non-vacuity controls "
            f"({CONTROL_MODULE.rstrip(':')}). A 0 from a counter that saw nothing "
            "cannot be told from an unwired one."
        ]
    if not network:
        doubles = (report.get("llm_by_transport") or {}).get("in_process", 0)
        return EXIT_OK, [
            "LLM egress gate (#2444): 0 watched-LLM requests reached the network "
            f"({doubles} answered in-process; {len(controls)} control rows)."
        ]
    hosts = sorted(
        {
            r.get("host", "?")
            for r in report.get("requests", [])
            if r.get("class") == "llm" and r.get("transport") == "network"
        }
    )
    lines = [
        f"LLM egress gate (#2444): {sum(network.values())} watched-LLM request(s) "
        f"reached the network from {len(network)} test(s) inside the gate, "
        "where the expectation is 0:"
    ]
    for test, count in sorted(network.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {count:5d}  {test}")
    if hosts:
        lines.append(f"Hosts reached: {', '.join(hosts)}")
    lines.append(
        "Each is a real, billed call on every CI run. Cut the test's LLM route "
        "so its named degraded path runs, or mark it requires_api if its "
        "verdict reads a model output."
    )
    return EXIT_LEAK, lines


def main(argv: List[str]) -> int:
    path = Path(argv[0] if argv else "llm_egress_report.json")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        code, lines = EXIT_NOT_MEASURED, [
            f"NOT MEASURED (#2444): {path} does not exist. The suite ran but "
            "the egress counter wrote no report."
        ]
    except (OSError, ValueError) as exc:
        code, lines = EXIT_NOT_MEASURED, [
            f"NOT MEASURED (#2444): {path} is unreadable ({type(exc).__name__}: {exc})."
        ]
    else:
        if isinstance(report, dict):
            code, lines = evaluate(report)
        else:
            code, lines = EXIT_NOT_MEASURED, [
                f"NOT MEASURED (#2444): {path} does not hold a JSON object."
            ]
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
