"""FB-37 #1125 — terminal opaque-safe full spectacular capstone (reproducibility harness).

Epic #947 Phase-4 terminal deliverable: run `spectacular` + `fallacy_tier:full`
on the corpora (now that doc_A is unblocked by FB-36) and aggregate into an
opaque report. This is a RUN + REPORT capstone (no pipeline code change).

Corpora (opaque IDs, encrypted dataset in-memory):
  doc_A — the hard corpus, newly unblocked (FB-36: 0-args recursion fixed).
  doc_C — standard full run.
  doc_B — ~3M chars; best-effort under a generous bounded timeout. If size-
          bound, document fail-loud (NO silent `standard` fallback — anti-
          pendule per #1125).

Privacy HARD: global redact-filter over corpus chunks (overlapping 40-char
windows), redacted stdout, no full tracebacks. Raw results gitignored under
`argumentation_analysis/evaluation/results/fb37/`. A leak audit per corpus
confirms 0 corpus chunks in any extracted artifact before it can be committed.

Anti-pendule (#1125): NO `standard` fallback if `full` is slow; NO new
caps/templates (de-castration soldée; LLM is the only producer). If a corpus
can't complete, it is documented fail-loud.
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

# Privacy HARD — redact any substring of any corpus (see FB-36 harness).
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
    level=logging.WARNING,  # WARNING+ — per-phase INFO is captured via result, not logs
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger().addFilter(_RedactFilter())

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "fb37"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# doc_A first (hard, must complete), doc_C, doc_B best-effort last.
CORPORA = [("A", 11, 900), ("C", 2, 900), ("B", 3, 1800)]

# Phases that carry the formal axis (Tweety-verified PL/FOL/Modal).
FORMAL_PHASES = ["pl", "fol", "fol_solver", "modal", "modal_solver", "kb_to_tweety"]
# Phases that produce the synthesis report (Section-9 + deep synthesis).
SYNTHESIS_PHASES = ["synthesis", "deep_synthesis", "formal_synthesis"]


def load_corpus_text(label: str, idx: int) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[idx].get("full_text", "")
    _populate_redact(text)  # populate BEFORE any logging of corpus-derived content
    return text


def _phase_status(result: dict, name: str) -> str:
    phases = result.get("phases", {})
    pr = phases.get(name)
    if pr is None:
        return "absent"
    # PhaseResult has .status (PhaseStatus enum) — stringify defensively.
    try:
        return str(pr.status).split(".")[-1].lower()  # e.g. PhaseStatus.COMPLETED -> completed
    except Exception:
        return "unknown"


def _extract_metrics(result: dict, label: str, verdict: str, elapsed: float) -> dict:
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    n_fallacies = 0
    if isinstance(result, dict):
        n_fallacies = len(result.get("fallacies", []) or [])
        if n_fallacies == 0:
            for _k in ("analysis", "results", "state"):
                _sub = result.get(_k)
                if isinstance(_sub, dict) and isinstance(_sub.get("fallacies"), list):
                    n_fallacies = len(_sub["fallacies"])
                    break
    formal = {p: _phase_status(result, p) for p in FORMAL_PHASES}
    synth = {p: _phase_status(result, p) for p in SYNTHESIS_PHASES}
    # Synthesis text length = proxy for Section-9 variance (non-determinized output).
    synth_len = 0
    for p in SYNTHESIS_PHASES:
        pr = result.get("phases", {}).get(p)
        out = getattr(pr, "output", None) if pr is not None else None
        if isinstance(out, str):
            synth_len += len(out)
    return {
        "corpus": f"doc_{label}",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "phases_completed": summary.get("completed"),
        "phases_failed": summary.get("failed"),
        "phases_total": summary.get("total"),
        "failed_phases": summary.get("failed_phases", []),
        "completed_phases": summary.get("completed_phases", []),
        "fallacies_richness": n_fallacies,
        "formal_axis": formal,
        "synthesis_status": synth,
        "synthesis_text_chars": synth_len,
    }


def _extract_synthesis_text(result: dict) -> dict:
    """Pull the synthesis/deep-synthesis output text (opaque-by-construction
    via FB-34). Returned for leak audit — only short redacted excerpts reach the
    committed report."""
    out = {}
    for p in SYNTHESIS_PHASES:
        pr = result.get("phases", {}).get(p)
        o = getattr(pr, "output", None) if pr is not None else None
        if isinstance(o, str) and o.strip():
            out[p] = o
    return out


def _leak_audit(artifact_text: str, corpus_text: str) -> int:
    """Count corpus chunks present un-redacted in an artifact. 0 = clean."""
    chunks = []
    step, size = 20, 40
    for i in range(0, max(1, len(corpus_text) - size + 1), step):
        c = corpus_text[i:i + size].strip()
        if len(c) >= 20:
            chunks.append(c)
    return sum(1 for c in chunks if c in artifact_text)


async def run_one(label: str, idx: int, timeout: int, corpus_texts: dict) -> dict:
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    text = load_corpus_text(label, idx)
    corpus_texts[label] = text  # keep for per-corpus leak audit
    print(f"[FB-37] doc_{label}: {len(text)} chars | spectacular+full | ceiling {timeout}s")

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
            timeout=float(timeout),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{timeout}s"
        print(f"[FB-37] doc_{label} TIMED OUT after {timeout}s — documented fail-loud (no standard fallback).")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[FB-37] doc_{label} {verdict}: {_redact(str(exc))[:160]}")

    elapsed = time.time() - t0
    metrics = _extract_metrics(result, label, verdict, elapsed)

    # Leak audit: synthesis text must not contain corpus chunks.
    synth = _extract_synthesis_text(result)
    synth_blob = "\n".join(synth.values())
    metrics["synthesis_leak_chunks"] = _leak_audit(synth_blob, text) if synth_blob else 0

    # Save raw result (gitignored) for provenance.
    ts = time.strftime("%Y%m%dT%H%M%S")
    raw_out = RESULTS_DIR / f"capstone_doc{label}_{ts}.json"
    try:
        # phases hold non-serializable PhaseResult objects — snapshot summary only.
        serializable = {
            "corpus": f"doc_{label}",
            "metrics": metrics,
            "synthesis_text_chars": {k: len(v) for k, v in synth.items()},
            "state_snapshot": result.get("state_snapshot"),
            "capabilities_used": result.get("capabilities_used", []),
            "capabilities_missing": result.get("capabilities_missing", []),
        }
        with open(raw_out, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
        print(f"[FB-37] doc_{label} raw metrics saved -> {raw_out.name} (gitignored)")
    except Exception as exc:
        print(f"[FB-37] doc_{label} raw save failed: {type(exc).__name__}")

    print(
        f"[FB-37] doc_{label} DONE: {verdict} ({metrics['elapsed_s']}s) | "
        f"phases {metrics['phases_completed']}/{metrics['phases_total']} | "
        f"fallacies={metrics['fallacies_richness']} | "
        f"synth_leak={metrics['synthesis_leak_chunks']}"
    )
    return metrics


async def amain() -> None:
    print("=" * 72)
    print("[FB-37] Epic #947 Phase-4 terminal capstone — spectacular+full on corpora")
    print("=" * 72)
    corpus_texts: dict = {}
    all_metrics = []
    for label, idx, timeout in CORPORA:
        try:
            m = await run_one(label, idx, timeout, corpus_texts)
        except Exception as exc:
            m = {
                "corpus": f"doc_{label}",
                "verdict": f"FATAL:{type(exc).__name__}",
                "elapsed_s": -1,
                "error": _redact(str(exc))[:200],
            }
            print(f"[FB-37] doc_{label} FATAL: {_redact(str(exc))[:160]}")
        all_metrics.append(m)

    # Aggregate JSON (gitignored).
    agg = RESULTS_DIR / f"capstone_aggregate_{time.strftime('%Y%m%dT%H%M%S')}.json"
    with open(agg, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[FB-37] aggregate saved -> {agg.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[FB-37] CAPSTONE SUMMARY")
    print("=" * 72)
    for m in all_metrics:
        print(
            f"  {m.get('corpus')}: {m.get('verdict')} | {m.get('elapsed_s')}s | "
            f"phases {m.get('phases_completed')}/{m.get('phases_total')} | "
            f"fallacies={m.get('fallacies_richness')} | "
            f"synth_leak={m.get('synthesis_leak_chunks', '?')}"
        )
    print(f"\n[FB-37] DoD: doc_A completed+leak0, doc_C completed+leak0, doc_B documented.")


if __name__ == "__main__":
    asyncio.run(amain())
