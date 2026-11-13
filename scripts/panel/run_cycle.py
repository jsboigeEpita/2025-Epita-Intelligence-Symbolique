"""One panel cycle, from the pipeline run to the traced judge items.

    python scripts/panel/run_cycle.py --tag <cycle> \\
        --panel-file <panel> --zeroshot-dir <zero-shot arm> \\
        --judge g=gemini-4-argon,env.OPENROUTER_CHAT_MODEL_ID=google/gemini-4-argon \\
        --judge s=claude-sonnet-5-5,batch \\
        --passes 6 --partial-consensus 3 --compare-with-tag <previous cycle> \\
        --min-credit <expected OpenRouter cost>

    ... --plan            print every command of the cycle and run nothing
    ... --stage pipeline  the pipeline and the harvest only
    ... --stage judges    the judges, on a cycle already harvested
    ... --stage consensus the consensus and the trace only: pays nothing

A cycle is the unit of the v1 bar (CLAUDE.md, "When v1 Is Done"): the whole
panel through the pipeline once, each judge family over it several times, a
consensus per family, and the free tracer on the consensus. This runner is
that sequence with the stops a paid run has already cost us:

- **nothing paid on an unjudgeable cycle** — every panel document must have
  its zero-shot answer before the pipeline starts, and the OpenRouter key
  must have more left than ``--min-credit``;
- **no paid judge on a failed batch** (R1149) — a pipeline exit code other
  than 0 stops the cycle;
- **one commit per cycle** — ``HEAD`` is read before and after the pipeline;
  a checkout during the run means the documents did not all run the same
  code, and the cycle stops;
- **this cycle's states, not the last one's** — the harvest takes each panel
  document's state and signature only if the pipeline wrote them during this
  run; a missing or older file stops the cycle;
- **the judge's dry-run before its first paid pass** — it resolves the route
  and reads the arms exactly as the paid pass will;
- **one pass before five** — a synchronous family runs its first pass alone
  and the others in parallel only if it judged the whole panel (a batch
  family submits all its passes at once: nothing is saved by waiting);
- **no second spend** — a pass whose stored rows already cover the panel
  (``judge_panel.unjudged_documents``) is skipped, so ``--stage judges`` can
  be re-run after a failure;
- **a consensus of the planned passes or none** — a family with an incomplete
  pass builds no consensus;
- **a resume does not launder a failed batch** — the pipeline stage records
  its commit, exit code and harvest in ``pipeline.json``; ``--stage judges``
  reads that record back and refuses a pipeline it shows as failed, and every
  later ``cycle.json`` carries it, so the commit the states were produced at
  is never replaced by the commit of the invocation that judged them.

Everything is written under ``<results>/panel_cycles/<tag>/`` (gitignored):
``states/``, ``signatures/``, ``logs/``, ``pipeline.json`` (the pipeline
run: commit, tree, dirty flag, exit code, harvest), ``status.jsonl`` (one
event per line, as it happens), ``cycle.json`` (the last invocation: its
command and commit, exit codes, credit before and after, and the pipeline
record) and ``trace.jsonl``. The judge's own directories keep their names,
``<results>/judge_panel_3375_<tag>_<judge>_p<i>`` and ``..._cons<k>``.

Exit code: 0 the cycle ran whole; 1 it stopped before any judge; 2 a judge
family did not complete. The panel is passed by path and stays local: this
file names no document.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402
from scripts.panel import openrouter_credit  # noqa: E402

PASS_PREFIX = "judge_panel_3375"
PIPELINE_RECORD = "pipeline.json"
STAGES = ("all", "pipeline", "judges", "consensus")
DEFAULT_PASSES = 6
DEFAULT_PIPELINE_TIMEOUT = 7200
# A file the pipeline wrote during the run can carry a timestamp a little
# before the clock reading taken at launch (filesystem and clock granularity).
# A state left by an earlier cycle is hours old: two seconds cannot admit it.
FRESHNESS_TOLERANCE_SECONDS = 2.0
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

EXIT_OK, EXIT_STOPPED, EXIT_JUDGES = 0, 1, 2


@dataclass(frozen=True)
class Judge:
    """One judge family: ``name`` enters its directory names."""

    name: str
    model: str
    batch: bool = False
    env: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Step:
    """One command of the cycle."""

    name: str
    argv: List[str]
    log: Path
    env: Mapping[str, str] = field(default_factory=dict)
    paid: bool = False


Runner = Callable[[Step], int]


def parse_judge(spec: str) -> Judge:
    """``NAME=MODEL[,batch][,env.KEY=VALUE ...]``"""
    head, _, rest = spec.partition(",")
    name, sep, model = head.partition("=")
    if not sep or not _NAME.match(name) or not model.strip():
        raise ValueError(f"judge spec {spec!r}: expected NAME=MODEL[,batch][,env.K=V]")
    batch = False
    env: Dict[str, str] = {}
    for option in filter(None, (part.strip() for part in rest.split(","))):
        if option == "batch":
            batch = True
        elif option.startswith("env.") and "=" in option:
            key, _, value = option[len("env.") :].partition("=")
            env[key] = value
        else:
            raise ValueError(f"judge spec {spec!r}: unknown option {option!r}")
    return Judge(name=name, model=model.strip(), batch=batch, env=env)


@dataclass
class Config:
    tag: str
    panel_file: Path
    zeroshot_dir: Path
    judges: Sequence[Judge] = ()
    passes: int = DEFAULT_PASSES
    partial_consensus: Sequence[int] = ()
    compare_with_tag: Optional[str] = None
    seed: int = c.DEFAULT_SEED
    pipeline_timeout: int = DEFAULT_PIPELINE_TIMEOUT
    min_credit: float = 0.0
    stage: str = "all"
    results_root: Path = c.RESULTS_ROOT
    kb_root: Path = c.REPO_ROOT / "analysis_kb"
    repo_root: Path = c.REPO_ROOT
    python: str = sys.executable

    def __post_init__(self) -> None:
        if not _NAME.match(self.tag):
            raise ValueError(f"tag {self.tag!r}: letters, digits, '_', '.', '-' only")
        if self.stage not in STAGES:
            raise ValueError(f"stage {self.stage!r}: one of {STAGES}")
        if self.passes < 1:
            raise ValueError("passes must be at least 1")
        names = [judge.name for judge in self.judges]
        if len(set(names)) != len(names):
            raise ValueError(f"two judges share a name: {names}")
        for size in self.partial_consensus:
            if not 2 <= size < self.passes:
                raise ValueError(
                    f"partial consensus {size}: between 2 and passes-1 "
                    f"({self.passes - 1})"
                )

    # -- where things live ---------------------------------------------------

    @property
    def cycle_dir(self) -> Path:
        return self.results_root / "panel_cycles" / self.tag

    @property
    def states_dir(self) -> Path:
        return self.cycle_dir / "states"

    @property
    def signatures_dir(self) -> Path:
        return self.cycle_dir / "signatures"

    @property
    def logs_dir(self) -> Path:
        return self.cycle_dir / "logs"

    def pass_dir(self, judge: Judge, number: int, tag: Optional[str] = None) -> Path:
        return self.results_root / (
            f"{PASS_PREFIX}_{tag or self.tag}_{judge.name}_p{number}"
        )

    def consensus_dir(self, judge: Judge, size: int, tag: Optional[str] = None) -> Path:
        return self.results_root / (
            f"{PASS_PREFIX}_{tag or self.tag}_{judge.name}_cons{size}"
        )

    def consensus_sizes(self) -> List[int]:
        """The partial consensuses, then the one over every pass. One pass is
        not a consensus: a single-pass cycle builds none."""
        sizes = sorted(set(self.partial_consensus))
        if self.passes >= 2:
            sizes.append(self.passes)
        return sizes

    def previous_consensus(self, judge: Judge, size: int) -> Optional[Path]:
        """The consensus of ``compare_with_tag`` a new one is compared with:
        the same size when the previous cycle has it, else its largest."""
        if not self.compare_with_tag:
            return None
        same = self.consensus_dir(judge, size, self.compare_with_tag)
        if same.is_dir():
            return same
        prefix = f"{PASS_PREFIX}_{self.compare_with_tag}_{judge.name}_cons"
        found = []
        for path in self.results_root.glob(prefix + "*"):
            suffix = path.name[len(prefix) :]
            if path.is_dir() and suffix.isdigit():
                found.append((int(suffix), path))
        return max(found)[1] if found else None


# ---------------------------------------------------------------------------
# The commands
# ---------------------------------------------------------------------------


def pipeline_step(cfg: Config) -> Step:
    return Step(
        name="pipeline",
        argv=[
            cfg.python,
            "scripts/dataset/run_corpus_batch.py",
            "--panel-file",
            str(cfg.panel_file),
            "--timeout",
            str(cfg.pipeline_timeout),
        ],
        log=cfg.logs_dir / "pipeline.log",
        paid=True,
    )


def _judge_argv(cfg: Config, judge: Judge, number: int) -> List[str]:
    argv = [
        cfg.python,
        "scripts/dataset/judge_panel.py",
        "--judge-model",
        judge.model,
        "--panel-file",
        str(cfg.panel_file),
        "--seed",
        str(cfg.seed),
        "--states-dir",
        str(cfg.states_dir),
        "--signatures-dir",
        str(cfg.signatures_dir),
        "--zeroshot-dir",
        str(cfg.zeroshot_dir),
        "--out-dir",
        str(cfg.pass_dir(judge, number)),
    ]
    if judge.batch:
        argv.append("--anthropic-batch")
    return argv


def dry_run_step(cfg: Config, judge: Judge, number: int = 1) -> Step:
    return Step(
        name=f"{judge.name}.dry",
        argv=_judge_argv(cfg, judge, number) + ["--dry-run"],
        log=cfg.logs_dir / f"judge_{judge.name}_dry.log",
        env=dict(judge.env),
    )


def pass_step(cfg: Config, judge: Judge, number: int) -> Step:
    return Step(
        name=f"{judge.name}.p{number}",
        argv=_judge_argv(cfg, judge, number),
        log=cfg.logs_dir / f"judge_{judge.name}_p{number}.log",
        env=dict(judge.env),
        paid=True,
    )


def consensus_step(cfg: Config, judge: Judge, size: int) -> Step:
    argv = [cfg.python, "scripts/dataset/judge_panel.py", "--consensus"]
    argv += [str(cfg.pass_dir(judge, number)) for number in range(1, size + 1)]
    argv += [
        "--panel-file",
        str(cfg.panel_file),
        "--out-dir",
        str(cfg.consensus_dir(judge, size)),
    ]
    previous = cfg.previous_consensus(judge, size)
    if previous is not None:
        argv += ["--compare-with", str(previous)]
    return Step(
        name=f"{judge.name}.cons{size}",
        argv=argv,
        log=cfg.logs_dir / f"judge_{judge.name}_cons{size}.log",
    )


def trace_step(cfg: Config, judges: Sequence[Judge]) -> Step:
    argv = [
        cfg.python,
        "scripts/panel/trace_items.py",
        "--states-dir",
        str(cfg.states_dir),
        "--consensus-dir",
    ]
    argv += [str(cfg.consensus_dir(judge, cfg.passes)) for judge in judges]
    argv += ["--out", str(cfg.cycle_dir / "trace.jsonl")]
    return Step(name="trace", argv=argv, log=cfg.logs_dir / "trace.log")


def plan(cfg: Config) -> List[Step]:
    """Every command the cycle can run, in order. ``--plan`` prints it; the
    run itself goes through the same builders."""
    steps: List[Step] = []
    if cfg.stage in ("all", "pipeline"):
        steps.append(pipeline_step(cfg))
    if cfg.stage != "pipeline":
        for judge in cfg.judges:
            if cfg.stage != "consensus":
                steps.append(dry_run_step(cfg, judge))
                steps += [pass_step(cfg, judge, n) for n in range(1, cfg.passes + 1)]
            steps += [consensus_step(cfg, judge, k) for k in cfg.consensus_sizes()]
        if cfg.judges and cfg.passes >= 2:
            steps.append(trace_step(cfg, cfg.judges))
    return steps


def subprocess_runner(step: Step, repo_root: Path = c.REPO_ROOT) -> int:
    """Run a step from the checkout root, its output in its log."""
    step.log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root) + (os.pathsep + inherited if inherited else "")
    # A user-site package must not shadow the environment's (#2282 A0), and a
    # redirected child must not die encoding its own report.
    env.setdefault("PYTHONNOUSERSITE", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.update(step.env)
    with step.log.open("w", encoding="utf-8") as log:
        return subprocess.run(
            step.argv, cwd=repo_root, env=env, stdout=log, stderr=subprocess.STDOUT
        ).returncode


def run_parallel(runner: Runner, steps: Sequence[Step]) -> List[int]:
    if not steps:
        return []
    with ThreadPoolExecutor(max_workers=len(steps)) as pool:
        return list(pool.map(runner, steps))


# ---------------------------------------------------------------------------
# What the runner reads back
# ---------------------------------------------------------------------------


def git_head(repo_root: Path = c.REPO_ROOT) -> Dict[str, Any]:
    """``head``, ``tree`` and whether tracked files differ from the commit."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, check=True
        ).stdout.strip()

    return {
        "head": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
    }


