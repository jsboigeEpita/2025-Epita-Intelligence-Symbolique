"""W1 #1169 DoD validation — spectacular+full phase status for newly-wired reasoners.

Diagnostic harness (not a feature). Validates that the 5 Dung-family/logic
reasoners wired into ``spectacular`` by W1 (#1169) produce non-trivial state,
and that the 3 formerly-hollow phases (modal/neural_detect/tweety_interpretation)
now report fail-loud status instead of silent skeletons.

Privacy HARD: opaque id only, corpus consumed in-memory (encrypted dataset),
results written under a gitignored path.
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

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "w1_validation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

SMOKE_IDX = 11  # doc_A
TIMEOUT = 1500  # spectacular+full + 5 new reasoners — generous ceiling

# The 5 reasoners wired by W1 (capability names).
W1_WIRED = ["setaf_reasoning", "aba_reasoning", "delp_reasoning",
            "dl_reasoning", "dialogue_reasoning"]
# 3 formerly-hollow phases — must NOT emit a silent skeleton.
W1_HOLLOW = ["modal", "neural_detect", "tweety_interpretation"]


def _redact(s: str) -> str:
    return s[:60]


def load_corpus_text(idx: int) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[idx].get("full_text", "")
    return text


async def main() -> None:
    print("=" * 72)
    print("[W1] Track W1 validation — spectacular+full reasoner status")
    print("=" * 72)

    text = load_corpus_text(SMOKE_IDX)
    print(f"[W1] w1_smoke: {len(text)} chars | spectacular+full | ceiling {TIMEOUT}s")

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
                render_restitution=False,
            ),
            timeout=float(TIMEOUT),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{TIMEOUT}s"
        print(f"[W1] TIMED OUT after {TIMEOUT}s.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[W1] {verdict}: {_redact(str(exc))}")

    elapsed = time.time() - t0

    phases = result.get("phases", {}) or {}

    def _status(pr: object) -> str:
        try:
            return str(pr.status).split(".")[-1].lower()
        except Exception:
            return "unknown"

    # W1 wired reasoners: completed + non-trivial is the win.
    wired_table = []
    for name in W1_WIRED:
        pr = phases.get(name)
        if pr is None:
            wired_table.append({"phase": name, "status": "absent"})
            continue
        output = getattr(pr, "output", None) or {}
        nontrivial = bool(
            output and any(
                v for v in (output.values() if isinstance(output, dict) else [output])
            )
        )
        wired_table.append({
            "phase": name, "status": _status(pr), "nontrivial": nontrivial,
        })

    # Hollow phases: must NOT be a silent skeleton. A phase is "honest" if it
    # either completed with real output OR reports an explicit unavailable/
    # degraded status (not a fake non-empty skeleton presented as a result).
    hollow_table = []
    for name in W1_HOLLOW:
        pr = phases.get(name)
        if pr is None:
            hollow_table.append({"phase": name, "status": "absent"})
            continue
        st = _status(pr)
        output = getattr(pr, "output", None) or {}
        # A fail-loud hollow phase carries a status="unavailable"/"degraded"
        # marker OR is empty (no fake content).
        has_status_marker = isinstance(output, dict) and output.get("status") in (
            "unavailable", "degraded", "ok",
        )
        hollow_table.append({
            "phase": name, "status": st,
            "output_status": output.get("status") if isinstance(output, dict) else None,
            "honest": has_status_marker or st != "completed",
        })

    metrics = {
        "opaque_id": "w1_smoke",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "w1_wired_phases": wired_table,
        "w1_hollow_phases": hollow_table,
        "w1_wired_pass": all(
            row.get("status") == "completed" and row.get("nontrivial")
            for row in wired_table
        ),
        "w1_hollow_honest": all(
            row.get("honest") for row in hollow_table
        ),
        "summary": result.get("summary"),
    }
    ts = time.strftime("%Y%m%dT%H%M%S")
    out = RESULTS_DIR / f"w1_validation_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[W1] metrics -> {out.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[W1] WIRED REASONERS (completed + non-trivial = PASS)")
    print("=" * 72)
    for row in wired_table:
        mark = "✓" if row.get("status") == "completed" and row.get("nontrivial") else "✗"
        print(f"  {mark} {row['phase']:<22} status={row.get('status'):<12} nontrivial={row.get('nontrivial')}")
    print("\n[W1] HOLLOW PHASES (must be fail-loud, not silent skeleton)")
    for row in hollow_table:
        mark = "✓" if row.get("honest") else "✗"
        print(f"  {mark} {row['phase']:<22} status={row.get('status'):<12} out_status={row.get('output_status')}")

    vp = "PASS" if metrics["w1_wired_pass"] else "PARTIAL"
    hp = "HONEST" if metrics["w1_hollow_honest"] else "SILENT-SKELETON"
    print(f"\n[W1] verdict: wired={vp} | hollow={hp} ({verdict}, {round(elapsed,1)}s)")


if __name__ == "__main__":
    asyncio.run(main())
