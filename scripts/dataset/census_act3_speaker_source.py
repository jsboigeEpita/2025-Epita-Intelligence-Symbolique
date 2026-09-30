"""#2845 — reach census: did each run's Acte III prompt carry the source it names?

Rebuilds Acte III's prompt from every stored state dump (deterministic: no LLM,
no JVM, no network) and reports, per run, whether the prompt carries the
recorded source metadata — the substrate the prompt's own instruction (« nomme
le locuteur et l'arène (via les métadonnées) ») presupposes. Before the fix the
block did not exist, so the census reads 0 of N: that is the hole's reach, and
it is why the writer resolved the instruction against the extracts, where a
reply names only the interlocutor.

Privacy (#2168): this producer is TRACKED, so it prints counts, booleans and the
opaque dump ids the filenames already carry — never a metadata value, never a
prompt line. The dumps it reads are gitignored local artifacts.

Usage (from a checkout root; the dumps directory is a local artifact):

    python scripts/dataset/census_act3_speaker_source.py \
        --state-dumps-dir analysis_kb/state_dumps --since 2026-09-29

    # the after-fix gate form — exits non-zero if any run is still unsubstrated
    python scripts/dataset/census_act3_speaker_source.py --require-block
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (  # noqa: E402
    build_act3_evidence,
    build_act3_prompt,
)

BLOCK_HEADER = "MÉTADONNÉES DE LA SOURCE"
_API = "argumentation_analysis/reporting/restitution/act3_conclusion_plugin.py"


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60
        )
        return out.stdout.strip()
    except Exception:  # pragma: no cover - a missing git is reported, not raised
        return ""


def _provenance(args: argparse.Namespace, considered: list[Path]) -> str:
    head = _git("rev-parse", "HEAD") or "unknown"
    dirty = _git("status", "--porcelain", "--", _API)
    window = "unknown"
    if considered:
        stamps = sorted(p.stat().st_mtime for p in considered)
        fmt = lambda s: _dt.datetime.fromtimestamp(s).strftime(
            "%Y-%m-%d %H:%M"
        )  # noqa: E731
        window = f"{fmt(stamps[0])} .. {fmt(stamps[-1])} (file mtimes)"
    return (
        "# census_act3_speaker_source.py — #2845\n"
        f"# repo HEAD       : {head} ({'dirty on ' + _API if dirty else 'clean on the Acte III module'})\n"
        f"# command         : {' '.join(sys.argv)}\n"
        f"# dumps directory : {args.state_dumps_dir}\n"
        f"# window          : {window}\n"
        "# LLM requests    : 0 (pure state reading)\n"
        "# prints          : counts, booleans, opaque ids — never a metadata value\n"
    )


def _recorded(dump: dict) -> dict:
    meta = dump.get("source_metadata") or {}
    if not isinstance(meta, dict):
        return {}
    return {
        str(k): str(v)
        for k, v in meta.items()
        if v and str(v).strip() and str(v).strip().lower() != "unknown"
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dumps-dir", default="analysis_kb/state_dumps")
    parser.add_argument(
        "--since",
        default="",
        help="keep only dumps whose FILE mtime is on/after this date (YYYY-MM-DD). "
        "The dumps carry no run stamp; this is an mtime filter and is reported as one.",
    )
    parser.add_argument(
        "--require-block",
        action="store_true",
        help="exit non-zero when a run's prompt lacks the metadata block",
    )
    args = parser.parse_args()

    directory = Path(args.state_dumps_dir)
    if not directory.is_dir():
        print(f"missing dumps directory: {directory}", file=sys.stderr)
        return 2

    paths = sorted(directory.glob("state_full_*.json"))
    if args.since:
        floor = _dt.datetime.strptime(args.since, "%Y-%m-%d").timestamp()
        paths = [p for p in paths if p.stat().st_mtime >= floor]

    print(_provenance(args, paths))
    print(f"# population: {len(paths)} dump(s)")

    with_recorded = 0
    with_block = 0
    fully_carried = 0
    unreadable = 0
    missing: list[str] = []

    for path in paths:
        try:
            dump = json.loads(path.read_text(encoding="utf-8"))
            prompt = build_act3_prompt(
                build_act3_evidence(types.SimpleNamespace(**dump))
            )
        except Exception as exc:  # a dump this script cannot read is reported
            unreadable += 1
            print(f"  {path.stem:34s} UNREADABLE ({type(exc).__name__})")
            continue
        fields = _recorded(dump)
        carried = sum(1 for value in fields.values() if value in prompt)
        block = BLOCK_HEADER in prompt
        with_recorded += 1 if fields else 0
        with_block += 1 if block else 0
        fully_carried += 1 if fields and carried == len(fields) else 0
        if not block:
            missing.append(path.stem)
        print(
            f"  {path.stem:34s} recorded={len(fields):2d} carried={carried:2d} "
            f"block={'yes' if block else 'NO'}"
        )

    print()
    print(f"dumps considered                 : {len(paths)}")
    print(f"  unreadable                     : {unreadable}")
    print(f"  recorded a source (non-unknown): {with_recorded}")
    print(f"  prompt carries the block       : {with_block}")
    print(f"  every recorded field carried   : {fully_carried}")
    if missing:
        print(f"  WITHOUT the block              : {len(missing)}")
    if args.require_block and missing:
        print(
            "\nFAIL: run(s) whose Acte III prompt is not substrated:", file=sys.stderr
        )
        for stem in missing:
            print(f"  {stem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
