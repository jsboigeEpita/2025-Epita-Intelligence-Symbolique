"""N-draw witness: how many of the judge's passages does the first reading name?

    python scripts/panel/first_reading_draws.py calibrate --states-dir <cycle>/states \\
        --passages-from <results>/judge_panel_3375_<cycle>_<family>_p[1-6] --min-chars 6016
    python scripts/panel/first_reading_draws.py dry   --states-dir ... --min-chars 6016
    python scripts/panel/first_reading_draws.py paid  --states-dir ... --passages-from ... \\
        --draws 3 --out-dir <results>/panel_cycles/<cycle>/first_reading_draws

The first reading is one LLM call per document, and one call measures one
draw: on the same documents, the recorded cycle named 11 of 39 passages and
three reruns of the same call 20, 14 and 19 (#3511). So a bar on this stage
is read on **three draws or more**:
the minimum, the mean and the spread, per document and in total. A single
draw that passes a bar has shown that the bar can be passed once.

Modes:

  calibrate  no call. The recorded moves against the passages: the positive
             control (it must give back the figure of the cycle that recorded
             the states), and the random-anchor control beside it.
  dry        no call. The prompt each document would receive: stated bounds
             and size.
  paid       ``--draws`` live calls per document on the checked-out code.
             Each draw writes ``d<i>/moves_<doc>.json`` (the input of
             ``replay_selection.py --moves-dir``) and the report holds every
             draw's counts, tokens and finish reason.

A passage is **named** when a move overlaps it — a positioned move by its
span, an unpositioned one by locating its quote. The count is read against
anchors of the same number and lengths drawn anywhere in the text: a reading
that lists more passages names more of anything.

Documents come from ``--panel-file`` (default: every state of the directory)
and ``--min-chars``. Nothing is written outside a gitignored path; stdout
prints counts and the ids it was given, never document text.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

MIN_DRAWS_FOR_A_BAR = 3


def move_spans(moves: Sequence[Dict[str, Any]], index: c.DocIndex) -> List[c.Span]:
    """The spans of the moves: recorded offset, else the located quote."""
    spans: List[c.Span] = []
    for move in moves:
        offset, quote = move.get("offset"), move.get("quote") or ""
        if isinstance(offset, int) and not isinstance(offset, bool) and quote:
            spans.append((offset, offset + len(quote)))
        elif quote:
            span = index.locate(quote)
            if span is not None:
                spans.append(span)
    return spans


def count_named(
    index: c.DocIndex,
    moves: Sequence[Dict[str, Any]],
    quotes: Sequence[str],
    control_draws: int = 0,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Passages named by the moves, with the random-anchor expectation."""
    spans = move_spans(moves, index)
    passages = [span for span in map(index.locate, quotes) if span is not None]
    named = sum(
        any(c.overlaps(span, passage) for span in spans) for passage in passages
    )
    result: Dict[str, Any] = {
        "passages": len(quotes),
        "located": len(passages),
        "named": named,
        "moves": len(moves),
        "positioned": len(spans),
    }
    if control_draws:
        result["random"] = round(
            c.random_anchor_expectation(
                spans,
                passages,
                len(index.raw),
                control_draws,
                rng or random.Random(c.DEFAULT_SEED),
            ),
            1,
        )
    return result


def summarise_draws(named_per_draw: Sequence[int]) -> Dict[str, Any]:
    """Minimum, mean, maximum and spread of one count over the draws.

    ``enough`` is false under three draws: the figures are then one or two
    observations, and no bar is read on them.
    """
    values = list(named_per_draw)
    if not values:
        return {"draws": 0, "enough": False}
    return {
        "draws": len(values),
        "min": min(values),
        "mean": round(statistics.fmean(values), 1),
        "max": max(values),
        "spread": max(values) - min(values),
        "enough": len(values) >= MIN_DRAWS_FOR_A_BAR,
    }


def selected_docs(args: argparse.Namespace) -> List[str]:
    docs = c.read_panel(args.panel_file) or c.docs_in(args.states_dir)
    kept = []
    for doc in docs:
        if not c.state_path(args.states_dir, doc).exists():
            print(f"{doc}: no recorded state — skipped")
            continue
        state = c.load_state(args.states_dir, doc)
        if len(state.get("raw_text") or "") >= args.min_chars:
            kept.append(doc)
    return kept


