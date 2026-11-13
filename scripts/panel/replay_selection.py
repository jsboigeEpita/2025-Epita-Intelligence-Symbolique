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
  k=<K>      the same at a forced budget (--budget)
  <dir>      the first reading's moves replaced by ``moves_<doc>.json`` of a
             directory (--moves-dir, e.g. the draws of first_reading_draws.py)
  union      the union of those directories' moves, when two or more are given

Two controls decide whether a count means anything:

- **fidelity** — the population that reproduces the recorded selection
  (``_common.resolve_population``). ``unfaithful`` means the replay does not
  reproduce the run: nothing on that line is a measure, and the exit code is 2.
- **random** — the same passages redrawn anywhere in the text. A variant that
  examines 20 passages where random ones score 18 has found nothing.

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
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
) -> Dict[str, Any]:
    """Today's selection on ``state`` at budget ``k``, scored on the passages."""
    ns = SimpleNamespace(**state)
    population = c.population_of(ns)
    selection = c.select(ns, population, k)
    selected = list(selection.selected)
    _units, starts = c.positioned_units(population)
    return {
        "examined": examined_count(selected, starts, passages),
        "random": c.random_passage_expectation(
            passages,
            len(state.get("raw_text") or ""),
            lambda span: bool(c.units_overlapping(selected, span, starts)),
            draws,
            rng,
        ),
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
) -> Dict[str, Any]:
    """One document's line: fidelity, located passages, and every variant."""
    rng = rng or random.Random(c.DEFAULT_SEED)
    index = c.build_doc_index(doc, state)
    passages = [span for span in map(index.locate, quotes) if span is not None]
    recorded_units = [u for u in index.units if u.unit_id in index.examined]
    variants: Dict[str, Dict[str, Any]] = {
        "recorded": {
            "examined": examined_count(recorded_units, index.starts, passages),
            "selected": len(index.examined),
        },
        "today": replay_variant(state, passages, None, draws, rng),
    }
    for k in budgets:
        variants[f"k={k}"] = replay_variant(state, passages, k, draws, rng)
    moves_by_dir = moves_by_dir or {}
    for name, moves in moves_by_dir.items():
        variants[name] = replay_variant(
            with_moves(state, moves), passages, None, draws, rng
        )
    if len(moves_by_dir) >= 2:
        variants["union"] = replay_variant(
            with_moves(state, union_moves(list(moves_by_dir.values()))),
            passages,
            None,
            draws,
            rng,
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
                {"examined": 0, "random": 0.0, "selected": 0, "located": 0, "docs": 0},
            )
            total["examined"] += variant["examined"]
            total["random"] += variant.get("random", 0.0)
            total["selected"] += variant["selected"]
            total["located"] += line["located"]
            total["docs"] += 1
    return out


def _cell(name: str, variant: Dict[str, Any], located: int) -> str:
    text = f"{name} {variant['examined']}/{located}"
    if "random" in variant:
        text += f" (random {variant['random']:.1f})"
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
            doc, state, quotes, args.budget, moves_by_dir, args.draws, rng
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
        ratio = (
            f" x{total['examined'] / total['random']:.2f}" if total["random"] else ""
        )
        tail = f" (random {total['random']:.1f}{ratio})" if name != "recorded" else ""
        print(
            f"TOTAL {name}: {int(total['examined'])}/{int(total['located'])}{tail} "
            f"units={int(total['selected'])} docs={int(total['docs'])}"
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
