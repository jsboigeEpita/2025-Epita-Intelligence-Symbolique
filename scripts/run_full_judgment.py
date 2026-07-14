"""Full end-to-end judgment run — cluster-reproducible qualitative judgment harness.

Runs the `spectacular` + `fallacy_tier:"full"` pipeline on ONE real corpus and
captures EVERYTHING needed to judge, qualitatively, whether the orchestration ran
at the max of the deployed capabilities:

  1. full unscrubbed shared-state snapshot (JSON ground truth)
  2. per-phase AGENTIC TRACE: name, capability, component_used, status, duration,
     output shape, error — i.e. which capability fired, which component handled it,
     how long, and whether it silently produced nothing
  3. the readable 3-act restitution report (render_restitution=True) + gate verdict
  4. a run meta: workflow, summary, capabilities used/missing, state key→size map

This SCRIPT is tracked (privacy-safe: it reads the encrypted dataset in-memory via the
derived key, addresses corpora by opaque index only, and prints NO corpus text/meta).
Its OUTPUT lands under argumentation_analysis/evaluation/results/full_judgment/ which is
GITIGNORED (.gitignore covers evaluation/results/) and carries nominative content —
NEVER commit an artifact, NEVER post its content to dashboard / PR / chat. When you need
to publish, hand-curate an OPAQUE aggregate (dimensions/verdicts/gate per corpus, opaque
IDs) from judge_*_meta.json + judge_*_trace.json (both already non-nominative).

Usage (any cluster machine with the dataset + TEXT_CONFIG_PASSPHRASE in .env):
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_full_judgment.py --corpus A
    # corpus B carries archival front-matter (TOC); land inside prose with --offset 120000
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/full_judgment")
DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")


def load_corpus(label: str, max_chars: int = 60000, offset: int = 0) -> Dict[str, Any]:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    meta = {
        k: v
        for k, v in entry.items()
        if k != "full_text" and not isinstance(v, (list, dict))
    }
    # offset lets us skip archival front-matter (e.g. a table of contents) and land
    # the analysis window squarely inside substantive prose.
    window = text[offset : offset + max_chars]
    return {"text": window, "raw_len": len(text), "offset": offset, "meta": meta}


def _shape(v: Any) -> Dict[str, Any]:
    """Structural digest of a phase output — no content, just shape (trace is readable)."""
    out: Dict[str, Any] = {"type": type(v).__name__}
    if v is None:
        out["empty"] = True
    elif isinstance(v, str):
        out["len"] = len(v)
        out["empty"] = len(v.strip()) == 0
    elif isinstance(v, (list, tuple)):
        out["len"] = len(v)
        out["empty"] = len(v) == 0
        if v and isinstance(v[0], dict):
            out["item_keys"] = sorted(v[0].keys())
    elif isinstance(v, dict):
        out["len"] = len(v)
        out["empty"] = len(v) == 0
        out["keys"] = sorted(list(v.keys()))[:25]
    else:
        out["repr"] = str(v)[:80]
    return out


def _state_key_sizes(snap: Dict[str, Any]) -> Dict[str, Any]:
    """For every top-level state key, report its size — the at-a-glance fill map."""
    sizes: Dict[str, Any] = {}
    for k, v in snap.items():
        if k in ("raw_text", "raw_text_snippet"):
            sizes[k] = f"<text {len(str(v))} chars>"
        elif isinstance(v, (list, dict)):
            sizes[k] = len(v)
        elif isinstance(v, str):
            sizes[k] = f"str({len(v)})"
        else:
            sizes[k] = v
    return sizes


async def main_async(label: str, offset: int = 0, out_suffix: str = "") -> None:
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{label}{out_suffix}"  # e.g. "B_speech" — keeps offset run distinct from base run
    corpus = load_corpus(label, offset=offset)
    # NB: deliberately NOT printing corpus text or meta (meta carries names).
    print(
        f"[JUDGE] corpus {label}: {corpus['raw_len']} chars "
        f"(using {len(corpus['text'])} from offset {offset})"
    )

    context = {"fallacy_tier": "full"}
    t0 = time.time()
    result = await run_unified_analysis(
        text=corpus["text"],
        workflow_name="spectacular",
        context=context,
        render_restitution=True,
    )
    elapsed = time.time() - t0
    print(f"[JUDGE] pipeline done in {elapsed:.1f}s")

    # ── 1. full ground-truth state ───────────────────────────────────────
    state = result.get("unified_state")
    snap = state.get_state_snapshot(summarize=False) if state is not None else {}
    (RESULTS_DIR / f"judge_{tag}_state.json").write_text(
        json.dumps(snap, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # ── 2. per-phase agentic trace ───────────────────────────────────────
    phases = result.get("phases", {}) or {}
    trace = []
    for name, pr in phases.items():
        trace.append(
            {
                "phase": getattr(pr, "phase_name", name),
                "capability": getattr(pr, "capability", None),
                "component_used": getattr(pr, "component_used", None),
                "status": str(getattr(pr, "status", "?")).split(".")[-1].lower(),
                "duration_s": round(getattr(pr, "duration_seconds", 0.0), 2),
                "output": _shape(getattr(pr, "output", None)),
                "error": (getattr(pr, "error", None) or None),
            }
        )
    (RESULTS_DIR / f"judge_{tag}_trace.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # ── 3. the readable 3-act restitution report + gate ──────────────────
    report_obj = result.get("restitution_report")
    gate = {"band": "N/A", "reasons": []}
    if report_obj is not None:
        md = getattr(report_obj, "markdown", "") or ""
        (RESULTS_DIR / f"judge_{tag}_restitution.md").write_text(md, encoding="utf-8")
        gv = getattr(report_obj, "verdict", None)
        if gv is not None:
            gate = {
                "band": getattr(gv, "band", "N/A"),
                "reasons": list(getattr(gv, "reasons", []) or []),
            }

    # ── 4. run meta (no corpus content) ──────────────────────────────────
    summary = result.get("summary", {}) or {}
    meta = {
        "corpus_label": label,
        "offset": offset,
        "raw_len": corpus["raw_len"],
        "used_len": len(corpus["text"]),
        "elapsed_s": round(elapsed, 1),
        "workflow_name": result.get("workflow_name"),
        "summary": summary,
        "capabilities_used": result.get("capabilities_used"),
        "capabilities_missing": result.get("capabilities_missing"),
        "gate": gate,
        "report_chars": (
            len(getattr(report_obj, "markdown", "") or "") if report_obj else 0
        ),
        "state_key_sizes": _state_key_sizes(snap),
    }
    (RESULTS_DIR / f"judge_{tag}_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # terse, non-nominative stdout summary
    print(
        f"[JUDGE] phases {summary.get('completed')}/{summary.get('total')} completed "
        f"| failed={summary.get('failed_phases')} | skipped={summary.get('skipped_phases')}"
    )
    print(f"[JUDGE] gate={gate['band']} | report={meta['report_chars']} chars")
    print(
        f"[JUDGE] artifacts -> {RESULTS_DIR}/ (gitignored): "
        f"judge_{tag}_state.json / _trace.json / _restitution.md / _meta.json"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", choices=["A", "B", "C"], default="A")
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="skip N chars of front-matter before the analysis window",
    )
    parser.add_argument(
        "--out-suffix",
        default="",
        help="suffix appended to output filenames (e.g. _speech) to avoid clobber",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args.corpus, offset=args.offset, out_suffix=args.out_suffix))


if __name__ == "__main__":
    main()
