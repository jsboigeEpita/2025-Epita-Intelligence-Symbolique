"""Act replay: a harvested cycle's recorded acts, judged offline, no model call.

    python scripts/panel/replay_acts.py --cycle-dir \\
        argumentation_analysis/evaluation/results/panel_cycles/c22 \\
        --dest argumentation_analysis/evaluation/results/panel_cycles/c22/replay_r1 \\
        [--panel-file argumentation_analysis/evaluation/results/panel_v1/panel.txt] \\
        [--doc-ids id,id,...] [--acts recorded]

#3658 item 46c. The replay re-runs the three acts of a harvested cycle and
judges the render that follows. This is its **launcher**: the one command that
decides whether a replay may run at all, then produces the text the judge
would read and compares it with a reference rebuilt by the original code.

Three properties, in this order, and the order is the instrument:

1. **Nothing is spent before the inputs are proven.** ``preflight``
   (:mod:`scripts.panel.act_replay_preflight`, #3701) answers, from the files
   alone, whether the cycle is whole and the destination free. It runs first,
   and the modules that build a judged text — the judge's entry point, the
   fiche caller, the pipeline runtime — are imported **after** it answers.
   A preflight that fails therefore creates no model client, reads no
   ``.env``, and writes nothing: a witness in
   ``tests/unit/scripts/panel/test_act_replay_launcher_3658.py`` reads the
   child's ``sys.modules`` on that path.

2. **The reference is reconstructed, never replayed from a stored fiche.**
   Per document the launcher builds two renders of the *same* records by the
   original code — the judge's own entry point (:func:`judge_render`) and the
   fiche caller (:func:`fiche_render`) — and a third by the replay path
   (:func:`replay_render`: a JSON round trip, the recorded act texts written
   back at the state's root, which is what a driver hands the judge). The
   three must be one string, byte for byte. Both constructions come from
   :mod:`scripts.panel.act_replay_fidelity` (#3696), whose logic is reused
   here and never copied.

3. **The comparison can fail, and in which direction it should fail is read
   from the branch.** Each recorded act is altered in memory, one at a time,
   and the render is watched: on a branch whose text carries the acts the
   alteration must move it, and on a branch that prints a terminal
   classification instead — ``non_argumentative`` (``pipeline_full_text``
   never opens the three acts there), ``conversation_real``,
   ``hierarchical_delegation`` (#3470/#3472, no acts by design) — no
   alteration may move it, or an act has leaked into a verdict that does not
   read acts. A branch the witness does not name an expectation for is a
   failure, not a pass: a control that has no stated direction measures
   nothing. Nothing is altered on disk; the alteration lives in the returned
   dictionary.

``--acts recorded`` (the default) is the free path: it replays the recorded
acts and proves the render round-trips. ``--acts live`` runs
:mod:`scripts.panel.act_replay_live`, which **re-runs** the three acts over the
recorded states — one model call per act and per document, the only paid step
of the replay — and writes a sibling tag ``run_cycle --stage judges`` accepts.
That runner is imported only once this launcher's own ``--acts`` dispatch has
chosen it, and it answers the same preflight before it imports anything that
could build a prompt; its identity control refuses the run, before a call,
when the instrument cannot give back the record byte for byte. A refusal that
says what is missing is worth more than a flag that silently spends.

The cycle's own ``pipeline.json`` is applied as the cycle applies it before a
paid judge (:func:`run_cycle.pipeline_problem`): a failed batch, a HEAD that
moved, or an incomplete harvest stops the replay instead of measuring a render
nobody should read.

Report: counts, per-act presence, and sha256 digests, never a passage. It is
valid JSON whose first key is ``provenance`` (#2353), naming the three
instruments that composed it — this launcher, the preflight, the fidelity
witness — by content sha256, so a cited report says which code produced it.
Exit 0 = every document round-trips and every control held in its stated
direction; 1 = a mismatch, a control that did not hold, or a cycle the cycle
itself refuses; 2 = the invocation could not run as asked (nothing is written).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402
from scripts.panel.act_replay_preflight import preflight  # noqa: E402

REPORT = "act_replay.json"
RECORDED = "recorded"
LIVE = "live"
ALTERATION = "\nWITNESS_ALTERATION the recorded act is not this text."

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

STAGE_PREFLIGHT = "preflight"
STAGE_CYCLE = "cycle"
STAGE_RECORDS = "records"
STAGE_REPLAYED = "replayed"

MUST_MOVE = "must_move"
MUST_NOT_MOVE = "must_not_move"
#: The fidelity witness's own branch vocabulary, read from it at call time so
#: that a branch it renames is a loud failure here and not a silent copy.
POSITIVE_BRANCHES = ("BRANCH_ACTS", "BRANCH_CUT")
NEGATIVE_BRANCHES = (
    "BRANCH_NON_ARGUMENTATIVE",
    "BRANCH_CONVERSATION_REAL",
    "BRANCH_HIERARCHICAL_DELEGATION",
)


# ---------------------------------------------------------------------------
# Small, textual, corpus-free helpers
# ---------------------------------------------------------------------------


def _digest(text: str) -> str:
    """The sha256 of a rendered text — the only thing the report keeps of it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _instruments() -> Dict[str, Optional[str]]:
    """The content sha256 of the three instruments that composed this report.

    A report that cannot say which code produced it can only be believed from
    another seat (#2353). ``None`` where a module is not yet imported, which is
    then itself the datum: a header that names nothing is not a header.
    """
    here = Path(__file__).resolve()
    out: Dict[str, Optional[str]] = {
        "launcher": hashlib.sha256(here.read_bytes()).hexdigest()
    }
    for name in ("act_replay_preflight", "act_replay_fidelity"):
        module = sys.modules.get(f"scripts.panel.{name}")
        path = getattr(module, "__file__", None)
        out[name] = (
            hashlib.sha256(Path(path).read_bytes()).hexdigest() if path else None
        )
    return out


