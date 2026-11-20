"""#3543 — the condition-2 counter of the v1 bar, as a tracked command.

The counter was applied by hand from two per-family ``STABILITY.md`` files:
the DIRECTION of a state change and the rule that both families must agree
lived nowhere in code, so a cycle-to-cycle reading could not be replayed.
This module computes, per family, which settled documents moved toward or
away from the pipeline, then the cross-family verdict and the counter.

Definitions (the issue's asks, pinned by ``tests/unit/scripts/test_condition2_3543.py``):

- **state order** — ``ZEROSHOT_WINS < PARITY < PIPELINE_SUPPLIES_WITH_GAP <
  PIPELINE_SUPPLIES``; a change into or out of ``BOTH_ABSTAIN`` or
  ``UNPARSED`` is ``outside`` and counts neither way.
- **settled** — a document non-fragile in BOTH cycles, exactly the set
  ``judge_panel.compare_passes`` reports through ``fragile_a``/``fragile_b``.
- **family direction** — ``progress`` when at least one settled document
  moves toward and none moves away; ``no_progress`` otherwise;
  ``not_measurable`` when nothing is settled.
- **cross-family verdict** — ``progress`` when both families progress,
  ``no_progress`` when neither does, ``disagree`` otherwise,
  ``not_measurable`` if either family is not measurable OR fewer than two
  families contributed (one family's direction is diagnostic, never a
  verdict — the #3639 review).
- **judge independence** — the official verdict needs two DISTINCT RECORDED
  judge families: ``judge_family`` in each consensus ``META.json``, never
  the CLI labels or the directory names. The same judge's results under two
  labels — or two consensus sizes of one family — are one reading, not two;
  a META that records no judge family proves nothing and is diagnostic only.
- **execution binding** — the families of one cycle must be bound to the
  same measured execution: every META of the role records ``seed`` and
  ``run_head`` and they all agree. ``run_head`` is the zero-shot arm's head
  and on its own cannot identify the pipeline run — agreement is what the
  records prove, not more; a role that records disagreeing executions (same
  arms, another run) or cannot prove the binding keeps its per-family
  diagnosis and the counter holds. The inherited counter is bound the same
  way: it must come from the selected predecessor, whose condition2.json
  names the same series.
- **series** — the ARMS identify a series: ``pipeline_model`` and
  ``pipeline_family`` in the consensus ``META.json``, which come from the
  zero-shot record's provenance (#3138's single resolver) under the
  same-model doctrine. A judge change WITHIN a series is not a break (the
  doctrine; the panel ledger records no such comparison yet — the
  skip-a-break numbering is hypothetical, not a published cycle pair). A
  pair spanning a series break is refused — the official predecessor is the
  same-series cycle, skipping any newer cycles of other series — and the
  families of one cycle must name one series (two META that disagree judged
  two different runs). A new series' first cycle is declared with
  ``--new-series``: its own baseline, the counter restarting at 1 (c21).
- **counter** — ``no_progress`` adds 1, ``progress`` resets to 0 (the bar
  counts consecutive cycles), ``disagree`` and ``not_measurable`` leave it.

Two modes: ``--family NAME=CUR|PREV`` pairs explicit consensus directories
(the pre-#3531 cycles are not named ``<tag>_<judge>_cons<k>``); the default
reads ``--cycle-dir``, which ``scripts/panel/run_cycle.py`` fills. The
previous counter comes from the previous cycle's ``condition2.json`` or
``--counter-before N``. Free: stored directories only, no key, no corpus.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402
from scripts.dataset import judge_panel as jp  # noqa: E402

# Where a cycle's consensus directories live (#3531's naming).
PASS_PREFIX = "judge_panel_3375"

# The order the five measured readings imply (#3543): the pipeline's supply
# with a gap sits between parity and a clean supply.
STATE_ORDER: Tuple[str, ...] = (
    "ZEROSHOT_WINS",
    "PARITY",
    "PIPELINE_SUPPLIES_WITH_GAP",
    "PIPELINE_SUPPLIES",
)

OUTSIDE = "outside"
TOWARD = "toward"
AWAY = "away"
UNCHANGED = "unchanged"

PROGRESS = "progress"
NO_PROGRESS = "no_progress"
DISAGREE = "disagree"
NOT_MEASURABLE = "not_measurable"
NEW_SERIES = "new_series"


def state_direction(state_a: str, state_b: str) -> str:
    """The direction of a change from ``state_a`` (previous) to ``state_b``.

    A state outside ``STATE_ORDER`` (``BOTH_ABSTAIN``, ``UNPARSED``) takes the
    change ``outside``: it counts neither toward nor away.
    """
    if state_a not in STATE_ORDER or state_b not in STATE_ORDER:
        return OUTSIDE
    delta = STATE_ORDER.index(state_b) - STATE_ORDER.index(state_a)
    if delta > 0:
        return TOWARD
    if delta < 0:
        return AWAY
    return UNCHANGED


def family_direction(
    current_dir: Path, previous_dir: Path, panel: Optional[Sequence[str]] = None
) -> Dict[str, Any]:
    """One family's reading over two consensus directories.

    The comparison itself is ``judge_panel.compare_passes`` — the settled set
    and the states are never re-derived here, so a figure printed by
    ``STABILITY.md`` and this reading cannot disagree on WHO changed.
    """
    report = jp.compare_passes(
        jp.load_rows(previous_dir, panel), jp.load_rows(current_dir, panel)
    )
    settled: List[str] = []
    toward: List[str] = []
    away: List[str] = []
    outside: List[str] = []
    for entry in report:
        if entry.get("fragile_a") or entry.get("fragile_b"):
            continue
        doc = str(entry["opaque_id"])
        settled.append(doc)
        direction = state_direction(str(entry["state_a"]), str(entry["state_b"]))
        if direction == TOWARD:
            toward.append(doc)
        elif direction == AWAY:
            away.append(doc)
        elif direction == OUTSIDE:
            outside.append(doc)
    if not settled:
        direction = NOT_MEASURABLE
    elif toward and not away:
        direction = PROGRESS
    else:
        direction = NO_PROGRESS
    return {
        "current_dir": str(current_dir),
        "previous_dir": str(previous_dir),
        "settled": settled,
        "toward": toward,
        "away": away,
        "outside": outside,
        "direction": direction,
    }


def cross_family(readings: Mapping[str, Mapping[str, Any]]) -> str:
    """The verdict of the cycle over its families' directions.

    The bar says BOTH families (#3639 review): with fewer than two
    contributing families there is no cross-family reading — one family's
    direction stays in ``families`` for diagnostic replay, but the verdict is
    ``not_measurable`` so the official counter holds.
    """
    if len(readings) < 2:
        return NOT_MEASURABLE
    directions = {str(r["direction"]) for r in readings.values()}
    if NOT_MEASURABLE in directions:
        return NOT_MEASURABLE
    if directions == {PROGRESS}:
        return PROGRESS
    if directions == {NO_PROGRESS}:
        return NO_PROGRESS
    return DISAGREE


def next_counter(verdict: str, before: int) -> int:
    """``no_progress`` adds 1; ``progress`` resets; the others hold."""
    if verdict == NO_PROGRESS:
        return before + 1
    if verdict == PROGRESS:
        return 0
    return before


def read_heads(
    current_dir: Path, cycle_dir: Optional[Path] = None
) -> Dict[str, Optional[str]]:
    """Name what each head IS: the pipeline's head (``pipeline.json``'s
    ``head``, or else the signatures' ``provenance.code_sha``) and the
    zero-shot arm's head (the consensus ``META.json``'s ``run_head`` — never
    read as the judged cycle's head, which is how c6's reader took c0).
    """
    out: Dict[str, Optional[str]] = {
        "pipeline_head": None,
        "pipeline_head_source": None,
        "zeroshot_head": None,
    }
    if cycle_dir is not None:
        record_path = cycle_dir / "pipeline.json"
        if record_path.exists():
            record = jp.load_json(record_path)
            out["pipeline_head"] = record.get("head")
            out["pipeline_head_source"] = str(record_path)
    if out["pipeline_head"] is None and cycle_dir is not None:
        signatures = sorted((cycle_dir / "signatures").glob("signature_*.json"))
        for signature in signatures:
            sha = (jp.load_json(signature).get("provenance") or {}).get("code_sha")
            if sha:
                out["pipeline_head"] = sha
                out["pipeline_head_source"] = str(signature)
                break
    meta_path = current_dir / jp.META_FILENAME
    if meta_path.exists():
        out["zeroshot_head"] = jp.load_json(meta_path).get("run_head")
    return out


def read_counter_before(previous_cycle_dir: Optional[Path]) -> Optional[int]:
    """The counter the previous cycle recorded, when it recorded one."""
    if previous_cycle_dir is None:
        return None
    path = previous_cycle_dir / "condition2.json"
    if not path.exists():
        return None
    value = jp.load_json(path).get("counter_after")
    return int(value) if isinstance(value, int) else None


def _norm_dir(path: Path) -> str:
    """The identity of a consensus directory, spelling-independent."""
    return os.path.normcase(str(path.resolve()))


def _reject_reused_directories(family_dirs: Mapping[str, Sequence[Path]]) -> None:
    """Two labels over the same consensus directories are not two readings.

    The #3639 review v2: the same current/previous pair supplied under both
    ``s`` and ``g`` passed the two-family guard and reset the official
    counter. Every consensus directory must belong to ONE family — the check
    compares resolved, case-normalised paths, so an equivalent spelling of
    the same directory is caught too.
    """
    seen: Dict[str, str] = {}
    for name, directories in family_dirs.items():
        for directory in directories:
            key = _norm_dir(directory)
            if key in seen and seen[key] != name:
                raise SystemExit(
                    f"consensus directory reused across families "
                    f"({seen[key]} and {name}): {directory} — two labels are "
                    "not two independent readings"
                )
            seen[key] = name


def _series_key(meta: Mapping[str, Any], directory: Path) -> Tuple[str, str]:
    """The arms' identity of a judged run, as the consensus META records it.

    ``pipeline_model``/``pipeline_family`` come from the zero-shot record's
    provenance through #3138's single resolver — under the same-model
    doctrine they name BOTH arms, which is what a series is (a judge change
    within a series is not a break, by the doctrine — the panel ledger
    records no such comparison yet). A META that names no model is a named
    exit, never a guess.
    """
    model = meta.get("pipeline_model")
    family = meta.get("pipeline_family")
    if not model or not family:
        raise SystemExit(
            f"{directory}: the consensus META names no pipeline_model/"
            f"pipeline_family — the series cannot be guessed (#3138)"
        )
    return str(model), str(family)


def _read_meta(directory: Path) -> Mapping[str, Any]:
    """One consensus directory's META, or a named exit when unreadable."""
    meta_path = directory / jp.META_FILENAME
    if not meta_path.exists():
        raise SystemExit(
            f"{directory}: no {jp.META_FILENAME} — the series is unreadable"
        )
    return jp.load_json(meta_path)


