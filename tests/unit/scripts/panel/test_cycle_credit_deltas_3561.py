"""#3561 — the cycle's spend is the fall of the credit, not the change of ``usage``.

The provider's key endpoint returns two counters, ``usage`` and
``limit_remaining``. On the cycles of November 2026 they disagree by an order
of magnitude: the credit fell by about 10 USD over a cycle while ``usage``
moved by about 0.3 USD, and on one paid run ``usage`` did not move at all.
The cycle runner recorded the change of ``usage`` under the name
``openrouter_spent``, so the record carried a figure that does not measure the
spend.

What is witnessed here, on synthetic readings and with no key, no network and
no corpus:

- the cycle records the change of BOTH provider fields, each under a name
  that says which field it reads;
- the figure the runbook names as the spend is the fall of the credit, and the
  record says which field it reads;
- when the two deltas disagree by more than the stated margin, the record says
  so — and when they do not, it stays quiet (the flag is not always on).

The synthetic panel carries one opaque label and no document text.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import run_cycle  # noqa: E402

PANEL = ["doc_A"]
HEAD = {"head": "a" * 40, "dirty": False}

# The provider's two counters, on two readings of the same key: the credit
# falls by 10.00 while the usage counter moves by 0.29.
BEFORE = {"usage": 61.3462, "limit": 700, "limit_remaining": 161.8336}
AFTER = {"usage": 61.6405, "limit": 700, "limit_remaining": 151.8336}


class Credit:
    """The runner's readings: before the cycle, and after it.

    ``run_cycle`` reads the credit three times on a pipeline stage (before
    the pipeline, after it, and when it ends); the cycle's own pair is the
    first and the last. The count is asserted by the test, so a change in
    the number of readings is visible instead of silent.
    """

    def __init__(self, readings: List[Dict[str, Any]]):
        self.readings = list(readings)
        self.count = 0

    def __call__(self) -> Dict[str, Any]:
        reading = self.readings[self.count]
        self.count += 1
        return dict(reading)


def _world(tmp_path: Path):
    """A cycle on disk, with one synthetic panel document."""
    panel_file = tmp_path / "panel.txt"
    panel_file.write_text("\n".join(PANEL) + "\n", encoding="utf-8")
    zeroshot = tmp_path / "zeroshot"
    zeroshot.mkdir()
    for doc in PANEL:
        (zeroshot / f"{doc}.json").write_text(
            json.dumps({"answer": "une reponse de reference"}), encoding="utf-8"
        )
    kb = tmp_path / "kb"
    (kb / "state_dumps").mkdir(parents=True)
    (kb / "signatures").mkdir(parents=True)
    cfg = run_cycle.Config(
        tag="t1",
        panel_file=panel_file,
        zeroshot_dir=zeroshot,
        stage="pipeline",
        results_root=tmp_path / "results",
        kb_root=kb,
    )
    return cfg, kb


def _runner(kb: Path):
    """A runner that writes the pipeline's own files and no call at all."""

    def runner(step: run_cycle.Step) -> int:
        step.log.parent.mkdir(parents=True, exist_ok=True)
        step.log.write_text("Verdict: PASS (0 documents failed)\n", encoding="utf-8")
        for doc in PANEL:
            (kb / "state_dumps" / f"state_full_{doc}.json").write_text(
                "{}", encoding="utf-8"
            )
            (kb / "signatures" / f"signature_{doc}.json").write_text(
                "{}", encoding="utf-8"
            )
        return 0

    return runner


def _run(tmp_path: Path, readings: List[Dict[str, Any]]):
    cfg, kb = _world(tmp_path)
    credit = Credit(readings)
    summary = run_cycle.run_cycle(
        cfg,
        runner=_runner(kb),
        credit=credit,
        head=lambda: dict(HEAD),
    )
    return summary, credit


class TestTheSpendAndItsTwoDeltas:
    def test_the_cycle_records_both_deltas_and_says_which_field_it_reads(
        self, tmp_path
    ):
        summary, credit = _run(tmp_path, [BEFORE, BEFORE, AFTER])
        assert credit.count == 3
        # The spend the runbook names: the fall of the credit.
        assert summary["openrouter_spent"] == 10.0
        assert summary["openrouter_spent_field"] == "limit_remaining"
        # Both provider deltas, each under a name that says which field it is.
        assert summary["openrouter_usage_delta"] == 0.2943
        assert summary["openrouter_limit_remaining_delta"] == -10.0
        # The disagreement between them is stated.
        assert summary["openrouter_spent_disagreement"] is True
        assert summary["openrouter_spent_disagreement_margin"]

    def test_the_record_on_disk_carries_the_same_figures(self, tmp_path):
        _run(tmp_path, [BEFORE, BEFORE, AFTER])
        on_disk = json.loads(
            (tmp_path / "results" / "panel_cycles" / "t1" / "cycle.json").read_text(
                encoding="utf-8"
            )
        )
        assert on_disk["openrouter_spent"] == 10.0
        assert on_disk["openrouter_spent_field"] == "limit_remaining"
        assert on_disk["openrouter_usage_delta"] == 0.2943
        assert on_disk["openrouter_limit_remaining_delta"] == -10.0
        assert on_disk["openrouter_spent_disagreement"] is True

    def test_the_end_event_carries_the_same_figures(self, tmp_path):
        _run(tmp_path, [BEFORE, BEFORE, AFTER])
        events = [
            json.loads(line)
            for line in (tmp_path / "results" / "panel_cycles" / "t1" / "status.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        end = [event for event in events if event.get("event") == "end"]
        assert end, "the cycle wrote no end event"
        assert end[-1]["openrouter_spent"] == 10.0
        assert end[-1]["openrouter_spent_field"] == "limit_remaining"
        assert end[-1]["openrouter_usage_delta"] == 0.2943
        assert end[-1]["openrouter_limit_remaining_delta"] == -10.0
        assert end[-1]["openrouter_spent_disagreement"] is True

    def test_two_readings_that_agree_state_no_disagreement(self, tmp_path):
        """The positive control: the flag is not always on."""
        summary, _ = _run(tmp_path, [BEFORE, BEFORE, BEFORE])
        assert summary["openrouter_spent"] == 0.0
        assert summary["openrouter_usage_delta"] == 0.0
        assert summary["openrouter_limit_remaining_delta"] == 0.0
        assert summary["openrouter_spent_disagreement"] is False

    def test_an_unread_credit_is_still_not_a_zero_spend(self, tmp_path):
        unread = {"unavailable": "the key endpoint is unreachable"}
        summary, _ = _run(tmp_path, [unread, unread, unread])
        assert summary["openrouter_spent"] is None
        assert summary["openrouter_usage_delta"] is None
        assert summary["openrouter_limit_remaining_delta"] is None
        assert summary["openrouter_spent_disagreement"] is None
