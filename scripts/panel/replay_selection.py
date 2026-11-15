"""Free replay: which of the judge's passages would the per-argument pass examine?

    python scripts/panel/replay_selection.py --states-dir <cycle>/states \\
        --passages-from <results>/judge_panel_3375_<cycle>_<family>_p[1-6] \\
        [--panel-file <panel>] [--min-chars 6016] \\
        [--budget 45 60 90] [--moves-dir <draws>/d1 <draws>/d2 <draws>/d3]

No model call. Each recorded state is replayed through the production
selector, and a passage counts as examined when a selected unit overlaps it
under the selector's own rule. One line per document, then the total, with a
column per variant:

  recorded   the units the state recorded as selected
  today      today's population, budget and priority spans on the same state
             (what the checked-out code would select: the free measure of a
             selector, budget or population change before any paid run)
  rests-on   --rests-on: the #3511 selector variant behind its flag — beside
             each move's priority seat, the unit its claim RESTS ON earns one
             too (``selection.rests_on_unit_ids``, model-free), same budget,
             same victim order. The cell prints what the variant ADDS and
             what it DROPS against ``today``: passages gained (``+g``),
             passages lost (``-l``) and the units given up (``victims``) —
             a variant that only says its count says half the trade.
  k=<K>      the same at a forced budget (--budget)
  <dir>      the first reading's moves replaced by ``moves_<doc>.json`` of a
             directory (--moves-dir, e.g. the draws of first_reading_draws.py)
  union      the union of those directories' moves, when two or more are given

Two controls decide whether a count means anything:

- **fidelity** — the population that reproduces the recorded selection
  (``_common.resolve_population``). ``unfaithful`` means the replay does not
  reproduce the run: nothing on that line is a measure, and the exit code is 2.
- **random** — every variant prints TWO controls under their own names.
  ``random-side`` redraws each passage on its side of the record (a passage
  the recorded run did not examine is redrawn where that run did not examine
  either; ``_common.random_passage_expectation`` says why): the control of a
  CHANGE, and on a selection that IS the record it gives back the count by
  construction. ``random-anywhere`` draws it anywhere in the text: the chance
  control of the recorded selection itself. The ``recorded`` line carries
  ``random-anywhere`` alone; a variant whose selected unit ids are exactly
  the record's prints ``random-side = count, unchanged selection`` instead of
  a number, so it cannot be quoted as chance (#3592).

The passages are the judge's kept M1 items on the central thesis
(``--passages-from``: pass or consensus directories), or the rows of a tracer
jsonl at one stage (``--trace``, ``--stage``).
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

DEFAULT_TRACE_STAGE = "unit_not_examined"


def load_moves(path: Path) -> List[Dict[str, Any]]:
    """The moves of a first-reading payload (``{"moves": [...]}``) or a list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    moves = data.get("moves") if isinstance(data, dict) else data
    return list(moves or [])


def _move_span(move: Dict[str, Any]) -> Optional[c.Span]:
    offset, quote = move.get("offset"), move.get("quote") or ""
    if isinstance(offset, int) and not isinstance(offset, bool) and quote:
        return offset, offset + len(quote)
    return None


