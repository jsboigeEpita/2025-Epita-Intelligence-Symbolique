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
from typing import Any, Dict, List, Optional

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
    # ``dung_frameworks`` entry AND sits in the bulk ``phase_results`` — the
    # probe aggregates PER SURFACE (no cross-surface dedup): counting both
    # would double it, and the two surfaces agreeing is itself the check.
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


def _aggregate(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sum totals + per-nature counts across blocks (None-aware)."""
    out: Dict[str, Any] = {
        "blocks": len(blocks),
        "surfaces": {},
        "nature_keys_present": False,
    }
    for surface in ("curated", "bulk"):
        surface_blocks = [b for b in blocks if b.get("surface") == surface]
        agg: Dict[str, Any] = {
            "blocks": len(surface_blocks),
            "attacks_submitted": 0,
            "attacks_retained": 0,
            "attacks_dropped": 0,
            "by_nature": {n: {"submitted": 0, "dropped": 0} for n in _NATURES},
        }
        for b in surface_blocks:
            for k in ("attacks_submitted", "attacks_retained", "attacks_dropped"):
                v = b[k]
                if v is not None:
                    agg[k] += v
            for nature in _NATURES:
                for side in ("submitted", "dropped"):
                    v = b["by_nature"][nature][side]
                    if v is not None:
                        agg["by_nature"][nature][side] += v
                        out["nature_keys_present"] = True
        out["surfaces"][surface] = agg
    return out


def _report_doc(name: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    agg = _aggregate(blocks)
    agg["document"] = name
    return agg


def _render_surface(title: str, agg: Dict[str, Any]) -> List[str]:
    lines = [f"  {title} ({agg['blocks']} block(s)):"]
    lines.append(
        f"    totals: submitted={agg['attacks_submitted']} "
        f"retained={agg['attacks_retained']} "
        f"dropped={agg['attacks_dropped']}"
    )
    sub_f, drop_f = (
        agg["by_nature"]["fallacy"]["submitted"],
        agg["by_nature"]["fallacy"]["dropped"],
    )
    sub_c, drop_c = (
        agg["by_nature"]["ca"]["submitted"],
        agg["by_nature"]["ca"]["dropped"],
    )
    sub_o, drop_o = (
        agg["by_nature"]["other"]["submitted"],
        agg["by_nature"]["other"]["dropped"],
    )
    lines.append(
        "    split by source nature (submitted / dropped):\n"
        f"      fallacy: {sub_f} / {drop_f}\n"
        f"      ca:      {sub_c} / {drop_c}\n"
        f"      other:   {sub_o} / {drop_o}"
    )
    # Invariant: sum(natures) == submitted total (verifiable honesty).
    sum_sub = sub_f + sub_c + sub_o
    match = "OK" if sum_sub == agg["attacks_submitted"] else "MISMATCH"
    lines.append(f"    invariant sum(natures) == submitted: {match}")
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
                    print(f"{path}: not a state export (no state keys found)", file=sys.stderr)
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
