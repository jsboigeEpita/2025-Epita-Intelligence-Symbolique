#!/usr/bin/env python
"""#1698 (R791 item 2) — reproducible probe: dropped-edge split by source nature.

The #1704 honest report (``attacks_submitted/retained/dropped``) counted how
many attack candidates never reached the evaluated Dung-family graphs. Item 2
splits that count by the *nature* of the synthetic source the producer minted:

  * ``fallacy_*``   — fallacy detections with a resolvable target
  * ``CA: ...``     — counter-argument text matches (``ca`` family)
  * ``other``       — defensive bucket (unknown / malformed / upstream pairs)

The split is declared at the annotation point (``_annotate_attack_retention``,
where the candidates are in hand) as ``attacks_submitted_<nature>`` /
``attacks_dropped_<nature>`` — reproducible by construction, never
reconstructed post-hoc. This probe only READS those numeric keys off a state
snapshot and aggregates them.

Privacy HARD: this probe never reads, prints, or stores source strings — the
``CA:`` sources embed counter-argument text (= corpus). It touches the numeric
accounting keys only. If a snapshot predates the instrumentation, the probe
reports the totals and an honest "per-nature split unavailable" note rather
than fabricating a split (#1019).

Aggregation: the same accounting declaration is replicated within each
surface (the curated carry projects one axe onto several framework entries;
the bulk surface emits one block per axe over a shared candidate set), so
naive summation multiplies the true candidate count by the replication
factor (R792: curated raw 468, bulk raw 78, real 39). The probe dedups by a
fingerprint of the accounting before summing — the deduped totals are the
authoritative counts, the raw sum is kept as a diagnostic — and prints the
curated-vs-bulk agreement (on deduped totals) as an inter-surface verdict.

Usage:
    python scripts/probe_attack_source_nature_split.py STATE.json [STATE2.json ...]
    python scripts/probe_attack_source_nature_split.py --json STATE.json ...
    python scripts/probe_attack_source_nature_split.py --snapshots iter42_snapshots.jsonl

Input formats accepted:
  * a plain ``UnifiedAnalysisState`` export (``to_json()`` output) — the
    ``iter*_snapshots.jsonl`` ``state_snapshot`` payload;
  * ``--snapshots``: an LLM-Judge ``iter*_snapshots.jsonl`` where each line is
    ``{"document_name": ..., "state_snapshot": {...}}``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# The accounting keys the probe reads. Counts only — never source text.
_TOTAL_KEYS = ("attacks_submitted", "attacks_retained", "attacks_dropped")
_NATURE_KEYS = (
    ("attacks_submitted_fallacy", "attacks_dropped_fallacy"),
    ("attacks_submitted_ca", "attacks_dropped_ca"),
    ("attacks_submitted_other", "attacks_dropped_other"),
)
_NATURES = ("fallacy", "ca", "other")


def _as_int(value: Any) -> Optional[int]:
    """Accept ints only — a non-numeric accounting key is not a count we
    aggregate (the probe must never guess)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _collect_accounting(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect every dung-family accounting block in a state snapshot.

    Sources, in preference order:
      1. curated ``dung_frameworks[*]`` (the surface the conclusion reads,
         carries the accounting since R791 item 1);
      2. bulk ``formal_synthesis_reports[*].phase_results.*`` (invoke outputs).

    Returns a list of dicts, each carrying totals + per-nature counts when
    present (all ``None`` fields mean "keys absent — pre-instrumentation").
    """
    blocks: List[Dict[str, Any]] = []

    def _add(surface: str, prefix: str, block: Dict[str, Any]) -> None:
        submitted = _as_int(block.get("attacks_submitted"))
        retained = _as_int(block.get("attacks_retained"))
        dropped = _as_int(block.get("attacks_dropped"))
        if submitted is None and retained is None and dropped is None:
            return  # not an accounting block
        by_nature: Dict[str, Dict[str, Optional[int]]] = {}
        for nature, (sub_k, dropped_k) in zip(_NATURES, _NATURE_KEYS):
            by_nature[nature] = {
                "submitted": _as_int(block.get(sub_k)),
                "dropped": _as_int(block.get(dropped_k)),
            }
        blocks.append(
            {
                "surface": surface,
                "source": prefix,
                "attacks_submitted": submitted,
                "attacks_retained": retained,
                "attacks_dropped": dropped,
                "by_nature": by_nature,
            }
        )

    # Since R791 item 1 the SAME declaration is projected on the curated
    # ``dung_frameworks`` entries AND sits in the bulk ``phase_results``. The
    # probe aggregates PER SURFACE (no cross-surface dedup): counting both
    # would double it, and the two surfaces agreeing is itself the check.
    # WITHIN a surface the same declaration is also replicated (curated carry
    # onto several entries, bulk one-per-axe over a shared candidate set), so
    # ``_aggregate`` dedups by fingerprint before summing and prints the
    # curated-vs-bulk agreement as a verdict (R792).
    frameworks = state.get("dung_frameworks")
    if isinstance(frameworks, dict):
        for df_id, entry in frameworks.items():
            if isinstance(entry, dict):
                _add("curated", f"dung_frameworks[{df_id}]", entry)

    reports = state.get("formal_synthesis_reports")
    if isinstance(reports, list):
        for rep in reports:
            if not isinstance(rep, dict):
                continue
            phase_results = rep.get("phase_results")
            if not isinstance(phase_results, dict):
                continue
            for axe, block in phase_results.items():
                if isinstance(block, dict):
                    _add("bulk", f"phase_results.{axe}", block)
    return blocks


def _fingerprint(b: Dict[str, Any]) -> Tuple[Any, ...]:
    """Hashable identity of a block's accounting (totals + per-nature).

    The curated carry projects one axe's accounting onto multiple framework
    entries, and the producer submits the SAME candidate set to several axes
    (``dung_extensions`` and ``social_reasoning`` each receive every
    candidate), so an identical accounting declaration appears several times
    per surface. Blocks that share a fingerprint are that replication;
    summing them raw multiplies the count by the replication factor — the
    #1019 aggregation defect measured in R792 (curated raw 468, bulk raw 78,
    real 39: a value true at every site, false the moment it is aggregated).
    The fingerprint uses numeric accounting only; source strings are never
    touched (privacy HARD).
    """
    nat = b["by_nature"]
    return (
        b["attacks_submitted"],
        b["attacks_retained"],
        b["attacks_dropped"],
        nat["fallacy"]["submitted"],
        nat["fallacy"]["dropped"],
        nat["ca"]["submitted"],
        nat["ca"]["dropped"],
        nat["other"]["submitted"],
        nat["other"]["dropped"],
    )


def _sum_accounting(
    blocks: List[Dict[str, Any]],
) -> "tuple[Dict[str, Any], bool]":
    """Sum totals + per-nature counts across blocks (None-aware).

    Returns ``(sums, nature_keys_present)`` — the flag is True iff at least
    one block carried a non-None per-nature key. Pre-instrumentation blocks
    have None natures and the split must render UNAVAILABLE (#1019).
    """
    sums: Dict[str, Any] = {
        "attacks_submitted": 0,
        "attacks_retained": 0,
        "attacks_dropped": 0,
        "by_nature": {n: {"submitted": 0, "dropped": 0} for n in _NATURES},
    }
    nature_present = False
    for b in blocks:
        for key in ("attacks_submitted", "attacks_retained", "attacks_dropped"):
            v = b[key]
            if v is not None:
                sums[key] += v
        for nature in _NATURES:
            for side in ("submitted", "dropped"):
                v = b["by_nature"][nature][side]
                if v is not None:
                    sums["by_nature"][nature][side] += v
                    nature_present = True
    return sums, nature_present


def _aggregate(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per surface with fingerprint dedup.

    The raw sum across blocks is NOT the candidate count: the same accounting
    declaration is replicated (curated carry onto several framework entries;
    bulk one-per-axe over a shared candidate set). Identical fingerprints are
    collapsed to one representative before summing — the deduped totals are
    the authoritative candidate counts. The raw (inflated) sum is kept as a
    diagnostic so the replication stays visible, and the two surfaces deduped
    must agree: that agreement is the check, printed as the inter-surface
    verdict by ``_render`` (R792).
    """
    out: Dict[str, Any] = {
        "blocks": len(blocks),
        "surfaces": {},
        "nature_keys_present": False,
    }
    per_surface: Dict[str, Dict[str, Any]] = {}
    for surface in ("curated", "bulk"):
        surface_blocks = [b for b in blocks if b.get("surface") == surface]
        raw_sums, _ = _sum_accounting(surface_blocks)
        # Dedup: one representative per distinct fingerprint.
        representatives: List[Dict[str, Any]] = []
        multiplicity: Dict[Tuple[Any, ...], int] = {}
        for b in surface_blocks:
            fp = _fingerprint(b)
            if fp not in multiplicity:
                multiplicity[fp] = 0
                representatives.append(b)
            multiplicity[fp] += 1
        dedup_sums, nature_present = _sum_accounting(representatives)
        if nature_present:
            out["nature_keys_present"] = True
        max_mult = max(multiplicity.values()) if multiplicity else 0
        agg = {
            "blocks": len(surface_blocks),
            "distinct_fingerprints": len(multiplicity),
            "max_multiplicity": max_mult,
            "replicated": max_mult > 1,
            # Per-surface nature-availability flag. The invariant
            # (sum(natures) == submitted) is only meaningful when this surface
            # actually carried per-nature keys; otherwise it would compare
            # 0 (None summed) against the real submitted total and print a
            # spurious MISMATCH — a verdict on a magnitude it never received
            # (#1019 one level up from the aggregation defect).
            "nature_keys_present": nature_present,
            # Deduped totals = authoritative candidate counts.
            "attacks_submitted": dedup_sums["attacks_submitted"],
            "attacks_retained": dedup_sums["attacks_retained"],
            "attacks_dropped": dedup_sums["attacks_dropped"],
            "by_nature": dedup_sums["by_nature"],
            # Raw (inflated) sum — diagnostic only, do NOT read as a count.
            "raw_attacks_submitted": raw_sums["attacks_submitted"],
            "raw_attacks_retained": raw_sums["attacks_retained"],
            "raw_attacks_dropped": raw_sums["attacks_dropped"],
            "raw_by_nature": raw_sums["by_nature"],
        }
        per_surface[surface] = agg
        out["surfaces"][surface] = agg
    out["inter_surface"] = _inter_surface_verdict(per_surface)
    return out


def _inter_surface_verdict(per_surface: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compare the two surfaces on their deduped totals.

    The agreement of the curated surface (what the conclusion reads) and the
    bulk surface (invoke outputs) is the check that the accounting is
    consistent end-to-end. A constant ratio across corpora of different
    values is a replication signature, not noise (R792)."""
    curated = per_surface.get("curated", {})
    bulk = per_surface.get("bulk", {})
    if not curated.get("blocks") or not bulk.get("blocks"):
        return {"comparable": False}
    agree = (
        curated["attacks_submitted"] == bulk["attacks_submitted"]
        and curated["attacks_retained"] == bulk["attacks_retained"]
        and curated["attacks_dropped"] == bulk["attacks_dropped"]
        and curated["by_nature"] == bulk["by_nature"]
    )
    ratio: Optional[float] = None
    cs = curated["attacks_submitted"]
    bs = bulk["attacks_submitted"]
    if bs and cs is not None:
        ratio = round(cs / bs, 2)
    return {
        "comparable": True,
        "agree": agree,
        "curated_submitted": cs,
        "bulk_submitted": bs,
        "ratio": ratio,
    }


def _report_doc(name: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    agg = _aggregate(blocks)
    agg["document"] = name
    return agg


def _render_surface(title: str, agg: Dict[str, Any]) -> List[str]:
    lines = [
        f"  {title} ({agg['blocks']} raw block(s), "
        f"{agg['distinct_fingerprints']} distinct fingerprint(s)):"
    ]
    lines.append(
        f"    totals (deduped): submitted={agg['attacks_submitted']} "
        f"retained={agg['attacks_retained']} "
        f"dropped={agg['attacks_dropped']}"
    )
    if agg["replicated"]:
        lines.append(
            f"    raw sum (inflated {agg['max_multiplicity']}x — do NOT read "
            f"as a count): submitted={agg['raw_attacks_submitted']}"
        )
    bn = agg["by_nature"]
    lines.append(
        "    split by source nature (submitted / dropped):\n"
        f"      fallacy: {bn['fallacy']['submitted']} / {bn['fallacy']['dropped']}\n"
        f"      ca:      {bn['ca']['submitted']} / {bn['ca']['dropped']}\n"
        f"      other:   {bn['other']['submitted']} / {bn['other']['dropped']}"
    )
    # Invariant: sum(natures) == submitted total (verifiable honesty). Printed
    # only when this surface carried per-nature keys — on a pre-instrumentation
    # surface the per-nature values are absent (summed to 0) and the invariant
    # would print a spurious MISMATCH, a verdict on a magnitude the surface
    # never declared (#1019 one level up from the aggregation defect).
    if agg.get("nature_keys_present"):
        sum_sub = (
            bn["fallacy"]["submitted"]
            + bn["ca"]["submitted"]
            + bn["other"]["submitted"]
        )
        match = "OK" if sum_sub == agg["attacks_submitted"] else "MISMATCH"
        lines.append(f"    invariant sum(natures) == submitted: {match}")
    else:
        lines.append("    invariant sum(natures) == submitted: N/A (split unavailable)")
    return lines


def _render(agg: Dict[str, Any], as_json: bool) -> str:
    if as_json:
        return json.dumps(agg, ensure_ascii=False, indent=2)
    lines = [f"document: {agg.get('document', '?')}"]
    surfaces = agg.get("surfaces", {})
    curated = surfaces.get("curated", {})
    bulk = surfaces.get("bulk", {})
    if curated:
        lines.extend(_render_surface("curated surface", curated))
    if bulk:
        lines.extend(_render_surface("bulk phase_results", bulk))
    if not lines[1:]:
        lines.append("  no accounting blocks found")
    # Inter-surface verdict — printed, not just computed. R792: the
    # disagreement between the curated and bulk surfaces (a constant ratio
    # across corpora) was the signature of the replication defect.
    verdict = agg.get("inter_surface", {})
    if verdict.get("comparable"):
        cs = verdict["curated_submitted"]
        bs = verdict["bulk_submitted"]
        if verdict["agree"]:
            lines.append(f"  inter-surface verdict: AGREE (curated==bulk=={cs})")
        else:
            ratio = verdict.get("ratio")
            ratio_str = f", ratio {ratio}x" if ratio is not None else ""
            lines.append(
                "  inter-surface verdict: DISAGREE "
                f"(curated={cs}, bulk={bs}{ratio_str})"
            )
    if not agg["nature_keys_present"] and (curated or bulk):
        lines.append(
            "  per-nature split: UNAVAILABLE on this snapshot — the accounting "
            "carries totals only (pre-#1698 R791 instrumentation). Re-run the "
            "corpus with the instrumented producer to obtain the split; no "
            "split is fabricated (#1019)."
        )
    return "\n".join(lines)


def _load_snapshot(line: str) -> Dict[str, Any]:
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON line: {exc}") from exc


def _looks_like_state_payload(obj: Any) -> bool:
    """A state export (``to_json()``) carries collection keys the probe reads
    (``dung_frameworks`` / ``formal_synthesis_reports`` / ``counter_arguments``).
    The LLM-Judge wrapper carries a ``state_snapshot`` field instead."""
    if not isinstance(obj, dict):
        return False
    if "state_snapshot" in obj and isinstance(obj["state_snapshot"], dict):
        return True
    return any(
        k in obj
        for k in ("dung_frameworks", "formal_synthesis_reports", "counter_arguments")
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", help="state JSON files")
    parser.add_argument(
        "--snapshots",
        action="store_true",
        help="paths are LLM-Judge iter*_snapshots.jsonl (one JSON object per line)",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="paths are JSONL where each line is a state export (to_json output)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    results: List[Dict[str, Any]] = []

    for path in args.paths:
        with open(path, encoding="utf-8") as f:
            if args.snapshots:
                for line in f:
                    if not line.strip():
                        continue
                    raw = _load_snapshot(line)
                    if not _looks_like_state_payload(raw):
                        continue
                    snapshot = raw.get("state_snapshot", raw)
                    doc = str(raw.get("document_name", raw.get("document_index", "?")))
                    blocks = _collect_accounting(snapshot)
                    results.append(_report_doc(doc, blocks))
            elif args.jsonl:
                for line in f:
                    if not line.strip():
                        continue
                    raw = _load_snapshot(line)
                    if not _looks_like_state_payload(raw):
                        continue
                    snapshot = raw.get("state_snapshot", raw)
                    doc = str(raw.get("document_name", raw.get("document_index", "?")))
                    blocks = _collect_accounting(snapshot)
                    results.append(_report_doc(doc, blocks))
            else:
                # Auto-detect: peek at the first non-blank line, dispatch.
                first_obj = None
                try:
                    first_obj = json.load(f)
                except json.JSONDecodeError:
                    # Try JSONL fallback.
                    f.seek(0)
                    for line in f:
                        if not line.strip():
                            continue
                        first_obj = _load_snapshot(line)
                        break
                if not _looks_like_state_payload(first_obj):
                    print(
                        f"{path}: not a state export (no state keys found)",
                        file=sys.stderr,
                    )
                    return 2
                snapshot = first_obj.get("state_snapshot", first_obj)
                doc = str(first_obj.get("document_name", path))
                blocks = _collect_accounting(snapshot)
                results.append(_report_doc(doc, blocks))

    if not results:
        print("no state snapshots found in the given paths", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    for agg in results:
        print(_render(agg, as_json=False))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