def read_credit() -> Optional[Dict[str, Any]]:
    """The OpenRouter credit, or ``None`` when it cannot be read — an unread
    credit is reported as unread, never as zero."""
    try:
        return openrouter_credit.read_credit()
    except openrouter_credit.CreditUnavailable as exc:
        return {"unavailable": str(exc)}


def pipeline_verdict(log: Path) -> Optional[str]:
    """The pipeline's own ``Verdict:`` line (a status, no document text)."""
    if not log.is_file():
        return None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Verdict:"):
            return line.strip()[:160]
    return None


def missing_zeroshot(cfg: Config, panel: Sequence[str]) -> List[str]:
    """Panel documents without a zero-shot answer: the judge would refuse
    them, after the pipeline was paid."""
    missing = []
    for doc in panel:
        path = cfg.zeroshot_dir / f"{doc}.json"
        try:
            answer = json.loads(path.read_text(encoding="utf-8")).get("answer")
        except (OSError, ValueError, AttributeError):
            answer = None
        if not answer:
            missing.append(doc)
    return missing


def harvest(cfg: Config, panel: Sequence[str], started: float) -> Dict[str, List[str]]:
    """Copy each panel document's state and signature into the cycle, if the
    pipeline wrote them during this run.

    ``missing``: the pipeline wrote no file. ``stale``: the file is older than
    the run — it belongs to an earlier cycle, and judging it would grade code
    this cycle did not run. Either stops the cycle.
    """
    report: Dict[str, List[str]] = {"copied": [], "missing": [], "stale": []}
    cfg.states_dir.mkdir(parents=True, exist_ok=True)
    cfg.signatures_dir.mkdir(parents=True, exist_ok=True)
    floor = started - FRESHNESS_TOLERANCE_SECONDS
    for doc in panel:
        pairs = (
            (cfg.kb_root / "state_dumps" / f"state_full_{doc}.json", cfg.states_dir),
            (cfg.kb_root / "signatures" / f"signature_{doc}.json", cfg.signatures_dir),
        )
        if not all(source.is_file() for source, _ in pairs):
            report["missing"].append(doc)
        elif not all(source.stat().st_mtime >= floor for source, _ in pairs):
            report["stale"].append(doc)
        else:
            for source, target in pairs:
                shutil.copy2(source, target / source.name)
            report["copied"].append(doc)
    return report


