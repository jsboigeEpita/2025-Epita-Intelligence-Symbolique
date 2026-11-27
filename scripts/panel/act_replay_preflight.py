"""Act-replay input preflight: is the cycle whole, and the destination free?

    python scripts/panel/act_replay_preflight.py --cycle-dir \\
        argumentation_analysis/evaluation/results/panel_cycles/<cycle> \\
        --dest <a path that does not exist yet> [--panel <id,id,...>]

#3658 item 46c. The act replay (``scripts/panel/replay_acts.py``) re-runs the
three acts of a harvested cycle and pays one model call per act and per
document. Before the first call — before any model client exists — this
module answers, from the files alone, the three questions a replay cannot
recover from once it has spent:

1. **Panel membership.** A cycle is the whole panel through the pipeline
   once. The harvest (``run_cycle.harvest``) copies each panel document's
   state and signature into the cycle; ``pipeline.json`` records the length
   of each of its three lists — ``copied``, ``missing``, ``stale`` — and
   ``cycle.json`` the panel's size. Both records are required, and required
   to be what the contract writes: an absent, unreadable or count-less
   record is refused by name, because a named panel says which documents to
   check and never that their pairs were harvested *by this run* — a pair
   older than the run is exactly what ``stale`` counts. A cycle whose
   harvest missed a document is refused on that record; its counts must
   equal the pairs actually present. A caller that already holds the panel —
   the launcher reads it through the campaign's one parser (#3375) — passes
   the ids, and membership becomes a set as well: a panel document the cycle
   does not hold is missing, a cycle document the panel does not name is a
   stray. The verdict names which of the two ran (``record_counts`` or
   ``panel_set``), since they do not have the same strength.

2. **Matching readable pairs.** For each document the state dump and the
   signature must be readable JSON objects, and must be the pair one run
   wrote. Three witnesses, none of which reads a passage: the signature's
   ``opaque_id`` names the document (the batch runner writes that same id
   into both file names); the ``llm_usage`` it wrote into both files is the
   same; and the three acts the replay re-runs agree — the sanitiser reduces
   each act text, an empty one included, to ``{"length": N, "stripped":
   True}`` (#2841 guard 3), and a field it leaves whole is compared as text.
   A state that holds no act must face a signature that records none, and a
   value that is not text is refused whatever the signature says: no replay
   reads a list or a number as an act.

3. **A destination of its own.** The replay writes renders that carry corpus
   text. Its destination must not exist yet — one per replay, so two runs
   never share a directory and the fidelity control never compares a replay
   with itself — must not be the cycle directory, one of its two input
   directories, or a directory above them, and must be a path git ignores
   (``_common.ensure_gitignored``, the refusal every instrument of this
   folder shares). A fresh subdirectory of the cycle is accepted: it is where
   this folder's instruments already write their reports.

Three limits, stated. The count check cannot see a swap that keeps the count:
a genuine pair of another run put in place of a harvested one passes it,
because state and signature still agree with each other. A named panel
refuses the half of that where the intruder is a document outside the panel,
which is why the verdict names the membership it checked; a stale pair of a
panel document passes either way. A signature written before #2849 carries
no ``llm_usage``: that witness is then absent, not mismatched, and the acts
still witness the pair.
And nothing here judges what an act says: an act recorded empty is left to
the launcher's own per-act report, and only the three acts are compared —
the narrative synthesis and the interpretive question are not re-run by the
replay.

Not here either: whether the pipeline run itself can be trusted. Its exit
code, and whether HEAD moved during it, are ``run_cycle.pipeline_problem``'s
— the launcher applies them as the cycle does before a paid judge.

Keyless, clientless: the import graph is the standard library and
``_common``. The panel *file* is never read here — a cycle's panel is its
harvest record, and the launcher passes the ids its one parser produced;
importing that parser (``scripts.dataset.run_corpus_batch``) pulls the whole
pipeline runtime and the checkout's ``.env`` into the process.

Privacy: the report names the opaque ids it was given, the counts it read and
the witness that disagreed — never a value, never a passage. The preflight
writes nothing on any path, passing or failing.

Exit code: 0 every check holds; 1 at least one failed, the report says which;
2 the invocation could not run as asked.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

ACTS: Tuple[str, ...] = c.ACTS
PIPELINE_RECORD = "pipeline.json"
CYCLE_RECORD = "cycle.json"
#: The three counts ``run_cycle.harvest`` returns, each written into
#: ``pipeline.json`` as a length (``run_cycle`` line 929).
HARVEST_COUNTS: Tuple[str, ...] = ("copied", "missing", "stale")
STATES_DIR = "states"
SIGNATURES_DIR = "signatures"
STATE_PREFIX = "state_full_"
SIGNATURE_PREFIX = "signature_"

#: How panel membership was verified — named in the verdict, because the two
#: do not have the same strength.
MEMBERSHIP_RECORD = "record_counts"
MEMBERSHIP_SET = "panel_set"
MEMBERSHIP_NONE = "none"

CYCLE_MISSING = "cycle_missing"
STATES_DIR_MISSING = "states_dir_missing"
SIGNATURES_DIR_MISSING = "signatures_dir_missing"
RECORD_MISSING = "record_missing"
RECORD_UNREADABLE = "record_unreadable"
RECORD_MALFORMED = "record_malformed"
HARVEST_INCOMPLETE = "harvest_incomplete"
HARVEST_COUNT_MISMATCH = "harvest_count_mismatch"
MISSING_PAIR = "missing_pair"
STRAY_PAIR = "stray_pair"
UNREADABLE_STATE = "unreadable_state"
UNREADABLE_SIGNATURE = "unreadable_signature"
FOREIGN_SIGNATURE = "foreign_signature"
PAIR_MISMATCH = "pair_mismatch"
DESTINATION_EXISTS = "destination_exists"
DESTINATION_COLLIDES = "destination_collides"
DESTINATION_TRACKED = "destination_tracked"
DESTINATION_UNCHECKED = "destination_unchecked"

EXIT_OK, EXIT_FAILED = 0, 1


@dataclass(frozen=True)
class Problem:
    """One check that failed: its kind, the document if it has one, and the
    witness that disagreed — a name or a count, never a value."""

    kind: str
    doc: Optional[str] = None
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        row: Dict[str, Any] = {"kind": self.kind}
        if self.doc is not None:
            row["doc"] = self.doc
        if self.detail:
            row["detail"] = self.detail
        return row


@dataclass(frozen=True)
class Verdict:
    """What the preflight found. ``ok`` means no problem at all."""

    cycle_dir: Path
    destination: Path
    panel: Tuple[str, ...]
    membership: str
    pairs_ok: int
    problems: Tuple[Problem, ...]

    @property
    def ok(self) -> bool:
        return not self.problems

    def counts(self) -> Dict[str, int]:
        """How many problems of each kind."""
        out: Dict[str, int] = {}
        for problem in self.problems:
            out[problem.kind] = out.get(problem.kind, 0) + 1
        return dict(sorted(out.items()))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "cycle_dir": str(self.cycle_dir),
            "destination": str(self.destination),
            "panel": list(self.panel),
            "panel_size": len(self.panel),
            "membership": self.membership,
            "pairs_ok": self.pairs_ok,
            "counts": self.counts(),
            "problems": [problem.as_dict() for problem in self.problems],
        }


# ---------------------------------------------------------------------------
# Reading, without ever echoing
# ---------------------------------------------------------------------------


def _read_object(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """``(object, None)``, or ``(None, why)``. The reason is an exception's
    name or a JSON type — never a byte of the file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, type(exc).__name__
    if not isinstance(data, dict):
        return None, f"{type(data).__name__}, not an object"
    return data, None


