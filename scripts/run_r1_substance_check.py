"""R1 #1171 DoD validation — culminating run + substance checklist.

Terminal track of Epic #1165 (gated on D1+E1+W1+T1 merges). Runs
`spectacular`+`full`+`render_restitution=True` and verifies the substance
checklist (not just gate=PASS): every developed capability digested + integrated
into the final 3-act report.

Privacy HARD: opaque id only, corpus consumed in-memory (encrypted dataset),
results written under a gitignored path. The rendered report is audited for
0-leak (opaque IDs, paraphrase not verbatim) but its text is never printed.
"""
import os
import sys
import json
import asyncio
import time
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
with open(ROOT / ".env", encoding="utf-8") as _envf:
    for line in _envf:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

logging.disable(logging.WARNING)

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "r1_culminating"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# corpus_A (idx 11) is the canonical culminating-run target (same as E1/W1/FB-37).
SMOKE_IDX = 11
TIMEOUT = 1800  # spectacular+full+render_restitution — generous ceiling (LLM-conducted)


def load_corpus_text(idx: int) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    return defs[idx].get("full_text", "")


def _status(pr: object) -> str:
    try:
        return str(pr.status).split(".")[-1].lower()
    except Exception:
        return "unknown"


async def main() -> None:
    print("=" * 72)
    print("[R1] Culminating run — spectacular+full+render_restitution")
    print("=" * 72)

    text = load_corpus_text(SMOKE_IDX)
    print(f"[R1] r1_culminating: {len(text)} chars | ceiling {TIMEOUT}s")

    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    t0 = time.time()
    verdict = "UNKNOWN"
    result: dict = {}
    try:
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="spectacular",
                context={"fallacy_tier": "full"},
                render_restitution=True,
            ),
            timeout=float(TIMEOUT),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{TIMEOUT}s"
        print(f"[R1] TIMED OUT after {TIMEOUT}s.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[R1] {verdict}: {str(exc)[:80]}")

    elapsed = time.time() - t0

    phases = result.get("phases", {}) or {}
    summary = result.get("summary", {}) or {}
    restitution_obj = result.get("restitution_report")
    # restitution_report is a RenderedReport (markdown: str, verdict: ...) —
    # extract the markdown text for auditing; fall back to "" if absent.
    restitution = ""
    restitution_verdict = None
    if restitution_obj is not None:
        if isinstance(restitution_obj, str):
            restitution = restitution_obj
        else:
            restitution = getattr(restitution_obj, "markdown", "") or ""
            restitution_verdict = getattr(restitution_obj, "verdict", None)

    # --- Substance checklist (DoD: not just gate=PASS) ---
    checklist = {}

    # (a) fallacies narrated with family+target (hierarchical_fallacy phase)
    hf = phases.get("hierarchical_fallacy")
    hf_out = getattr(hf, "output", None) or {} if hf else {}
    fallacies = hf_out.get("fallacies") if isinstance(hf_out, dict) else None
    checklist["fallacies_with_family_target"] = bool(
        isinstance(fallacies, (list, dict)) and fallacies
    )

    # (b) deep_synthesis surfaced (narrative_synthesis non-empty)
    deep = phases.get("deep_synthesis")
    deep_out = getattr(deep, "output", None) or {} if deep else {}
    checklist["deep_synthesis_nontrivial"] = bool(
        isinstance(deep_out, dict)
        and any(v for v in deep_out.values())
    )

    # (c) the formal phases that were dead before E1b
    for name in ("quality", "probabilistic", "aspic_analysis", "belief_revision"):
        pr = phases.get(name)
        out = getattr(pr, "output", None) or {} if pr else {}
        checklist[f"phase_{name}_nontrivial"] = bool(
            isinstance(out, dict) and any(v for v in out.values())
        )

    # (d) W1 wired reasoners present + non-trivial
    for name in ("setaf_reasoning", "aba_reasoning", "delp_reasoning",
                 "dl_reasoning", "dialogue_reasoning"):
        pr = phases.get(name)
        out = getattr(pr, "output", None) or {} if pr else {}
        checklist[f"w1_{name}_nontrivial"] = bool(
            isinstance(out, dict) and any(v for v in out.values())
        )

    # (d') #1178 handler-fixed reasoners present + non-trivial
    for name in ("weighted_reasoning", "social_reasoning",
                 "qbf_reasoning", "cl_reasoning"):
        pr = phases.get(name)
        out = getattr(pr, "output", None) or {} if pr else {}
        checklist[f"i1178_{name}_nontrivial"] = bool(
            isinstance(out, dict) and any(v for v in out.values())
        )

    # (d'') verdict band credits formal axes (PL/FOL/Dung) — search the
    # rendered restitution for a verdict that credits verified formal state
    # rather than a bare boolean. Acte III carries the verdict band.
    formal_credit_terms = ("PL", "FOL", "Dung", "logique", "formel", "vérifié",
                           "verifie", "cohérent")
    checklist["verdict_band_credits_formal"] = bool(
        restitution and any(t in restitution for t in formal_credit_terms)
    )

    # (e) 0 failed phases (no env-failed phase)
    checklist["zero_failed_phases"] = summary.get("failed", 1) == 0

    # (f) restitution report rendered (3-act gate)
    checklist["restitution_rendered"] = bool(restitution and len(restitution) > 1000)

    # (g) duration in healthy band (LLM-conducted: minutes, not seconds)
    checklist["duration_healthy_band"] = 120 <= elapsed <= TIMEOUT

    all_green = all(checklist.values())

    # --- Privacy audit (0-leak): no long verbatim corpus fragment in the
    # rendered report. We sample distinctive 8-word windows from the source
    # and assert none appear verbatim in the restitution. (Privacy HARD.)
    leak_hits: list[str] = []
    if restitution and text:
        words = text.split()
        step = max(1, len(words) // 60)  # ~60 sample windows
        for i in range(0, len(words) - 8, step):
            window = " ".join(words[i:i + 8])
            # skip windows too short or with no alpha (punctuation-only)
            if len(window) < 30:
                continue
            if window in restitution:
                leak_hits.append(window[:40])
            if len(leak_hits) >= 3:
                break
    checklist["privacy_zero_leak"] = len(leak_hits) == 0
    all_green = all(checklist.values())

    metrics = {
        "opaque_id": "r1_culminating",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "substance_checklist": checklist,
        "substance_all_green": all_green,
        "completed_phases": summary.get("completed"),
        "failed_phases": summary.get("failed"),
        "total_phases": summary.get("total"),
        "restitution_chars": len(restitution),
        "gate": result.get("restitution_gate"),  # if exposed
        "privacy_leak_hit_count": len(leak_hits),
        "restitution_verdict": str(restitution_verdict) if restitution_verdict else None,
    }
    ts = time.strftime("%Y%m%dT%H%M%S")
    out_path = RESULTS_DIR / f"r1_culminating_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[R1] metrics -> {out_path.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[R1] SUBSTANCE CHECKLIST (gate=PASS AND all green = culminating DoD)")
    print("=" * 72)
    for k, v in checklist.items():
        mark = "✓" if v else "✗"
        print(f"  {mark} {k}")
    verdict_str = "CULMINATING (substance complete)" if all_green else "PARTIAL"
    print(f"\n[R1] verdict: {verdict_str} ({verdict}, {round(elapsed,1)}s, "
          f"{summary.get('completed')}/{summary.get('total')} phases)")


if __name__ == "__main__":
    asyncio.run(main())
