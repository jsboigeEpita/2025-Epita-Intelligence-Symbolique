"""A stronger model sorts the judge items of a cycle into defect classes.

    python scripts/panel/classify_items.py --states-dir <cycle>/states \\
        --trace <results>/panel_cycles/<cycle>/trace.jsonl \\
        --out <results>/panel_cycles/<cycle>/classes.json [--dry-run] [--model claude-opus-5-5]

One call per document. The model receives the three acts of the render and,
for each traced item (``trace_items.py``), the judge's note and quotes, the
stage the tracer measured, and for an M1 the units that overlap the passage
with the findings on them. It answers one class per item from the closed list
``CLASSES`` (or ``OTHER:<NAME>``), the mechanism in one sentence, and whether
the pipeline can fix it. The classes are what a cycle turns into issues: one
issue per class, never one per item.

The tracer's stage is the measure and the model's class is a reading of it:
the prompt asks the model to contradict the stage only on evidence, and to
say so. ``RENDERED_UNSEEN`` and ``JUDGE_WRONG`` are not pipeline defects.

Paid: ``--dry-run`` prints the prompt sizes and the estimate and makes no
call. The output carries quotes and stays under a gitignored path; stdout
prints counts and cost.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

DEFAULT_MODEL = "claude-opus-5-5"
# The answer is a short JSON object per document; the estimate assumes this
# many output tokens for each, and says it is an estimate.
ESTIMATED_OUTPUT_TOKENS = 3000
CHARS_PER_TOKEN_ESTIMATE = 3
CONCURRENCY = 5

CLASSES = {
    "READING_MISS": "M1 : la première lecture ne nomme pas le passage et aucune unité ne le porte",
    "EXTRACTION_GAP": "M1 : la lecture le nomme, mais l'extraction n'a coupé aucune unité là",
    "BUDGET": "M1 : une unité existe mais la passe par argument ne l'examine pas",
    "NO_LENS_ASKS": "M1 : examiné, mais l'observation du juge n'est pas un sophisme "
    "(structure, stratégie, contexte, enjeu, cohérence) et aucune lentille ne pose cette question",
    "LENS_MISSED": "M1 : examiné par une lentille qui aurait dû voir le point (sophisme réel non retenu)",
    "WRITER_DROP": "M1 : l'état porte le constat, l'acte ne le rend pas",
    "RENDERED_UNSEEN": "M1 : le rendu le porte déjà (paraphrase), le juge ne l'a pas reconnu "
    "— pas un défaut du pipeline",
    "JUDGE_WRONG": "l'item du juge est faux ou hors sujet au vu du document",
    "M2_ATTRIBUTION": "M2 : position attribuée au mauvais locuteur / sujet inversé",
    "M2_OVERREACH": "M2 : l'analyse affirme plus que le document (superlatif, généralisation, verdict)",
    "M2_MISREAD": "M2 : contresens sur ce que dit le passage",
    "M2_FABRICATED": "M2 : affirmation sans appui dans le document ni dans l'état",
}
NOT_A_PIPELINE_DEFECT = frozenset({"RENDERED_UNSEEN", "JUDGE_WRONG"})

PROMPT_HEAD = """Tu es l'auditeur d'un pipeline d'analyse argumentative. Un juge à l'aveugle a comparé le rendu du pipeline
à une lecture zero-shot du même document, et a relevé des items :
- M1 : une observation sur le document qu'aucune ligne du rendu ne porte ;
- M2 : une affirmation du rendu que le document dément.
Pour chaque item, un traceur déterministe a déjà mesuré à quelle étape le passage s'arrête dans l'état du pipeline
(`stage`, et les étapes `named` / `unit` / `examined` / `finding` / `reviewed` / `rendered`).

Ta tâche : classer CHAQUE item dans UNE classe de la liste fermée ci-dessous (ou `OTHER:<NOM_COURT>` si aucune ne convient),
nommer le mécanisme en une phrase précise (quel champ, quelle étape, pourquoi), et dire si le pipeline peut le corriger.
Appuie-toi sur le `stage` mesuré : ne le contredis que si les éléments fournis le démentent, et dis-le.

