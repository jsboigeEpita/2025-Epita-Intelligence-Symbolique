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

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset import judge_panel as jp  # noqa: E402
from scripts.panel import condition2  # noqa: E402
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
        # The runner asks the counter to refuse held readings: without the
        # flag the real command exits 0 on an unproven reading (R1199
        # review) and the cycle finishes green over an unread counter.
        assert "--refuse-holds" in argv
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
    """The plumbing: the dispatched cycle watches the counter step's exit
    code (the knob here covers the wiring only — the stop semantics over
    what the REAL command returns are witnessed one class below)."""

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


# --- the real command, not a knob ------------------------------------------


def _pipeline_record(label: str) -> Dict[str, object]:
    """The real ``pipeline_run`` record shape (#3639 review v4, #3543 item
    1): the run's identity is its inputs and code, not its mount."""
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    return {
        "states_dir": f"/mounts/{label}/states",
        "signatures_dir": f"/mounts/{label}/signatures",
        "code_shas": [digest],
        "inputs_sha256": digest,
    }


def _consensus_dir(path: Path, judge_family: str, pipeline_run=None) -> Path:
    """A consensus directory the REAL condition2 can read end to end: one
    settled row per panel document, a META naming the series, the execution
    (seed + run_head) and the judge family. ``pipeline_run=None`` writes no
    record — the stored c2-c21 shape: every other guarantee holds, the
    judged run does not."""
    votes = {"parsed": 6, "need": 4, "core": 6, "severe": 0, "abstain": 0}
    for doc in PANEL:
        row = {
            "opaque_id": doc,
            "reported_state": jp.state_from_votes(votes),
            "kept": [],
            "consensus": {
                "passes": 6,
                "need": 4,
                "parsed": 6,
                "sources": [],
                "votes": votes,
                "fragile": False,
            },
        }
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{doc}.json").write_text(json.dumps(row), encoding="utf-8")
    meta: Dict[str, object] = {
        "seed": 3375,
        "run_head": "z" * 40,
        "pipeline_model": "openai/gpt-5.6-luna",
        "pipeline_family": "openai",
        "judge_family": judge_family,
        "judge_model": f"judge-{judge_family}",
    }
    if pipeline_run is not None:
        meta["pipeline_run"] = pipeline_run
    (path / jp.META_FILENAME).write_text(json.dumps(meta), encoding="utf-8")
    return path


def _stored_consensuses(cfg: run_cycle.Config, *, run_labels=None) -> None:
    """Both roles' consensus directories under --results-root, as tag mode
    resolves them. ``run_labels=None`` leaves every META without a
    ``pipeline_run`` record (the c2-c21 shape the review measured); a dict
    binds each role to one recorded run label."""
    for judge in cfg.judges:
        for role, tag in (
            ("cur", cfg.tag),
            ("prev", cfg.compare_with_tag),
        ):
            record = (
                _pipeline_record(run_labels[role]) if run_labels is not None else None
            )
            _consensus_dir(
                cfg.results_root
                / f"judge_panel_3375_{tag}_{judge.name}_cons{cfg.passes}",
                f"family-{judge.name}",
                pipeline_run=record,
            )


def _real_condition2_runner():
    """A runner that dispatches the REAL condition2 for the counter step —
    in-process, over the step's own argv — and succeeds elsewhere. No exit
    code is invented: what stops the cycle is what the command returns."""
    ran: Dict[str, List[str]] = {"steps": []}

    def runner(step: run_cycle.Step) -> int:
        ran["steps"].append(step.name)
        if step.name != "condition2":
            return 0
        return condition2.main(step.argv[2:])

    return ran, runner


class TestTheRealCommandStopsTheCycleOnAHeldReading:
    """The R1199 review's measured defect: the real condition2 exits 0 on an
    unproven reading (the hold is a diagnosis, not a refusal), so a wiring
    that watches only the exit code finishes the cycle GREEN over an unread
    counter. These witnesses drive the real command over consensus
    directories of the stored c2-c21 shape — the stop must survive contact
    with what ``main()`` actually returns."""

    def _cycle(self, tmp_path, *, run_labels):
        cfg = _config(tmp_path, compare_with_tag="c21")
        _world(cfg)
        _stored_consensuses(cfg, run_labels=run_labels)
        ran, runner = _real_condition2_runner()
        summary = run_cycle.run_cycle(
            cfg,
            runner=runner,
            credit=lambda: dict(CREDIT),
            head=lambda: dict(HEAD),
        )
        return cfg, ran, summary

    def test_a_held_reading_stops_the_cycle_loud(self, tmp_path):
        cfg, ran, summary = self._cycle(tmp_path, run_labels=None)
        assert "condition2" in ran["steps"]
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED, (
            "the real command over an unproven pair (no pipeline_run record, "
            "the c2-c21 shape) must stop the cycle stopped-loud — got a "
            f"green finish (rc={summary['condition2']['rc']})"
        )
        assert summary["condition2"]["rc"] != 0
        assert "condition2 refused" in str(summary["stopped"])

    def test_a_recorded_reading_under_the_same_wiring_finishes_green(self, tmp_path):
        cfg, ran, summary = self._cycle(
            tmp_path,
            run_labels={"cur": "run-current", "prev": "run-previous"},
        )
        assert summary["exit_code"] == run_cycle.EXIT_OK
        assert summary["stopped"] is None
        assert summary["condition2"]["rc"] == 0