RunKey = Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]


def _run_key(meta: Mapping[str, Any]) -> RunKey:
    """The recorded binding to ONE measured execution.

    ``(pipeline_model, pipeline_family, seed, run_head)``, ``None`` where
    the META records nothing (historical provenance). ``run_head`` is the
    zero-shot arm's head and on its own cannot identify the pipeline run —
    agreement of the recorded tuple is what the records PROVE, never more.
    """
    model = meta.get("pipeline_model")
    family = meta.get("pipeline_family")
    seed = meta.get("seed")
    head = meta.get("run_head")
    return (
        str(model) if model else None,
        str(family) if family else None,
        str(seed) if seed is not None else None,
        str(head) if head else None,
    )


def _run_identity(record: Any) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """Which RUN a ``pipeline_run`` record names, ignoring where it was mounted.

    #3543 item 1 — the identity of a judged run is its inputs
    (``inputs_sha256``) and the code that produced them (``code_shas``).
    ``states_dir``/``signatures_dir`` say WHERE that run was read from, not
    WHICH run it was: the same run read under two directories, or by two
    family sets, carries one identity. ``None`` when the record does not
    carry both pieces (an older or partial record proves no identity).
    """
    if not isinstance(record, Mapping):
        return None
    inputs = record.get("inputs_sha256")
    code = record.get("code_shas")
    if not isinstance(inputs, str) or not inputs:
        return None
    if not isinstance(code, (list, tuple)):
        return None
    return (inputs, tuple(sorted(str(sha) for sha in code)))