def _git(root: Path, *args: str) -> Optional[str]:
    """One git query, ``None`` when git is absent or the query fails."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def provenance(
    argv: Sequence[str],
    cycle_dir: Path,
    destination: Path,
    panel: Optional[Sequence[str]],
) -> Dict[str, Any]:
    """The header #2353 requires: which code, which records, which command.

    Paths, shas, an interpreter version and counts — nothing corpus-derived, so
    the report stays quotable on a GitHub-indexed surface.
    """
    root = c.REPO_ROOT
    dirty_text = _git(root, "status", "--porcelain")
    return {
        "instrument": "act replay of a harvested cycle, recorded acts only",
        "command": ["python", "scripts/panel/replay_acts.py", *argv],
        "code": {
            "root": str(root),
            "head": _git(root, "rev-parse", "HEAD"),
            "dirty": None if dirty_text is None else bool(dirty_text),
            "instruments": _instruments(),
            "executable": sys.executable,
        },
        "route": {
            "cycle_dir": str(Path(cycle_dir).resolve()),
            "destination": str(Path(destination).resolve()),
            "panel_size": None if panel is None else len(panel),
        },
        "python": sys.version.split()[0],
        "llm_requests": 0,
        "units": "characters, counts and sha256 only, never text",
    }


# ---------------------------------------------------------------------------
# The per-document measurement
# ---------------------------------------------------------------------------


def act_report(recorded: Mapping[str, Any]) -> Dict[str, Any]:
    """What the state records for each of the three acts, by name.

    Whether an act is *empty* is left to the launcher by the preflight's own
    docstring. An act the state does not carry and an act recorded as the
    empty string are told apart: the first is absent, the second was produced
    and said nothing.
    """
    rows: Dict[str, Any] = {}
    for key in c.ACTS:
        value = recorded.get(key)
        text = value if isinstance(value, str) else None
        rows[key] = {
            "present": key in recorded,
            "recorded": text is not None,
            "empty": None if text is None else not text.strip(),
            "chars": None if text is None else len(text),
        }
    return rows


def direction_of(branch: Optional[str], fidelity: Any) -> Optional[str]:
    """The direction this branch's control must hold, or ``None`` if unnamed.

    Read from the witness's own constants, never from a copy of their values: a
    branch added or renamed there lands here as ``None``, and ``None`` fails
    closed rather than silently measuring nothing.
    """
    for name in POSITIVE_BRANCHES:
        if branch is not None and getattr(fidelity, name, None) == branch:
            return MUST_MOVE
    for name in NEGATIVE_BRANCHES:
        if branch is not None and getattr(fidelity, name, None) == branch:
            return MUST_NOT_MOVE
    return None


def controls(
    state: Mapping[str, Any],
    signature: Mapping[str, Any],
    reference: str,
    recorded: Mapping[str, Any],
    branch: Optional[str],
    fidelity: Any,
) -> Dict[str, Any]:
    """Alter each recorded act in memory; the render must answer as the branch says.

    ``fidelity`` is passed in, not imported here: this module's scope stays
    free of the text builders so that the preflight can answer before they
    exist.
    """
    direction = direction_of(branch, fidelity)
    rows: Dict[str, Any] = {}
    for key in c.ACTS:
        current = recorded.get(key)
        altered = dict(recorded)
        altered[key] = (current if isinstance(current, str) else "") + ALTERATION
        moved = fidelity.compare(
            reference, fidelity.replay_render(state, signature, altered)
        )
        rows[key] = {
            "moved": moved["equal"] is False,
            "sections": moved["sections_differing"][:6],
            "sections_only_in_reference": moved["sections_only_in_reference"][:6],
            "sections_only_in_rebuilt": moved["sections_only_in_rebuilt"][:6],
        }
    moved_keys = [key for key, row in rows.items() if row["moved"]]
    if direction == MUST_MOVE:
        # Every act slot must reach the text: writing prose into a slot the
        # render reads changes it, whether the slot held an act or the
        # absence line that stands in for one.
        expected = list(c.ACTS)
        missing = [key for key in expected if key not in moved_keys]
        held = not missing
    elif direction == MUST_NOT_MOVE:
        expected, missing = [], []
        held = not moved_keys
    else:
        expected, missing, held = [], [], False
    return {
        "direction": direction,
        "branch": branch,
        "acts": rows,
        "moved": moved_keys,
        "expected_to_move": expected,
        "did_not_move": missing,
        "ok": held,
    }


def document(
    doc: str,
    state: Mapping[str, Any],
    signature: Mapping[str, Any],
    fidelity: Any,
) -> Dict[str, Any]:
    """One document's line: three constructions of one text, and the control."""
    branch = fidelity.render_branch(state, signature)
    recorded = fidelity.recorded_acts(state)
    reference = fidelity.judge_render(state, signature)
    fiche = fidelity.fiche_render(state, signature)
    replay = fidelity.replay_render(state, signature)
    from_judge = fidelity.compare(reference, replay)
    from_fiche = fidelity.compare(fiche, replay)
    lengths = fidelity.recorded_lengths(state, signature)
    inputs_hold = all(
        row["equal"] is True for row in lengths.values() if row["equal"] is not None
    )
    control = controls(state, signature, reference, recorded, branch, fidelity)
    entry: Dict[str, Any] = {
        "doc": doc,
        "branch": branch,
        "inputs_unchanged": inputs_hold,
        "acts": act_report(recorded),
        "reference": {"chars": len(reference), "sha256": _digest(reference)},
        "callers": {
            "fiche": {"chars": len(fiche), "sha256": _digest(fiche)},
            "replay": {"chars": len(replay), "sha256": _digest(replay)},
        },
        "equal": {
            "judge_vs_replay": from_judge["equal"],
            "fiche_vs_replay": from_fiche["equal"],
        },
        "diff": {
            "judge_vs_replay": from_judge,
            "fiche_vs_replay": from_fiche,
        },
        "control": control,
    }
    entry["ok"] = (
        entry["equal"]["judge_vs_replay"] is True
        and entry["equal"]["fiche_vs_replay"] is True
        and entry["inputs_unchanged"]
        and control["ok"]
    )
    return entry


