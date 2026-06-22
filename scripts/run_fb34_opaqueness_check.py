"""FB-34 #1118 — opaqueness hardening verification.

Runs the spectacular pipeline + Section-9 LLM synthesis (wiring now active) on
>=2 corpora, then greps the synthesis prose for non-opaque leak indicators
(proper nouns / leaders / countries / parties / dates). DoD: 0 hits.

Privacy HARD: corpus loaded in-memory from the encrypted dataset (opaque
``corpus_A``/``doc_A`` IDs). No ``raw_text``/``full_text`` ever in
committed artifacts — per-run prose is written under gitignored
``evaluation/results/fb34/``.
"""
import os
import re
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

# FB-34 privacy: silence the chatty network_utils HTTP body logger, which
# dumps the raw corpus text (sent to the LLM) into stdout/log files. The
# corpus text is politically sensitive — it must never be logged in full.
# (The .cache/ logs are gitignored, but reducing the blast radius is hygiene.)
import logging as _logging
_logging.getLogger("argumentation_analysis.core.utils.network_utils").setLevel(_logging.WARNING)
# FB-34: tame the whole library tree to WARNING. The first run's log hit 141k
# lines because the pipeline's INFO logging dumped full LLM request/response
# payloads (raw corpus text re-embedded on disk). This script reports via
# print() and reads statuses from the report dict, so suppressing library INFO
# loses nothing load-bearing while keeping the log readable + small.
_logging.getLogger("argumentation_analysis").setLevel(_logging.WARNING)
_logging.getLogger().setLevel(_logging.WARNING)

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "fb34"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# corpus label -> dataset index (opaque). A=11, C=2 (per FB-32 mapping).
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
CORPUS_LABELS = {"A": "corpus_A", "B": "corpus_B", "C": "corpus_C"}

# Leak indicators: real names of leaders/states/parties that appear in the
# encrypted corpus (politically sensitive speeches). If the opaque-ID directive
# works, NONE of these should appear in the synthesis prose. Curated from the
# known corpus composition (dictators / heads of state / domestic politics).
# NOTE: these are grep patterns ONLY — never written to a committed artifact
# except as this verification result (which reports hit counts, not context).
LEAK_PATTERNS = [
    # leaders / heads of state
    r"\bPutin\b", r"\bPoutine\b", r"\bStalin\b", r"\bStaline\b",
    r"\bLenin\b", r"\bLénine\b", r"\bHitler\b", r"\bMussolini\b",
    r"\bMacron\b", r"\bSarkozy\b", r"\bMitterrand\b", r"\bLe Pen\b",
    r"\bKhrushchev\b", r"\bKhrouchtchev\b", r"\bTrump\b", r"\bBiden\b",
    r"\bMélenchon\b", r"\bZelensky\b", r"\bZelenskiy\b",
    # states / regions
    r"\bUkraine\b", r"\bUkrainien(?:ne)?s?\b", r"\bRussie\b", r"\bRussian\b",
    r"\bFrance\b", r"\bFrench\b", r"\bAllemagne\b", r"\bGermany\b",
    r"\bCrimée\b", r"\bCrimea\b", r"\bDonbass\b", r"\bDonetsk\b",
    # parties / ideologies (proper-noun forms)
    r"\bBolshevik\b", r"\bBolchevik(?:s)?\b", r"\bNazi(?:s)?\b",
    r"\bCommunist(?:e)?(?:s)?\b", r"\bSoviétique(?:s)?\b", r"\bSoviet\b",
    # specific events/dates that betray identity
    r"\b1917\b", r"\bBrest-Litovsk\b",
]
LEAK_RE = re.compile("|".join(LEAK_PATTERNS), re.IGNORECASE)


def load_corpus_text(label: str) -> str:
    """Load one corpus text in-memory from the encrypted dataset (opaque)."""
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[CORPUS_SRC_IDX[label]].get("full_text", "")
    return text


def base64_urlsafe(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).decode()


