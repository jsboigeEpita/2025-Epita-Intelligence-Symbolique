"""3-way comparison: 0-shot raw / 0-shot+taxonomy FC / sub-workflow guided.

Runs fallacy detection in 3 modes on the same input text, compares results.
Outputs comparison report with opaque IDs only.

Usage:
    python scripts/compare_fallacy_detection_modes.py --corpus all
    python scripts/compare_fallacy_detection_modes.py --corpus A
"""
import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
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
    "A": {"src_idx": 11, "label": "corpus_dense_A"},
    "B": {"src_idx": 3, "label": "corpus_dense_B"},
    "C": {"src_idx": 2, "label": "corpus_dense_C"},
}

TAXONOMY_PATH = Path("argumentation_analysis/data/argumentum_fallacies_taxonomy.csv")
OUTPUTS_DIR = Path("outputs/fallacy_comparison")


def load_corpus(corpus_id: str) -> str:
    info = CORPORA[corpus_id]
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    src = defs[info["src_idx"]]
    text = src.get("full_text", "")
    if corpus_id == "B":
        chunks = re.split(r"(?=\d{4}\.\d{2}\.\d{2})", text)
        best = ""
        for c in chunks:
            if 30000 <= len(c) <= 60000 and len(c) > len(best):
                best = c
        if not best:
            best = text[len(text) // 4: len(text) // 4 + 50000]
        text = best
    return text


def load_taxonomy() -> list:
    with open(TAXONOMY_PATH, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _extract_fallacies_from_text(raw: str) -> List[Dict[str, Any]]:
    """Parse LLM free-text or JSON response into structured fallacies."""
    fallacies = []
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        fallacies.append(item)
                    elif isinstance(item, str):
                        fallacies.append({"fallacy_type": item})
                return fallacies
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            if isinstance(parsed, dict):
                if "fallacies" in parsed:
                    return parsed["fallacies"]
                return [parsed]
    except (json.JSONDecodeError, ValueError):
        pass
    if fallacies:
        return fallacies
    return [{"fallacy_type": "raw_text", "raw": raw[:500]}]


def _assess_depth(fallacy: Dict, taxonomy_data: list) -> str:
    """Assess classification depth: leaf, family, or vague."""
    ft = fallacy.get("fallacy_type", "")
    pk = fallacy.get("taxonomy_pk", "")
    if pk:
        for node in taxonomy_data:
            if node.get("PK") == pk:
                depth = int(node.get("depth", 0))
                if depth >= 3:
                    return "leaf"
                elif depth >= 1:
                    return "family"
    if any(kw in ft.lower() for kw in ["ad hominem", "appel", "faux dilemme", "pente"]):
        return "family"
    return "vague"


def _assess_specificity(fallacy: Dict) -> str:
    ft = fallacy.get("fallacy_type", "")
    explanation = fallacy.get("explanation", fallacy.get("justification", ""))
    if len(ft) > 30 or any(kw in ft.lower() for kw in ["abusif", "circonstanciel", "poisoning", "guilt"]):
        return "exact_subtype"
    elif len(ft) > 10:
        return "family_level"
    return "generic"


def _assess_citation(fallacy: Dict, original_text: str) -> str:
    explanation = fallacy.get("explanation", fallacy.get("justification", ""))
    quotes = re.findall(r'["\'][^"\']{10,}["\']', explanation)
    if quotes:
        for q in quotes:
            clean = q.strip('"\'')
            if clean[:20].lower() in original_text.lower():
                return "exact_quote"
        return "paraphrase"
    return "no_citation"


async def run_mode_a_raw(text: str) -> Dict[str, Any]:
    """Mode A: 0-shot raw LLM — 'find fallacies in this text'."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
    start = time.time()
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert in logical fallacies. Identify all fallacies in the text. Respond with a JSON array of objects: {\"fallacy_type\": \"...\", \"explanation\": \"...\", \"citation\": \"exact quote from text\"}"},
            {"role": "user", "content": f"Analyze this text for logical fallacies:\n\n{text[:10000]}"},
        ],
    )
    duration = time.time() - start
    raw = resp.choices[0].message.content or ""
    fallacies = _extract_fallacies_from_text(raw)
    return {"mode": "A_0shot_raw", "fallacies": fallacies, "duration": round(duration, 1), "raw_output_chars": len(raw)}


async def run_mode_b_taxonomy_fc(text: str, taxonomy_data: list) -> Dict[str, Any]:
    """Mode B: 0-shot LLM + taxonomy as free function-calling tool."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

    taxonomy_summary = []
    for node in taxonomy_data:
        depth = int(node.get("depth", 0))
        if depth > 3:
            continue
        pk = node.get("PK", "")
        name = node.get("text_fr", node.get("nom_vulgarise", ""))
        if name:
            taxonomy_summary.append(f"PK={pk}: {name}")

    taxonomy_text = "\n".join(taxonomy_summary[:100])

    start = time.time()
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "You are a fallacy classifier. You have access to a taxonomy of fallacies.\n"
                "For each fallacy found, respond with JSON: "
                "{\"fallacy_type\": \"name from taxonomy\", \"taxonomy_pk\": \"PK from taxonomy\", "
                "\"explanation\": \"...\", \"citation\": \"exact quote\"}\n\n"
                f"TAXONOMY:\n{taxonomy_text}"
            )},
            {"role": "user", "content": f"Identify fallacies in this text using the taxonomy:\n\n{text[:10000]}"},
        ],
    )
    duration = time.time() - start
    raw = resp.choices[0].message.content or ""
    fallacies = _extract_fallacies_from_text(raw)
    return {"mode": "B_0shot_taxonomy", "fallacies": fallacies, "duration": round(duration, 1), "raw_output_chars": len(raw)}


