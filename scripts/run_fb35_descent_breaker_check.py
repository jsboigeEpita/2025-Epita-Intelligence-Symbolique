"""FB-35 #1121 — descent-breaker verification (reproducibility harness — see privacy note).

v2: tests the descent DIRECTLY via ``plugin.run_guided_analysis(corpus_text)``
(the FB-30 agentic descent the breaker bounds), NOT the full invoke path. v1
called ``_invoke_hierarchical_fallacy`` in isolation, which (without the extract
phase) hit a pre-existing per-arg fallback-to-single-text RECURSION — a harness
bug, not the descent. This version exercises the real descent on the full corpus
text under a hard per-corpus ``asyncio.wait_for`` ceiling.

Verifies:
  - DoD #2: the doc_A descent COMPLETES within the call budget + timeout (no
    >2h runaway). Either it finishes naturally (< DESCENT_TOTAL_CALL_BUDGET
    calls) or the breaker trips at the budget (fail-loud partial).
  - DoD #3: doc_B / doc_C descent completes with the breaker NOT tripping
    (degraded=False → richness structurally unchanged vs main).
  - Calibration: reads ``descent_calls_made`` on every corpus to defend the
    default budget value.

Privacy HARD: corpus loaded in-memory from the encrypted dataset (opaque IDs).
No raw_text in output; per-run JSON gitignored under evaluation/results/fb35/.
Script tracked for reproducibility (FB-34 precedent).
"""
import os
import sys
import json
import asyncio
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in open(ROOT / ".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

import logging as _logging
_logging.getLogger("argumentation_analysis").setLevel(_logging.WARNING)
_logging.getLogger().setLevel(_logging.WARNING)

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "fb35"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
CORPUS_LABELS = {"A": "corpus_A", "B": "corpus_B", "C": "corpus_C"}


def load_corpus_text(label: str) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    return defs[CORPUS_SRC_IDX[label]].get("full_text", "")


def _build_plugin():
    from semantic_kernel.kernel import Kernel
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.plugins.fallacy_workflow_plugin import (
        FallacyWorkflowPlugin,
    )

    taxonomy_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "argumentation_analysis",
        "data",
        "argumentum_fallacies_taxonomy.csv",
    )
    llm = create_llm_service(service_id="fallacy_widenet", force_authentic=True)
    kernel = Kernel()
    kernel.add_service(llm)
    return FallacyWorkflowPlugin(
        master_kernel=kernel, llm_service=llm, taxonomy_file_path=taxonomy_path
    )


async def run_one_corpus(label: str) -> dict:
    from argumentation_analysis.plugins.fallacy_workflow_plugin import (
        FallacyWorkflowPlugin,
    )

    text = load_corpus_text(label)
    opaque = CORPUS_LABELS[label]
    budget = FallacyWorkflowPlugin.DESCENT_TOTAL_CALL_BUDGET
    t0 = time.time()
    plugin = _build_plugin()
    try:
        result_json = await plugin.run_guided_analysis(argument_text=text)
        result = json.loads(result_json)
    except Exception as exc:
        return {
            "corpus": opaque,
            "verdict": "ERROR",
            "elapsed_s": round(time.time() - t0, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }
    elapsed = round(time.time() - t0, 1)
    fallacies = result.get("fallacies", []) if isinstance(result, dict) else []
    return {
        "corpus": opaque,
        "verdict": "COMPLETED",
        "elapsed_s": elapsed,
        "raw_len": len(text),
        "fallacy_count": len(fallacies),
        "descent_calls_made": result.get("descent_calls_made"),
        "descent_budget_exceeded": bool(result.get("descent_budget_exceeded")),
        "exploration_method": result.get("exploration_method"),
        "budget": budget,
    }


async def amain():
    corpora = ["A", "B", "C"]
    PER_CORPUS_TIMEOUT_S = 600  # 10 min hard ceiling per corpus.
    from argumentation_analysis.plugins.fallacy_workflow_plugin import (
        FallacyWorkflowPlugin,
    )
    budget = FallacyWorkflowPlugin.DESCENT_TOTAL_CALL_BUDGET
    print(
        f"[FB-35 v2] direct-descent breaker check on {corpora} "
        f"(budget={budget} calls/invocation, per-corpus ceiling {PER_CORPUS_TIMEOUT_S}s)"
    )
    results = []
    for lbl in corpora:
        print(f"\n--- {CORPUS_LABELS[lbl]} ---")
        try:
            r = await asyncio.wait_for(
                run_one_corpus(lbl), timeout=PER_CORPUS_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            r = {
                "corpus": CORPUS_LABELS[lbl],
                "verdict": "TIMEOUT",
                "elapsed_s": PER_CORPUS_TIMEOUT_S,
                "note": f"descent exceeded {PER_CORPUS_TIMEOUT_S}s ceiling",
            }
            print(f"  TIMEOUT after {PER_CORPUS_TIMEOUT_S}s")
        print(
            f"  verdict={r.get('verdict')} elapsed={r.get('elapsed_s')}s "
            f"fallacies={r.get('fallacy_count')} calls={r.get('descent_calls_made')} "
            f"breaker_tripped={r.get('descent_budget_exceeded')} "
            f"method={r.get('exploration_method')}"
        )
        results.append(r)

    doc_a = next((r for r in results if r["corpus"] == "corpus_A"), {})
    doc_b = next((r for r in results if r["corpus"] == "corpus_B"), {})
    doc_c = next((r for r in results if r["corpus"] == "corpus_C"), {})
    dod2 = doc_a.get("verdict") == "COMPLETED"
    dod3 = (
        doc_b.get("verdict") == "COMPLETED"
        and not doc_b.get("descent_budget_exceeded")
        and doc_c.get("verdict") == "COMPLETED"
        and not doc_c.get("descent_budget_exceeded")
    )
    print(
        f"\n[FB-35] DoD item 2 (doc_A descent bounded): "
        f"{'PASS' if dod2 else 'FAIL'} ({doc_a.get('verdict')}, {doc_a.get('elapsed_s')}s, "
        f"calls={doc_a.get('descent_calls_made')}, tripped={doc_a.get('descent_budget_exceeded')})"
    )
    print(
        f"[FB-35] DoD item 3 (doc_B/C richness unchanged, no trip): "
        f"{'PASS' if dod3 else 'FAIL'} "
        f"(B calls={doc_b.get('descent_calls_made')} tripped={doc_b.get('descent_budget_exceeded')}, "
        f"C calls={doc_c.get('descent_calls_made')} tripped={doc_c.get('descent_budget_exceeded')})"
    )

    ts = time.strftime("%Y%m%dT%H%M%S")
    out = RESULTS_DIR / f"fb35_breaker_v2_{ts}.json"
    summary = {
        "corpora": corpora,
        "budget_per_invocation": budget,
        "per_corpus_ceiling_s": PER_CORPUS_TIMEOUT_S,
        "results": results,
        "dod2_doc_a_bounded": dod2,
        "dod3_bc_richness_unchanged": dod3,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[FB-35] saved {out}")


if __name__ == "__main__":
    asyncio.run(amain())
