"""R6-final #1140 — terminal restitution run (UNTRACKED, privacy HARD).

Epic #1134 terminal deliverable: run `spectacular` on a corpus, render the
readable 3-act restitution report via the new pipeline_adapter (the missing
render path wired in #1156), and resolve Finding B empirically (capture the
real `quality` phase output + status — the "spectacular = empty quality"
rumour never proven by a direct run, per #1149/#1151).

Privacy HARD (same harness as FB-37): global redact-filter over corpus chunks,
redacted stdout, no full tracebacks. Raw + readable results gitignored under
`argumentation_analysis/evaluation/results/r6final/`. A leak audit confirms 0
corpus chunks in the rendered report before it is declared clean.

Anti-pendule (#1019): the gate verdict is REPORTED HONESTLY. If the report
fails the readability gate, it is said (no curve). If the run times out, it is
documented fail-loud (no standard fallback).

Single corpus (doc_A) — richest analytical coverage post-FB-36, so the 3 acts
have substance to weave. Hard wall-clock cap.
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
for line in open(ROOT / ".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

# Privacy HARD — redact any substring of any corpus (FB-36/37 harness).
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


class _RedactStream:
    def __init__(self, stream: object) -> None:
        self._stream = stream  # type: ignore[assignment]

    def write(self, s: str) -> int:
        return self._stream.write(_redact(s))  # type: ignore[attr-defined]

    def flush(self) -> None:
        self._stream.flush()  # type: ignore[attr-defined]

    def __getattr__(self, name: str) -> object:
        return getattr(self._stream, name)


sys.stdout = _RedactStream(sys.stdout)  # type: ignore[assignment]
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger().addFilter(_RedactFilter())

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "r6final"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# doc_A = idx 11 (per FB-37 CORPORA mapping). Hard cap 1200s (FB-37 full = 532s;
# the 3 act weaves add a few LLM calls on top).
LABEL, IDX, TIMEOUT = "A", 11, 1200


def load_corpus_text() -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[IDX].get("full_text", "")
    _populate_redact(text)
    return text


def _phase_status(result: dict, name: str) -> str:
    pr = result.get("phases", {}).get(name)
    if pr is None:
        return "absent"
    try:
        return str(pr.status).split(".")[-1].lower()
    except Exception:
        return "unknown"


def _phase_output(result: dict, name: str) -> str:
    pr = result.get("phases", {}).get(name)
    out = getattr(pr, "output", None) if pr is not None else None
    return out if isinstance(out, str) else ""


def _leak_audit(artifact_text: str, corpus_text: str) -> int:
    """Count corpus chunks present un-redacted in an artifact. 0 = clean."""
    chunks = []
    step, size = 20, 40
    for i in range(0, max(1, len(corpus_text) - size + 1), step):
        c = corpus_text[i:i + size].strip()
        if len(c) >= 20:
            chunks.append(c)
    return sum(1 for c in chunks if c in artifact_text)


async def amain() -> None:
    print("=" * 72)
    print(f"[R6-FINAL] spectacular on doc_{LABEL} → readable 3-act report + Finding B")
    print("=" * 72)

    text = load_corpus_text()
    print(f"[R6-FINAL] doc_{LABEL}: {len(text)} chars | spectacular+full | ceiling {TIMEOUT}s")

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
                render_restitution=True,  # the wiring (#1156) — report attached to result
            ),
            timeout=float(TIMEOUT),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{TIMEOUT}s"
        print(f"[R6-FINAL] doc_{LABEL} TIMED OUT after {TIMEOUT}s — documented fail-loud.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[R6-FINAL] doc_{LABEL} {verdict}: {_redact(str(exc))[:200]}")

    elapsed = time.time() - t0
    ts = time.strftime("%Y%m%dT%H%M%S")

    # ── Finding B: the real quality phase output + status ───────────────
    quality_status = _phase_status(result, "quality")
    quality_out = _phase_output(result, "quality")
    quality_out_chars = len(quality_out)
    snap = result.get("state_snapshot") or {}
    quality_count = snap.get("quality_scores_count", "?")
    fallacy_count = snap.get("fallacy_count", "?")
    arg_count = snap.get("argument_count", "?")
    finding_b_empty = (quality_count == 0) if isinstance(quality_count, int) else None

    print(
        f"[R6-FINAL] Finding B — quality phase: status={quality_status} | "
        f"output_chars={quality_out_chars} | snapshot quality_scores_count={quality_count} | "
        f"EMPTY={'YES' if finding_b_empty else 'NO' if finding_b_empty is False else '?'}"
    )

    # ── The readable report (the Epic terminal deliverable) ─────────────
    report_md = ""
    gate_band = "N/A"
    gate_reasons: list = []
    report_obj = result.get("restitution_report")
    if report_obj is not None:
        report_md = getattr(report_obj, "markdown", "") or ""
        gv = getattr(report_obj, "verdict", None)
        if gv is not None:
            gate_band = getattr(gv, "band", "N/A")
            gate_reasons = list(getattr(gv, "reasons", []) or [])

    # Leak audit on the rendered report body.
    leak = _leak_audit(report_md, text) if report_md else -1

    # Write the readable report (gitignored).
    if report_md:
        report_path = RESULTS_DIR / f"restitution_doc{LABEL}_{ts}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[R6-FINAL] readable report -> {report_path.name} (gitignored, {len(report_md)} chars)")

    # Write the metrics + Finding B fact (gitignored).
    metrics = {
        "corpus": f"doc_{LABEL}",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "phases_completed": (result.get("summary") or {}).get("completed"),
        "phases_failed": (result.get("summary") or {}).get("failed"),
        "phases_total": (result.get("summary") or {}).get("total"),
        "argument_count": arg_count,
        "fallacy_count": fallacy_count,
        "finding_b": {
            "quality_phase_status": quality_status,
            "quality_output_chars": quality_out_chars,
            "quality_scores_count": quality_count,
            "is_empty": finding_b_empty,
        },
        "gate": {
            "band": gate_band,
            "reasons": gate_reasons,
        },
        "report_chars": len(report_md),
        "report_leak_chunks": leak,
    }
    metrics_path = RESULTS_DIR / f"restitution_doc{LABEL}_metrics_{ts}.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[R6-FINAL] metrics -> {metrics_path.name} (gitignored)")

    # Acts presence (did the 3 act phases populate state?).
    state = result.get("unified_state")
    acts_present = {}
    if state is not None:
        for k in ("act1_framing", "act2_narrative", "act3_conclusion"):
            v = getattr(state, k, "")
            acts_present[k] = len(v) if isinstance(v, str) else 0

    print("\n" + "=" * 72)
    print(f"[R6-FINAL] SUMMARY — doc_{LABEL}")
    print("=" * 72)
    print(f"  run: {verdict} ({round(elapsed,1)}s) | phases {(result.get('summary') or {}).get('completed')}/{(result.get('summary') or {}).get('total')}")
    print(f"  args={arg_count} | fallacies={fallacy_count}")
    print(f"  acts present: {acts_present}")
    print(f"  Finding B: quality status={quality_status} count={quality_count} EMPTY={'YES' if finding_b_empty else 'NO' if finding_b_empty is False else '?'}")
    print(f"  report: {len(report_md)} chars | gate={gate_band} | leak_chunks={leak}")
    if gate_reasons:
        print(f"  gate reasons: {gate_reasons[:3]}")


if __name__ == "__main__":
    asyncio.run(amain())
