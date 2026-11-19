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


def build(
    families: Mapping[str, Tuple[Path, Path]],
    *,
    cycle_dir: Optional[Path] = None,
    counter_before: int = 0,
    panel: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """The whole reading: per family, the verdict, the counter, the heads."""
    readings = {
        name: family_direction(current, previous, panel)
        for name, (current, previous) in families.items()
    }
    verdict = cross_family(readings)
    first_current = next(iter(families.values()))[0]
    return {
        "families": readings,
        "verdict": verdict,
        "counter_before": counter_before,
        "counter_after": next_counter(verdict, counter_before),
        "heads": read_heads(first_current, cycle_dir),
    }


def _parse_family(spec: str) -> Tuple[str, Tuple[Path, Path]]:
    """``NAME=CUR_DIR|PREV_DIR`` — ``|``, not ``:``: a Windows path carries
    its own ``C:`` and a colon separator would split inside the drive."""
    name, sep, pair = spec.partition("=")
    if not sep or "|" not in pair:
        raise SystemExit(f"--family {spec!r}: expected NAME=CUR_DIR|PREV_DIR")
    current, _, previous = pair.partition("|")
    return name, (Path(current), Path(previous))


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
    args = parser.parse_args(argv)

    families: Dict[str, Tuple[Path, Path]] = dict(_parse_family(s) for s in args.family)
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
            "no family: pass --family NAME=CUR|PREV (or --tag/--previous-tag/--judge)"
        )

    before = read_counter_before(args.previous_cycle_dir)
    if before is None:
        before = args.counter_before if args.counter_before is not None else 0
    panel = c.read_panel(args.panel_file) if args.panel_file else None
    result = build(
        families, cycle_dir=args.cycle_dir, counter_before=before, panel=panel
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
