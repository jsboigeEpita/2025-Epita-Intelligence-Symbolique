#!/usr/bin/env python3
"""Corpus batch runner — encrypted corpus → per-doc sanitized signatures.

Iterates over every (source, extract) in the encrypted dataset, runs the
chosen workflow on each, and persists both the full state dump and a
privacy-safe signature.

Usage:
    python scripts/dataset/run_corpus_batch.py \
        --workflow spectacular \
        --output-dir .analysis_kb/signatures \
        --max-docs 0 \
        --skip-existing

Output layout (all gitignored):
    .analysis_kb/
    ├── state_dumps/   state_full_<opaque_id>.json
    └── signatures/    signature_<opaque_id>.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "argumentation_analysis" / "data"
ENCRYPTED_PATH = DATA_DIR / "extract_sources.json.gz.enc"
DEFAULT_KB = REPO_ROOT / "analysis_kb"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("corpus_batch")


# ---------------------------------------------------------------------------
# Metadata classifier — simple heuristics from source_name / date
# ---------------------------------------------------------------------------


def classify_metadata(source_name: str, date_iso: str = "") -> Dict[str, str]:
    """Infer discourse_type, era, regime_type from source metadata.

    This is a best-effort heuristic.  When metadata is unavailable the
    fields default to ``"unknown"``.
    """
    meta: Dict[str, str] = {
        "discourse_type": "unknown",
        "era": "unknown",
        "regime_type": "unknown",
        "year_bucket": "unknown",
    }
    name_lower = source_name.lower()

    # Era from date
    if date_iso and len(date_iso) >= 4:
        try:
            year = int(date_iso[:4])
            meta["era"] = str(year)
            bucket = f"{(year // 5) * 5}-{(year // 5) * 5 + 4}"
            meta["year_bucket"] = bucket
        except ValueError:
            pass

    # Discourse type heuristics (very loose)
    political_kw = {"discours", "president", "ministre", "chancelier", "speech"}
    media_kw = {"editorial", "tribune", "chronique", "op-ed"}
    scientific_kw = {"etude", "rapport", "study", "report"}
    if any(kw in name_lower for kw in political_kw):
        meta["discourse_type"] = "political"
    elif any(kw in name_lower for kw in media_kw):
        meta["discourse_type"] = "media"
    elif any(kw in name_lower for kw in scientific_kw):
        meta["discourse_type"] = "scientific"

    # Regime type (default for Western democracies)
    meta["regime_type"] = "democracy"

    return meta


# ---------------------------------------------------------------------------
# Per-document processing
# ---------------------------------------------------------------------------


async def _run_single(
    text: str,
    source_name: str,
    opaque_id_str: str,
    workflow: str,
    metadata: Dict[str, str],
    state_dumps_dir: Path,
    signatures_dir: Path,
    skip_existing: bool,
    timeout: int = 900,
    pipeline_fn: Optional[Any] = None,
    sanitize_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Process one document and write outputs.  Returns signature dict or None."""

    sig_path = signatures_dir / f"signature_{opaque_id_str}.json"
    if skip_existing and sig_path.exists():
        logger.info("[%s] skip (signature exists)", opaque_id_str)
        return None

    if sanitize_fn is None:
        from argumentation_analysis.evaluation.sanitize_state import sanitize_state

        sanitize_fn = sanitize_state

    t0 = time.perf_counter()
    partial = False
    state_snapshot: Dict[str, Any] = {}

    try:
        if pipeline_fn is None:
            from argumentation_analysis.orchestration.unified_pipeline import (
                run_unified_analysis,
            )

            pipeline_fn = run_unified_analysis

        result = await asyncio.wait_for(
            pipeline_fn(text, workflow_name=workflow),
            timeout=timeout,
        )
        # Prefer full (non-summarized) state for pattern mining.
        state_snapshot = result.get("state_snapshot", {})
        unified = result.get("unified_state")
        if unified is not None:
            try:
                full = unified.get_state_snapshot(summarize=False)
                if full:
                    state_snapshot = full
            except Exception:
                pass
    except asyncio.TimeoutError:
        logger.warning("[%s] timeout (>600s), marking partial", opaque_id_str)
        partial = True
    except Exception as exc:
        logger.error("[%s] error: %s", opaque_id_str, exc)
        partial = True

    wall_clock = round(time.perf_counter() - t0, 1)

    # Write full state dump
    state_dumps_dir.mkdir(parents=True, exist_ok=True)
    dump_path = state_dumps_dir / f"state_full_{opaque_id_str}.json"
    dump_path.write_text(
        json.dumps(state_snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        "[%s] state dump written (%d bytes)", opaque_id_str, dump_path.stat().st_size
    )

    # Build sanitized signature
    sanitized = sanitize_fn(state_snapshot)
    signature: Dict[str, Any] = {
        "opaque_id": opaque_id_str,
        "metadata": metadata,
        "workflow": workflow,
        "wall_clock_s": wall_clock,
        "state": sanitized,
    }
    if partial:
        signature["partial"] = True

    signatures_dir.mkdir(parents=True, exist_ok=True)
    sig_path.write_text(
        json.dumps(signature, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("[%s] signature written (wall=%.1fs)", opaque_id_str, wall_clock)

    return signature


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Corpus batch runner")
    parser.add_argument(
        "--workflow",
        default="spectacular",
        help="Workflow name (default: spectacular)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_KB / "signatures",
        help="Directory for sanitized signatures (gitignored)",
    )
    parser.add_argument(
        "--max-docs", type=int, default=0, help="Max docs to process (0 = all)"
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Skip extracts longer than N chars (0 = no limit)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip docs with existing signatures",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Per-doc timeout in seconds (default: 900)",
    )
    args = parser.parse_args(argv)

    state_dumps_dir = DEFAULT_KB / "state_dumps"

    # Load encrypted dataset
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("TEXT_CONFIG_PASSPHRASE not set in .env")
        return 1

    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.evaluation.opaque_id import opaque_id

    key = derive_encryption_key(passphrase)
    if not key:
        logger.error("Failed to derive encryption key")
        return 1

    definitions = load_extract_definitions(
        config_file=ENCRYPTED_PATH,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )

    # Flatten to (source_name, full_text, metadata) tuples
    docs: List[Dict[str, Any]] = []
    for source_def in definitions:
        src_name = source_def.get("source_name", "unknown")
        src_meta = source_def.get("metadata", {})
        date_iso = src_meta.get("date_iso", source_def.get("date", ""))
        classified = classify_metadata(src_name, date_iso)
        # Merge source-level metadata into classified
        for k, v in src_meta.items():
            classified.setdefault(k, v)

        src_oid = opaque_id(src_name)
        for ext_idx, extract in enumerate(source_def.get("extracts", [])):
            # Corpus uses "extract_text" (not "full_text") at extract level.
            # Fallback chain: extract_text → full_text_segment → source full_text.
            full_text = (
                extract.get("extract_text", "")
                or extract.get("full_text_segment", "")
                or source_def.get("full_text", "")
            )
            if not full_text:
                continue
            if args.max_chars > 0 and len(full_text) > args.max_chars:
                logger.info(
                    "[%s] skip (text too long: %d > %d)",
                    src_oid, len(full_text), args.max_chars,
                )
                continue
            # Per-extract unique ID: src_oid_ext_N or src_oid if only 1 extract
            n_extracts = len(source_def.get("extracts", []))
            if n_extracts > 1:
                oid = f"{src_oid}_ext{ext_idx}"
            else:
                oid = src_oid
            docs.append(
                {
                    "source_name": src_name,
                    "opaque_id": oid,
                    "full_text": full_text,
                    "metadata": classified,
                }
            )

    if args.max_docs > 0:
        docs = docs[: args.max_docs]

    logger.info(
        "Starting batch: %d docs, workflow=%s, skip_existing=%s",
        len(docs),
        args.workflow,
        args.skip_existing,
    )

    # Process documents serially
    signatures: List[Dict[str, Any]] = []
    for i, doc in enumerate(docs, 1):
        logger.info("[%d/%d] Processing %s", i, len(docs), doc["opaque_id"])
        sig = asyncio.run(
            _run_single(
                text=doc["full_text"],
                source_name=doc["source_name"],
                opaque_id_str=doc["opaque_id"],
                workflow=args.workflow,
                metadata=doc["metadata"],
                state_dumps_dir=state_dumps_dir,
                signatures_dir=args.output_dir,
                skip_existing=args.skip_existing,
                timeout=args.timeout,
            )
        )
        if sig is not None:
            signatures.append(sig)

    logger.info(
        "Batch complete: %d/%d signatures produced",
        len(signatures),
        len(docs),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
