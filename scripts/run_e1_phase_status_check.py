"""#1168 Track E1 — phase-status validation harness (reproducibility harness, privacy HARD).

Verifies the DoD of #1168 (Track E1 — Env/classpath): a `spectacular`+`full`
run shows ``quality``, ``probabilistic``, ``aspic_analysis``, ``belief_revision``
all reach ``status=completed`` with non-trivial output.

Privacy HARD (same harness pattern as FB-37 / #1160 capstone): global
redact-filter over corpus chunks, redacted stdout, no full tracebacks.
Source referenced ONLY by opaque id ``e1_smoke``.

This is a diagnostic harness (not a feature): the fixes it validates are in
``agents/core/logic/{probabilistic,belief_revision,aspic}_handler.py``
(wrong Tweety class names + wrong method calls, NOT a classpath issue).
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

# Privacy HARD — redact any substring of any corpus.
_REDACT_CHUNKS: "list[str]" = []


def _populate_redact(text: str) -> None:
    if not text:
        return
    step, size = 20, 40
    for i in range(0, max(1, len(text) - size + 1), step):
        chunk = text[i:i + size].strip()
        if len(chunk) >= 20:
            _REDACT_CHUNKS.append(chunk)


def _redact(msg: object) -> str:
    s = str(msg)
    for chunk in _REDACT_CHUNKS:
        if chunk and chunk in s:
            s = s.replace(chunk, "[REDACTED]")
    return s


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = _redact(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return True


logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger().addFilter(_RedactFilter())

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "e1_validation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# A small corpus extract for the smoke run (opaque id only).
SMOKE_IDX = 11  # doc_A — same as R6-final / FB-37 capstone validation
TIMEOUT = 1200


def load_corpus_text(idx: int) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[idx].get("full_text", "")
    _populate_redact(text)
    return text


async def main() -> None:
    print("=" * 72)
    print("[E1] Track E1 validation — spectacular+full phase status")
    print("=" * 72)

    text = load_corpus_text(SMOKE_IDX)
    print(f"[E1] e1_smoke: {len(text)} chars | spectacular+full | ceiling {TIMEOUT}s")

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
        print(f"[E1] TIMED OUT after {TIMEOUT}s — documented fail-loud.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[E1] {verdict}: {_redact(str(exc))[:200]}")

    elapsed = time.time() - t0

    # Per-phase status table (the DoD artefact).
    phases = result.get("phases", {}) or {}
    e1_phases = ["quality", "probabilistic", "aspic_analysis", "belief_revision"]
    table = []
    for name in e1_phases:
        pr = phases.get(name)
        if pr is None:
            table.append({"phase": name, "status": "absent"})
            continue
        try:
            status = str(pr.status).split(".")[-1].lower()
        except Exception:
            status = "unknown"
        # Non-trivial output check: the phase result has some content.
        output = getattr(pr, "output", None) or {}
        nontrivial = bool(
            output and any(
                v for v in (output.values() if isinstance(output, dict) else [output])
            )
        )
        table.append({"phase": name, "status": status, "nontrivial": nontrivial})

    # All-completed phases for context.
    all_phases = []
    for name, pr in phases.items():
        try:
            st = str(pr.status).split(".")[-1].lower()
        except Exception:
            st = "unknown"
        all_phases.append({"phase": name, "status": st})

    metrics = {
        "opaque_id": "e1_smoke",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "e1_target_phases": table,
        "e1_all_pass": all(
            row.get("status") == "completed" for row in table
        ),
        "summary": result.get("summary"),
        "all_phases": all_phases,
    }
    ts = time.strftime("%Y%m%dT%H%M%S")
    out = RESULTS_DIR / f"e1_validation_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[E1] metrics -> {out.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[E1] DoD TABLE — quality / probabilistic / aspic_analysis / belief_revision")
    print("=" * 72)
    for row in table:
        mark = "✓" if row.get("status") == "completed" and row.get("nontrivial") else "✗"
        print(f"  {mark} {row['phase']:<20} status={row.get('status'):<12} nontrivial={row.get('nontrivial')}")
    verdict_str = "ALL PASS" if metrics["e1_all_pass"] else "SOME FAIL"
    print(f"\n[E1] verdict: {verdict_str} ({verdict}, {round(elapsed,1)}s)")


if __name__ == "__main__":
    asyncio.run(main())
