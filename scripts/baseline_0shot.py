"""Baseline 0-shot LLM analysis on dense corpora (#546).

Runs 4 single-shot LLM calls per corpus (fallacies, PL, FOL, counter-arguments),
validates PL/FOL formulas against Tweety, and produces an aggregate report.

Usage:
    python scripts/baseline_0shot.py
    python scripts/baseline_0shot.py --corpus A

Outputs: outputs/baseline_0shot/<corpus>/ (gitignored)
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

CORPORA = {
    "A": {"src_idx": 11, "label": "corpus_dense_A", "desc": "src11 EN ~58K"},
    "B": {"src_idx": 3, "label": "corpus_dense_B", "desc": "src3 DE ~50K extract"},
    "C": {"src_idx": 2, "label": "corpus_dense_C", "desc": "src2 EN ~46K"},
}

OUTPUTS_DIR = Path("outputs/baseline_0shot")

PROMPTS = {
    "fallacies": (
        "You are a critical thinker analyzing political rhetoric. "
        "List every fallacy you can identify in this text. For each, give: "
        "type (using Walton/Aristotle taxonomy, e.g. ad populum, ad hominem, "
        "false dilemma, slippery slope, appeal to authority, straw man, "
        "hasty generalization, post hoc), the exact quote from the text, "
        "and brief reasoning why it is that fallacy.\n\n"
        'Return as a JSON array: [{{"type": "...", "quote": "...", "reasoning": "..."}}]\n\n'
        "Text:\n{text}"
    ),
    "pl": (
        "Extract the propositional logic structure of this text.\n\n"
        "Return JSON with this exact schema:\n"
        '{{"atoms": ["atom_name_1", "atom_name_2"], '
        '"formulas": ["p && q", "p => r"]}}\n\n'
        "Rules for atoms: use short snake_case names (max 3 words). "
        "Each atom represents one atomic proposition.\n"
        "Rules for formulas: use ONLY the operators &&, ||, =>, !, <=>. "
        "Use ONLY atoms from your atoms list. Keep formulas simple "
        "(max 4 atoms per formula). No nested parens deeper than 2 levels.\n\n"
        "Text:\n{text}"
    ),
    "fol": (
        "Extract the first-order logic structure of this text.\n\n"
        "Return JSON with this exact schema:\n"
        '{{"sorts": ["Person", "Nation"], '
        '"constants": {{"SortName": ["const1", "const2"]}}, '
        '"predicates": [{{"name": "PredName", "arity": 2}}], '
        '"formulas": ["forall X: (P(X) => Q(X))"]}}\n\n'
        "Rules: Use forall X: (...) and exists X: (...) syntax. "
        "Use ONLY &&, ||, =>, !, <=> between quantified expressions. "
        "Keep formulas simple. Use only declared predicates and constants.\n\n"
        "Text:\n{text}"
    ),
    "counter": (
        "For each main claim in this text, propose one strong counter-argument. "
        "Use one of these strategies: reductio ad absurdum, counter-example, "
        "distinction, reformulation, or concession.\n\n"
        'Return as a JSON array: [{{"claim": "...", "strategy": "...", '
        '"counter_text": "..."}}]\n\n'
        "Text:\n{text}"
    ),
}


def load_corpus(corpus_id: str) -> str:
    info = CORPORA[corpus_id]
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    src = defs[info["src_idx"]]
    text = src.get("full_text", "")

    if corpus_id == "B":
        speech_markers = re.split(r'(?=\d{4}\.\d{2}\.\d{2})', text)
        best_chunk = ""
        for chunk in speech_markers:
            if 30000 <= len(chunk) <= 60000 and len(chunk) > len(best_chunk):
                best_chunk = chunk
        if not best_chunk:
            start = len(text) // 4
            boundary = text.find("\n\n", start)
            if boundary > 0:
                start = boundary
            best_chunk = text[start:start + 50000]
        text = best_chunk

    return text


def call_llm(prompt: str) -> str:
    import openai
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
    )
    model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=4096,
    )
    return response.choices[0].message.content


def extract_json(text: str) -> Any:
    """Extract JSON from LLM response (may have markdown fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON array/object in the text
        for pattern in [r'\[.*\]', r'\{.*\}']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
    return None


def validate_pl_formulas(formulas: List[str]) -> Dict[str, Any]:
    """Validate PL formulas against Tweety parser."""
    results = {"total": len(formulas), "parsed": 0, "failed": 0, "errors": []}
    try:
        from argumentation_analysis.agents.core.logic.pl_handler import PLHandler
        handler = PLHandler()
        for f in formulas:
            try:
                handler.parse_formula(f)
                results["parsed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e)[:100])
    except Exception as e:
        results["error"] = f"Tweety unavailable: {str(e)[:100]}"
    return results


def run_corpus(corpus_id: str) -> Dict[str, Any]:
    info = CORPORA[corpus_id]
    print(f"\n{'='*50}")
    print(f"Baseline 0-shot — {info['label']} ({info['desc']})")
    print(f"{'='*50}")

    text = load_corpus(corpus_id)
    print(f"Loaded {len(text):,} chars")

    out_dir = OUTPUTS_DIR / info["label"]
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    stats = {"text_length": len(text), "corpus_id": corpus_id}

    for call_name, prompt_template in PROMPTS.items():
        print(f"  Running {call_name}...", end=" ", flush=True)
        prompt = prompt_template.format(text=text)
        start = time.time()
        try:
            raw = call_llm(prompt)
            duration = time.time() - start
            parsed = extract_json(raw)

            # Save raw + parsed
            with open(out_dir / f"{call_name}_raw.txt", "w", encoding="utf-8") as f:
                f.write(raw)
            with open(out_dir / f"{call_name}.json", "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False, default=str)

            if call_name == "fallacies" and isinstance(parsed, list):
                stats["fallacies_count"] = len(parsed)
                print(f"{len(parsed)} fallacies ({duration:.1f}s)")
            elif call_name == "pl" and isinstance(parsed, dict):
                atoms = parsed.get("atoms", [])
                formulas = parsed.get("formulas", [])
                stats["pl_atoms"] = len(atoms)
                stats["pl_formulas"] = len(formulas)
                pl_validation = validate_pl_formulas(formulas)
                stats["pl_parse_success"] = pl_validation["parsed"]
                stats["pl_parse_failed"] = pl_validation["failed"]
                stats["pl_parse_rate"] = (
                    f"{pl_validation['parsed']}/{len(formulas)}"
                    if formulas else "N/A"
                )
                with open(out_dir / "pl_validation.json", "w", encoding="utf-8") as f:
                    json.dump(pl_validation, f, indent=2, ensure_ascii=False)
                print(f"{len(atoms)} atoms, {len(formulas)} formulas, "
                      f"{pl_validation['parsed']}/{len(formulas)} parsed ({duration:.1f}s)")
            elif call_name == "fol" and isinstance(parsed, dict):
                sorts = parsed.get("sorts", [])
                predicates = parsed.get("predicates", [])
                formulas = parsed.get("formulas", [])
                stats["fol_sorts"] = len(sorts)
                stats["fol_predicates"] = len(predicates)
                stats["fol_formulas"] = len(formulas)
                print(f"{len(sorts)} sorts, {len(predicates)} preds, "
                      f"{len(formulas)} formulas ({duration:.1f}s)")
            elif call_name == "counter" and isinstance(parsed, list):
                stats["counter_count"] = len(parsed)
                print(f"{len(parsed)} counter-arguments ({duration:.1f}s)")
            else:
                print(f"done ({duration:.1f}s) — parse issue")

        except Exception as e:
            print(f"ERROR: {e}")
            stats[f"{call_name}_error"] = str(e)[:200]

    with open(out_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"  Stats: {json.dumps(stats, indent=2)}")
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="all",
                        help="Corpus ID (A, B, C) or 'all'")
    args = parser.parse_args()

    corpora = ["A", "B", "C"] if args.corpus.lower() == "all" else [args.corpus.upper()]
    all_stats = {}
    for cid in corpora:
        all_stats[cid] = run_corpus(cid)

    print(f"\n{'='*60}")
    print("BASELINE 0-SHOT SUMMARY")
    print(f"{'='*60}")
    for cid, s in all_stats.items():
        print(f"\n{CORPORA[cid]['label']}:")
        for k, v in s.items():
            if k != "corpus_id":
                print(f"  {k}: {v}")

    # Save aggregate
    with open(OUTPUTS_DIR / "aggregate_stats.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
