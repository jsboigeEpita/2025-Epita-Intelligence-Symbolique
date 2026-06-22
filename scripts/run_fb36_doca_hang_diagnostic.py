"""FB-36 #1123 — doc_A spectacular+full hang diagnostic (reproducibility harness).

Goal: NAME which phase hangs on doc_A spectacular+full (DoD item 1: wall-clock
evidence), and confirm/refute the latent recursion hypothesis. Bounded run only
(hard asyncio.wait_for ceiling) — never an unbounded >2h run.

Three probes:
  1. ``_extract_arguments_for_parallel`` — log which Sources are available in a
     REAL spectacular run (``_state_object``? ``phase_extract_output``? ``\\n\\n``?).
     This directly answers whether the per-arg recursion (invoke_callables.py
     ~L3932: 0 args -> recurse) fires in production.
  2. ``_invoke_hierarchical_fallacy`` entry counter — recursion smoking gun if
     it enters >1 time for one analysis (each cycle re-runs the wide-net).
  3. Per-phase wall-clock via structured "Phase completed" log lines.

Privacy HARD: doc_A loaded in-memory from the encrypted dataset (opaque ID).
No raw_text in output. Diagnostic JSON gitignored under evaluation/results/fb36/.
Script tracked for reproducibility (FB-34/FB-35 precedent — references the encrypted dataset path).
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

# Privacy HARD (FB-36 #1123): raw corpus text must NEVER reach stdout/log
# (prior run leaked it via APIConnectionError tracebacks that embed the prompt).
# Redact ANY substring of the corpus: overlapping 40-char windows (stride 20) so
# every >20-char span matches. Populated by load_corpus_text once decrypted.
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
    """Wrap stdout so direct prints are redacted too."""

    def __init__(self, stream: object) -> None:
        self._stream = stream  # type: ignore[assignment]

    def write(self, s: str) -> int:
        return self._stream.write(_redact(s))  # type: ignore[attr-defined]

    def flush(self) -> None:
        self._stream.flush()  # type: ignore[attr-defined]

    def __getattr__(self, name: str) -> object:
        return getattr(self._stream, name)


sys.stdout = _RedactStream(sys.stdout)  # type: ignore[assignment]

# Capture EVERYTHING for per-phase evidence (redact filter strips corpus).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger().addFilter(_RedactFilter())

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "fb36"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

_PROBE = {
    "extract_args_calls": [],
    "hierarchical_entries": 0,
    "hierarchical_entry_times": [],
    "fallback_messages": 0,
    "phase_completed": [],
}


def _install_probes():
    """Monkeypatch the two functions to capture diagnostic evidence."""
    import argumentation_analysis.orchestration.invoke_callables as ic

    _orig_extract = ic._extract_arguments_for_parallel

    def _probe_extract(input_text, context):
        has_state = bool(context.get("_state_object"))
        state_args = None
        if has_state:
            so = context.get("_state_object")
            ia = getattr(so, "identified_arguments", None)
            state_args = len(ia) if isinstance(ia, dict) else None
        peo = context.get("phase_extract_output")
        peo_args = (
            len(peo.get("arguments", []))
            if isinstance(peo, dict)
            else None
        )
        n_paras = len([p for p in input_text.split("\n\n") if p.strip()])
        result = _orig_extract(input_text, context)
        _PROBE["extract_args_calls"].append(
            {
                "has_state_object": has_state,
                "state_identified_args": state_args,
                "phase_extract_output_args": peo_args,
                "n_paragraph_splits": n_paras,
                "returned_args": len(result),
                "WILL_RECURSE": len(result) == 0,
            }
        )
        return result

    _orig_hier = ic._invoke_hierarchical_fallacy

    async def _probe_hier(input_text, context):
        _PROBE["hierarchical_entries"] += 1
        _PROBE["hierarchical_entry_times"].append(time.time())
        # Recursion abort: if _invoke_hierarchical_fallacy re-enters 3+ times
        # within one analysis, the per-arg 0-args fallback is recursing back
        # into it. Abort DEFINITIVELY + cheaply rather than loop until timeout.
        if _PROBE["hierarchical_entries"] >= 3:
            raise RuntimeError(
                "FB-36 RECURSION_ABORT: _invoke_hierarchical_fallacy re-entered "
                f"{_PROBE['hierarchical_entries']}x — per-arg 0-args fallback "
                "recurses (the >2h hang root cause)"
            )
        return await _orig_hier(input_text, context)

    # Count "falling back to single-text" log lines via the logger.
    class _FallbackFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            if "falling back to single-text analysis" in msg:
                _PROBE["fallback_messages"] += 1
            if "Phase completed" in msg:
                _PROBE["phase_completed"].append(msg)
            return True

    logging.getLogger().addFilter(_FallbackFilter())

    ic._extract_arguments_for_parallel = _probe_extract
    ic._invoke_hierarchical_fallacy = _probe_hier
    print("[FB-36 probe] probes installed")


def load_corpus_text(label: str) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    # corpus_A = idx 11 (matches FB-35 harness)
    idx = {"A": 11, "B": 3, "C": 2}[label]
    text = defs[idx].get("full_text", "")
    _populate_redact(text)  # populate redaction windows BEFORE any logging
    return text


async def amain():
    _install_probes()
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    label = sys.argv[1] if len(sys.argv) > 1 else "A"
    text = load_corpus_text(label)
    print(f"[FB-36] doc_{label} loaded: {len(text)} chars")
    print("[FB-36] running spectacular + fallacy_tier:full under 900s hard ceiling...")

    t0 = time.time()
    verdict = "UNKNOWN"
    try:
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="spectacular",
                context={"fallacy_tier": "full"},
            ),
            timeout=900.0,
        )
        verdict = "COMPLETED"
        summary = result.get("summary", {}) if isinstance(result, dict) else {}
        # Richness probe for DoD-5 (fallacies come from the wide-net, untouched
        # by the FB-36 fix; a non-zero count proves richness survived).
        n_fallacies = 0
        if isinstance(result, dict):
            n_fallacies = len(result.get("fallacies", []) or [])
            if n_fallacies == 0:
                # nested under analysis/results key sometimes
                for _k in ("analysis", "results", "state"):
                    _sub = result.get(_k)
                    if isinstance(_sub, dict) and isinstance(
                        _sub.get("fallacies"), list
                    ):
                        n_fallacies = len(_sub["fallacies"])
                        break
        print(
            f"[FB-36] COMPLETED in {round(time.time()-t0,1)}s. "
            f"fallacies={n_fallacies} phases_done={summary.get('completed','?')}"
        )
    except asyncio.TimeoutError:
        verdict = "TIMED_OUT_900s"
        print(f"[FB-36] TIMED OUT after 900s — hang confirmed.")
    except Exception as exc:
        # NO full traceback (privacy: tracebacks embed the prompt). Redact the
        # message in case the provider echoed request content into the error.
        verdict = f"ERROR: {type(exc).__name__}: {_redact(str(exc))[:200]}"
        print(f"[FB-36] {verdict}")

    elapsed = round(time.time() - t0, 1)

    # Recursion smoking gun: hierarchical_entries > 1 with 0-arg extract calls.
    recursion_confirmed = (
        _PROBE["hierarchical_entries"] > 1
        and any(c["WILL_RECURSE"] for c in _PROBE["extract_args_calls"])
    )

    print("\n" + "=" * 70)
    print("[FB-36] DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print(f"verdict: {verdict}  (elapsed {elapsed}s)")
    print(f"_invoke_hierarchical_fallacy entries: {_PROBE['hierarchical_entries']}")
    print(f"'falling back to single-text' messages: {_PROBE['fallback_messages']}")
    print(f"_extract_arguments_for_parallel calls: {len(_PROBE['extract_args_calls'])}")
    for i, c in enumerate(_PROBE["extract_args_calls"]):
        print(f"  call#{i}: {c}")
    print(f"phase_completed log lines: {len(_PROBE['phase_completed'])}")
    for p in _PROBE["phase_completed"][-12:]:
        print(f"  {p}")
    print(
        f"\n>>> RECURSION CONFIRMED: {recursion_confirmed} "
        f"(hierarchical_entries>1 AND a 0-arg extract call)"
    )

    ts = time.strftime("%Y%m%dT%H%M%S")
    out = RESULTS_DIR / f"fb36_diag_{label}_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "corpus": f"doc_{label}",
                "workflow": "spectacular+full",
                "verdict": verdict,
                "elapsed_s": elapsed,
                "hierarchical_entries": _PROBE["hierarchical_entries"],
                "fallback_messages": _PROBE["fallback_messages"],
                "extract_args_calls": _PROBE["extract_args_calls"],
                "phase_completed_tail": _PROBE["phase_completed"][-20:],
                "recursion_confirmed": recursion_confirmed,
            },
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    print(f"\n[FB-36] saved {out}")


if __name__ == "__main__":
    asyncio.run(amain())
