"""#3543 — the condition-2 counter is the cycle's own step.

The State comment of 2026-11-20 wired it: the two roles' consensus
directories in, a refusal on ``unproven``, the reading written where the
runbook files the cycle's artifacts (``panel_cycles/<tag>/condition2.json``
— the command's own default under ``--cycle-dir``). No paid step: the
counter reads consensus directories the cycle already wrote, and the
refusals are the standalone command's provenance checks exiting non-zero.

Witnessed here, synthetic and hermetic (one opaque label, no corpus, no
key, no network):

- the plan carries the step: one ``--judge`` per family, the reading aimed
  at the cycle directory, and the previous half (``--previous-tag`` plus
  the previous cycle's directory, where the counter chains from) — or
  ``--new-series`` when no comparison cycle is configured;
- the dispatched cycle REFUSES a non-zero condition2 exit: stopped-loud,
  never a green finish over an unread counter;
- a green condition2 exit lets the cycle finish green, the reading's exit
  code in the record and in the status line.

Born red on ``main`` ``9ae0e314b``: the plan held no condition2 step, and
a refused counter could not stop anything.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import run_cycle  # noqa: E402

PANEL = ["doc_A"]
HEAD = {"head": "a" * 40, "dirty": False}
CREDIT = {"usage": 0.0, "limit": 700, "limit_remaining": 100.0}


def _config(tmp_path: Path, compare_with_tag: str = None) -> run_cycle.Config:
    panel_file = tmp_path / "panel.txt"
    panel_file.write_text("\n".join(PANEL) + "\n", encoding="utf-8")
    zeroshot = tmp_path / "zeroshot"
    zeroshot.mkdir(exist_ok=True)
    for doc in PANEL:
        (zeroshot / f"{doc}.json").write_text(
            json.dumps({"answer": "une reponse de reference"}), encoding="utf-8"
        )
    kb = tmp_path / "kb"
    (kb / "state_dumps").mkdir(parents=True, exist_ok=True)
    (kb / "signatures").mkdir(parents=True, exist_ok=True)
    return run_cycle.Config(
        tag="t1",
        panel_file=panel_file,
        zeroshot_dir=zeroshot,
        judges=[
            run_cycle.parse_judge("g=model-x"),
            run_cycle.parse_judge("s=model-y"),
        ],
        passes=6,
        compare_with_tag=compare_with_tag,
        stage="consensus",
        results_root=tmp_path / "results",
        kb_root=kb,
    )


def _world(cfg: run_cycle.Config) -> None:
    """A cycle whose passes are complete on disk and states harvested: the
    consensus stage reads them and pays nothing."""
    for judge in cfg.judges:
        for number in range(1, cfg.passes + 1):
            out_dir = cfg.pass_dir(judge, number)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "META.json").write_text("{}", encoding="utf-8")
            for doc in PANEL:
                (out_dir / f"{doc}.json").write_text(
                    json.dumps({"opaque_id": doc, "status_code": 200}),
                    encoding="utf-8",
                )
    cfg.states_dir.mkdir(parents=True, exist_ok=True)
    cfg.signatures_dir.mkdir(parents=True, exist_ok=True)
    for doc in PANEL:
        (cfg.states_dir / f"state_full_{doc}.json").write_text("{}", encoding="utf-8")
        (cfg.signatures_dir / f"signature_{doc}.json").write_text(
            "{}", encoding="utf-8"
        )


def _runner(condition2_rc: int) -> Dict[str, List[str]]:
    """A runner that succeeds at everything the disk already fed, and whose
    condition2 exit is the witness's knob."""
    ran: Dict[str, List[str]] = {"steps": []}

    def runner(step: run_cycle.Step) -> int:
        ran["steps"].append(step.name)
        return condition2_rc if step.name == "condition2" else 0

    return ran, runner


class TestThePlanCarriesTheCounter:
    def test_both_roles_the_cycle_dir_and_the_previous_half(self, tmp_path):
        cfg = _config(tmp_path, compare_with_tag="c21")
        step = next(s for s in run_cycle.plan(cfg) if s.name == "condition2")
        argv = step.argv
        # One --judge per family: the two roles' consensus directories.
        judges = [argv[i + 1] for i, a in enumerate(argv) if a == "--judge"]
        assert judges == [
            "g",
            "s",
        ], f"the counter must read both roles' consensuses, got {judges!r}"
        # The reading goes where the runbook files the cycle's artifacts.
        i = argv.index("--cycle-dir")
        assert Path(argv[i + 1]) == cfg.cycle_dir
        # The comparison half: the previous tag, and its cycle directory —
        # where the counter this reading chains from lives.
        i = argv.index("--previous-tag")
        assert argv[i + 1] == "c21"
        i = argv.index("--previous-cycle-dir")
        assert Path(argv[i + 1]) == cfg.results_root / "panel_cycles" / "c21"
        assert "--new-series" not in argv
        # The counter is free: never a paid step.
        assert step.paid is False

    def test_a_cycle_without_a_comparison_tag_declares_a_new_series(self, tmp_path):
        cfg = _config(tmp_path, compare_with_tag=None)
        step = next(s for s in run_cycle.plan(cfg) if s.name == "condition2")
        assert "--new-series" in step.argv
        assert "--previous-tag" not in step.argv
        assert "--previous-cycle-dir" not in step.argv

    def test_a_single_pass_cycle_builds_no_counter_step(self, tmp_path):
        cfg = _config(tmp_path, compare_with_tag="c21")
        cfg.passes = 1
        names = [step.name for step in run_cycle.plan(cfg)]
        assert (
            "condition2" not in names
        ), "one pass is not a consensus: there is nothing to compare"


class TestTheCycleRefusesAnUnreadCounter:
    def _cycle(self, tmp_path, condition2_rc: int):
        cfg = _config(tmp_path, compare_with_tag="c21")
        _world(cfg)
        ran, runner = _runner(condition2_rc)
        summary = run_cycle.run_cycle(
            cfg,
            runner=runner,
            credit=lambda: dict(CREDIT),
            head=lambda: dict(HEAD),
        )
        return cfg, ran, summary

    def test_a_refused_condition2_stops_the_cycle_loud(self, tmp_path):
        cfg, ran, summary = self._cycle(tmp_path, condition2_rc=1)
        assert "condition2" in ran["steps"], "the counter step must be dispatched"
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert "condition2 refused" in str(summary["stopped"]), (
            "a refused counter must stop the cycle stopped-loud, never a "
            f"green finish — got stopped={summary['stopped']!r}"
        )
        assert summary["condition2"] == {"rc": 1, "families": ["g", "s"]}

    def test_a_refused_condition2_is_named_in_the_status_line(self, tmp_path):
        cfg, ran, summary = self._cycle(tmp_path, condition2_rc=1)
        events = [
            json.loads(line)
            for line in (cfg.cycle_dir / "status.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        counters = [e for e in events if e.get("event") == "condition2"]
        assert counters and counters[-1]["rc"] == 1

    def test_a_green_condition2_lets_the_cycle_finish_green(self, tmp_path):
        cfg, ran, summary = self._cycle(tmp_path, condition2_rc=0)
        assert "condition2" in ran["steps"]
        assert summary["exit_code"] == run_cycle.EXIT_OK
        assert summary["stopped"] is None
        assert summary["condition2"] == {"rc": 0, "families": ["g", "s"]}