def _single_run_identity(
    records: Mapping[str, Any],
) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """The ONE run these families judged, or ``None`` when it is not one."""
    identities = {_run_identity(record) for record in records.values()}
    if len(identities) != 1:
        return None
    identity = next(iter(identities))
    return identity


def _role_provenance(dirs: Mapping[str, Path], role: str) -> Dict[str, Any]:
    """What the ``role``'s META files record about what they judged.

    - **series** — ONE series or a named exit: two META that disagree on the
      ARMS judged two different runs, and a cross-family verdict over them
      would read one run against another.
    - **runs** — the execution binding: ``proven`` when every META records
      ``seed`` and ``run_head`` and they all agree; ``different`` when the
      recorded values disagree (same arms, another execution); ``unproven``
      when some META records nothing.
    - **judge_families** — the RECORDED judge family per directory (``None``
      where the META records none): independence is counted over these,
      never over CLI labels or directory names.
    - **pipeline_run** — WHICH pipeline run was judged, as the judge records
      it since #3639 review v4, identified by ``inputs_sha256`` + ``code_shas``
      (#3543 item 1 — the mounted directories are not part of the run): ``one``
      when every META carries the same identity, ``different`` when they
      disagree, ``unproven`` when any META carries none (c2-c21's stored
      shape — arms/seed/run_head identical across cycles, which proves neither
      "two cycles" nor "one cycle against itself").
    """
    metas = {name: _read_meta(directory) for name, directory in dirs.items()}
    series_keys: Dict[Tuple[str, str], str] = {}
    for name, meta in metas.items():
        series_keys.setdefault(_series_key(meta, dirs[name]), name)
    if len(series_keys) > 1:
        mixed = "; ".join(
            f"{name}: {'/'.join(key)}" for key, name in series_keys.items()
        )
        raise SystemExit(
            f"the {role} families judge different runs ({mixed}) — "
            "a cross-family verdict reads ONE run"
        )
    series_key = next(iter(series_keys))
    runs = {name: _run_key(meta) for name, meta in metas.items()}
    if any(any(part is None for part in run) for run in runs.values()):
        binding = "unproven"
    elif len(set(runs.values())) == 1:
        binding = "proven"
    else:
        binding = "different"
    pipeline_records = {name: meta.get("pipeline_run") for name, meta in metas.items()}
    # #3543 item 1 — the binding is over the RUN, not over the whole record:
    # two directories mounting the same run (or two family sets judging it)
    # used to disagree on ``states_dir``/``signatures_dir`` and read as two
    # runs, while a cycle read against itself under two family sets slipped
    # through the pair hold below. The identity is inputs+code.
    pipeline_identities = {
        name: _run_identity(record) for name, record in pipeline_records.items()
    }
    if any(identity is None for identity in pipeline_identities.values()):
        pipeline_binding = "unproven"
    elif len(set(pipeline_identities.values())) == 1:
        pipeline_binding = "one"
    else:
        pipeline_binding = "different"
    return {
        "series": {"model": series_key[0], "family": series_key[1]},
        "runs": {
            "binding": binding,
            "per_family": {n: list(v) for n, v in runs.items()},
        },
        "pipeline_run": {"binding": pipeline_binding, "per_family": pipeline_records},
        "judge_families": {
            name: (str(meta["judge_family"]) if meta.get("judge_family") else None)
            for name, meta in metas.items()
        },
    }


