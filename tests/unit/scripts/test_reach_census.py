"""Synthetic witnesses for the contribution reach census (#3549)."""

import json
import subprocess
import sys
from pathlib import Path


def test_synthetic_cycle_counts_filled_named_and_channels(tmp_path):
    states = tmp_path / "states"
    states.mkdir()
    (tmp_path / "cycle.json").write_text(
        json.dumps({"head": "synthetic"}), encoding="utf-8"
    )
    for i, state in enumerate(
        [
            {
                "jtms_retraction_chain": [{"reason": "synthetic"}],
                "act3_conclusion": "Une rétractation est constatée.",
            },
            {},
        ]
    ):
        (states / f"state_full_{i}.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
    result = subprocess.run(
        [sys.executable, "scripts/audit/reach_census.py", "--cycle-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    rows = result.stdout.splitlines()
    jtms = next(row for row in rows if row.startswith("| 1.4.1-JTMS |"))
    mobile = next(row for row in rows if row.startswith("| 3.1.5_Interface_Mobile |"))
    assert "1 of 2" in jtms
    assert jtms.count("1 of 2") >= 2
    assert "n/a (channel)" in mobile
    assert "0 of 2" in result.stdout
    assert "state_full_" not in result.stdout
    assert r"\|" in jtms  # regex alternatives do not create table columns

    first = states / "state_full_0.json"
    first.write_text(
        json.dumps({"jtms_retraction_chain": [{"reason": "synthetic"}]}),
        encoding="utf-8",
    )
    changed = subprocess.run(
        [sys.executable, "scripts/audit/reach_census.py", "--cycle-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    changed_jtms = next(
        row for row in changed.stdout.splitlines() if row.startswith("| 1.4.1-JTMS |")
    )
    assert "| 0 of 2 |" in changed_jtms
    assert "| 1 of 2 |" in changed_jtms