async def run_mode_c_subworkflow(text: str, taxonomy_data: list) -> Dict[str, Any]:
    """Mode C: FallacyWorkflowPlugin sub-workflow (iterative deepening)."""
    from semantic_kernel.kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from openai import AsyncOpenAI
    from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

    async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    llm_service = OpenAIChatCompletion(ai_model_id=model_id, async_client=async_client)
    kernel = Kernel()
    kernel.add_service(llm_service)

    plugin = FallacyWorkflowPlugin(
        master_kernel=kernel,
        llm_service=llm_service,
        taxonomy_data=taxonomy_data,
    )

    start = time.time()
    result_json = await plugin.run_guided_analysis(argument_text=text[:10000])
    duration = time.time() - start

    try:
        parsed = json.loads(result_json)
        fallacies = parsed.get("fallacies", [])
        method = parsed.get("exploration_method", "unknown")
    except (json.JSONDecodeError, TypeError):
        fallacies = []
        method = "parse_error"

    return {
        "mode": "C_subworkflow",
        "fallacies": fallacies,
        "duration": round(duration, 1),
        "exploration_method": method,
    }


async def compare_corpus(corpus_id: str, taxonomy_data: list) -> Dict[str, Any]:
    text = load_corpus(corpus_id)
    label = CORPORA[corpus_id]["label"]
    print(f"\n{'='*60}")
    print(f"3-Way Comparison — {label} ({len(text):,} chars)")
    print(f"{'='*60}")

    results = {}
    for name, coro in [
        ("A", run_mode_a_raw(text)),
        ("B", run_mode_b_taxonomy_fc(text, taxonomy_data)),
        ("C", run_mode_c_subworkflow(text, taxonomy_data)),
    ]:
        print(f"  Running mode {name}...", end=" ", flush=True)
        try:
            result = await coro
            results[name] = result
            n = len(result.get("fallacies", []))
            print(f"done ({result['duration']}s, {n} fallacies)")
        except Exception as e:
            results[name] = {"mode": name, "error": str(e), "fallacies": []}
            print(f"ERROR: {e}")

    comparison = {
        "corpus_id": corpus_id,
        "corpus_label": label,
        "text_length": len(text),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modes": {},
    }

    for mode_key, mode_data in results.items():
        fallacies = mode_data.get("fallacies", [])
        assessed = []
        for f in fallacies:
            assessed.append({
                "fallacy_type": f.get("fallacy_type", f.get("name", "")),
                "depth": _assess_depth(f, taxonomy_data),
                "specificity": _assess_specificity(f),
                "citation_quality": _assess_citation(f, text),
                "explanation_length": len(f.get("explanation", f.get("justification", ""))),
            })
        comparison["modes"][mode_key] = {
            "num_fallacies": len(fallacies),
            "duration_seconds": mode_data.get("duration", 0),
            "assessed_fallacies": assessed,
            "exploration_method": mode_data.get("exploration_method", ""),
            "error": mode_data.get("error", None),
        }

    out_dir = OUTPUTS_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)

    return comparison


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, help="Corpus ID (A, B, C) or 'all'")
    args = parser.parse_args()

    taxonomy_data = load_taxonomy()
    corpora = ["A", "B", "C"] if args.corpus.lower() == "all" else [args.corpus.upper()]

    all_comparisons = []
    for cid in corpora:
        comp = await compare_corpus(cid, taxonomy_data)
        all_comparisons.append(comp)

    if len(all_comparisons) > 1:
        print(f"\n{'='*60}")
        print("GLOBAL COMPARISON SUMMARY")
        print(f"{'='*60}")
        for c in all_comparisons:
            print(f"\n{c['corpus_label']}:")
            for mode_key, mdata in c["modes"].items():
                n = mdata["num_fallacies"]
                dur = mdata["duration_seconds"]
                depths = [f["depth"] for f in mdata.get("assessed_fallacies", [])]
                leaf_pct = (depths.count("leaf") / len(depths) * 100) if depths else 0
                print(f"  Mode {mode_key}: {n} fallacies, {dur}s, {leaf_pct:.0f}% leaf-level")


if __name__ == "__main__":
    asyncio.run(main())