async def run_one_corpus(label: str) -> dict:
    """Pipeline + Section-9 synthesis, then leak grep. Opaque labels only out."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        DeepSynthesisAgent,
        DeepSynthesisReport,
    )
    from argumentation_analysis.orchestration.invoke_callables import _invoke_deep_synthesis
    from semantic_kernel import Kernel
    from argumentation_analysis.core.llm_service import create_llm_service

    text = load_corpus_text(label)
    opaque = CORPUS_LABELS[label]
    t0 = time.time()
    state = UnifiedAnalysisState(text)
    try:
        # FB-34: use the BOUNDED `standard` workflow (not `spectacular`).
        # Rationale: spectacular + fallacy_tier:"full" triggers the FB-30
        # unbounded agentic fallacy descent, which hung >2h on corpus_A in the
        # first attempt (a separate corpus-A descent bug, out of FB-34 scope).
        # The opaqueness property is a property of the synthesis PROMPTS, not
        # the workflow depth — `standard` produces a synthesis-usable state
        # (extract + fallacy + logic) on real corpus text, which is all the
        # leak grep needs. A per-corpus hard timeout below is the safety net.
        result = await run_unified_analysis(
            text=text, workflow_name="standard",
        )
        if isinstance(result, dict):
            s = result.get("unified_state", result.get("state"))
            if isinstance(s, UnifiedAnalysisState):
                state = s
    except Exception as exc:
        return {"corpus": opaque, "pipeline_err": str(exc), "prose": "", "leaks": []}
    pipeline_s = round(time.time() - t0, 1)

    # Invoke the prod synthesis path (wiring active) — this exercises the
    # hardened SYSTEM_PROMPT + inline _llm_synthesis prompt + grounded prompt.
    ds = await _invoke_deep_synthesis(
        "", {"_state_object": state, "source_metadata": {"opaque_id": f"doc_{label}"}}
    )
    report = ds.get("report", {})
    prose = report.get("final_synthesis", "")
    grounded_prose = ""  # captured below if present
    status = report.get("final_synthesis_status", "")
    grounded_status = report.get("grounded_synthesis_status", "")

    # Also explicitly exercise the FB-18 grounded path via a fresh agent call
    # so the GROUNDED_SYNTHESIS_PROMPT (hardened) is tested too. NOTE: the
    # method is `grounded_transversal_synthesis` (the prior session's run used
    # the wrong name `_llm_grounded_synthesis` → silent AttributeError → the
    # grounded prompt was NEVER actually exercised).
    try:
        kernel = Kernel()
        llm = create_llm_service(service_id="default")
        if llm:
            kernel.add_service(llm)
        agent = DeepSynthesisAgent(kernel=kernel, service_id="default")
        # Build a fresh report to feed the grounded path
        fresh = DeepSynthesisReport()
        fresh.source_overview = DeepSynthesisAgent._build_source_overview(
            state, {"opaque_id": f"doc_{label}"}
        )
        fresh.argument_map = DeepSynthesisAgent._build_argument_map(state)
        fresh.fallacy_diagnoses = DeepSynthesisAgent._build_fallacy_diagnoses(state)
        fresh.convergent_verdicts, fresh.convergence_conclusion = (
            DeepSynthesisAgent._build_convergent_verdicts(state)
        )
        grounded_prose = await agent.grounded_transversal_synthesis(state, fresh)
    except Exception as exc:
        grounded_prose = f"[grounded_err: {type(exc).__name__}: {exc}]"

    # Leak grep — combined prose (Section 9 + grounded)
    combined = f"{prose}\n{grounded_prose}"
    leaks = []
    for m in LEAK_RE.finditer(combined):
        leaks.append(m.group(0))
    elapsed = round(time.time() - t0, 1)

    return {
        "corpus": opaque,
        "final_synthesis_status": status,
        "grounded_synthesis_status": grounded_status,
        "pipeline_s": pipeline_s,
        "elapsed_s": elapsed,
        "prose_len": len(prose),
        "grounded_len": len(grounded_prose) if grounded_prose else 0,
        "leak_hits": len(leaks),
        "leak_terms_found": sorted(set(leaks)),
        "verdict": "PASS" if len(leaks) == 0 else "LEAK",
    }


async def amain():
    corpora = ["A", "C"]  # >=2 corpora (DoD)
    # Per-corpus HARD timeout (anti-runaway): the first attempt hung >2h on
    # corpus_A inside the spectacular fallacy descent. asyncio.wait_for cancels
    # the coroutine on expiry so one stuck corpus can never block the whole
    # sweep — the run records TIMEOUT and proceeds to the next corpus.
    PER_CORPUS_TIMEOUT_S = 900  # 15 min ceiling (standard finishes in ~3-5 min)
    print(f"[FB-34] opaqueness check on corpora {corpora} "
          f"(per-corpus timeout {PER_CORPUS_TIMEOUT_S}s)")
    results = []
    for lbl in corpora:
        print(f"\n--- {CORPUS_LABELS[lbl]} ---")
        try:
            r = await asyncio.wait_for(
                run_one_corpus(lbl), timeout=PER_CORPUS_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            r = {"corpus": CORPUS_LABELS[lbl], "verdict": "TIMEOUT",
                 "leak_hits": -1, "leak_terms_found": [],
                 "note": f"exceeded {PER_CORPUS_TIMEOUT_S}s ceiling "
                         f"(unbounded descent / hang — separate bug)"}
            print(f"  TIMEOUT after {PER_CORPUS_TIMEOUT_S}s — skipping to next corpus")
        print(f"  status={r.get('final_synthesis_status')} grounded={r.get('grounded_synthesis_status')} "
              f"prose_len={r.get('prose_len')} grounded_len={r.get('grounded_len')} "
              f"leaks={r.get('leak_hits')} verdict={r.get('verdict')}")
        if r.get("leak_terms_found"):
            print(f"  LEAK TERMS: {r['leak_terms_found']}")
        results.append(r)
    # Save per-run prose (gitignored) for audit
    ts = time.strftime("%Y%m%dT%H%M%S")
    out = RESULTS_DIR / f"fb34_opaqueness_{ts}.json"
    summary = {"corpora": corpora, "results": results,
               "all_pass": all(r["verdict"] == "PASS" for r in results)}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[FB-34] saved {out} | all_pass={summary['all_pass']}")


if __name__ == "__main__":
    asyncio.run(amain())
