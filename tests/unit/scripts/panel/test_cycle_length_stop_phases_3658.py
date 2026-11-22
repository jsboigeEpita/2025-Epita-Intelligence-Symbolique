"""#3658 ask 2 — the pipeline event names the phases cut at the token cap.

Measured (issue #3658): a PASS with five phases stopped at the token cap was
indistinguishable from a PASS without one — the stop lived only in the
state's ``llm_usage``, which the runner never opened. The pipeline event of
``status.jsonl`` now carries ``length_stop_phases``: the sorted phase names
whose harvested states count ``length_stops > 0`` — names only, the counts
stay in the state.

Stub seat, no key, no network, no corpus (the runner and the credit reader
are stubs, the panel is opaque labels).
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import run_cycle  # noqa: E402

HEAD = {"head": "a" * 40, "tree": "b" * 40, "dirty": False}
JUDGE = run_cycle.Judge("g", "judge-model")

READINGS = [
    {"usage": 61.3462, "limit": 700, "limit_remaining": 161.8336},
    {"usage": 61.6405, "limit": 700, "limit_remaining": 157.8336},
]


def _bucket(length_stops: int) -> Dict[str, Any]:
    return {
        "prompt_tokens": 10,
        "completion_tokens": 4096,
        "calls": 1,
        "calls_without_usage": 0,
        "length_stops": length_stops,
        "calls_without_finish_reason": 0,
    }


def _state(cuts: Dict[str, int]) -> Dict[str, Any]:
    """A state whose ``llm_usage`` mixes phase buckets with the run-level
    cost fields a real state also carries (not phase buckets)."""
    usage: Dict[str, Any] = {phase: _bucket(n) for phase, n in cuts.items()}
    usage["cost_usd"] = 0.0
    usage["computed_cost_usd"] = 0.01
    return {"llm_usage": usage}


class Seat:
    """A pipeline-stage invocation whose fake pipeline harvests given states."""

    def __init__(self, tmp_path: Path, states: Dict[str, Dict[str, Any]]):
        panel = list(states)
        panel_file = tmp_path / "panel.txt"
        panel_file.write_text("\n".join(panel) + "\n", encoding="utf-8")
        self.zeroshot = tmp_path / "zeroshot"
        self.zeroshot.mkdir()
        for doc in panel:
            (self.zeroshot / f"{doc}.json").write_text(
                json.dumps({"answer": "une reponse de reference"}), encoding="utf-8"
            )
        self.cfg = run_cycle.Config(
            tag="t3658",
            panel_file=panel_file,
            zeroshot_dir=self.zeroshot,
            judges=[JUDGE],
            passes=2,
            results_root=tmp_path / "results",
            kb_root=tmp_path / "kb",
        )
        self.panel = panel
        self.states = states
        self.readings: List[Dict[str, Any]] = []

    def credit(self) -> Dict[str, Any]:
        reading = self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]
        return dict(reading)

    def runner(self, step: run_cycle.Step) -> int:
        """Plays the pipeline: a PASS log + the states the harvest copies."""
        step.log.parent.mkdir(parents=True, exist_ok=True)
        if step.name == "pipeline":
            step.log.write_text(
                "Verdict: PASS (0 documents failed)\n", encoding="utf-8"
            )
            for doc in self.panel:
                for folder, name, body in (
                    ("state_dumps", f"state_full_{doc}.json", self.states[doc]),
                    ("signatures", f"signature_{doc}.json", {}),
                ):
                    path = self.cfg.kb_root / folder / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(body), encoding="utf-8")
        else:
            step.log.write_text("", encoding="utf-8")
        return 0

    def invoke(self) -> Dict[str, Any]:
        self.cfg = dataclasses.replace(self.cfg, stage="pipeline")
        self.readings = list(READINGS)
        return run_cycle.run_cycle(
            self.cfg, runner=self.runner, credit=self.credit, head=lambda: dict(HEAD)
        )

    def events(self, name: str) -> List[Dict[str, Any]]:
        return [
            json.loads(line)
            for line in (self.cfg.cycle_dir / "status.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and json.loads(line).get("event") == name
        ]


class TestThePipelineEventNamesTheCutPhases:
    def test_a_pass_with_length_stops_names_the_phases(self, tmp_path):
        """Born red: on main the pipeline event carries no stop field — a
        PASS with a cut reply read exactly like a PASS without one."""
        seat = Seat(
            tmp_path,
            {
                "doc_A": _state(
                    {"first_reading": 1, "strategist": 0, "act2_narrative": 2}
                )
            },
        )
        assert seat.invoke()["exit_code"] == 0
        (pipeline,) = seat.events("pipeline")
        assert pipeline["length_stop_phases"] == ["act2_narrative", "first_reading"]

    def test_a_pass_without_any_stop_names_none(self, tmp_path):
        seat = Seat(tmp_path, {"doc_A": _state({"first_reading": 0})})
        assert seat.invoke()["exit_code"] == 0
        (pipeline,) = seat.events("pipeline")
        assert pipeline["length_stop_phases"] == []

    def test_two_documents_union_their_cut_phases(self, tmp_path):
        seat = Seat(
            tmp_path,
            {
                "doc_A": _state({"first_reading": 1}),
                "doc_B": _state({"act2_narrative": 1, "strategist": 0}),
            },
        )
        assert seat.invoke()["exit_code"] == 0
        (pipeline,) = seat.events("pipeline")
        assert pipeline["length_stop_phases"] == ["act2_narrative", "first_reading"]

    def test_a_state_that_never_ran_a_phase_is_silent(self, tmp_path):
        """A state whose llm_usage holds only the run-level cost fields — no
        bucket, nothing to name."""
        seat = Seat(tmp_path, {"doc_A": {"llm_usage": {"cost_usd": None}}})
        assert seat.invoke()["exit_code"] == 0
        (pipeline,) = seat.events("pipeline")
        assert pipeline["length_stop_phases"] == []


class TestThePhaseReader:
    """The reader itself, on plain files — a missing or unreadable state is
    skipped, never raised: the harvest already named missing documents."""

    def test_a_missing_state_is_skipped_not_raised(self, tmp_path):
        assert run_cycle.length_stop_phases(tmp_path, ["absent"]) == []

    def test_an_unreadable_state_is_skipped_not_raised(self, tmp_path):
        (tmp_path / "state_full_doc_A.json").write_text("not json", encoding="utf-8")
        assert run_cycle.length_stop_phases(tmp_path, ["doc_A"]) == []
