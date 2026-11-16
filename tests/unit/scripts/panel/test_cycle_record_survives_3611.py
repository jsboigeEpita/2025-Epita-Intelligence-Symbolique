"""#3611 — a free re-consolidation replaces no paid record.

``run_cycle`` wrote ``cycle.json`` as the record of the LAST invocation, and
``status.jsonl`` recorded ``credit_before`` and ``credit_after_pipeline``
but never ``credit_after``. So the runbook's free re-consolidation
(``--stage consensus``, which pays nothing) replaced the paid run's record —
on cycle 16 the paid readings and the paid ``openrouter_spent`` were
overwritten by an invocation whose spend reads 0.0, and the paid run's final
raw reading existed nowhere once ``cycle.json`` was rewritten.

What is witnessed here, with no key, no network and no corpus (the runner
and the credit reader are stubs, the panel is one opaque label):

- after a paid invocation and then a ``--stage consensus`` invocation, the
  paid record — its ``credit_before``, ``credit_after_pipeline``,
  ``credit_after`` and ``openrouter_spent`` — is still readable from the
  cycle directory, byte for byte untouched;
- the free invocation writes its own record beside the paid one, and says
  which steps it paid for (none);
- an invocation that DID run a paid step still writes the cycle record
  itself, and a stopped invocation that ran no paid step replaces no paid
  record either;
- every invocation, paid or free, records its final credit reading as a
  ``credit_after`` event in ``status.jsonl``, with the same payload as
  ``credit_before``.
"""

from __future__ import annotations

import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import run_cycle  # noqa: E402

PANEL = ["doc_A"]
HEAD = {"head": "a" * 40, "tree": "b" * 40, "dirty": False}
JUDGE = run_cycle.Judge("g", "judge-model")

# The paid invocation's three readings: the credit falls by 10.00 over the
# cycle (4.00 over the pipeline, 6.00 over the judges).
PAID_BEFORE = {"usage": 61.3462, "limit": 700, "limit_remaining": 161.8336}
PAID_AFTER_PIPELINE = {"usage": 61.6405, "limit": 700, "limit_remaining": 157.8336}
PAID_AFTER = {"usage": 61.9348, "limit": 700, "limit_remaining": 151.8336}
# The free re-consolidation's two readings: the credit does not move.
FREE_BEFORE = {"usage": 61.9348, "limit": 700, "limit_remaining": 151.8336}
FREE_AFTER = {"usage": 61.9348, "limit": 700, "limit_remaining": 151.8336}

PAID_READINGS = [PAID_BEFORE, PAID_AFTER_PIPELINE, PAID_AFTER]
FREE_READINGS = [FREE_BEFORE, FREE_AFTER]


