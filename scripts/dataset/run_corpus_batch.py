#!/usr/bin/env python3
"""Corpus batch runner — encrypted corpus → per-doc sanitized signatures.

Iterates over every (source, extract) in the encrypted dataset, runs the
chosen workflow on each, and persists both the full state dump and a
privacy-safe signature.

Supports checkpoint/resume: after each DAG level, a checkpoint file is
written atomically.  On crash, ``--resume`` picks up from the last
checkpoint instead of restarting the document.

Usage:
    python scripts/dataset/run_corpus_batch.py \\
        --workflow spectacular \\
        --output-dir .analysis_kb/signatures \\
        --max-docs 0 \\
        --skip-existing

    # Resume an interrupted batch
    python scripts/dataset/run_corpus_batch.py --resume

Output layout (all gitignored):
    .analysis_kb/
    ├── checkpoints/   <opaque_id>.checkpoint.json
    ├── state_dumps/   state_full_<opaque_id>.json
    └── signatures/    signature_<opaque_id>.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "argumentation_analysis" / "data"
ENCRYPTED_PATH = DATA_DIR / "extract_sources.json.gz.enc"
DEFAULT_KB = REPO_ROOT / "analysis_kb"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("corpus_batch")


class _SafeEncoder(json.JSONEncoder):
    """JSON encoder that converts sets to sorted lists."""

    def default(self, o: Any) -> Any:
        if isinstance(o, set):
            return sorted(o, key=str)
        return super().default(o)


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

    # #1906: ``regime_type`` was assigned "democracy" unconditionally here --
    # not a heuristic but a constant, contradicting this function's own
    # docstring ("the fields default to unknown"). It has no code consumer, yet
    # since #1913 wired ``source_metadata`` through the batch runner it reaches
    # the Act I framing verbatim (act1_framing_plugin renders every key), so the
    # model was handed a hard-coded claim about every source as established
    # metadata. Removed rather than replaced: the declared default already says
    # "unknown", and a corpus definition that states the regime now wins at the
    # merge site below.

    return meta


def merge_source_metadata(
    classified: Dict[str, str], src_meta: Dict[str, Any]
) -> Dict[str, str]:
    """Overlay a corpus definition's explicit metadata onto the inference.

    #1906: explicit structured metadata wins over label inference, field by
    field. The previous ``classified.setdefault(k, v)`` did the opposite:
    ``classify_metadata`` always writes its four keys, so an explicit ``era``
    from the definition was discarded in favour of the inferred ``"unknown"``
    -- the sentinel is a value, and ``setdefault`` treats it as present. Only
    keys the inference never writes (e.g. ``speaker``) used to survive.

    An explicit ``"unknown"`` does **not** erase a resolved inference:
    precedence is for values, not for the sentinel. Extracted from ``main()``
    so the merge is reachable by a test -- inline, it could only be checked by
    a copy of itself, which cannot fail.
    """
    merged = dict(classified)
    for k, v in src_meta.items():
        if v not in (None, "", "unknown"):
            merged[k] = v
        else:
            merged.setdefault(k, v)
    return merged


# ---------------------------------------------------------------------------
# Legacy label parser (#1906 scope item 2)
# ---------------------------------------------------------------------------

_GENRE_KEYWORDS = [
    ("compte rendu", "rapport"),
    ("editorial", "éditorial"),
    ("discours", "discours"),
    ("speech", "discours"),
    ("address", "discours"),
    ("débat", "débat"),
    ("debat", "débat"),
    ("rapport", "rapport"),
]

# Parenthetical file-format tags — not venues, whatever else they say.
_FORMAT_TAG_RE = re.compile(r"\A(?:pdf|mp3|wav|txt|docx?|source)\Z", re.IGNORECASE)

_FRENCH_MONTHS = (
    "janvier|février|mars|avril|mai|juin|juillet|"
    "août|septembre|octobre|novembre|décembre"
)
_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/(\d{4}))\b")
_DATE_FRENCH_RE = re.compile(
    rf"\b(\d{{1,2}}(?:er)?\s+(?:{_FRENCH_MONTHS})\s+(\d{{4}}))\b", re.IGNORECASE
)
_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
_TITLE_STOPWORDS = {"the", "le", "la", "les", "du", "de", "des", "un", "une"}


def _person_shaped(segment: str) -> bool:
    """True for a ``First Last`` / ``First Middle Last`` person name."""
    words = segment.split()
    return (
        2 <= len(words) <= 3
        and all(w[:1].isupper() for w in words)
        and not any(w.lower() in _TITLE_STOPWORDS for w in words)
    )


def parse_legacy_label(source_name: str) -> Dict[str, str]:
    """Structurally parse a legacy corpus source label into short metadata.

    #1906: most corpus definitions carry speaker/title/year information only
    in the label string. Without a parser, ``source_metadata`` reached Act I
    as ``unknown`` for fields the label states explicitly, and Act III then
    inferred the speaker from the text — the inter-act contradiction this
    issue exists to close.

    Only structurally stated information is claimed: a field the label does
    not carry is omitted, never invented. Precedence (heuristics < parsed
    label < explicit corpus metadata) is applied by the merge sites above.
    """
    meta: Dict[str, str] = {}
    text = source_name.strip()

    year: Optional[int] = None
    m = _DATE_NUMERIC_RE.search(text) or _DATE_FRENCH_RE.search(text)
    if m:
        meta["date_or_year"] = m.group(1)
        year = int(m.group(2))
    else:
        m = _YEAR_RE.search(text)
        if m:
            year = int(m.group(1))
            meta["date_or_year"] = str(year)
    if year is not None:
        meta["era"] = str(year)
        meta["year_bucket"] = f"{(year // 5) * 5}-{(year // 5) * 5 + 4}"

    paren = re.search(r"\(([^)]*)\)", text)
    if paren and paren.group(1).strip():
        inner = paren.group(1).strip()
        if not (
            _DATE_NUMERIC_RE.search(inner)
            or _DATE_FRENCH_RE.search(inner)
            or _FORMAT_TAG_RE.match(inner)
        ):
            meta["venue"] = inner

    lowered = text.lower()
    for keyword, genre in _GENRE_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            meta["genre"] = genre
            keyword_pos = lowered.find(keyword)
            break
    else:
        keyword_pos = -1

    segments = [s.strip() for s in re.split(r"\s+-\s+", text) if s.strip()]
    if len(segments) >= 2:
        if (
            len(segments) == 2
            and len(segments[0].split()) == 1
            and _person_shaped(segments[1])
        ):
            # ``Oeuvre - Auteur``, the inverted shape.
            meta["speaker"] = segments[1]
            meta["title"] = segments[0]
        else:
            meta["speaker"] = segments[0]
            meta["title"] = " - ".join(segments[1:])
        for key in ("speaker", "title"):
            meta[key] = _YEAR_RE.sub("", meta[key]).strip()
            meta[key] = re.sub(r"\s*\([^)]*\)", "", meta[key]).strip()
    elif keyword_pos > 0:
        speaker = text[:keyword_pos].strip(" -:–")
        if speaker:
            meta["speaker"] = speaker
    else:
        m = re.match(r"\A([A-ZÀ-Þ][\w'’-]+-[A-ZÀ-Þ][\w'’-]+)(?:\s|\Z)", text)
        if m:
            meta["speaker"] = m.group(1)

    meta = {k: v for k, v in meta.items() if v}
    return meta


# ---------------------------------------------------------------------------
# Checkpoint-aware per-document processing
# ---------------------------------------------------------------------------


def expand_corpus(
    definitions: List[Dict[str, Any]], max_chars: int = 0
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], int]:
    """Flatten corpus definitions into per-document records, named skip counts.

    #1909 slice 2: a document skipped for length and a source that produced
    no document are populations the batch summary must be able to count — the
    ``skipped_too_long`` and ``source_without_extract`` buckets. Returns
    ``(docs, omitted_sources, skipped_too_long)``.
    """
    from argumentation_analysis.evaluation.opaque_id import opaque_id as _opaque_id

    docs: List[Dict[str, Any]] = []
    omitted_sources: List[Dict[str, str]] = []
    skipped_too_long = 0
    for source_def in definitions:
        src_name = source_def.get("source_name", "unknown")
        src_meta = source_def.get("metadata", {})
        date_iso = src_meta.get("date_iso", source_def.get("date", ""))
        # #1906 precedence chain: keyword heuristics < parsed legacy label <
        # explicit corpus metadata. Each layer may only resolve what the
        # previous one left unknown or absent.
        classified = merge_source_metadata(
            merge_source_metadata(
                classify_metadata(src_name, date_iso),
                parse_legacy_label(src_name),
            ),
            src_meta,
        )

        src_oid = _opaque_id(src_name)
        extracts = source_def.get("extracts", [])
        src_doc_count = 0
        n_filtered = 0
        n_no_text = 0
        for ext_idx, extract in enumerate(extracts):
            # Corpus uses "extract_text" (not "full_text") at extract level.
            # Fallback chain: extract_text → full_text_segment → source full_text.
            full_text = (
                extract.get("extract_text", "")
                or extract.get("full_text_segment", "")
                or source_def.get("full_text", "")
            )
            if not full_text:
                logger.info(
                    "[%s] skip (extract %d/%d has no text after fallback chain)",
                    src_oid,
                    ext_idx + 1,
                    len(extracts),
                )
                n_no_text += 1
                continue
            if max_chars > 0 and len(full_text) > max_chars:
                logger.info(
                    "[%s] skip (text too long: %d > %d)",
                    src_oid,
                    len(full_text),
                    max_chars,
                )
                n_filtered += 1
                continue
            # Per-extract unique ID: src_oid_ext_N or src_oid if only 1 extract
            if len(extracts) > 1:
                oid = f"{src_oid}_ext{ext_idx}"
            else:
                oid = src_oid
            docs.append(
                {
                    "source_name": src_name,
                    "source_opaque_id": src_oid,
                    "opaque_id": oid,
                    "full_text": full_text,
                    "metadata": classified,
                }
            )
            src_doc_count += 1

        skipped_too_long += n_filtered
        if src_doc_count == 0:
            if not extracts:
                cause = "0 extract"
            elif n_filtered and n_no_text:
                cause = (
                    f"{n_filtered} extract(s) filtered, " f"{n_no_text} without text"
                )
            elif n_filtered:
                cause = f"all {n_filtered} extract(s) filtered (--max-chars)"
            else:
                cause = f"all {n_no_text} extract(s) without text"
            logger.info("[%s] source without documents: %s", src_oid, cause)
            omitted_sources.append({"opaque_id": src_oid, "cause": cause})

    return docs, omitted_sources, skipped_too_long


_FAILED_STATUSES = ("failed", "partial_timeout", "partial_error", "unknown")


def summarize_batch(
    outcome_counts: Dict[str, int],
    skipped_too_long: int,
    sources_without_extract: int,
) -> Dict[str, Any]:
    """Project per-document outcomes into the five reader-facing buckets.

    ``argumentative`` maps from ``ok`` (the pipeline has no other success
    status; the tri-state lives in ``document_classification``), the valid
    no-analysis terminal keeps its own bucket (#1909), and every failure,
    partial, and unreadable status lands in ``failed`` with the raw status
    counts preserved under ``failed_detail`` — the buckets are a sum for
    humans, never a replacement of what the runner must be able to say.
    """
    failed_detail = {
        status: outcome_counts.get(status, 0) for status in _FAILED_STATUSES
    }
    return {
        "argumentative": outcome_counts.get("ok", 0),
        "non_argumentative": outcome_counts.get("non_argumentative", 0),
        "failed": sum(failed_detail.values()),
        "skipped_too_long": skipped_too_long,
        "source_without_extract": sources_without_extract,
        "failed_detail": failed_detail,
    }


def render_batch_summary(summary: Dict[str, Any]) -> str:
    return (
        "Batch summary: argumentative={} non_argumentative={} failed={} "
        "skipped_too_long={} source_without_extract={} (failed detail: {})".format(
            summary["argumentative"],
            summary["non_argumentative"],
            summary["failed"],
            summary["skipped_too_long"],
            summary["source_without_extract"],
            summary["failed_detail"],
        )
    )


def render_batch_verdict(summary: Dict[str, Any]) -> str:
    failed = summary["failed"]
    if failed:
        return f"Verdict: FAIL ({failed} document(s) failed)"
    return "Verdict: PASS (0 documents failed)"


def render_non_argumentative_restitution(
    opaque_id_str: str, outcome: Dict[str, Any]
) -> str:
    """Short reader-facing report for the valid no-analysis case (#1909).

    States what kind of material was found and why no argumentative analysis
    follows — a named terminal success, never confusable with a failure.
    """
    phase = outcome.get("phase", "extraction")
    return (
        f"Document {opaque_id_str}: classified non-argumentative at {phase} — "
        "the extraction found factual material with no identified arguments; "
        "argument-dependent phases were skipped as a valid terminal "
        "classification (#1909). Analysis intentionally partial: not a failure."
    )


def _with_document_classification(
    signature: Dict[str, Any], analysis_outcome: Dict[str, Any]
) -> Dict[str, Any]:
    """Surface the tri-state on the signature (#1909 slice 2, scope 4).

    Mirrors the pipeline: the key is written only for the non-argumentative
    classification; argumentative documents leave it absent.
    """
    if analysis_outcome.get("status") == "non_argumentative":
        signature["document_classification"] = "non_argumentative"
    return signature


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
    checkpoint_mgr: Optional[Any] = None,
    pipeline_fn: Optional[Any] = None,
    sanitize_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Process one document and write outputs.  Returns signature dict or None."""

    sig_path = signatures_dir / f"signature_{opaque_id_str}.json"
    if skip_existing and sig_path.exists():
        logger.info("[%s] skip (signature exists; reusing its outcome)", opaque_id_str)
        try:
            existing = json.loads(sig_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "opaque_id": opaque_id_str,
                "outcome": {
                    "status": "partial_error",
                    "reason": f"unreadable existing signature: {type(exc).__name__}",
                },
            }
        if isinstance(existing, dict):
            if isinstance(existing.get("outcome"), dict):
                return existing
            if existing.get("partial") is True:
                existing["outcome"] = {
                    "status": "partial_error",
                    "reason": "legacy partial signature without outcome",
                }
                return existing
            legacy_fields = {"opaque_id", "workflow", "state"}
            if legacy_fields.issubset(existing):
                existing["outcome"] = {
                    "status": "skipped_existing",
                    "reason": "legacy successful signature without outcome",
                }
                return existing
            return {
                "opaque_id": opaque_id_str,
                "outcome": {
                    "status": "partial_error",
                    "reason": "existing signature has no recognizable outcome",
                },
            }
        return {
            "opaque_id": opaque_id_str,
            "outcome": {
                "status": "partial_error",
                "reason": "existing signature is not a JSON object",
            },
        }

    if sanitize_fn is None:
        from argumentation_analysis.evaluation.sanitize_state import sanitize_state

        sanitize_fn = sanitize_state

    # --- Resume logic -------------------------------------------------------
    resume_from: Optional[set] = None
    resume_context: Optional[Dict[str, Any]] = None
    checkpoint_snapshot: Optional[Dict[str, Any]] = None

    if checkpoint_mgr is not None:
        ckpt = checkpoint_mgr.load(opaque_id_str)
        if ckpt is not None:
            completed = set(ckpt.get("completed_phases", []))
            if completed:
                from argumentation_analysis.orchestration.checkpoint import (
                    deserialize_phase_outputs,
                )
                from argumentation_analysis.orchestration.workflow_dsl import (
                    PhaseResult,
                    PhaseStatus,
                )

                phase_outputs = deserialize_phase_outputs(ckpt.get("phase_outputs", {}))
                resume_context = {}
                resume_from = completed
                checkpoint_snapshot = ckpt.get("state_snapshot")

                for pname in completed:
                    output = phase_outputs.get(pname)
                    if output is not None:
                        resume_context[f"phase_{pname}_output"] = output
                        resume_context[f"phase_{pname}_result"] = PhaseResult(
                            phase_name=pname,
                            status=PhaseStatus.COMPLETED,
                            capability="unknown",
                            output=output,
                        )
                logger.info(
                    "[%s] resuming from checkpoint (%d phases)",
                    opaque_id_str,
                    len(completed),
                )

    # --- Build checkpoint callback ------------------------------------------
    level_counter = [0]

    def _checkpoint_callback(results: Dict, ctx: Dict) -> None:
        """Called by WorkflowExecutor after each DAG level."""
        if checkpoint_mgr is None:
            return

        from argumentation_analysis.orchestration.checkpoint import (
            serialize_phase_result,
        )

        completed_phases = sorted(
            n for n, r in results.items() if r.status.value == "completed"
        )
        phase_outputs = {}
        for name in completed_phases:
            r = results[name]
            phase_outputs[name] = serialize_phase_result(
                name, r.status.value, r.output, r.duration_seconds, r.error
            )

        # Capture state snapshot if available
        snap = None
        ust = ctx.get("unified_state")
        if ust is not None and hasattr(ust, "get_state_snapshot"):
            try:
                snap = ust.get_state_snapshot(summarize=False)
            except Exception:
                pass

        checkpoint_mgr.save(
            doc_id=opaque_id_str,
            workflow=workflow,
            completed_phases=completed_phases,
            phase_outputs=phase_outputs,
            state_snapshot=snap,
        )
        level_counter[0] += 1

    # --- Execute pipeline ---------------------------------------------------
    t0 = time.perf_counter()
    partial = False
    partial_reason: Optional[str] = None
    analysis_outcome: Dict[str, str] = {"status": "ok"}
    state_snapshot: Dict[str, Any] = {}

    try:
        if pipeline_fn is None:
            from argumentation_analysis.orchestration.unified_pipeline import (
                run_unified_analysis,
            )

            pipeline_fn = run_unified_analysis

        result = await asyncio.wait_for(
            pipeline_fn(
                text,
                workflow_name=workflow,
                context=resume_context,
                checkpoint_callback=(
                    _checkpoint_callback if checkpoint_mgr is not None else None
                ),
                resume_from=resume_from,
                source_metadata=metadata,
            ),
            timeout=timeout,
        )
        returned_outcome = result.get("analysis_outcome")
        if isinstance(returned_outcome, dict) and isinstance(
            returned_outcome.get("status"), str
        ):
            analysis_outcome = dict(returned_outcome)
        # Prefer full (non-summarized) state for pattern mining.
        state_snapshot = result.get("state_snapshot", {})
        # Prefer full (non-summarized) state for pattern mining.
        unified = result.get("unified_state")
        if unified is not None:
            try:
                full = unified.get_state_snapshot(summarize=False)
                if full:
                    state_snapshot = full
            except Exception:
                pass

        # Merge checkpoint snapshot with new snapshot if resuming
        if checkpoint_snapshot and isinstance(state_snapshot, dict):
            merged = _merge_snapshots(checkpoint_snapshot, state_snapshot)
            state_snapshot = merged
    except asyncio.TimeoutError:
        partial_reason = f"timeout after {timeout}s"
        logger.warning("[%s] %s, marking partial", opaque_id_str, partial_reason)
        partial = True
        analysis_outcome = {
            "status": "partial_timeout",
            "reason": partial_reason,
        }
    except Exception as exc:
        partial_reason = str(exc) or type(exc).__name__
        logger.error("[%s] error: %s", opaque_id_str, partial_reason)
        partial = True
        analysis_outcome = {
            "status": "partial_error",
            "reason": partial_reason,
        }

    wall_clock = round(time.perf_counter() - t0, 1)

    # Write full state dump
    state_dumps_dir.mkdir(parents=True, exist_ok=True)
    dump_path = state_dumps_dir / f"state_full_{opaque_id_str}.json"
    dump_path.write_text(
        json.dumps(state_snapshot, ensure_ascii=False, indent=2, cls=_SafeEncoder),
        encoding="utf-8",
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
        "outcome": analysis_outcome,
        "state": sanitized,
    }
    if partial:
        signature["partial"] = True
    _with_document_classification(signature, analysis_outcome)

    signatures_dir.mkdir(parents=True, exist_ok=True)
    sig_path.write_text(
        json.dumps(signature, ensure_ascii=False, indent=2, cls=_SafeEncoder),
        encoding="utf-8",
    )
    logger.info("[%s] signature written (wall=%.1fs)", opaque_id_str, wall_clock)

    # Remove checkpoint on success
    if checkpoint_mgr is not None and not partial:
        checkpoint_mgr.remove(opaque_id_str)

    return signature


def _merge_snapshots(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two state snapshots.  *override* takes precedence."""
    merged = dict(base)
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = {**merged[key], **val}
        else:
            merged[key] = val
    return merged


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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted batch from per-document checkpoints",
    )
    args = parser.parse_args(argv)

    state_dumps_dir = DEFAULT_KB / "state_dumps"
    checkpoint_dir = DEFAULT_KB / "checkpoints"

    # Setup checkpoint manager
    checkpoint_mgr = None
    if args.resume:
        from argumentation_analysis.orchestration.checkpoint import CheckpointManager

        checkpoint_mgr = CheckpointManager(checkpoint_dir)
        incomplete = checkpoint_mgr.list_incomplete()
        if incomplete:
            logger.info(
                "Resume mode: %d incomplete checkpoints found: %s",
                len(incomplete),
                incomplete[:5],
            )
        else:
            logger.info("Resume mode: no incomplete checkpoints found")

    # Also enable checkpoints for new runs when --resume is active
    if checkpoint_mgr is None and args.resume:
        from argumentation_analysis.orchestration.checkpoint import CheckpointManager

        checkpoint_mgr = CheckpointManager(checkpoint_dir)

    # Load encrypted dataset
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("TEXT_CONFIG_PASSPHRASE not set in .env")
        return 1

    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    key = derive_encryption_key(passphrase)
    if not key:
        logger.error("Failed to derive encryption key")
        return 1

    definitions = load_extract_definitions(
        config_file=ENCRYPTED_PATH,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )

    # Flatten to (source_name, full_text, metadata) tuples.
    # #1903: a source contributing zero documents must be named with its
    # cause -- an unlogged omission silently falsifies the denominator of
    # every corpus report.
    docs, omitted_sources, skipped_too_long = expand_corpus(definitions, args.max_chars)

    documents_before_limit = len(docs)
    truncated_source_ids: List[str] = []
    if args.max_docs > 0:
        processed_source_ids = {
            doc["source_opaque_id"] for doc in docs[: args.max_docs]
        }
        all_source_ids = {doc["source_opaque_id"] for doc in docs}
        truncated_source_ids = sorted(all_source_ids - processed_source_ids)
        docs = docs[: args.max_docs]

    # #1903: the honest denominator, on stdout (the surface #1874 established
    # for run-visible facts) and before processing starts. #1919 preserves the
    # byte-identical unlimited line while naming both populations when a limit
    # excludes otherwise valid source documents.
    if args.max_docs > 0:
        print(
            "Coverage: {} sources -> {} documents before --max-docs; "
            "{} documents processed; {} sources without documents: [{}]; "
            "{} sources excluded by --max-docs: [{}]".format(
                len(definitions),
                documents_before_limit,
                len(docs),
                len(omitted_sources),
                ", ".join(o["opaque_id"] for o in omitted_sources),
                len(truncated_source_ids),
                ", ".join(truncated_source_ids),
            ),
            flush=True,
        )
    else:
        print(
            "Coverage: {} sources -> {} documents; {} sources without documents: "
            "[{}]".format(
                len(definitions),
                len(docs),
                len(omitted_sources),
                ", ".join(o["opaque_id"] for o in omitted_sources),
            ),
            flush=True,
        )

    logger.info(
        "Starting batch: %d docs, workflow=%s, skip_existing=%s, resume=%s",
        len(docs),
        args.workflow,
        args.skip_existing,
        args.resume,
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
                checkpoint_mgr=checkpoint_mgr,
            )
        )
        if sig is not None:
            signatures.append(sig)
            outcome = sig.get("outcome")
            if (
                isinstance(outcome, dict)
                and outcome.get("status") == "non_argumentative"
            ):
                print(
                    render_non_argumentative_restitution(doc["opaque_id"], outcome),
                    flush=True,
                )

    outcome_counts: Dict[str, int] = {}
    for signature in signatures:
        outcome = signature.get("outcome")
        status = outcome.get("status") if isinstance(outcome, dict) else "unknown"
        outcome_counts[str(status)] = outcome_counts.get(str(status), 0) + 1

    logger.info(
        "Batch complete: %d/%d signatures produced; outcomes=%s",
        len(signatures),
        len(docs),
        outcome_counts,
    )
    summary = summarize_batch(outcome_counts, skipped_too_long, len(omitted_sources))
    # stdout is the run-visible surface (#1874/#1903): the five buckets and
    # the gate verdict in plain text, not a logger line.
    print(render_batch_summary(summary), flush=True)
    print(render_batch_verdict(summary), flush=True)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