def _broken(doc: str, failed: BaseException) -> Dict[str, Any]:
    """A document the measurement could not carry: named, and still a count.

    One unreadable record must not cost the other nine their measurement, and
    must not read as a pass either: ``ok`` is false and the reason says the
    measurement itself failed, which is not the same as a render that differs.
    """
    return {
        "doc": doc,
        "ok": False,
        "error": type(failed).__name__,
        "branch": None,
        "inputs_unchanged": None,
        "acts": {},
        "equal": {},
        "control": {"direction": None, "acts": {}, "moved": [], "ok": False},
    }


def _reasons(entry: Mapping[str, Any]) -> List[str]:
    """Why one document does not hold (empty = it holds)."""
    if entry.get("error"):
        return [f"measurement failed ({entry['error']})"]
    out: List[str] = []
    for name, equal in entry["equal"].items():
        if equal is not True:
            out.append(f"render mismatch ({name})")
    if not entry["inputs_unchanged"]:
        out.append("the signature recorded another act length")
    control = entry["control"]
    if control["direction"] is None:
        out.append(f"no expected direction for branch {entry['branch']!r}")
    elif control["direction"] == MUST_MOVE and control["did_not_move"]:
        out.append(
            "an act that must reach the render did not: "
            + ", ".join(control["did_not_move"])
        )
    elif control["direction"] == MUST_NOT_MOVE and control["moved"]:
        out.append(
            "an act moved a render that must not read acts: "
            + ", ".join(control["moved"])
        )
    return out