def recorded_pipeline(cfg: Config) -> Optional[Dict[str, Any]]:
    """What the pipeline stage recorded for this cycle — the commit its states
    were produced at, its exit code, the harvest — or ``None`` for a cycle
    harvested without the runner."""
    try:
        record = json.loads(
            (cfg.cycle_dir / PIPELINE_RECORD).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def pipeline_problem(record: Mapping[str, Any]) -> Optional[str]:
    """Why a pipeline run cannot be judged, or ``None``. One rule for the run
    that just ended and for the record a resumed cycle reads back."""
    rc, harvested = record.get("rc"), record.get("harvest") or {}
    if rc != 0:
        return f"pipeline exit {rc}: no paid judge on a failed batch (R1149)"
    before, after = str(record.get("head")), str(record.get("head_after"))
    if before != after:
        return (
            f"HEAD moved during the pipeline ({before[:9]} -> {after[:9]}): "
            "the documents did not all run the same code"
        )
    if harvested.get("missing") or harvested.get("stale"):
        return (
            f"harvest incomplete: {harvested.get('missing')} missing, "
            f"{harvested.get('stale')} older than the run"
        )
    return None


def unharvested(cfg: Config, panel: Sequence[str]) -> List[str]:
    """Panel documents the cycle holds no state or signature for."""
    return [
        doc
        for doc in panel
        if not (cfg.states_dir / f"state_full_{doc}.json").is_file()
        or not (cfg.signatures_dir / f"signature_{doc}.json").is_file()
    ]


def pass_complete(out_dir: Path, panel: Sequence[str]) -> bool:
    """A pass that judged the whole panel, by the judge's own rule."""
    from scripts.dataset import judge_panel as jp

    if not (out_dir / jp.META_FILENAME).is_file():
        return False
    rows = []
    for doc in panel:
        path = out_dir / f"{doc}.json"
        if not path.is_file():
            return False
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except ValueError:
            return False
    failed, truncated = jp.unjudged_documents(rows)
    return not failed and not truncated


class Status:
    """The cycle's events, one JSON line each, printed as they happen."""

    def __init__(self, path: Path, now: Callable[[], float] = time.time) -> None:
        self.path, self.now = path, now
        self.events: List[Dict[str, Any]] = []

    def stamp(self) -> str:
        return datetime.fromtimestamp(self.now(), timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    def event(self, name: str, **fields: Any) -> None:
        record = {"at": self.stamp(), "event": name, **fields}
        self.events.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------


def run_family(
    cfg: Config, judge: Judge, panel: Sequence[str], runner: Runner, status: Status
) -> Dict[str, Any]:
    """One judge family: dry-run, passes, consensus."""
    result: Dict[str, Any] = {
        "model": judge.model,
        "batch": judge.batch,
        "passes": {},
        "consensus": {},
        "ok": False,
    }
    numbers = list(range(1, cfg.passes + 1))
    todo = []
    for number in numbers:
        if pass_complete(cfg.pass_dir(judge, number), panel):
            result["passes"][f"p{number}"] = "already complete"
            status.event("pass_skipped_complete", judge=judge.name, n=number)
        else:
            todo.append(number)
    if todo and cfg.stage == "consensus":
        # The stage that pays nothing: it reads the passes that exist.
        result["stopped"] = f"incomplete pass(es) {todo}: --stage consensus pays none"
        status.event("family_incomplete", judge=judge.name, passes=todo)
        return result
    if todo:
        rc = runner(dry_run_step(cfg, judge, todo[0]))
        status.event("judge_dry_run", judge=judge.name, rc=rc)
        if rc != 0:
            result["stopped"] = f"dry-run exit {rc}: no paid pass"
            return result
        # A batch family gains nothing by waiting on its first pass; a
        # synchronous one pays five more passes on whatever broke the first.
        groups = [todo] if judge.batch else [todo[:1], todo[1:]]
        for group in groups:
            steps = [pass_step(cfg, judge, number) for number in group]
            for number, rc in zip(group, run_parallel(runner, steps)):
                result["passes"][f"p{number}"] = rc
                status.event("judge_pass", judge=judge.name, n=number, rc=rc)
            if any(result["passes"][f"p{number}"] != 0 for number in group):
                break
    incomplete = [
        number
        for number in numbers
        if not pass_complete(cfg.pass_dir(judge, number), panel)
    ]
    if incomplete:
        result["stopped"] = f"incomplete pass(es) {incomplete}: no consensus"
        status.event("family_incomplete", judge=judge.name, passes=incomplete)
        return result
    for size in cfg.consensus_sizes():
        step = consensus_step(cfg, judge, size)
        rc = runner(step)
        result["consensus"][f"cons{size}"] = rc
        status.event(
            "consensus",
            judge=judge.name,
            size=size,
            rc=rc,
            compared="--compare-with" in step.argv,
        )
    result["ok"] = all(rc == 0 for rc in result["consensus"].values())
    return result


def run_cycle(
    cfg: Config,
    runner: Runner = subprocess_runner,
    credit: Callable[[], Optional[Dict[str, Any]]] = read_credit,
    head: Callable[[], Dict[str, Any]] = git_head,
    now: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """Run the cycle; the returned summary is what ``cycle.json`` holds."""
    c.ensure_gitignored(cfg.cycle_dir, cfg.repo_root)
    # The campaign's one parser: it raises on a missing or empty panel file.
    panel = c.read_panel(cfg.panel_file) or []
    status = Status(cfg.cycle_dir / "status.jsonl", now)
    at_start = head()
    summary: Dict[str, Any] = {
        "tag": cfg.tag,
        "stage": cfg.stage,
        "command": "python scripts/panel/run_cycle.py " + " ".join(sys.argv[1:]),
        "started": status.stamp(),
        **at_start,
        "panel_file": str(cfg.panel_file),
        "panel_size": len(panel),
        "zeroshot_dir": str(cfg.zeroshot_dir),
        "passes": cfg.passes,
        "judges": {},
        "stopped": None,
        "exit_code": EXIT_OK,
    }

    def finish(stopped: Optional[str], code: int) -> Dict[str, Any]:
        after = credit()
        summary["credit_after"] = after
        summary["openrouter_spent"] = openrouter_credit.spent_between(
            summary.get("credit_before"), after
        )
        summary["head_at_end"] = head()["head"]
        summary["stopped"], summary["exit_code"] = stopped, code
        summary["ended"] = status.stamp()
        status.event(
            "end",
            stopped=stopped,
            exit_code=code,
            openrouter_spent=summary["openrouter_spent"],
        )
        (cfg.cycle_dir / "cycle.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return summary

    status.event(
        "start",
        tag=cfg.tag,
        stage=cfg.stage,
        panel_size=len(panel),
        judges=[judge.name for judge in cfg.judges],
        **at_start,
    )
    summary["credit_before"] = credit()
    status.event("credit_before", **(summary["credit_before"] or {}))
    if cfg.stage != "pipeline" and not cfg.judges:
        return finish("no judge given: pass --judge NAME=MODEL", EXIT_STOPPED)
    absent = missing_zeroshot(cfg, panel)
    if absent:
        status.event("zeroshot_missing", documents=absent)
        return finish(
            f"{len(absent)} panel document(s) have no zero-shot answer: the "
            "cycle could not be judged",
            EXIT_STOPPED,
        )

    if cfg.stage in ("all", "pipeline"):
        remaining = (summary["credit_before"] or {}).get("limit_remaining")
        if isinstance(remaining, (int, float)) and remaining <= cfg.min_credit:
            return finish(
                f"OpenRouter credit left ({remaining}) is not above "
                f"--min-credit ({cfg.min_credit})",
                EXIT_STOPPED,
            )
        started = now()
        step = pipeline_step(cfg)
        rc = runner(step)
        seconds = round(now() - started)
        report = harvest(cfg, panel, started)
        record = {
            **at_start,
            "head_after": head()["head"],
            "started": summary["started"],
            "rc": rc,
            "verdict": pipeline_verdict(step.log),
            "seconds": seconds,
            "harvest": {key: len(value) for key, value in report.items()},
        }
        (cfg.cycle_dir / PIPELINE_RECORD).write_text(
            json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        summary["pipeline"] = record
        status.event(
            "pipeline",
            **record,
            missing_documents=report["missing"],
            stale_documents=report["stale"],
        )
        summary["credit_after_pipeline"] = credit()
        status.event(
            "credit_after_pipeline", **(summary["credit_after_pipeline"] or {})
        )
        problem = pipeline_problem(record)
        if problem:
            return finish(problem, EXIT_STOPPED)
    else:
        # A resumed cycle is judged on states an earlier invocation produced:
        # their commit is the pipeline's record, never this invocation's HEAD.
        summary["pipeline"] = recorded_pipeline(cfg)
        if summary["pipeline"] is None:
            status.event("pipeline_unrecorded")
        elif cfg.stage == "judges":
            problem = pipeline_problem(summary["pipeline"])
            if problem:
                return finish(
                    f"the recorded pipeline cannot be judged — {problem}",
                    EXIT_STOPPED,
                )
    if cfg.stage == "pipeline":
        return finish(None, EXIT_OK)

    absent = unharvested(cfg, panel)
    if absent:
        status.event("unharvested", documents=absent)
        return finish(
            f"{len(absent)} panel document(s) have no harvested state: run "
            "--stage pipeline first",
            EXIT_STOPPED,
        )
    with ThreadPoolExecutor(max_workers=len(cfg.judges)) as pool:
        results = list(
            pool.map(
                lambda judge: run_family(cfg, judge, panel, runner, status), cfg.judges
            )
        )
    summary["judges"] = {
        judge.name: result for judge, result in zip(cfg.judges, results)
    }
    judged = [judge for judge, result in zip(cfg.judges, results) if result["ok"]]
    if judged and cfg.passes >= 2:
        rc = runner(trace_step(cfg, judged))
        summary["trace"] = {"rc": rc, "families": [judge.name for judge in judged]}
        status.event("trace", **summary["trace"])
    failed = [
        judge.name for judge, result in zip(cfg.judges, results) if not result["ok"]
    ]
    if failed:
        return finish(f"judge family not complete: {failed}", EXIT_JUDGES)
    return finish(None, EXIT_OK)


def _quote(arg: str) -> str:
    return f'"{arg}"' if (" " in arg or not arg) else arg


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tag", required=True, help="the cycle's name, e.g. c7")
    parser.add_argument("--panel-file", type=Path, required=True)
    parser.add_argument("--zeroshot-dir", type=Path, required=True)
    parser.add_argument(
        "--judge",
        action="append",
        default=[],
        metavar="NAME=MODEL[,batch][,env.KEY=VALUE]",
        help="a judge family; repeat for several. 'batch' routes an Anthropic "
        "judge through Message Batches; env.KEY=VALUE is set for that judge's "
        "commands only",
    )
    parser.add_argument("--passes", type=int, default=DEFAULT_PASSES)
    parser.add_argument(
        "--partial-consensus",
        type=int,
        nargs="*",
        default=[],
        help="also build a consensus over the first K passes",
    )
    parser.add_argument(
        "--compare-with-tag",
        default=None,
        help="the previous cycle: each consensus gets a STABILITY.md against it",
    )
    parser.add_argument("--seed", type=int, default=c.DEFAULT_SEED)
    parser.add_argument(
        "--pipeline-timeout", type=int, default=DEFAULT_PIPELINE_TIMEOUT
    )
    parser.add_argument(
        "--min-credit",
        type=float,
        default=0.0,
        help="USD the OpenRouter key must have left, strictly above, for the "
        "pipeline to start: pass the cycle's expected cost",
    )
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = Config(
            tag=args.tag,
            panel_file=args.panel_file,
            zeroshot_dir=args.zeroshot_dir,
            judges=[parse_judge(spec) for spec in args.judge],
            passes=args.passes,
            partial_consensus=args.partial_consensus,
            compare_with_tag=args.compare_with_tag,
            seed=args.seed,
            pipeline_timeout=args.pipeline_timeout,
            min_credit=args.min_credit,
            stage=args.stage,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.plan:
        for step in plan(cfg):
            env = " ".join(f"{key}={value}" for key, value in step.env.items())
            print(
                f"[{step.name}]{' PAID' if step.paid else ''} "
                f"{env + ' ' if env else ''}{' '.join(map(_quote, step.argv))}"
            )
        print("plan only: nothing was run")
        return 0
    try:
        summary = run_cycle(cfg)
    except (ValueError, c.OutputRefused) as exc:
        parser.error(str(exc))
    if summary["stopped"]:
        print(f"STOPPED: {summary['stopped']}")
    return int(summary["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