def _record(path: Path, problems: List[Problem]) -> Optional[Dict[str, Any]]:
    """A record the harvest contract writes for every cycle: the object, or
    ``None`` with the reason named — absent, not a file, unreadable. The
    contract writes no cycle without it, so none of the three is tolerated."""
    name = path.name
    if not path.exists():
        problems.append(Problem(RECORD_MISSING, detail=name))
        return None
    if not path.is_file():
        problems.append(Problem(RECORD_UNREADABLE, detail=f"{name}: not a file"))
        return None
    record, why = _read_object(path)
    if record is None:
        problems.append(Problem(RECORD_UNREADABLE, detail=f"{name}: {why}"))
    return record


def _inner(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """The level the producers read (``state.get("state") or state``)."""
    nested = record.get("state")
    return nested if isinstance(nested, dict) else record


def _ids(directory: Path, prefix: str) -> Set[str]:
    return {p.stem[len(prefix) :] for p in directory.glob(f"{prefix}*.json")}


def _count(record: Mapping[str, Any], key: str) -> Optional[int]:
    value = record.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _within(path: Path, directory: Path) -> bool:
    """Is ``path`` ``directory`` itself or below it?"""
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# 1. Panel membership
# ---------------------------------------------------------------------------


def _harvest_counts(
    cycle_dir: Path, problems: List[Problem]
) -> Optional[Dict[str, int]]:
    """The three counts ``run_cycle.harvest`` records, those a reader can
    compare; ``None`` when the record carries none. A count that is absent or
    is not a count is named: read leniently it would compare nothing while the
    verdict still claimed the record as its witness."""
    record = _record(cycle_dir / PIPELINE_RECORD, problems)
    if record is None:
        return None
    harvested = record.get("harvest")
    if not isinstance(harvested, dict):
        problems.append(
            Problem(RECORD_MALFORMED, detail=f"{PIPELINE_RECORD}: no harvest object")
        )
        return None
    counts: Dict[str, int] = {}
    for key in HARVEST_COUNTS:
        value = _count(harvested, key)
        if value is None:
            problems.append(
                Problem(RECORD_MALFORMED, detail=f"{PIPELINE_RECORD}: no {key} count")
            )
        else:
            counts[key] = value
    return counts or None


def _panel_size(cycle_dir: Path, problems: List[Problem]) -> Optional[int]:
    """The panel's size as ``cycle.json`` records it."""
    record = _record(cycle_dir / CYCLE_RECORD, problems)
    size = _count(record or {}, "panel_size")
    if record is not None and size is None:
        problems.append(
            Problem(RECORD_MALFORMED, detail=f"{CYCLE_RECORD}: no panel_size count")
        )
    return size


def _membership(
    cycle_dir: Path, docs: Sequence[str], panel: Optional[Sequence[str]]
) -> Tuple[List[Problem], Tuple[str, ...], str]:
    """``(problems, the documents to check, how membership was verified)``."""
    problems: List[Problem] = []
    counts = _harvest_counts(cycle_dir, problems)
    size = _panel_size(cycle_dir, problems)

    if panel is None:
        to_check = tuple(docs)
        membership = MEMBERSHIP_RECORD if counts else MEMBERSHIP_NONE
    else:
        to_check = tuple(dict.fromkeys(panel))
        membership = MEMBERSHIP_SET
        problems.extend(
            Problem(STRAY_PAIR, doc, "the panel does not name it")
            for doc in docs
            if doc not in to_check
        )

    if counts:
        missing, stale = counts.get("missing"), counts.get("stale")
        if missing is not None and stale is not None and (missing or stale):
            problems.append(
                Problem(HARVEST_INCOMPLETE, detail=f"missing={missing} stale={stale}")
            )
        copied = counts.get("copied")
        if copied is not None and copied != len(docs):
            problems.append(
                Problem(
                    HARVEST_COUNT_MISMATCH,
                    detail=f"copied={copied} present={len(docs)}",
                )
            )
    if size is not None and size != len(docs):
        problems.append(
            Problem(
                HARVEST_COUNT_MISMATCH, detail=f"panel_size={size} present={len(docs)}"
            )
        )
    return problems, to_check, membership


# ---------------------------------------------------------------------------
# 2. Matching readable pairs
# ---------------------------------------------------------------------------


def _recorded(entry: Any) -> Optional[Tuple[str, Any]]:
    """What a signature records for one text input: ``("text", str)`` for a
    field the sanitiser leaves whole, ``("length", N)`` for the record it
    writes in place of narrative, ``None`` for a shape it never writes."""
    if isinstance(entry, str):
        return "text", entry
    if isinstance(entry, dict) and entry.get("stripped") is True:
        length = entry.get("length")
        if isinstance(length, int) and not isinstance(length, bool):
            return "length", length
    return None


def _act_problems(
    doc: str, state: Mapping[str, Any], signature: Mapping[str, Any]
) -> List[Problem]:
    """The three acts the replay re-runs: what the state holds against what the
    signature recorded, each compared the only way the signature allows."""
    recorded = signature.get("state")
    recorded = recorded if isinstance(recorded, dict) else {}
    inner = _inner(state)
    problems: List[Problem] = []
    for act in ACTS:
        text = inner.get(act)
        claim = _recorded(recorded.get(act))
        if text is not None and not isinstance(text, str):
            # No replay reads a list or a number as an act.
            problems.append(Problem(PAIR_MISMATCH, doc, f"{act} is not text"))
        elif text is None:
            # The state holds no act here: a signature that records one was
            # written from another state.
            if act in recorded and recorded[act] is not None:
                problems.append(
                    Problem(PAIR_MISMATCH, doc, f"{act} recorded, not held")
                )
        elif claim is None:
            problems.append(Problem(PAIR_MISMATCH, doc, f"{act} not recorded"))
        elif claim[0] == "length" and claim[1] != len(text):
            problems.append(Problem(PAIR_MISMATCH, doc, f"{act} length"))
        elif claim[0] == "text" and claim[1] != text:
            problems.append(Problem(PAIR_MISMATCH, doc, f"{act} text"))
    return problems


def _pair(
    doc: str, states_dir: Path, signatures_dir: Path
) -> Tuple[List[Problem], bool]:
    """``(problems, did the pair match)`` for one document."""
    problems: List[Problem] = []
    state: Optional[Dict[str, Any]] = None
    signature: Optional[Dict[str, Any]] = None
    state_path = states_dir / f"{STATE_PREFIX}{doc}.json"
    sig_path = signatures_dir / f"{SIGNATURE_PREFIX}{doc}.json"
    if state_path.is_file():
        state, why = _read_object(state_path)
        if state is None:
            problems.append(Problem(UNREADABLE_STATE, doc, why or ""))
    else:
        problems.append(Problem(MISSING_PAIR, doc, "no state dump"))
    if sig_path.is_file():
        signature, why = _read_object(sig_path)
        if signature is None:
            problems.append(Problem(UNREADABLE_SIGNATURE, doc, why or ""))
    else:
        problems.append(Problem(MISSING_PAIR, doc, "no signature"))
    if state is None or signature is None:
        return problems, False

    inner = _inner(state)
    if signature.get("opaque_id") != doc:
        problems.append(
            Problem(FOREIGN_SIGNATURE, doc, "its opaque_id does not name this document")
        )
    recorded_usage, state_usage = signature.get("llm_usage"), inner.get("llm_usage")
    if isinstance(recorded_usage, dict) and isinstance(state_usage, dict):
        if recorded_usage != state_usage:
            problems.append(Problem(PAIR_MISMATCH, doc, "llm_usage"))
    if not isinstance(signature.get("state"), dict):
        problems.append(Problem(PAIR_MISMATCH, doc, "no sanitised state"))
    problems.extend(_act_problems(doc, state, signature))
    return problems, not problems


# ---------------------------------------------------------------------------
# 3. A destination of its own
# ---------------------------------------------------------------------------


def _destination(destination: Path, cycle_dir: Path, repo_root: Path) -> List[Problem]:
    resolved = destination.resolve()
    cycle = cycle_dir.resolve()
    problems: List[Problem] = []
    if destination.exists() or destination.is_symlink():
        problems.append(Problem(DESTINATION_EXISTS, detail="the path already exists"))
    if _within(resolved, cycle / STATES_DIR) or _within(
        resolved, cycle / SIGNATURES_DIR
    ):
        problems.append(
            Problem(DESTINATION_COLLIDES, detail="it is inside an input directory")
        )
    elif resolved == cycle or _within(cycle, resolved):
        problems.append(
            Problem(DESTINATION_COLLIDES, detail="it holds the cycle directory")
        )
    try:
        c.ensure_gitignored(destination, repo_root)
    except c.OutputRefused:
        problems.append(
            Problem(DESTINATION_TRACKED, detail="git would track it: corpus text")
        )
    except OSError as exc:
        problems.append(Problem(DESTINATION_UNCHECKED, detail=type(exc).__name__))
    return problems


# ---------------------------------------------------------------------------
# The preflight
# ---------------------------------------------------------------------------


def preflight(
    cycle_dir: Path,
    destination: Path,
    panel: Optional[Sequence[str]] = None,
    repo_root: Path = c.REPO_ROOT,
) -> Verdict:
    """The three checks, in the order of the module's docstring.

    Every problem is collected and none stops the next check: one run shows
    the whole state of the cycle. Nothing is written on any path."""
    cycle_dir, destination = Path(cycle_dir), Path(destination)
    if not cycle_dir.is_dir():
        return Verdict(
            cycle_dir,
            destination,
            (),
            MEMBERSHIP_NONE,
            0,
            (
                Problem(CYCLE_MISSING, detail="no such directory"),
                *_destination(destination, cycle_dir, repo_root),
            ),
        )
    states_dir, signatures_dir = cycle_dir / STATES_DIR, cycle_dir / SIGNATURES_DIR
    problems: List[Problem] = []
    for directory, kind in (
        (states_dir, STATES_DIR_MISSING),
        (signatures_dir, SIGNATURES_DIR_MISSING),
    ):
        if not directory.is_dir():
            problems.append(Problem(kind, detail=f"no {directory.name}/ directory"))
    docs = sorted(
        _ids(states_dir, STATE_PREFIX) | _ids(signatures_dir, SIGNATURE_PREFIX)
    )
    found, to_check, membership = _membership(cycle_dir, docs, panel)
    problems.extend(found)
    pairs_ok = 0
    for doc in to_check:
        found, matched = _pair(doc, states_dir, signatures_dir)
        problems.extend(found)
        pairs_ok += int(matched)
    problems.extend(_destination(destination, cycle_dir, repo_root))
    return Verdict(
        cycle_dir, destination, to_check, membership, pairs_ok, tuple(problems)
    )


def _split_panel(text: str) -> List[str]:
    """The ids as the campaign's ``--doc-ids`` takes them: separated by
    commas or whitespace."""
    return [part for part in re.split(r"[,\s]+", text) if part]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Act-replay input preflight: is the cycle whole, and the destination "
            "free? Reads only; prints one JSON object."
        )
    )
    parser.add_argument("--cycle-dir", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument(
        "--panel",
        default=None,
        help=(
            "the ids the caller intends to replay, separated by commas or "
            f"spaces; without it the cycle's own {PIPELINE_RECORD} harvest is "
            "the panel"
        ),
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    panel = _split_panel(args.panel) if args.panel is not None else None
    if args.panel is not None and not panel:
        # An empty panel would check nothing, and call the cycle whole.
        parser.error("--panel: empty — an empty panel checks nothing")
    verdict = preflight(args.cycle_dir, args.dest, panel)
    print(json.dumps(verdict.as_dict(), sort_keys=True))
    return EXIT_OK if verdict.ok else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
