"""#1629 paired re-measure — fallacy->argument attack pairing on real corpora.

The fix (R974, ``_resolve_target_argument_id``) made the attack-graph edge for
a fallacy come from its explicit ``target_argument`` identifier — arithmetic
inverse of the ``arg_N`` minting — and REMOVED the positional fallback
(``fallacy_i -> arg_{i+1}``): a detection without a resolvable target is
skipped and counted, never paired by position. This harness measures the AFTER
state on the same three opaque corpora as the #1605/#1629 artifacts so the
before/after comparison is paired.

Measured per corpus (LLM real, one pass):
  - distribution of the pairing: resolved-by-identifier vs lexical fallback
    vs skip-counted (the fallacy branch has NO lexical fallback by design —
    the value is measured as 0 through the production path);
  - positional correlation of the resolved targets: for the i-th detection,
    does its resolved target coincide with ``arguments[min(i, n-1)]`` (what
    the pre-fix enumeration-index pairing would have produced)?
  - the production attack graph itself via ``_generate_attacks_from_args`` —
    the edge count must equal the resolved count (cross-check, not a
    reimplementation).

AVANT (rejoué): the pre-fix pairing is a deterministic function of the same
detection list — every fallacy got ``arguments[min(i, n-1)]`` — so the
simulated-before is computed on the SAME after-run detections for a same-run
paired comparison. The documented historical before (issue #1629: corpus_C,
24 positional pairings pre-fix) remains the external anchor.

Routing is MANDATED (dispatch R1012): gpt-5.6-luna via OpenRouter ONLY, so
``OPENROUTER_BASE_URL`` and ``OPENAI_CHAT_MODEL_ID`` are pinned below BEFORE
the .env setdefault pass — .env cannot override them. The OpenRouter key
triplet (/api/v1/key) is queried before/after and stored in the artifact.

Privacy HARD: in-memory corpus, opaque IDs only (corpus_A/B/C, arg_N), no
fallacy labels, no rationale strings, no argument text — only counts and
identifiers leave the process. Artifact under the gitignored
``evaluation/results/real_analysis/``.

Usage:
    python scripts/measure_1629_attack_pairing.py --labels A B C
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Mandated routing (dispatch R1012): gpt-5.6-luna via OpenRouter ONLY.
# OPENROUTER_CHAT_MODEL_ID is the load-bearing pin: it is read FIRST by both
# resolve_active_model_id and create_llm_service when the toggle is on, and it
# is defined in NO .env file — so the project_core environment manager (which
# loads root .env AND argumentation_analysis/.env at import time with override,
# and stomps any in-process OPENAI_CHAT_MODEL_ID back to the file value) cannot
# touch it. OPENROUTER_API_KEY still comes from .env.
MANDATED_MODEL = "gpt-5.6-luna"
os.environ["OPENROUTER_BASE_URL"] = "https://openrouter.ai/api/v1"
os.environ["OPENROUTER_CHAT_MODEL_ID"] = MANDATED_MODEL
os.environ["OPENAI_CHAT_MODEL_ID"] = MANDATED_MODEL

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)

from argumentation_analysis.core.llm_service import (
    resolve_active_model_id,
)  # noqa: E402
from argumentation_analysis.core.utils.crypto_utils import (
    derive_encryption_key,
)  # noqa: E402
from argumentation_analysis.core.io_manager import (
    load_extract_definitions,
)  # noqa: E402
from argumentation_analysis.orchestration.invoke_callables import (  # noqa: E402
    _generate_attacks_from_args,
    _invoke_fact_extraction,
    _invoke_hierarchical_fallacy,
    _read_fallacy_target,
    _resolve_target_argument_index,
)

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")
MAX_CHARS = 40000


def load_corpus(label: str) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    return text[:MAX_CHARS]


def inventory_texts(extraction: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for a in extraction.get("arguments", []) if isinstance(extraction, dict) else []:
        if isinstance(a, dict) and a.get("text"):
            out.append(str(a["text"]))
        elif a:
            out.append(str(a))
    return out


def query_openrouter_key() -> Dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return {"error": "OPENROUTER_API_KEY not set"}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — reported in the artifact, not raised
        return {"error": repr(exc)}
    info = (data.get("data") or data) if isinstance(data, dict) else {}
    out: Dict[str, Any] = {}
    for field in ("limit", "usage", "limit_remaining"):
        val = info.get(field)
        out[field] = round(float(val), 4) if isinstance(val, (int, float)) else val
    return out


def pairing_metrics(fallacies: List[Any], arguments: List[str]) -> Dict[str, Any]:
    """Distribution + positional correlation, identifiers only (no text)."""
    n_args = len(arguments)
    rows: List[Dict[str, Any]] = []
    hist: Dict[str, int] = {}
    for i, f in enumerate(fallacies):
        if not isinstance(f, dict):
            continue
        raw = _read_fallacy_target(f)
        raw_class = "absent"
        if raw:
            raw_class = (
                "id_like"
                if _resolve_target_argument_index(str(raw), max(n_args, 1)) is not None
                else "other"
            )
        resolved_idx = (
            _resolve_target_argument_index(str(raw), n_args) if raw and n_args else None
        )
        pos_idx = min(i, n_args - 1) if n_args else None
        resolved_id = f"arg_{resolved_idx + 1}" if resolved_idx is not None else None
        if resolved_id:
            hist[resolved_id] = hist.get(resolved_id, 0) + 1
        rows.append(
            {
                "i": i,
                "target_raw_class": raw_class,
                "resolved": resolved_idx is not None,
                "resolved_id": resolved_id,
                "positional_id": f"arg_{pos_idx + 1}" if pos_idx is not None else None,
                "agrees_positional": (
                    resolved_idx is not None and resolved_idx == pos_idx
                ),
            }
        )
    n = len(rows)
    n_resolved = sum(1 for r in rows if r["resolved"])
    n_agree = sum(1 for r in rows if r["agrees_positional"])

    def pct(num: int, den: int) -> Optional[float]:
        return round(100.0 * num / den, 1) if den else None

    return {
        "n_fallacies": n,
        "n_arguments": n_args,
        "target_raw_class_counts": {
            k: sum(1 for r in rows if r["target_raw_class"] == k)
            for k in ("absent", "id_like", "other")
        },
        "resolved_by_id": n_resolved,
        "lexical_fallback": 0,
        "skipped": n - n_resolved,
        "pct_resolved_by_id": pct(n_resolved, n),
        "pct_lexical_fallback": pct(0, n) if n else None,
        "pct_skipped": pct(n - n_resolved, n),
        "positional_agreement": {
            "agree": n_agree,
            "among_resolved": n_resolved,
            "pct_among_resolved": pct(n_agree, n_resolved),
        },
        "resolved_target_histogram": dict(sorted(hist.items())),
        "simulated_before_on_same_detections": {
            "edges": n,
            "by_id": 0,
            "skipped": 0,
            "positional_edges": n,
            "agrees_positional_pct": 100.0 if n else None,
            "note": (
                "pre-fix behavior replayed on the SAME after-run detections: "
                "phantom keys never resolved, every fallacy paired to "
                "arguments[min(i, n-1)]"
            ),
        },
        "per_detection": rows,
    }


async def run_corpus(label: str) -> Dict[str, Any]:
    text = load_corpus(label)
    extraction = await _invoke_fact_extraction(text, {"_state_object": None})
    arguments = inventory_texts(extraction)
    # Production-shaped context: the per-argument enrichment (which attaches
    # the arg_N targets, D1a #1167) reads context["phase_extract_output"] —
    # without it the pass skips fail-loud (FB-36 #1123) and the fallacies
    # arrive orphaned, which measures a degraded path production never runs.
    context = {
        "_state_object": None,
        "phase_extract_output": extraction,
    }
    fallacy_out = await _invoke_hierarchical_fallacy(text, context)
    fallacies = (
        fallacy_out.get("fallacies", []) if isinstance(fallacy_out, dict) else []
    )
    metrics = pairing_metrics(fallacies, arguments)
    metrics["n_chars_input"] = len(text)

    def _flag(name: str) -> Any:
        return fallacy_out.get(name) if isinstance(fallacy_out, dict) else None

    extraction_method = _flag("extraction_method")
    metrics["fallacy_output_flags"] = {
        "wide_net_timed_out": _flag("wide_net_timed_out"),
        "exploration_method": _flag("exploration_method"),
        "extraction_method": extraction_method,
        "degraded": _flag("degraded"),
        "last_error": _flag("last_error"),
    }
    # Validity gate: only comparable to the documented before when the
    # per-argument pass actually ran (widenet+perarg_union).
    metrics["production_path_valid"] = (
        extraction_method == "widenet+perarg_union" and not _flag("degraded")
    )
    # Cross-check through the production path itself.
    attacks = _generate_attacks_from_args(
        arguments, {"phase_hierarchical_fallacy_output": fallacy_out}
    )
    metrics["attacks_edges_production"] = len(attacks)
    metrics["edges_match_resolved"] = len(attacks) == metrics["resolved_by_id"]
    return metrics


async def main_async(labels: List[str]) -> Dict[str, Any]:
    budget_before = query_openrouter_key()
    model_id = resolve_active_model_id()
    toggle_on = bool(
        os.environ.get("OPENROUTER_BASE_URL") and os.environ.get("OPENROUTER_API_KEY")
    )
    print(
        f"[routing] model={model_id} openrouter_toggle={'ON' if toggle_on else 'OFF'}"
    )
    if model_id != MANDATED_MODEL or not toggle_on:
        print(
            f"ABORT: mandated routing is {MANDATED_MODEL} via OpenRouter, "
            f"resolved {model_id} (toggle {'ON' if toggle_on else 'OFF'})."
        )
        return {"abort": "routing guard"}

    corpora: Dict[str, Any] = {}
    for label in labels:
        print(f"[corpus_{label}] start...", flush=True)
        try:
            corpora[label] = await run_corpus(label)
            m = corpora[label]
            print(
                f"[corpus_{label}] fallacies={m['n_fallacies']} args={m['n_arguments']} "
                f"resolved={m['resolved_by_id']} skipped={m['skipped']} "
                f"edges={m['attacks_edges_production']} match={m['edges_match_resolved']} "
                f"method={m['fallacy_output_flags']['extraction_method']} "
                f"valid={m['production_path_valid']}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 — recorded per corpus, run continues
            corpora[label] = {"error": repr(exc)}
            print(f"[corpus_{label}] ERROR {exc!r}", flush=True)

    budget_after = query_openrouter_key()
    delta = None
    if isinstance(budget_before.get("usage"), float) and isinstance(
        budget_after.get("usage"), float
    ):
        delta = round(budget_after["usage"] - budget_before["usage"], 4)
    artifact = {
        "issue": 1629,
        "purpose": "paired re-measure of fallacy->argument attack pairing (#1629)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "routing": "openrouter",
        "budget": {
            "before": budget_before,
            "after": budget_after,
            "delta_usage": delta,
        },
        "documented_before_reference": (
            "issue #1629 comments: corpus_C pre-fix carried 24 positional "
            "pairings (fallacy_i -> arg_{i+1}), 0 resolved by identifier"
        ),
        "corpora": corpora,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"measure_1629_attack_pairing_{stamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=2)
    print(f"[artifact] {out_path}")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--labels", nargs="+", default=["A", "B", "C"], choices=sorted(CORPUS_SRC_IDX)
    )
    args = parser.parse_args()
    artifact = asyncio.run(main_async(args.labels))
    if "abort" in artifact:
        sys.exit(2)


if __name__ == "__main__":
    main()