# ---------------------------------------------------------------------------
# The launcher proper
# ---------------------------------------------------------------------------


def replay(
    cycle_dir: Path,
    destination: Path,
    panel: Optional[Sequence[str]] = None,
    acts: str = RECORDED,
    repo_root: Path = c.REPO_ROOT,
    argv: Sequence[str] = (),
) -> Dict[str, Any]:
    """The report, or the reason no replay ran. Writes nothing, on any path.

    1. the preflight answers first (:mod:`act_replay_preflight`);
    2. the cycle's own ``pipeline.json`` is applied as the cycle applies it;
    3. only then are the text builders imported, and the records measured.

    Every return is a plain dictionary: ``ok`` says whether the replay may be
    read as a measurement, ``stage`` says where it stopped.
    """
    if acts != RECORDED:
        # Not a silent fallback: the paid path is another module with its own
        # gate, its own budget and its own tag. A caller that asks for it here
        # is sent to it by name.
        return {
            "ok": False,
            "stage": STAGE_PREFLIGHT,
            "refused": (
                f"--acts {acts}: this launcher replays the recorded acts only. "
                "The live path is scripts.panel.act_replay_live (it re-runs the "
                "acts, pays one call per act and per document, and writes a "
                "judge-readable tag)."
            ),
        }
    verdict = preflight(Path(cycle_dir), Path(destination), panel, repo_root)
    if not verdict.ok:
        return {
            "ok": False,
            "stage": STAGE_PREFLIGHT,
            "preflight": verdict.as_dict(),
        }
    # --- past this line, and only past it, the text builders may exist ---
    from scripts.panel import act_replay_fidelity as fidelity
    from scripts.panel.run_cycle import pipeline_problem

    prov = provenance(argv, cycle_dir, destination, panel)
    record_path = Path(cycle_dir) / "pipeline.json"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as failed:
        return {
            "provenance": prov,
            "ok": False,
            "stage": STAGE_CYCLE,
            "refused": f"pipeline.json unreadable: {type(failed).__name__}",
            "preflight": verdict.as_dict(),
        }
    problem = pipeline_problem(record)
    if problem is not None:
        return {
            "provenance": prov,
            "ok": False,
            "stage": STAGE_CYCLE,
            "refused": problem,
            "preflight": verdict.as_dict(),
        }
    try:
        docs, states, signatures = fidelity.load_records(Path(cycle_dir))
    except (OSError, ValueError) as failed:
        return {
            "provenance": prov,
            "ok": False,
            "stage": STAGE_RECORDS,
            "refused": f"records unreadable: {type(failed).__name__}",
            "preflight": verdict.as_dict(),
        }
    entries: List[Dict[str, Any]] = []
    for doc in docs:
        try:
            entries.append(document(doc, states[doc], signatures[doc], fidelity))
        except Exception as failed:  # one record must not cost the other nine
            entries.append(_broken(doc, failed))
    failures = {entry["doc"]: _reasons(entry) for entry in entries if not entry["ok"]}
    counts: Dict[str, int] = {
        "documents": len(entries),
        "documents_ok": sum(1 for entry in entries if entry["ok"]),
        "acts_recorded": sum(
            1 for entry in entries for row in entry["acts"].values() if row["recorded"]
        ),
        "acts_empty": sum(
            1 for entry in entries for row in entry["acts"].values() if row["empty"]
        ),
        "act_alterations_run": sum(len(entry["control"]["acts"]) for entry in entries),
        "act_alterations_moved": sum(
            len(entry["control"]["moved"]) for entry in entries
        ),
        "controls_ok": sum(1 for entry in entries if entry["control"]["ok"]),
        "render_mismatches": sum(
            1
            for entry in entries
            for equal in entry["equal"].values()
            if equal is not True
        ),
    }
    return {
        "provenance": prov,
        "ok": not failures,
        "stage": STAGE_REPLAYED,
        "acts": acts,
        "preflight": verdict.as_dict(),
        "counts": counts,
        "documents": entries,
        "failures": failures,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    invoked = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description=(
            "Act replay of a harvested cycle: the preflight, then the recorded "
            "acts' judged text against a reconstructed reference. No model call."
        )
    )
    parser.add_argument("--cycle-dir", required=True, type=Path)
    parser.add_argument(
        "--dest",
        required=True,
        type=Path,
        help="a directory that does not exist yet; the report is written there",
    )
    parser.add_argument(
        "--panel-file",
        default=None,
        type=Path,
        help="the campaign's panel file; its ids make membership a set check",
    )
    parser.add_argument(
        "--doc-ids",
        default=None,
        help="the panel's ids, comma or space separated (the campaign's parser)",
    )
    parser.add_argument(
        "--acts",
        default=RECORDED,
        choices=(RECORDED, LIVE),
        help=(
            f"{RECORDED} (default) replays the recorded acts, free; {LIVE} "
            "re-runs them on the recorded states (one paid call per act and "
            "per document) and writes a tag the judges stage accepts"
        ),
    )
    args = parser.parse_args(invoked)

    panel: Optional[List[str]] = None
    if args.panel_file is not None or args.doc_ids is not None:
        from scripts.dataset.panel_ids import parse_doc_ids

        panel = parse_doc_ids(
            args.doc_ids,
            None if args.panel_file is None else str(args.panel_file),
        )
        if not panel:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "stage": STAGE_PREFLIGHT,
                        "refused": (
                            "--panel-file/--doc-ids named no document: an empty "
                            "panel checks nothing"
                        ),
                    },
                    indent=1,
                    sort_keys=True,
                )
            )
            return EXIT_USAGE

    if args.acts == LIVE:
        # Imported here, after the panel is parsed and before anything is read:
        # the live runner answers the same preflight itself, so a cycle that
        # does not hold still imports no text builder.
        from scripts.panel.act_replay_live import main as live_main

        return live_main(args.cycle_dir, args.dest, panel, invoked)

    report = replay(args.cycle_dir, args.dest, panel, acts=args.acts, argv=invoked)
    if report.get("stage") == STAGE_PREFLIGHT and not report.get("ok"):
        # Nothing exists yet: no destination, no client, no report on disk.
        print(json.dumps(report, indent=1, sort_keys=True))
        return EXIT_USAGE if "refused" in report else EXIT_FAILED

    destination = Path(args.dest)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / REPORT).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        json.dumps(
            {key: report.get(key) for key in ("ok", "stage", "counts", "failures")},
            indent=1,
            sort_keys=True,
        )
    )
    return EXIT_OK if report.get("ok") else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