def _reject_series_break(
    families: Mapping[str, Tuple[Path, Path]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """The pair must belong to ONE series, or it is an input error.

    A series break is not a reading: no verdict reads across it (c21's
    entry: "No verdict of this series reads against c6–c20"), and the
    official predecessor of a cycle is the SAME-SERIES one — the last cycle
    of this series, skipping any newer cycles of other series (hypothetical
    numbering: were c21 a one-cycle break, the next cycle would read against
    the last same-series cycle before it; the panel ledger publishes no such
    pair). A pair that spans the break is refused — reading it anyway (as a
    verdict or a silent hold) is how one series' counter would count another
    series' cycles. The new series' first cycle is declared with
    ``--new-series``.
    """
    current = _role_provenance({n: p[0] for n, p in families.items()}, "current")
    previous = _role_provenance({n: p[1] for n, p in families.items()}, "previous")
    if current["series"] != previous["series"]:
        raise SystemExit(
            f"the pair spans a series break (previous "
            f"{previous['series']['model']}, current {current['series']['model']}): "
            "no verdict reads across series — supply the same-series "
            "predecessor (the last cycle of this series, skipping any newer "
            "cycles of other series), or declare the new series' baseline "
            "with --new-series"
        )
    return current, previous


def _provenance_holds(
    current: Mapping[str, Any], previous: Mapping[str, Any]
) -> List[str]:
    """Why the reading is not official — empty when both guarantees hold.

    Judge independence and execution binding (the #3639 review v3) are
    provenance facts read from the consensus META, not from CLI labels or
    directory names. A role that fails either keeps its per-family
    diagnosis; the official verdict is ``not_measurable`` and the counter
    holds.
    """
    holds: List[str] = []
    for role, provenance in (("current", current), ("previous", previous)):
        recorded = [
            family
            for family in provenance["judge_families"].values()
            if family is not None
        ]
        distinct = sorted(set(recorded))
        missing = sorted(
            name
            for name, family in provenance["judge_families"].items()
            if family is None
        )
        if len(distinct) < 2:
            if missing:
                holds.append(
                    f"{role}: judge provenance missing in {', '.join(missing)} — "
                    "not two recorded judge families"
                )
            else:
                holds.append(
                    f"{role}: one recorded judge family ({'/'.join(distinct)}) "
                    f"under {len(provenance['judge_families'])} labels — two "
                    "labels are not two independent readings"
                )
        binding = provenance["runs"]["binding"]
        if binding == "different":
            holds.append(
                f"{role}: the families judge different executions of the same "
                "arms (same model, another seed/run_head) — a verdict reads "
                "ONE execution"
            )
        elif binding == "unproven":
            holds.append(
                f"{role}: the execution binding is unproven (seed/run_head not "
                "recorded everywhere) — historical provenance is diagnostic only"
            )
        pipeline_binding = provenance["pipeline_run"]["binding"]
        if pipeline_binding == "different":
            holds.append(
                f"{role}: the families judge different pipeline runs "
                "(pipeline_run records disagree) — a verdict reads ONE run"
            )
        elif pipeline_binding == "unproven":
            holds.append(
                f"{role}: the judged pipeline run is unproven (no pipeline_run "
                "record — the c2-c21 shape) — diagnostic only, the counter holds"
            )
    # The pair must be TWO runs: one pipeline run in both roles is a cycle
    # read against itself (the review's measured case: cons6 vs cons3 of one
    # cycle reads no_progress and the counter ticks) — never official.
    # #3543 item 1 — compared on the RUN IDENTITY, not on the per-family
    # records: the old dict comparison missed the same run mounted under two
    # directories (the records differ there) and the same run judged under
    # two family sets (the keys differ there).
    if (
        current["pipeline_run"]["binding"] == "one"
        and previous["pipeline_run"]["binding"] == "one"
        and _single_run_identity(current["pipeline_run"]["per_family"]) is not None
        and _single_run_identity(current["pipeline_run"]["per_family"])
        == _single_run_identity(previous["pipeline_run"]["per_family"])
    ):
        holds.append(
            "both roles record the same pipeline run — a cycle read against "
            "itself is not a cycle-to-cycle comparison"
        )
    return holds


def _reject_foreign_counter(
    counter_source_dir: Optional[Path], series: Mapping[str, str]
) -> None:
    """The inherited counter must come from the selected predecessor.

    The previous cycle's ``condition2.json`` names the series it counted: a
    counter of ANOTHER series feeding this pair is the caller wiring the
    wrong predecessor — a named exit, not a hold (a silent hold would let
    one series' consecutive count feed another's).
    """
    if counter_source_dir is None:
        return
    path = counter_source_dir / "condition2.json"
    if not path.exists():
        return
    recorded = jp.load_json(path).get("series")
    if isinstance(recorded, dict) and recorded != dict(series):
        raise SystemExit(
            f"the inherited counter comes from {counter_source_dir}, whose "
            f"series is {recorded.get('model')}, not {series['model']} — the "
            "counter must be inherited from the selected predecessor (the "
            "same series' previous cycle)"
        )


def build(
    families: Mapping[str, Tuple[Path, Path]],
    *,
    cycle_dir: Optional[Path] = None,
    counter_before: int = 0,
    panel: Optional[Sequence[str]] = None,
    counter_source_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """The whole reading: per family, the verdict, the counter, the heads.

    The verdict is OFFICIAL only when the provenance holds (two distinct
    recorded judge families per role, one proven execution binding per
    role, the counter inherited from the selected predecessor): otherwise
    the per-family diagnosis is preserved, the verdict is
    ``not_measurable`` and the counter holds.
    """
    _reject_reused_directories(families)
    current, previous = _reject_series_break(families)
    _reject_foreign_counter(counter_source_dir, current["series"])
    readings = {
        name: family_direction(cur, prev, panel)
        for name, (cur, prev) in families.items()
    }
    raw_verdict = cross_family(readings)
    holds = _provenance_holds(current, previous)
    verdict = NOT_MEASURABLE if holds else raw_verdict
    first_current = next(iter(families.values()))[0]
    return {
        "families": readings,
        "verdict": verdict,
        "counter_before": counter_before,
        "counter_after": next_counter(verdict, counter_before),
        "series": current["series"],
        "heads": read_heads(first_current, cycle_dir),
        "provenance": {
            "official": not holds,
            "holds": holds,
            "cross_family_verdict": raw_verdict,
            "judge_families": {
                "current": current["judge_families"],
                "previous": previous["judge_families"],
            },
            "run_binding": {
                "current": current["runs"]["binding"],
                "previous": previous["runs"]["binding"],
            },
            "counter": {
                "source_dir": (str(counter_source_dir) if counter_source_dir else None),
                "before": counter_before,
            },
        },
    }


def build_baseline(
    currents: Mapping[str, Path], *, cycle_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """The first cycle of a new series: its own baseline, the counter at 1.

    c21's entry: "condition 2 restarts at 1 on this series (c21 is its own
    baseline)". Nothing compares — the report names the series and the heads
    so the NEXT cycle's pair is verifiable against it. The currents must be
    bound to ONE execution (two consensus recording different runs of the
    same arms cannot both be the baseline); a judge family is recorded, not
    required — a new series' first cycle may legitimately have one judge.
    """
    _reject_reused_directories({name: [d] for name, d in currents.items()})
    provenance = _role_provenance(currents, "current")
    if provenance["runs"]["binding"] == "different":
        raise SystemExit(
            "the baseline families judge different executions of the same "
            "arms (same model, another seed/run_head) — a baseline declares "
            "ONE execution"
        )
    first_current = next(iter(currents.values()))
    return {
        "families": {name: {"current_dir": str(d)} for name, d in currents.items()},
        "verdict": NEW_SERIES,
        "counter_before": None,
        "counter_after": 1,
        "series": provenance["series"],
        "heads": read_heads(first_current, cycle_dir),
        "provenance": {
            "official": True,
            "holds": [],
            "judge_families": {"current": provenance["judge_families"]},
            "run_binding": {"current": provenance["runs"]["binding"]},
        },
    }


def _parse_family(spec: str) -> Tuple[str, Tuple[Path, Path]]:
    """``NAME=CUR_DIR|PREV_DIR`` — ``|``, not ``:``: a Windows path carries
    its own ``C:`` and a colon separator would split inside the drive."""
    name, sep, pair = spec.partition("=")
    if not sep or "|" not in pair:
        raise SystemExit(f"--family {spec!r}: expected NAME=CUR_DIR|PREV_DIR")
    current, _, previous = pair.partition("|")
    return name, (Path(current), Path(previous))


def _parse_baseline(spec: str) -> Tuple[str, Path]:
    """``NAME=CUR_DIR`` — a new series' baseline has no previous half."""
    name, sep, path = spec.partition("=")
    if not sep or "|" in path:
        raise SystemExit(
            f"--family {spec!r}: a --new-series baseline takes NAME=CUR_DIR, "
            "no previous half — the series has no predecessor to read against"
        )
    return name, Path(path)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--family",
        action="append",
        default=[],
        metavar="NAME=CUR|PREV",
        help="one family's current and previous consensus directories; repeatable",
    )
    parser.add_argument(
        "--cycle-dir",
        type=Path,
        default=None,
        help="the current cycle directory: reads pipeline.json/signatures for the head",
    )
    parser.add_argument(
        "--judge",
        action="append",
        default=[],
        help="tag mode: judge name; directories resolved under --results-root",
    )
    parser.add_argument("--tag", default=None, help="tag mode: current cycle tag")
    parser.add_argument(
        "--previous-tag", default=None, help="tag mode: previous cycle tag"
    )
    parser.add_argument(
        "--passes", type=int, default=6, help="tag mode: consensus size"
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=c.RESULTS_ROOT,
        help="tag mode: where judge_panel_3375_* directories live",
    )
    parser.add_argument("--panel-file", type=Path, default=None)
    parser.add_argument(
        "--previous-cycle-dir",
        type=Path,
        default=None,
        help="where the previous cycle's condition2.json lives",
    )
    parser.add_argument(
        "--counter-before",
        type=int,
        default=None,
        help="the previous counter, when no previous condition2.json exists",
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="where condition2.json goes"
    )
    parser.add_argument(
        "--new-series",
        action="store_true",
        help="declare the first cycle of a new series: no comparison, the "
        "counter restarts at 1 (--family NAME=CUR, without a previous half)",
    )
    args = parser.parse_args(argv)

    if args.new_series:
        if args.previous_tag:
            parser.error(
                "--new-series: a new series has no previous cycle to read against"
            )
        currents: Dict[str, Path] = dict(_parse_baseline(s) for s in args.family)
        if args.tag:
            for judge in args.judge:
                currents[judge] = (
                    args.results_root
                    / f"{PASS_PREFIX}_{args.tag}_{judge}_cons{args.passes}"
                )
        if not currents:
            parser.error(
                "no family: pass --family NAME=CUR (or --tag with --judge) "
                "for --new-series"
            )
        result = build_baseline(currents, cycle_dir=args.cycle_dir)
    else:
        families: Dict[str, Tuple[Path, Path]] = dict(
            _parse_family(s) for s in args.family
        )
        if args.tag and args.previous_tag:
            for judge in args.judge:
                current = (
                    args.results_root
                    / f"{PASS_PREFIX}_{args.tag}_{judge}_cons{args.passes}"
                )
                previous = (
                    args.results_root
                    / f"{PASS_PREFIX}_{args.previous_tag}_{judge}_cons{args.passes}"
                )
                families[judge] = (current, previous)
        if not families:
            parser.error(
                "no family: pass --family NAME=CUR|PREV "
                "(or --tag/--previous-tag/--judge)"
            )
        before = read_counter_before(args.previous_cycle_dir)
        if before is None:
            before = args.counter_before if args.counter_before is not None else 0
        panel = c.read_panel(args.panel_file) if args.panel_file else None
        result = build(
            families,
            cycle_dir=args.cycle_dir,
            counter_before=before,
            panel=panel,
            counter_source_dir=args.previous_cycle_dir,
        )

    out = args.out
    if out is None and args.cycle_dir is not None:
        out = args.cycle_dir / "condition2.json"
    if out is not None:
        c.ensure_gitignored(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    if result["verdict"] == NEW_SERIES:
        print(f"series: {result['series']['model']} ({result['series']['family']})")
    else:
        for name, reading in result["families"].items():
            print(
                f"{name}: {reading['direction']} — {len(reading['settled'])} settled, "
                f"toward {reading['toward']}, away {reading['away']}, "
                f"outside {reading['outside']}"
            )
    print(
        f"verdict: {result['verdict']} — counter {result['counter_before']} "
        f"-> {result['counter_after']}"
    )
    for reason in result.get("provenance", {}).get("holds", []):
        print(f"hold: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