def calibrate(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    total = {"located": 0, "named": 0, "random": 0.0}
    for doc in selected_docs(args):
        state = c.load_state(args.states_dir, doc)
        index = c.build_doc_index(doc, state)
        moves = (state.get("defining_moves") or {}).get("moves") or []
        quotes = c.central_passages(args.passages_from or [], doc)
        result = count_named(index, moves, quotes, args.control_draws, rng)
        for key in total:
            total[key] += result.get(key, 0)
        print(doc, json.dumps(result))
    total["random"] = round(total["random"], 1)
    print("TOTAL", json.dumps(total))
    return 0


def dry(args: argparse.Namespace) -> int:
    from argumentation_analysis.agents.core.reading import build_first_reading_prompt
    from argumentation_analysis.core.reading_window import (
        inventory_budget,
        pillar_budget,
    )

    for doc in selected_docs(args):
        raw = c.load_state(args.states_dir, doc)["raw_text"]
        prompt = build_first_reading_prompt(raw)
        stated = re.search(r"At most (\d+) entries", prompt)
        print(
            doc,
            json.dumps(
                {
                    "chars": len(raw),
                    "inventory_budget": inventory_budget(len(raw)),
                    "pillar_budget": pillar_budget(len(raw)),
                    "prompt_states": int(stated.group(1)) if stated else None,
                    "prompt_chars": len(prompt),
                }
            ),
        )
    return 0


async def paid(args: argparse.Namespace) -> int:
    import argumentation_analysis.orchestration.invoke_callables as ic
    from argumentation_analysis.agents.core.reading import build_first_reading
    from argumentation_analysis.services.model_prices import price_tokens

    c.ensure_gitignored(args.out_dir)
    docs = selected_docs(args)
    last: Dict[str, Any] = {}
    real = ic._guarded_chat_completion

    async def recorder(client: Any, **kwargs: Any) -> Any:
        started = time.time()
        response = await real(client, **kwargs)
        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        last.clear()
        last.update(
            finish_reason=getattr(choice, "finish_reason", None),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            model=kwargs.get("model"),
            seconds=round(time.time() - started, 1),
        )
        return response

    ic._guarded_chat_completion = recorder
    try:
        llm, reason = ic._build_persona_callable(
            "first_reading", max_completion_tokens=ic._FIRST_READING_MAX_TOKENS or None
        )
        if llm is None:
            print("NO ROUTE:", reason)
            return 3
        rng = random.Random(args.seed)
        report: Dict[str, List[Dict[str, Any]]] = {doc: [] for doc in docs}
        for draw in range(1, args.draws + 1):
            out = args.out_dir / f"d{draw}"
            out.mkdir(parents=True, exist_ok=True)
            for doc in docs:
                state = c.load_state(args.states_dir, doc)
                index = c.build_doc_index(doc, state)
                last.clear()
                reading = await build_first_reading(
                    SimpleNamespace(raw_text=state["raw_text"]), llm
                )
                payload = reading.to_state()
                (out / f"moves_{doc}.json").write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
                result = count_named(
                    index,
                    payload.get("moves") or [],
                    c.central_passages(args.passages_from or [], doc),
                    args.control_draws,
                    rng,
                )
                result.update(last or {"finish_reason": "NO_CALL"})
                result["status"] = payload.get("status")
                result["draw"] = draw
                report[doc].append(result)
                print(f"draw {draw}", doc, json.dumps(result), flush=True)
    finally:
        ic._guarded_chat_completion = real

    summary = {
        doc: summarise_draws([r["named"] for r in results])
        for doc, results in report.items()
    }
    per_draw = [sum(report[doc][i]["named"] for doc in docs) for i in range(args.draws)]
    located = sum(report[doc][0]["located"] for doc in docs) if docs else 0
    cost = 0.0
    priced = True
    for results in report.values():
        for r in results:
            usd = price_tokens(
                r.get("model") or "",
                r.get("prompt_tokens") or 0,
                r.get("completion_tokens") or 0,
            )
            priced = priced and usd is not None
            cost += usd or 0.0
    total = summarise_draws(per_draw)
    (args.out_dir / "report.json").write_text(
        json.dumps(
            {"per_doc": report, "summary": summary, "total": total, "located": located},
            indent=1,
        ),
        encoding="utf-8",
    )
    for doc, line in summary.items():
        print("SUMMARY", doc, json.dumps(line))
    print(f"TOTAL named per draw {per_draw} of {located} located:", json.dumps(total))
    print(f"cost: {cost:.3f} $" if priced else "cost: a model of the run is not priced")
    cuts = sorted(
        {
            doc
            for doc, rs in report.items()
            for r in rs
            if r.get("finish_reason") == "length"
        }
    )
    if cuts:
        print(f"answers cut at the token cap on {len(cuts)} document(s): {cuts}")
    if not total.get("enough"):
        print(
            f"fewer than {MIN_DRAWS_FOR_A_BAR} draws: these figures are "
            "observations, no bar is read on them"
        )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=("calibrate", "dry", "paid"))
    parser.add_argument("--states-dir", type=Path, required=True)
    parser.add_argument("--panel-file", type=Path, default=None)
    parser.add_argument("--min-chars", type=int, default=0)
    parser.add_argument("--passages-from", type=Path, nargs="*", default=[])
    parser.add_argument("--draws", type=int, default=MIN_DRAWS_FOR_A_BAR)
    parser.add_argument("--control-draws", type=int, default=1000)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=c.DEFAULT_SEED)
    args = parser.parse_args(argv)
    if args.mode == "calibrate":
        return calibrate(args)
    if args.mode == "dry":
        return dry(args)
    if args.out_dir is None:
        parser.error("paid needs --out-dir (a gitignored directory)")
    return asyncio.run(paid(args))


if __name__ == "__main__":
    raise SystemExit(main())
