"""Free tracer: where each judge item of a panel cycle stands in the recorded state.

    python scripts/panel/trace_items.py --states-dir <cycle>/states \\
        --consensus-dir <results>/judge_panel_3375_<cycle>_<family>_cons6 [...] \\
        --out <results>/panel_cycles/<cycle>/trace.jsonl

No model call, no network: it reads the judge's stored rows and the pipeline's
recorded states. It is the step that turns a verdict table into defect
classes — each item gets the stage at which the pipeline lost it.

For an **M1** (an observation no line of the analysis carries), the hops are:

  located   the judge's document quote is found in the document
  named     a positioned first-reading move overlaps it
  unit      a unit of the per-argument population overlaps it (selector's rule)
  examined  a unit the per-argument pass examined overlaps it
  finding   a retained fallacy targets one of those units
  reviewed  a coverage-review item overlaps it
  rendered  a six-word run of the passage appears in an act

and the stage is the first hop that fails (``STAGES``). A passage the
coverage review reached counts as found whatever its unit hops say: the review
examines passages outside the per-argument pass.

For an **M2** (a claim of the analysis the document contradicts), the stage
names the acts that carry the pipeline quote.

Each document's population is the one that reproduces its recorded selection
(``_common.resolve_population``). A document whose record no population
reproduces is listed as ``unfaithful``: its ``named_no_unit`` and
``unit_not_examined`` stages describe today's code, not the run.

The jsonl carries quotes and stays under a gitignored path; stdout prints
counts and the ids the judge rows carry.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

STAGE_UNLOCATED = "unlocated"
STAGE_NOT_NAMED_NO_UNIT = "not_named_no_unit"
STAGE_NAMED_NO_UNIT = "named_no_unit"
STAGE_UNIT_NOT_EXAMINED = "unit_not_examined"
STAGE_EXAMINED_NO_FINDING = "examined_no_finding"
STAGE_FOUND_NOT_RENDERED = "found_not_rendered"
STAGE_RENDERED_JUDGE_DISAGREES = "rendered_judge_disagrees"
STAGES = (
    STAGE_UNLOCATED,
    STAGE_NOT_NAMED_NO_UNIT,
    STAGE_NAMED_NO_UNIT,
    STAGE_UNIT_NOT_EXAMINED,
    STAGE_EXAMINED_NO_FINDING,
    STAGE_FOUND_NOT_RENDERED,
    STAGE_RENDERED_JUDGE_DISAGREES,
)
M2_STAGE_PREFIX = "m2_in_"


def m1_stage(row: Dict[str, Any]) -> str:
    """The first hop an M1 row fails."""
    if not row.get("located"):
        return STAGE_UNLOCATED
    if row["reviewed"] or (row["examined"] and row["finding"]):
        return (
            STAGE_RENDERED_JUDGE_DISAGREES
            if row["rendered"]
            else STAGE_FOUND_NOT_RENDERED
        )
    if row["examined"]:
        return STAGE_EXAMINED_NO_FINDING
    if row["unit"]:
        return STAGE_UNIT_NOT_EXAMINED
    if row["named"]:
        return STAGE_NAMED_NO_UNIT
    return STAGE_NOT_NAMED_NO_UNIT


def trace_item(index: c.DocIndex, item: Dict[str, Any]) -> Dict[str, Any]:
    """The hops and the stage of one judge item."""
    row: Dict[str, Any] = {
        "code": item["code"],
        "support": item.get("support"),
        "central": bool(item.get("on_central_thesis")),
        "note": item.get("note"),
        "document_quote": item.get("document_quote"),
        "pipeline_quote": item.get("pipeline_quote"),
        "zeroshot_quote": item.get("zeroshot_quote"),
    }
    if item["code"] == "M2":
        runs = c.word_runs(item.get("pipeline_quote") or "")
        row["acts"] = sorted(act for act in c.ACTS if runs & index.act_runs[act])
        row["stage"] = M2_STAGE_PREFIX + (
            "+".join(act.split("_")[0] for act in row["acts"]) or "none"
        )
        return row
    span = index.locate(item.get("document_quote"))
    row["located"] = span is not None
    if span is not None:
        hit = c.units_overlapping(index.units, span, index.starts)
        examined = [u.unit_id for u in hit if u.unit_id in index.examined]
        passage_runs = c.word_runs(index.raw[span[0] : span[1]])
        row.update(
            named=any(c.overlaps(move, span) for move in index.moves),
            unit=bool(hit),
            examined=bool(examined),
            finding=any(index.targets.get(unit_id) for unit_id in examined),
            reviewed=any(c.overlaps(item_span, span) for item_span in index.review),
            rendered=sorted(
                act for act in c.ACTS if passage_runs & index.act_runs[act]
            ),
        )
    row["stage"] = m1_stage(row)
    return row


def trace(
    states_dir: Path, consensus_dirs: Sequence[Path]
) -> tuple[List[Dict[str, Any]], Dict[str, c.DocIndex]]:
    """Every M1 / M2 item of the given directories, traced."""
    indexes: Dict[str, c.DocIndex] = {}
    rows: List[Dict[str, Any]] = []
    for family, doc, bucket, item in c.iter_judge_items(consensus_dirs):
        if doc not in indexes:
            indexes[doc] = c.build_doc_index(doc, c.load_state(states_dir, doc))
        row = {"family": family, "doc": doc, "bucket": bucket}
        row.update(trace_item(indexes[doc], item))
        rows.append(row)
    return rows, indexes


def summarise(rows: Sequence[Dict[str, Any]]) -> Dict[tuple, Dict[str, int]]:
    """Stage counts per (family, code, central|other)."""
    by: Dict[tuple, Counter] = defaultdict(Counter)
    for row in rows:
        key = (row["family"], row["code"], "central" if row["central"] else "other")
        by[key][row["stage"]] += 1
    return {key: dict(counter) for key, counter in sorted(by.items())}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--states-dir", type=Path, required=True)
    parser.add_argument(
        "--consensus-dir",
        type=Path,
        nargs="+",
        required=True,
        help="consensus (or pass) directories of the judge, one per family",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="jsonl of the traced rows (gitignored)"
    )
    args = parser.parse_args(argv)
    c.ensure_gitignored(args.out)

    rows, indexes = trace(args.states_dir, args.consensus_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
        encoding="utf-8",
    )
    print(f"items traced: {len(rows)} over {len(indexes)} document(s) -> {args.out}")
    for key, stages in summarise(rows).items():
        print(" ", key, stages)
    kinds = Counter(index.population_kind for index in indexes.values())
    print("population:", dict(kinds))
    unfaithful = sorted(
        doc
        for doc, index in indexes.items()
        if index.population_kind == c.POPULATION_UNFAITHFUL
    )
    if unfaithful:
        print(
            f"UNFAITHFUL replay on {len(unfaithful)} document(s): {unfaithful} — "
            "their unit stages describe today's code, not the recorded run"
        )
    print("k/N:", {doc: (index.k, index.n) for doc, index in sorted(indexes.items())})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