class Seat:
    """A cycle directory and the stubs around it, one invocation at a time."""

    def __init__(self, tmp_path: Path):
        panel_file = tmp_path / "panel.txt"
        panel_file.write_text("\n".join(PANEL) + "\n", encoding="utf-8")
        self.zeroshot = tmp_path / "zeroshot"
        self.zeroshot.mkdir()
        for doc in PANEL:
            (self.zeroshot / f"{doc}.json").write_text(
                json.dumps({"answer": "une reponse de reference"}), encoding="utf-8"
            )
        self.cfg = run_cycle.Config(
            tag="t1",
            panel_file=panel_file,
            zeroshot_dir=self.zeroshot,
            judges=[JUDGE],
            passes=2,
            results_root=tmp_path / "results",
            kb_root=tmp_path / "kb",
        )
        self.readings: List[Dict[str, Any]] = []

    def credit(self) -> Dict[str, Any]:
        reading = self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]
        return dict(reading)

    def runner(self, step: run_cycle.Step) -> int:
        """Plays every command: the pipeline harvests, a pass writes its rows."""
        step.log.parent.mkdir(parents=True, exist_ok=True)
        if step.name == "pipeline":
            step.log.write_text(
                "Verdict: PASS (0 documents failed)\n", encoding="utf-8"
            )
            for doc in PANEL:
                for folder, name in (
                    ("state_dumps", f"state_full_{doc}.json"),
                    ("signatures", f"signature_{doc}.json"),
                ):
                    path = self.cfg.kb_root / folder / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
        elif re.fullmatch(r"g\.p\d+", step.name):
            out = Path(step.argv[step.argv.index("--out-dir") + 1])
            out.mkdir(parents=True, exist_ok=True)
            (out / "META.json").write_text("{}", encoding="utf-8")
            for doc in PANEL:
                (out / f"{doc}.json").write_text(
                    json.dumps(
                        {
                            "opaque_id": doc,
                            "status_code": 200,
                            "state": "EQUAL",
                            "kept": [],
                        }
                    ),
                    encoding="utf-8",
                )
        else:
            step.log.write_text("", encoding="utf-8")
        return 0

    def invoke(self, stage: str, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.cfg = dataclasses.replace(self.cfg, stage=stage)
        self.readings = list(readings)
        return run_cycle.run_cycle(
            self.cfg, runner=self.runner, credit=self.credit, head=lambda: dict(HEAD)
        )

    # -- reading back ------------------------------------------------------

    def record(self, name: str) -> Dict[str, Any]:
        return json.loads((self.cfg.cycle_dir / name).read_text(encoding="utf-8"))

    def events(self, name: str) -> List[Dict[str, Any]]:
        return [
            json.loads(line)
            for line in (self.cfg.cycle_dir / "status.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and json.loads(line).get("event") == name
        ]


class TestThePaidRecordSurvivesAReconsolidation:
    def test_the_paid_record_is_still_readable_after_a_free_reconsolidation(
        self, tmp_path
    ):
        seat = Seat(tmp_path)
        paid = seat.invoke("all", PAID_READINGS)
        assert paid["exit_code"] == 0 and paid["openrouter_spent"] == 10.0
        paid_record = (seat.cfg.cycle_dir / "cycle.json").read_bytes()
        free = seat.invoke("consensus", FREE_READINGS)
        assert free["exit_code"] == 0
        # The paid record is untouched, byte for byte.
        assert (seat.cfg.cycle_dir / "cycle.json").read_bytes() == paid_record
        record = seat.record("cycle.json")
        assert record["credit_before"] == PAID_BEFORE
        assert record["credit_after_pipeline"] == PAID_AFTER_PIPELINE
        assert record["credit_after"] == PAID_AFTER
        assert record["openrouter_spent"] == 10.0
        assert record["paid_steps"] == ["pipeline", "g.p1", "g.p2"]

    def test_the_free_invocation_writes_its_own_record_beside_the_paid_one(
        self, tmp_path
    ):
        seat = Seat(tmp_path)
        seat.invoke("all", PAID_READINGS)
        free = seat.invoke("consensus", FREE_READINGS)
        assert free["exit_code"] == 0
        record = seat.record("cycle_free.json")
        assert record["stage"] == "consensus"
        assert record["credit_after"] == FREE_AFTER
        assert record["openrouter_spent"] == 0.0
        assert record["paid_steps"] == []

    def test_an_invocation_that_paid_still_writes_the_cycle_record(self, tmp_path):
        seat = Seat(tmp_path)
        summary = seat.invoke("all", PAID_READINGS)
        assert summary["exit_code"] == 0
        record = seat.record("cycle.json")
        assert record["stage"] == "all"
        assert record["openrouter_spent"] == 10.0
        assert not (seat.cfg.cycle_dir / "cycle_free.json").exists()

    def test_a_stopped_invocation_that_ran_nothing_replaces_no_paid_record(
        self, tmp_path
    ):
        seat = Seat(tmp_path)
        seat.invoke("all", PAID_READINGS)
        paid_record = (seat.cfg.cycle_dir / "cycle.json").read_bytes()
        # The next invocation stops before any step: a panel document has no
        # zero-shot answer any more.
        (seat.zeroshot / f"{PANEL[0]}.json").write_text(
            json.dumps({"answer": ""}), encoding="utf-8"
        )
        stopped = seat.invoke("consensus", FREE_READINGS)
        assert stopped["exit_code"] == run_cycle.EXIT_STOPPED
        assert (seat.cfg.cycle_dir / "cycle.json").read_bytes() == paid_record
        assert seat.record("cycle_free.json")["stopped"]


class TestTheCreditAfterEvent:
    def test_every_invocation_records_its_final_reading_as_an_event(self, tmp_path):
        seat = Seat(tmp_path)
        seat.invoke("all", PAID_READINGS)
        seat.invoke("consensus", FREE_READINGS)
        afters = seat.events("credit_after")
        assert len(afters) == 2, "one credit_after event per invocation"
        # The paid invocation's final reading, then the free one's.
        assert afters[0]["limit_remaining"] == PAID_AFTER["limit_remaining"]
        assert afters[1]["limit_remaining"] == FREE_AFTER["limit_remaining"]
        # The same payload as credit_before: every field of the reading.
        befores = seat.events("credit_before")
        assert len(befores) == 2
        for event, reading in (
            (afters[0], PAID_AFTER),
            (afters[1], FREE_AFTER),
        ):
            for field, value in reading.items():
                assert event[field] == value
        assert set(afters[1]) == {"at", "event", *FREE_AFTER}

    def test_a_stopped_invocation_records_its_final_reading_too(self, tmp_path):
        seat = Seat(tmp_path)
        (seat.zeroshot / f"{PANEL[0]}.json").write_text(
            json.dumps({"answer": ""}), encoding="utf-8"
        )
        stopped = seat.invoke("consensus", FREE_READINGS)
        assert stopped["exit_code"] == run_cycle.EXIT_STOPPED
        afters = seat.events("credit_after")
        assert len(afters) == 1
        assert afters[0]["limit_remaining"] == FREE_AFTER["limit_remaining"]
        # The closing event of the invocation is still the end event.
        every = [
            json.loads(line)
            for line in (seat.cfg.cycle_dir / "status.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        assert every[-1]["event"] == "end"
