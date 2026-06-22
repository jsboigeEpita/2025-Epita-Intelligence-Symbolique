"""#1178 DoD validation — spectacular run proving the 4 fixed reasoners wired.

Runs `spectacular`+`full` and verifies the 4 reasoners fixed in #1178
(weighted/social/qbf/cl) reach `status=completed` with non-trivial output,
plus 0 failed phases. Opaque id only; results written under a gitignored path.
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

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "r1178"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
SMOKE_IDX = 11  # corpus_A — canonical culminating-run target
TIMEOUT = 1800


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
    print("[#1178] spectacular+full — 4 fixed reasoners wired + non-trivial")
    print("=" * 72)

    text = load_corpus_text(SMOKE_IDX)
    print(f"[#1178] {len(text)} chars | ceiling {TIMEOUT}s")

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
            ),
            timeout=float(TIMEOUT),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{TIMEOUT}s"
        print(f"[#1178] TIMED OUT after {TIMEOUT}s.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[#1178] {verdict}: {str(exc)[:120]}")

    elapsed = time.time() - t0
    phases = result.get("phases", {}) or {}
    summary = result.get("summary", {}) or {}

    checklist = {}
    # The 4 reasoners fixed in #1178 must be completed + non-trivial.
    for name in ("weighted_reasoning", "social_reasoning", "qbf_reasoning", "cl_reasoning"):
        pr = phases.get(name)
        out = getattr(pr, "output", None) or {} if pr else {}
        st = _status(pr) if pr else "missing"
        checklist[f"{name}_completed"] = st == "completed"
        checklist[f"{name}_nontrivial"] = bool(
            isinstance(out, dict) and any(v for v in out.values())
        )

    checklist["zero_failed_phases"] = summary.get("failed", 1) == 0
    all_green = all(checklist.values())

    metrics = {
        "opaque_id": "r1178_check",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "checklist": checklist,
        "all_green": all_green,
        "completed_phases": summary.get("completed"),
        "failed_phases": summary.get("failed"),
        "total_phases": summary.get("total"),
    }
    ts = time.strftime("%Y%m%dT%H%M%S")
    out_path = RESULTS_DIR / f"r1178_check_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[#1178] metrics -> {out_path.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[#1178] CHECKLIST (all green = DoD)")
    print("=" * 72)
    for k, v in checklist.items():
        print(f"  {'✓' if v else '✗'} {k}")
    print(
        f"\n[#1178] verdict: {'DoD PASS' if all_green else 'PARTIAL'} "
        f"({verdict}, {round(elapsed,1)}s, {summary.get('completed')}/{summary.get('total')} phases)"
    )


if __name__ == "__main__":
    asyncio.run(main())
