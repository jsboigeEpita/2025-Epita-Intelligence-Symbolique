"""#1160 capstone — virtuous-text restitution end-to-end (UNTRACKED, privacy HARD).

Epic #1134 closing capstone: run `spectacular` on a genuinely virtuous speech
(a historically-celebrated one from the corpus), render the 3-act restitution
via the #1156 wiring, and prove the virtuous mode (#1157) fires — Acte III
titles on the measured virtues, not on the absence of fallacies. Gate PASS.

Privacy HARD (same harness as FB-37 / r6final): global redact-filter over corpus
chunks, redacted stdout, no full tracebacks. Source is referenced ONLY by an
opaque id (``virtuous_speech_N``) in every log, metric, and the committable
aggregate — never the real speaker name / title / date. The readable report
stays gitignored.

Anti-pendule (#1019): the virtuous verdict is REPORTED HONESTLY via
``detect_virtuous_mode`` — derived from pipeline output, never asserted. If the
speech turns out non-virtuous (e.g. the detector finds localized fallacies), it
is said (no curve). The corpus scan (#1161) only surfaced low-lexical-signal
candidates (false positives per #1146); genuinely virtuous speeches were
excluded by the lexical screen — this run targets a historically-virtuous
speech directly.
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

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "virtuous_capstone"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# Candidate: a historically-celebrated virtuous speech, smallest viable size.
# Referred to ONLY by opaque id below — never the real name in output.
# idx is the dataset index of the chosen speech.
CANDIDATES = [
    {"opaque_id": "virtuous_speech_1", "idx": 15, "timeout": 900},   # smallest virtuous
    {"opaque_id": "virtuous_speech_2", "idx": 14, "timeout": 1100},  # second virtuous
]


def load_corpus_text(idx: int) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[idx].get("full_text", "")
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


def _leak_audit(artifact_text: str, corpus_text: str) -> int:
    chunks = []
    step, size = 20, 40
    for i in range(0, max(1, len(corpus_text) - size + 1), step):
        c = corpus_text[i:i + size].strip()
        if len(c) >= 20:
            chunks.append(c)
    return sum(1 for c in chunks if c in artifact_text)


async def run_one(opaque_id: str, idx: int, timeout: int) -> dict:
    text = load_corpus_text(idx)
    print(f"[CAPSTONE] {opaque_id}: {len(text)} chars | spectacular+full | ceiling {timeout}s")

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
            timeout=float(timeout),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{timeout}s"
        print(f"[CAPSTONE] {opaque_id} TIMED OUT after {timeout}s — documented fail-loud.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[CAPSTONE] {opaque_id} {verdict}: {_redact(str(exc))[:200]}")

    elapsed = time.time() - t0

    # ── Virtuous mode (the DERIVED flag, #1157) ─────────────────────────
    state = result.get("unified_state")
    virtuous_assessment: dict = {}
    if state is not None:
        try:
            from argumentation_analysis.reporting.restitution.virtuous_identification import (
                detect_virtuous_mode,
            )
            vm = detect_virtuous_mode(state)
            virtuous_assessment = {
                "is_virtuous": vm.is_virtuous,
                "fallacy_count": vm.fallacy_count,
                "quality_virtues_present": vm.quality_virtues_present,
                "formal_holds": vm.formal_holds,
                "reasoning": _redact(vm.reasoning),
            }
        except Exception as exc:
            virtuous_assessment = {"error": type(exc).__name__}

    # ── The readable report ─────────────────────────────────────────────
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

    leak = _leak_audit(report_md, text) if report_md else -1
    snap = result.get("state_snapshot") or {}

    ts = time.strftime("%Y%m%dT%H%M%S")
    if report_md:
        report_path = RESULTS_DIR / f"restitution_{opaque_id}_{ts}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[CAPSTONE] {opaque_id} readable report -> {report_path.name} (gitignored, {len(report_md)} chars)")

    # Does Acte III title on virtues? (opaque structural check — no names/leak).
    # Real signal: in Acte III, the strengths header must PRECEDE the weaknesses
    # header (virtues led, not fallacies) — verified by index order on the two
    # headers the plugin actually emits, not on a bare literal that could match
    # anywhere. NB: these headers come from the plugin (generated), not corpus.
    act3_titled_virtues = False
    if report_md:
        strengths_idx = report_md.find("### Ce qui tient")
        weaknesses_idx = report_md.find("### Ce qui dérape")
        act3_titled_virtues = strengths_idx >= 0 and weaknesses_idx >= 0 and strengths_idx < weaknesses_idx

    metrics = {
        "opaque_id": opaque_id,
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "phases_completed": (result.get("summary") or {}).get("completed"),
        "phases_total": (result.get("summary") or {}).get("total"),
        "argument_count": snap.get("argument_count", "?"),
        "fallacy_count": snap.get("fallacy_count", "?"),
        "quality_scores_count": snap.get("quality_scores_count", "?"),
        "virtuous_mode": virtuous_assessment,
        "act3_titles_virtues": act3_titled_virtues,
        "gate": {"band": gate_band, "reasons": gate_reasons},
        "report_chars": len(report_md),
        "report_leak_chunks": leak,
    }
    metrics_path = RESULTS_DIR / f"{opaque_id}_metrics_{ts}.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[CAPSTONE] {opaque_id} metrics -> {metrics_path.name} (gitignored)")

    print(
        f"[CAPSTONE] {opaque_id} DONE: {verdict} ({round(elapsed,1)}s) | "
        f"phases {metrics['phases_completed']}/{metrics['phases_total']} | "
        f"args={metrics['argument_count']} fallacies={metrics['fallacy_count']} | "
        f"virtuous={virtuous_assessment.get('is_virtuous')} | "
        f"act3_virtues={act3_titled_virtues} | gate={gate_band} | leak={leak}"
    )
    return metrics


async def amain() -> None:
    print("=" * 72)
    print("[CAPSTONE] Epic #1134 virtuous-text restitution — spectacular + render")
    print("=" * 72)
    all_metrics = []
    for c in CANDIDATES:
        try:
            m = await run_one(c["opaque_id"], c["idx"], c["timeout"])
        except Exception as exc:
            m = {"opaque_id": c["opaque_id"], "verdict": f"FATAL:{type(exc).__name__}",
                 "error": _redact(str(exc))[:200]}
            print(f"[CAPSTONE] {c['opaque_id']} FATAL: {_redact(str(exc))[:160]}")
        all_metrics.append(m)
        # Early-exit the second candidate if the first is already virtuous (save budget).
        if m.get("virtuous_mode", {}).get("is_virtuous") is True:
            print(f"[CAPSTONE] {m['opaque_id']} is virtuous — sufficient proof; skipping further candidates.")
            break

    agg = RESULTS_DIR / f"virtuous_capstone_aggregate_{time.strftime('%Y%m%dT%H%M%S')}.json"
    with open(agg, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[CAPSTONE] aggregate -> {agg.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[CAPSTONE] SUMMARY")
    print("=" * 72)
    for m in all_metrics:
        vm = m.get("virtuous_mode", {})
        print(
            f"  {m.get('opaque_id')}: {m.get('verdict')} | {m.get('elapsed_s')}s | "
            f"args={m.get('argument_count')} fallacies={m.get('fallacy_count')} | "
            f"virtuous={vm.get('is_virtuous')} act3_virtues={m.get('act3_titles_virtues')} | "
            f"gate={m.get('gate',{}).get('band')} leak={m.get('report_leak_chunks')}"
        )


if __name__ == "__main__":
    asyncio.run(amain())