Classes :
{classes}

Réponds UNIQUEMENT par un objet JSON :
{{"items": [{{"i": <index>, "class": "<CLASSE>", "mechanism": "<une phrase>", "fixable": true|false, "severity": "high"|"medium"|"low"}}],
  "doc_pattern": "<une phrase : le défaut dominant de ce document, s'il y en a un>"}}

## Rendu du pipeline (actes)
{acts}

## Items
{items}
"""
HOPS = ("named", "unit", "examined", "finding", "reviewed", "rendered", "acts")


def worth_classifying(row: Dict[str, Any]) -> bool:
    """An M2, a central item, an item two passes or more support, or a kept
    one. A lone minority M1 off the thesis is noise at this stage."""
    return bool(
        row.get("code") == "M2"
        or row.get("central")
        or (row.get("support") or 0) >= 2
        or row.get("bucket") == "kept"
    )


def unit_context(
    state: Dict[str, Any], index: c.DocIndex, span: c.Span
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """What the state holds at a passage: overlapping units with the findings
    on them, and the coverage-review items there."""
    findings: Dict[str, List[str]] = defaultdict(list)
    for value in (state.get("identified_fallacies") or {}).values():
        if isinstance(value, dict) and value.get("target_argument_id"):
            findings[value["target_argument_id"]].append(
                f"{value.get('type')}: {(value.get('justification') or '')[:240]}"
            )
    units = [
        {
            "unit_id": unit.unit_id,
            "examined": unit.unit_id in index.examined,
            "text": (unit.text or "")[:300],
            "findings": findings.get(unit.unit_id, [])[:3],
        }
        for unit in c.units_overlapping(index.units, span, index.starts)
    ]
    review = [
        {
            "class": item.get("class"),
            "lens": item.get("lens"),
            "conclusion": (item.get("conclusion") or "")[:240],
        }
        for item in (state.get("coverage_review") or {}).get("items") or []
        if isinstance(item.get("offset"), int)
        and item.get("quote")
        and c.overlaps((item["offset"], item["offset"] + len(item["quote"])), span)
    ]
    return units[:4], review[:3]


def build_prompts(
    states_dir: Path, rows: Sequence[Dict[str, Any]]
) -> Tuple[Dict[str, str], Dict[str, List[Dict[str, Any]]]]:
    """One prompt per document, and the rows each prompt indexes."""
    by_doc: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_doc[row["doc"]].append(row)
    prompts: Dict[str, str] = {}
    for doc, doc_rows in sorted(by_doc.items()):
        state = c.load_state(states_dir, doc)
        index = c.build_doc_index(doc, state)
        acts = "\n\n".join(f"### {act}\n{state.get(act) or '(vide)'}" for act in c.ACTS)
        blocks = []
        for i, row in enumerate(doc_rows):
            block: Dict[str, Any] = {
                "i": i,
                "family": row.get("family"),
                "code": row["code"],
                "support": row.get("support"),
                "central": row.get("central"),
                "note": row.get("note"),
                "document_quote": row.get("document_quote"),
                "zeroshot_quote": row.get("zeroshot_quote"),
                "pipeline_quote": row.get("pipeline_quote"),
                "stage": row.get("stage"),
                "hops": {hop: row.get(hop) for hop in HOPS if hop in row},
            }
            if row["code"] == "M1" and row.get("located"):
                span = index.locate(row.get("document_quote"))
                if span is not None:
                    block["units"], block["coverage_review"] = unit_context(
                        state, index, span
                    )
            blocks.append(block)
        prompts[doc] = PROMPT_HEAD.format(
            classes="\n".join(f"- {name} — {text}" for name, text in CLASSES.items()),
            acts=acts,
            items=json.dumps(blocks, ensure_ascii=False, indent=1),
        )
    return prompts, dict(by_doc)


def parse_answer(answer: str) -> Dict[str, Any]:
    """The JSON object of an answer, fenced or not."""
    text = answer.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the answer")
    return json.loads(text[start : end + 1])


def merge_answer(
    parsed: Dict[str, Any], doc_rows: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """The model's items joined to the rows they index; an index the prompt
    never gave is dropped, never guessed."""
    merged = []
    for item in parsed.get("items") or []:
        i = item.get("i")
        if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(doc_rows):
            source = doc_rows[i]
            merged.append(
                {
                    **{
                        key: source.get(key)
                        for key in ("family", "code", "support", "central", "stage")
                    },
                    **item,
                }
            )
    return merged


def estimate_cost(model: str, prompts: Dict[str, str]) -> Optional[float]:
    """USD for the whole call set, or ``None`` when the model is unpriced."""
    from argumentation_analysis.services.model_prices import price_tokens

    total = 0.0
    for prompt in prompts.values():
        usd = price_tokens(
            model, len(prompt) // CHARS_PER_TOKEN_ESTIMATE, ESTIMATED_OUTPUT_TOKENS
        )
        if usd is None:
            return None
        total += usd
    return total


async def call_all(prompts: Dict[str, str], model: str) -> Dict[str, Dict[str, Any]]:
    from scripts.dataset import judge_panel as jp

    endpoint = jp.resolve_judge_endpoint(model)
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(doc: str, prompt: str) -> Tuple[str, Dict[str, Any]]:
        async with gate:
            return doc, await jp.call_judge(endpoint, prompt, timeout=900)

    return dict(await asyncio.gather(*(one(d, p) for d, p in prompts.items())))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--states-dir", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    c.ensure_gitignored(args.out)

    rows = [
        json.loads(line)
        for line in args.trace.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [row for row in rows if worth_classifying(row)]
    prompts, index = build_prompts(args.states_dir, rows)
    chars = sum(len(prompt) for prompt in prompts.values())
    estimate = estimate_cost(args.model, prompts)
    print(
        f"documents={len(prompts)} items={len(rows)} prompt_chars={chars} "
        f"estimate={'unpriced model' if estimate is None else f'{estimate:.2f} $'}"
    )
    if args.dry_run:
        print("dry-run: no call")
        return 0

    from argumentation_analysis.services.model_prices import price_tokens

    answers = asyncio.run(call_all(prompts, args.model))
    result: Dict[str, Any] = {}
    classes: Counter = Counter()
    tokens_in = tokens_out = 0
    for doc, answer in answers.items():
        tokens_in += answer.get("prompt_tokens") or 0
        tokens_out += answer.get("completion_tokens") or 0
        if not answer.get("answer"):
            result[doc] = {
                "error": answer.get("status_code"),
                "head": (answer.get("error_body_head") or "")[:200],
            }
            continue
        try:
            parsed = parse_answer(answer["answer"])
        except ValueError as exc:
            result[doc] = {"parse_error": str(exc)[:120]}
            continue
        merged = merge_answer(parsed, index[doc])
        for item in merged:
            classes[(item.get("class"), item.get("code"))] += 1
        result[doc] = {
            "doc_pattern": parsed.get("doc_pattern"),
            "items": merged,
            "stop": answer.get("stop_reason"),
        }
    cost = price_tokens(args.model, tokens_in, tokens_out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "model": args.model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": cost,
                "docs": result,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(
        f"model={args.model} in={tokens_in} out={tokens_out} "
        f"cost={'unpriced' if cost is None else f'{cost:.3f} $'} -> {args.out}"
    )
    for (name, code), count in classes.most_common():
        flag = "  (not a pipeline defect)" if name in NOT_A_PIPELINE_DEFECT else ""
        print(f"  {code} {name}: {count}{flag}")
    failed = sorted(
        doc
        for doc, value in result.items()
        if "error" in value or "parse_error" in value
    )
    if failed:
        print(f"FAILED on {len(failed)} document(s): {failed}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