def union_moves(draws: Sequence[Sequence[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """The moves of several draws, a passage counted once.

    A positioned move whose span overlaps one already kept is the same
    passage and is dropped; an unpositioned move cannot be compared and is
    kept.
    """
    kept: List[Dict[str, Any]] = []
    for moves in draws:
        for move in moves:
            span = _move_span(move)
            if span is not None and any(
                other is not None and c.overlaps(span, other)
                for other in map(_move_span, kept)
            ):
                continue
            kept.append(move)
    return kept


def with_moves(
    state: Dict[str, Any], moves: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """The state with its first-reading moves replaced."""
    reading = copy.deepcopy(state.get("defining_moves") or {})
    reading["moves"] = list(moves)
    return dict(state, defining_moves=reading)


def examined_count(
    selected: Sequence[Any], starts: Sequence[int], passages: Sequence[c.Span]
) -> int:
    return sum(bool(c.units_overlapping(selected, span, starts)) for span in passages)


def replay_variant(
    state: Dict[str, Any],
    passages: Sequence[c.Span],
    k: Optional[int],
    draws: int,
    rng: random.Random,
    recorded: Optional[Callable[[c.Span], bool]] = None,
    recorded_ids: Optional[Sequence[str]] = None,
    rests_on: bool = False,
) -> Dict[str, Any]:
    """Today's selection on ``state`` at budget ``k``, scored on the passages.

    Two controls, because they answer different questions. ``random_side``
    redraws each passage on its side of the recorded run (``recorded``'s
    predicate): the control of a CHANGE, and on a selection that IS the
    record it gives back the count by construction. ``random_anywhere``
    draws the passage anywhere in the text: the chance control of the
    recorded selection itself. ``unchanged_selection`` says the selected unit
    ids are exactly ``recorded_ids`` — the cell then refuses to print the
    side number as chance (``_cell``).

    ``rests_on=True`` replays the #3511 variant instead of today's selector
    (same population, same budget). ``hits`` carries the per-passage verdict
    so the caller can state what the variant adds and what it drops against
    ``today`` — the trade, not just the count.
    """
    ns = SimpleNamespace(**state)
    population = c.population_of(ns)
    selection = c.select(ns, population, k, rests_on=rests_on)
    selected = list(selection.selected)
    _units, starts = c.positioned_units(population)
    text_length = len(state.get("raw_text") or "")

    def hit(span: c.Span) -> bool:
        return bool(c.units_overlapping(selected, span, starts))

    hits = [hit(span) for span in passages]
    return {
        "examined": sum(hits),
        "hits": hits,
        "selected_ids": sorted(u.unit_id for u in selected),
        "random_side": c.random_passage_expectation(
            passages, text_length, hit, draws, rng, recorded
        ),
        "random_anywhere": c.random_passage_expectation(
            passages, text_length, hit, draws, rng
        ),
        "unchanged_selection": recorded_ids is not None
        and sorted(u.unit_id for u in selected) == sorted(recorded_ids),
        "selected": len(selected),
        "population": len(population),
    }


def replay_document(
    doc: str,
    state: Dict[str, Any],
    quotes: Sequence[str],
    budgets: Sequence[int] = (),
    moves_by_dir: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    draws: int = 300,
    rng: Optional[random.Random] = None,
    rests_on: bool = False,
) -> Dict[str, Any]:
    """One document's line: fidelity, located passages, and every variant."""
    rng = rng or random.Random(c.DEFAULT_SEED)
    index = c.build_doc_index(doc, state)
    passages = [span for span in map(index.locate, quotes) if span is not None]
    recorded_units = [u for u in index.units if u.unit_id in index.examined]
    record = c.recorded_selection(state)
    recorded_ids = record[0] if record is not None else None

    def in_record(span: c.Span) -> bool:
        return bool(c.units_overlapping(recorded_units, span, index.starts))

    variants: Dict[str, Dict[str, Any]] = {
        "recorded": {
            "examined": examined_count(recorded_units, index.starts, passages),
            "random_anywhere": c.random_passage_expectation(
                passages,
                len(index.raw),
                lambda span: bool(
                    c.units_overlapping(recorded_units, span, index.starts)
                ),
                draws,
                rng,
            ),
            "selected": len(index.examined),
        },
        "today": replay_variant(
            state, passages, None, draws, rng, in_record, recorded_ids
        ),
    }
    if rests_on:
        # The #3511 variant, stated as the trade against ``today``: passages
        # gained, passages lost, and the units the swap gave up. A variant
        # that only prints its count hides the cost the queue item demands.
        variant = replay_variant(
            state, passages, None, draws, rng, in_record, recorded_ids, rests_on=True
        )
        today = variants["today"]
        variant["gained"] = sum(
            1 for t, r in zip(today["hits"], variant["hits"]) if r and not t
        )
        variant["lost"] = sum(
            1 for t, r in zip(today["hits"], variant["hits"]) if t and not r
        )
        variant["victims"] = len(
            set(today["selected_ids"]) - set(variant["selected_ids"])
        )
        variants["rests-on"] = variant
    for k in budgets:
        variants[f"k={k}"] = replay_variant(
            state, passages, k, draws, rng, in_record, recorded_ids
        )
    moves_by_dir = moves_by_dir or {}
    for name, moves in moves_by_dir.items():
        variants[name] = replay_variant(
            with_moves(state, moves),
            passages,
            None,
            draws,
            rng,
            in_record,
            recorded_ids,
        )
    if len(moves_by_dir) >= 2:
        variants["union"] = replay_variant(
            with_moves(state, union_moves(list(moves_by_dir.values()))),
            passages,
            None,
            draws,
            rng,
            in_record,
            recorded_ids,
        )
    return {
        "doc": doc,
        "chars": len(index.raw),
        "fidelity": index.population_kind,
        "quotes": len(quotes),
        "located": len(passages),
        "variants": variants,
    }


def passages_from_trace(trace: Path, stage: str) -> Dict[str, List[str]]:
    """The M1 document quotes of a tracer jsonl at one stage, per document."""
    quotes: Dict[str, List[str]] = {}
    for line in Path(trace).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("code") == "M1" and row.get("stage") == stage:
            quote = (row.get("document_quote") or "").strip()
            if quote:
                quotes.setdefault(row["doc"], []).append(quote)
    return quotes


def totals(lines: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Per variant, over the documents that HAVE it: a variant absent from a
    document (no moves file there) must not borrow that document's passages
    for its denominator."""
    out: Dict[str, Dict[str, float]] = {}
    for line in lines:
        for name, variant in line["variants"].items():
            total = out.setdefault(
                name,
                {
                    "examined": 0,
                    "random_side": 0.0,
                    "random_anywhere": 0.0,
                    "unchanged": 0,
                    "selected": 0,
                    "located": 0,
                    "docs": 0,
                    "gained": 0,
                    "lost": 0,
                    "victims": 0,
                },
            )
            total["examined"] += variant["examined"]
            total["random_side"] += variant.get("random_side", 0.0)
            total["random_anywhere"] += variant.get("random_anywhere", 0.0)
            total["unchanged"] += 1 if variant.get("unchanged_selection") else 0
            total["selected"] += variant["selected"]
            total["located"] += line["located"]
            total["docs"] += 1
            total["gained"] += variant.get("gained", 0)
            total["lost"] += variant.get("lost", 0)
            total["victims"] += variant.get("victims", 0)
    return out


def _side_cell(unchanged: bool, value: float) -> str:
    if unchanged:
        return "random-side = count, unchanged selection"
    return f"random-side {value:.1f}"


def _cell(name: str, variant: Dict[str, Any], located: int) -> str:
    text = f"{name} {variant['examined']}/{located}"
    if name == "rests-on":
        text += (
            f" (+{variant['gained']}/-{variant['lost']} passages,"
            f" victims={variant['victims']})"
        )
    if name == "recorded":
        text += f" (random-anywhere {variant['random_anywhere']:.1f})"
    else:
        side = _side_cell(
            variant.get("unchanged_selection", False), variant["random_side"]
        )
        text += f" ({side}, random-anywhere {variant['random_anywhere']:.1f})"
    return f"{text} units={variant['selected']}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--states-dir", type=Path, required=True)
    parser.add_argument("--panel-file", type=Path, default=None)
    parser.add_argument(
        "--min-chars",
        type=int,
        default=0,
        help="only the documents at least this long (the long ones are where "
        "a budget rations)",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--passages-from", type=Path, nargs="+", default=None)
    source.add_argument("--trace", type=Path, default=None)
    parser.add_argument("--stage", default=DEFAULT_TRACE_STAGE)
    parser.add_argument("--budget", type=int, nargs="*", default=[])
    parser.add_argument("--moves-dir", type=Path, nargs="*", default=[])
    parser.add_argument(
        "--rests-on",
        action="store_true",
        default=False,
        help="add the #3511 variant: beside each move's priority seat, the "
        "unit its claim rests on earns one too (model-free rule, same "
        "budget) — printed with what it adds and drops against today",
    )
    parser.add_argument("--draws", type=int, default=300)
    parser.add_argument("--seed", type=int, default=c.DEFAULT_SEED)
    args = parser.parse_args(argv)

    docs = c.read_panel(args.panel_file) or c.docs_in(args.states_dir)
    traced = passages_from_trace(args.trace, args.stage) if args.trace else None
    rng = random.Random(args.seed)
    lines: List[Dict[str, Any]] = []
    for doc in docs:
        if not c.state_path(args.states_dir, doc).exists():
            print(f"{doc}: no recorded state — skipped")
            continue
        state = c.load_state(args.states_dir, doc)
        if len(state.get("raw_text") or "") < args.min_chars:
            continue
        quotes = (
            traced.get(doc, [])
            if traced is not None
            else c.central_passages(args.passages_from, doc)
        )
        moves_by_dir = {
            directory.name: load_moves(directory / f"moves_{doc}.json")
            for directory in args.moves_dir
            if (directory / f"moves_{doc}.json").exists()
        }
        line = replay_document(
            doc,
            state,
            quotes,
            args.budget,
            moves_by_dir,
            args.draws,
            rng,
            rests_on=args.rests_on,
        )
        lines.append(line)
        cells = " | ".join(
            _cell(name, variant, line["located"])
            for name, variant in line["variants"].items()
        )
        print(
            f"{doc} chars={line['chars']} fidelity={line['fidelity']} "
            f"passages={line['located']}/{line['quotes']} | {cells}"
        )
    for name, total in totals(lines).items():
        doc_count = int(total["docs"])
        anywhere = total["random_anywhere"]
        ratio = f" x{total['examined'] / anywhere:.2f}" if anywhere else ""
        parts: List[str] = []
        if name == "rests-on":
            parts.append(
                f"+{int(total['gained'])}/-{int(total['lost'])} passages vs today,"
                f" victims={int(total['victims'])}"
            )
        if name != "recorded":
            if total["unchanged"] and total["unchanged"] == doc_count:
                parts.append("random-side = count, unchanged selection")
            else:
                side = f"random-side {total['random_side']:.1f}"
                if total["unchanged"]:
                    side += (
                        f" (unchanged on {int(total['unchanged'])}/{doc_count} docs)"
                    )
                parts.append(side)
        parts.append(f"random-anywhere {anywhere:.1f}{ratio}")
        print(
            f"TOTAL {name}: {int(total['examined'])}/{int(total['located'])} "
            f"({', '.join(parts)}) units={int(total['selected'])} docs={doc_count}"
        )
    unfaithful = [
        line["doc"] for line in lines if line["fidelity"] == c.POPULATION_UNFAITHFUL
    ]
    if unfaithful:
        print(
            f"UNFAITHFUL replay on {len(unfaithful)} document(s): {unfaithful} — "
            "the replay does not reproduce the recorded selection there"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
