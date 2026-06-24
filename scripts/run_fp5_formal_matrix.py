"""FP-5 #1196 — multi-corpus formal-richness matrix on FIXED main (UNTRACKED).

Epic #1191 depth-parity DoD, un-frozen now that FP-3 #1192 (PL→SAT, FOL
fail-loud, Modal sig) landed on main `72586016`. Measuring before FP-3 would
have measured théâtre (FOL fabricated `consistent=True`, PL OOM). Now verdicts
are real.

Per formal capability × corpus, class the measured outcome:
  real-verdict — genuine solver output (PL SAT sat/unsat, Dung extensions, FOL
                 real consistency if it ran, nonzero *_count with non-trivial output).
  degraded     — fail-loud (FOL reasoner couldn't decide → None; honest, not théâtre).
  empty        — solver ran, no structure in corpus (honest-absent, count==0).
  error        — handler bug (should be ~0 after FP-3; flag any remaining).

Privacy HARD: corpus loaded in-memory (encrypted dataset), redact-filter over
chunks, results gitignored under evaluation/results/fp5/. Only opaque counts/
classes leave the machine. No raw_text. No verbatim.

Anti-pendule (#1196): do NOT pad empty/degraded cells to claim parity; do NOT
re-raise heap as a fix (PL is SAT now — if something still OOMs it's a NEW
finding to report). Synthesis-first: no bare count table.
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

# Privacy HARD — redact any substring of any corpus.
_REDACT_CHUNKS: "list[str]" = []


def _populate_redact(text: str) -> None:
    if not text:
        return
    step, size = 20, 40
    for i in range(0, max(1, len(text) - size + 1), step):
        chunk = text[i : i + size].strip()
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

RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "fp5"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"

# corpus (opaque id, dataset idx, ceiling s). A hard / C standard / B large.
CORPORA = [("A", 11, 900), ("C", 2, 900), ("B", 3, 1800)]

# The ~24 formal/richness capabilities. Each maps to (phase_name, state_count_key).
# state_count_key is the UnifiedAnalysisState snapshot counter for that capability.
CAPABILITIES = [
    # ── Formal logic layer (the FP-3 focus) ──
    # #1218 (FP-13): phase_name is the WORKFLOW phase id (workflows.py
    # ``add_phase("<id>", capability=...)``), NOT the capability name. PL and
    # counter-argument were mis-keyed (capability name vs phase id) → the phase
    # looked absent even though the snapshot carried the count (PL=3,
    # counter=28). Fixed to the real phase ids.
    ("pl", "pl", "propositional_analysis_count"),
    ("fol", "fol", "fol_analysis_count"),
    ("modal", "modal", "modal_analysis_count"),
    ("kb_to_tweety", "kb_to_tweety", "atomic_propositions_count"),
    # ── Dung family ──
    ("dung_extensions", "dung_extensions", "dung_framework_count"),
    ("aspic_analysis", "aspic_analysis", "aspic_result_count"),
    ("ranking_semantics", "ranking", "ranking_result_count"),  # FP-23 #1250: was unmeasured
    ("bipolar_argumentation", "bipolar", "bipolar_result_count"),  # FP-23 #1250: was unmeasured
    ("setaf_reasoning", "setaf_reasoning", None),  # W1 — count may be absent
    ("aba_reasoning", "aba_reasoning", None),
    ("weighted_reasoning", "weighted_reasoning", None),
    ("social_reasoning", "social_reasoning", None),
    # ── Extended reasoners (#1178) ──
    ("delp_reasoning", "delp_reasoning", None),
    ("dl_reasoning", "dl_reasoning", None),
    ("qbf_reasoning", "qbf_reasoning", None),
    ("cl_reasoning", "cl_reasoning", None),
    ("dialogue_reasoning", "dialogue_reasoning", "dialogue_result_count"),
    # ── Other formal/structured axes ──
    ("quality", "quality", "quality_scores_count"),
    ("probabilistic", "probabilistic", "probabilistic_result_count"),
    ("belief_revision", "belief_revision", "belief_revision_result_count"),
    (
        "counter_argument",
        "counter",
        "counter_argument_count",
    ),  # #1218: phase id "counter"
    ("governance", "governance", "governance_decision_count"),
    ("debate", "debate", "debate_transcript_count"),
    ("jtms", "jtms", "jtms_belief_count"),
    ("deep_synthesis", "deep_synthesis", "formal_synthesis_count"),
]


def load_corpus_text(label: str, idx: int) -> str:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    text = defs[idx].get("full_text", "")
    _populate_redact(text)
    return text


def _phase(result: dict, name: str):
    return result.get("phases", {}).get(name)


def _phase_status(result: dict, name: str) -> str:
    pr = _phase(result, name)
    if pr is None:
        return "absent"
    try:
        return str(pr.status).split(".")[-1].lower()
    except Exception:
        return "unknown"


def _output_repr(pr) -> object:
    """Best-effort non-triviality probe of a phase output."""
    if pr is None:
        return None
    out = getattr(pr, "output", None)
    if out is None:
        return None
    if isinstance(out, str):
        return out.strip() if out.strip() else None
    if isinstance(out, dict):
        # non-trivial if any truthy value
        return {k: v for k, v in out.items() if v} or None
    if isinstance(out, list):
        return out if out else None
    return out


def _classify_capability(result: dict, phase_name: str, count_key) -> tuple[str, dict]:
    """Return (class, evidence) for one capability.

    class ∈ {real-verdict, degraded, empty, error, absent}.
    evidence = short opaque dict (status, count, has_output) for the matrix cell.
    """
    status = _phase_status(result, phase_name)
    pr = _phase(result, phase_name)
    out = _output_repr(pr)
    # #1218 (FP-13): raw_out is the ORIGINAL phase output. ``_output_repr`` strips
    # falsy values (e.g. ``valid=False``), which would hide a real verdict and the
    # ``solver`` unavailability marker. Verdict + honest-absent checks read raw_out.
    raw_out = getattr(pr, "output", None) if pr else None
    snapshot = result.get("state_snapshot", {}) or {}
    if isinstance(snapshot, dict):
        count = snapshot.get(count_key) if count_key else None
    else:
        count = None
    has_output = out is not None

    # #1218 (FP-13): capture the verdict VALUE so each matrix cell is self-proving
    # (PL SAT/UNSAT model, FOL/DL consistency, modal validity, DeLP status, modal
    # solver). Read from raw_out (``_output_repr`` strips ``valid=False``).
    verdict_val: object = None
    if isinstance(raw_out, dict):
        for _k in ("is_consistent", "consistent", "valid"):
            if _k in raw_out:
                verdict_val = raw_out[_k]
                break
        if verdict_val is None:
            verdict_val = raw_out.get("status") or raw_out.get("solver")

    evidence = {
        "status": status,
        "count": count,
        "has_nontrivial_output": has_output,
        "verdict": verdict_val,
    }

    if status == "failed":
        return "error", evidence
    # #1218 (FP-13): a snapshot count key that is explicitly 0 means the
    # state-writer ran and found nothing → honest-absent (empty), not a wiring
    # gap (absent). Precedes the status=="absent" early-return so an optional
    # phase that produced 0 isn't mis-read as unwired. (count is None only when
    # the key is absent → fall through to the status check below.)
    if count == 0:
        return "empty", evidence
    if status == "absent":
        return "absent", evidence
    # #1218 (FP-13): honest-absent signal takes PRIORITY over the degraded
    # heuristic below. An explicit DECLINE marker means the capability could not
    # decide — DeLP ``status:"unavailable"`` (no program, FP-12), modal
    # ``solver:"unavailable"`` (no SPASS/Tweety solver loaded in the pipeline),
    # a reasoner gate-out. The output dict is non-empty (message + queries +
    # echoed formulas) but carries no decision → class as empty (honest-absent),
    # NOT real-verdict and NOT degraded. Anti-théâtre #1019: a filled-but-
    # declined dict must not count as decided. Read from raw_out (solver is
    # truthy so survives _output_repr, but be uniform with the verdict capture).
    # Must precede the degraded heuristic, which otherwise mis-fires on a
    # status/solver+message-only dict.
    if isinstance(raw_out, dict):
        _decl = ("unavailable", "unsupported", "skipped", "not_applicable")
        if (
            str(raw_out.get("status", "")).lower() in _decl
            or str(raw_out.get("solver", "")).lower() in _decl
        ):
            return "empty", evidence
    # #1222 (FP-14): a verdict key that EXISTS in raw_out with value None means
    # the solver RAN but could not decide (parse error, undecidable signature)
    # — degraded, NOT real-verdict. ``_output_repr`` strips ``valid=None``
    # (falsy), so the degraded branch below misses it when the dict also carries
    # echoed input (formulas/modalities/solver) and mis-labels via ``has_output``.
    # Surfaced by the post-#1219 matrix: modal now reaches SimpleMlReasoner
    # (solver="tweety", not "unavailable") but the real-corpus KB is malformed
    # → valid=None → over-labeled real-verdict. Read raw_out (unstripped). Must
    # follow the honest-absent check above: solver="unavailable" + valid=None
    # stays empty (solver never ran), while solver="tweety" + valid=None is
    # degraded (solver ran, could not decide). A real verdict (True OR False) is
    # untouched (``is None`` is False).
    if isinstance(raw_out, dict) and isinstance(out, dict):
        if any(
            raw_out.get(_k) is None
            for _k in ("is_consistent", "consistent", "valid")
            if _k in raw_out
        ):
            return "degraded", evidence
    # degraded: fail-loud tri-state — NO decisive verdict (every verdict key is
    # None) AND no other real structure. #1218 (FP-13): verdict-aware — the old
    # ``any()`` over is_consistent/consistent/valid mis-fired when FOL returned
    # ``is_consistent=True`` but had no ``consistent`` key (None → false marker).
    # A real verdict (True OR False, e.g. modal valid=False) now correctly
    # short-circuits to non-degraded; only an all-None verdict + bare message
    # (the FP-3 fail-loud shape) is degraded.
    if isinstance(out, dict):
        verdict_keys = [k for k in ("is_consistent", "consistent", "valid") if k in out]
        has_real_verdict = any(out.get(k) is not None for k in verdict_keys)
        no_other_structure = not any(
            v
            for k, v in out.items()
            if k not in ("is_consistent", "consistent", "valid", "message", "status")
        )
        if not has_real_verdict and no_other_structure:
            return "degraded", evidence
    if has_output:
        return "real-verdict", evidence
    # no output: fall back to count
    if count is not None:
        if count > 0:
            return "real-verdict", evidence
        return "empty", evidence
    # phase ran (completed) but no output and no count → empty honest-absent
    if status == "completed":
        return "empty", evidence
    return "degraded", evidence


def _leak_audit(artifact_text: str, corpus_text: str) -> int:
    chunks = []
    step, size = 20, 40
    for i in range(0, max(1, len(corpus_text) - size + 1), step):
        c = corpus_text[i : i + size].strip()
        if len(c) >= 20:
            chunks.append(c)
    return sum(1 for c in chunks if c in artifact_text)


async def run_one(label: str, idx: int, timeout: int, corpus_texts: dict) -> dict:
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    text = load_corpus_text(label, idx)
    corpus_texts[label] = text
    print(
        f"[FP-5] doc_{label}: {len(text)} chars | spectacular+full | ceiling {timeout}s"
    )

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
        print(f"[FP-5] doc_{label} TIMED OUT after {timeout}s — documented fail-loud.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[FP-5] doc_{label} {verdict}: {_redact(str(exc))[:160]}")

    elapsed = time.time() - t0
    summary = result.get("summary", {}) if isinstance(result, dict) else {}

    # Per-capability matrix row.
    matrix = {}
    pl_evidence: dict = {}
    fol_evidence: dict = {}
    for cap, phase, count_key in CAPABILITIES:
        cls, ev = _classify_capability(result, phase, count_key)
        matrix[cap] = {"class": cls, "evidence": ev}
        if cap == "pl":
            pl_evidence = ev
        if cap == "fol":
            fol_evidence = ev

    metrics = {
        "corpus": f"doc_{label}",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "phases_completed": summary.get("completed"),
        "phases_failed": summary.get("failed"),
        "phases_total": summary.get("total"),
        "failed_phases": summary.get("failed_phases", []),
        "matrix": matrix,
    }

    # DoD-specific confirmations.
    metrics["dod"] = {
        "pl_no_oom": verdict == "COMPLETED"
        and _phase_status(result, "pl") == "completed",
        "pl_wallclock_s": round(elapsed, 1) if label == "A" else None,
        "fol_fail_loud": fol_evidence.get("count") in (None, 0)
        or fol_evidence.get("has_nontrivial_output") is False
        or matrix["fol"]["class"] in ("degraded", "empty"),
        "fol_fabricated_true": False,  # set True only if we detect a real consistent=True
    }
    # Detect fabricated FOL consistent=True (anti-theater check): scan fol output
    fol_pr = _phase(result, "fol")
    fol_out = getattr(fol_pr, "output", None) if fol_pr else None
    if isinstance(fol_out, dict) and fol_out.get("is_consistent") is True:
        # Only suspicious if reasoner was supposed to fail; for now flag presence
        metrics["dod"]["fol_fabricated_true"] = True
        metrics["dod"]["fol_fail_loud"] = False

    # #1218 (FP-13): extend the fabricated-True anti-théâtre probe to modal +
    # DL. Like ``fol``, this flags the PRESENCE of a positive verdict
    # (consistent/valid == True); interpretation (real vs fabricated) happens in
    # the report — a true verdict on a real KB is genuine, not theater.
    for _cap, _phase_n, _key in (
        ("modal", "modal", "valid"),
        ("dl", "dl_reasoning", "consistent"),
    ):
        _pr = _phase(result, _phase_n)
        _out = getattr(_pr, "output", None) if _pr else None
        metrics["dod"][f"{_cap}_fabricated_true"] = bool(
            isinstance(_out, dict) and _out.get(_key) is True
        )

    # Raw provenance (gitignored).
    ts = time.strftime("%Y%m%dT%H%M%S")
    raw_out = RESULTS_DIR / f"fp5_doc{label}_{ts}.json"
    try:
        serializable = {
            "corpus": f"doc_{label}",
            "metrics": metrics,
            "state_snapshot": result.get("state_snapshot"),
            "capabilities_used": result.get("capabilities_used", []),
        }
        with open(raw_out, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
        print(f"[FP-5] doc_{label} raw metrics saved -> {raw_out.name} (gitignored)")
    except Exception as exc:
        print(f"[FP-5] doc_{label} raw save failed: {type(exc).__name__}")

    # Class tally for the console summary (opaque counts only).
    tally = {}
    for cap, row in matrix.items():
        tally[row["class"]] = tally.get(row["class"], 0) + 1
    print(
        f"[FP-5] doc_{label} DONE: {verdict} ({metrics['elapsed_s']}s) | "
        f"phases {metrics['phases_completed']}/{metrics['phases_total']} | "
        f"classes={tally}"
    )
    return metrics


async def amain() -> None:
    print("=" * 72)
    print("[FP-5] #1196 formal-richness matrix — spectacular+full on FIXED main")
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
            print(f"[FP-5] doc_{label} FATAL: {_redact(str(exc))[:160]}")
        all_metrics.append(m)

    agg = RESULTS_DIR / f"fp5_matrix_{time.strftime('%Y%m%dT%H%M%S')}.json"
    with open(agg, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[FP-5] matrix aggregate saved -> {agg.name} (gitignored)")

    # Console matrix (opaque classes only).
    print("\n" + "=" * 72)
    print("[FP-5] MATRIX (capability × corpus → class)")
    print("=" * 72)
    caps = [c for c, _, _ in CAPABILITIES]
    header = f"{'capability':<22}" + "".join(f"{f'doc_{l}':>12}" for l, _, _ in CORPORA)
    print(header)
    for cap in caps:
        row = f"{cap:<22}"
        for m in all_metrics:
            mx = m.get("matrix", {}).get(cap, {})
            cls = mx.get("class", "?") if isinstance(mx, dict) else "?"
            row += f"{cls:>12}"
        print(row)

    print("\n[FP-5] DoD confirmations:")
    for m in all_metrics:
        d = m.get("dod", {})
        print(
            f"  {m.get('corpus')}: pl_no_oom={d.get('pl_no_oom')} | "
            f"fol_fail_loud={d.get('fol_fail_loud')} | "
            f"fol_fabricated_true={d.get('fol_fabricated_true')}"
        )


if __name__ == "__main__":
    asyncio.run(amain())
