"""Re-derive the zero-shot surplus aggregate from a signatures directory (#2844).

The corpus batch persists one ``signature_<opaque_id>.json`` per document, each
carrying ``zero_shot_surplus`` — the projection derived at run time by
``conclusion_salience.projection_from_state``. That persisted projection is a
snapshot of the reader *as it was on the day of the run*: when the reader is
repaired, the stored aggregates describe the old behaviour and the corpus has to
be re-read through the new code to say what it now says.

This is that re-read, and it costs nothing: the reader is deterministic (no LLM,
no JVM), and each signature carries the sanitized state it was derived from, so
re-deriving needs no re-run of the corpus and no paid call. The script prints,
for the same population:

* the **stored** aggregate (what the runs persisted — the old reader), and
* the **re-derived** aggregate (the same production renderer,
  ``run_corpus_batch.render_surplus_aggregate``, on projections recomputed
  from each signature's state), and
* the **agreement census** between the two readers of one state: an axis the
  honest-absence ledger files ``degraded`` (``evaluated_empty`` /
  ``evaluated_degenerate``, #1671/#1647) must not also be counted as an
  established ``structural`` surplus item. ``#2844`` fixed the case where it
  was; the census is what keeps it fixed on real data.

Usage (from the checkout root, env ``projet-is-roo-new``)::

    python scripts/dataset/rederive_surplus_aggregate.py \\
        --signatures-dir .analysis_kb/signatures

Privacy: reads only the sanitized state a signature already carries and prints
counts, never a statement and never a document identifier beyond the opaque id
the signature itself uses. Writes nothing to disk.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (  # noqa: E402
    _ABSENT_DIMENSION_LABELS,
    _axis_label,
)
from argumentation_analysis.reporting.restitution.conclusion_salience import (  # noqa: E402
    projection_from_state,
)
from scripts.dataset.run_corpus_batch import (  # noqa: E402
    render_surplus_aggregate,
)

_LABEL_TO_CAPABILITY = {
    _axis_label(capability): capability for capability in _ABSENT_DIMENSION_LABELS
}
_STRUCTURAL = "structural"


def _git(args: List[str]) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001 — a provenance probe never fails the run
        return "unknown"


def _provenance_header(kept: int, args: argparse.Namespace) -> str:
    dirty = "dirty" if _git(["status", "--porcelain"]) else "clean"
    return (
        "# Zero-shot surplus aggregate — re-derived (#2844)\n"
        f"# head: {_git(['rev-parse', '--short', 'HEAD']) or 'unknown'} ({dirty})\n"
        f"# command: python scripts/dataset/rederive_surplus_aggregate.py "
        f"--signatures-dir {args.signatures_dir}"
        + (f" --run-started-utc {args.run_started_utc}" if args.run_started_utc else "")
        + "\n"
        "# reader: argumentation_analysis.reporting.restitution"
        ".conclusion_salience.projection_from_state (deterministic, no LLM, no JVM)\n"
        "# state source: the sanitized state each signature already carries\n"
        f"# signatures kept: {kept}\n"
        "# llm requests: 0 (this script makes none)\n"
    )


def load_signatures(
    signatures_dir: Path, run_started_utc: Optional[str]
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path in sorted(signatures_dir.glob("signature_*.json")):
        signature = json.loads(path.read_text(encoding="utf-8"))
        if run_started_utc:
            started = (signature.get("provenance") or {}).get("run_started_utc") or ""
            if not started.startswith(run_started_utc):
                continue
        out.append(signature)
    return out


def rederive(signature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The projection the CURRENT reader derives from the signature's state."""
    state = signature.get("state")
    if not isinstance(state, dict) or not state:
        return None
    try:
        return projection_from_state(SimpleNamespace(**state))
    except Exception:  # noqa: BLE001 — an unreadable state is named, not hidden
        return None


def census(signatures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The two readers of one state, cross-checked per document.

    Reader A (presence): the capabilities the surplus projection cites on a
    ``structural`` item. Reader B (honest absence): the capabilities the
    ``structured_arg_status`` ledger files ``degraded``. A document where the
    same capability is in both means one run is described two ways — the
    defect #2844 repaired. Returns counts and the disagreeing documents by
    opaque id (never a statement).
    """
    disagreements: List[str] = []
    unreadable = 0
    degraded_per_doc = 0
    for signature in signatures:
        projection = rederive(signature)
        if projection is None:
            unreadable += 1
            continue
        ledger = (signature.get("state") or {}).get("structured_arg_status") or {}
        degraded = {
            str(capability)
            for capability, info in ledger.items()
            if isinstance(info, dict) and info.get("degraded")
        }
        if degraded:
            degraded_per_doc += 1
        cited = {
            _LABEL_TO_CAPABILITY.get(item["cites"][0], item["cites"][0])
            for item in projection.get("established_items") or []
            if item.get("nature") == _STRUCTURAL and item.get("cites")
        }
        overlap = sorted(cited & degraded)
        if overlap:
            disagreements.append(
                "{}: {}".format(signature.get("opaque_id"), ", ".join(overlap))
            )
    return {
        "documents": len(signatures),
        "unreadable_state": unreadable,
        "documents_with_a_degraded_axis": degraded_per_doc,
        "documents_where_a_degraded_axis_is_cited_as_structural": len(disagreements),
        "disagreeing_documents": disagreements,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--signatures-dir",
        default=".analysis_kb/signatures",
        help="directory holding signature_<opaque_id>.json files",
    )
    parser.add_argument(
        "--run-started-utc",
        default=None,
        help="keep only the signatures whose provenance.run_started_utc starts "
        "with this prefix (a whole campaign under one timestamp)",
    )
    args = parser.parse_args(argv)

    signatures_dir = Path(args.signatures_dir)
    if not signatures_dir.is_dir():
        print("no such directory: {}".format(signatures_dir), file=sys.stderr)
        return 2
    signatures = load_signatures(signatures_dir, args.run_started_utc)
    if not signatures:
        print(
            "no signature matched {} (run_started_utc={!r})".format(
                signatures_dir, args.run_started_utc
            ),
            file=sys.stderr,
        )
        return 2

    print(_provenance_header(len(signatures), args))
    print("stored (as persisted by the runs):")
    print("  " + render_surplus_aggregate(signatures))

    rederived: List[Dict[str, Any]] = []
    for signature in signatures:
        projection = rederive(signature)
        if projection is None:
            projection = {
                "established_items": [],
                "established_by_nature": {},
                "procedural_items": 0,
                "carries_non_procedural_surplus": False,
                "unavailable_reason": "state missing or unreadable in the signature",
            }
        else:
            projection = dict(projection)
        clone = dict(signature)
        clone["zero_shot_surplus"] = projection
        rederived.append(clone)

    print("re-derived (current reader, per signature state):")
    print("  " + render_surplus_aggregate(rederived))

    report = census(signatures)
    print("two-reader census (presence surplus vs honest-absence ledger):")
    print(
        "  {documents} document(s); {n} with a degraded axis; "
        "{d} where a degraded axis is also counted as established structural "
        "surplus; {u} with an unreadable state".format(
            documents=report["documents"],
            n=report["documents_with_a_degraded_axis"],
            d=report["documents_where_a_degraded_axis_is_cited_as_structural"],
            u=report["unreadable_state"],
        )
    )
    for line in report["disagreeing_documents"]:
        print("  DISAGREES {}".format(line))
    return (
        0 if not report["documents_where_a_degraded_axis_is_cited_as_structural"] else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
