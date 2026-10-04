"""Calibration of the #1914 criteria-2/3/4 act controls on real renders.

Dispatch R1059: a control firing on ~100 % or ~0 % of real acts does not
discriminate — say so and do NOT wire it as a verdict. This producer walks
the seat's real restitution renders (gitignored evaluation results), runs
the three controls per act, and prints the aggregate table with OPAQUE ids
only (privacy HARD: no render text reaches any indexed surface; counts and
ids are the whole output — the --dump mode prints sentence text for LOCAL
truth-table classification only, never for a tracked surface).

R1060: the walk counts and reports every file it SKIPS, with the reason
(silent zeros) — a markdown file with no detectable act heading (any casing,
see the module) is skipped as such, not silently dropped.

Usage:
    python scripts/evaluation/calibrate_act_reader_contract_1914.py \
        [--results-dir argumentation_analysis/evaluation/results] [--dump]

Output goes to stdout (aggregate table + skipped-files table). Provenance:
this header IS the provenance record — rerun with the same tree for the
same numbers.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from argumentation_analysis.reporting.restitution.act_reader_contract_check import (  # noqa: E402
    _split_acts,
    check_act_reader_contract,
)


def _walk(results_dir: Path):
    """Yield (opaque id, text) for markdown files whose body carries at
    least one act heading (any casing — the module's own detection). Files
    are yielded with a skip reason when they carry none or cannot be read;
    nothing is dropped silently (R1060)."""
    for path in sorted(results_dir.rglob("*.md")):
        digest = hashlib.sha1(str(path.relative_to(results_dir)).encode()).hexdigest()
        rid = f"render_{digest[:8]}"
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            yield rid, None, "illisible"
            continue
        if not _split_acts(text.split("<details>")[0]):
            yield rid, None, "aucun titre d'acte"
            continue
        yield rid, text, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        default="argumentation_analysis/evaluation/results",
        help="gitignored evaluation results dir (opaque ids in output)",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="print each finding with its body line (LOCAL truth-table "
        "classification only — never paste dump output onto an indexed "
        "surface)",
    )
    args = parser.parse_args()
    results_dir = ROOT / args.results_dir
    if not results_dir.is_dir():
        print(f"no results dir at {results_dir}")
        return 1

    # per-control trigger counts + per-criterion kind histogram
    stats = {
        2: {"acts": 0, "triggers": 0, "findings": 0, "kinds": {}},
        3: {"acts": 0, "triggers": 0, "findings": 0, "kinds": {}},
        4: {"acts": 0, "triggers": 0, "findings": 0, "kinds": {}},
    }
    n_acts = 0
    skipped: list = []
    n_not_evaluated = 0
    dump_lines: list = []
    for render_id, text, skip in _walk(results_dir):
        if skip:
            skipped.append((render_id, skip))
            continue
        n_acts += 1
        findings = check_act_reader_contract(text)
        if any(f.criterion == 0 for f in findings):
            n_not_evaluated += 1
            continue
        if args.dump:
            body = text.split("<details>")[0]
            lines = body.splitlines()
            dump_lines.append(f"== {render_id}: {len(findings)} constats")
            for f in findings:
                line_text = (
                    lines[f.line - 1].strip()
                    if f.line <= len(lines)
                    else "<hors corps>"
                )
                if len(line_text) > 360:
                    line_text = line_text[:357] + "..."
                dump_lines.append(
                    f"[c{f.criterion} {f.kind} {f.act} L{f.line}] {line_text}"
                )
        for criterion in (2, 3, 4):
            subset = [f for f in findings if f.criterion == criterion]
            stats[criterion]["acts"] += 1
            if subset:
                stats[criterion]["triggers"] += 1
                stats[criterion]["findings"] += len(subset)
                for f in subset:
                    stats[criterion]["kinds"][f.kind] = (
                        stats[criterion]["kinds"].get(f.kind, 0) + 1
                    )

    print(f"# Calibration #1914 critères 2-4 — {n_acts} rendus évalués (ids opaques)")
    print()
    print("| Contrôle | Actes | Actes déclenchés | Taux | Constats totaux |")
    print("|---|---|---|---|---|")
    labels = {
        2: "critère 2 (citation formelle)",
        3: "critère 3 (étiquette sans fonction)",
        4: "critère 4 (forme classée Acte III)",
    }
    for criterion in (2, 3, 4):
        s = stats[criterion]
        rate = f"{(s['triggers'] / s['acts'] * 100):.0f} %" if s["acts"] else "n/a"
        print(
            f"| {labels[criterion]} | {s['acts']} | {s['triggers']} | {rate} | "
            f"{s['findings']} |"
        )
    print()
    for criterion in (2, 3, 4):
        if stats[criterion]["kinds"]:
            histogram = ", ".join(
                f"{k}={v}" for k, v in sorted(stats[criterion]["kinds"].items())
            )
            print(f"- critère {criterion} par forme : {histogram}")
    # R1060 (c): the skipped files are counted, with their reason — a
    # calibration that quietly narrows its population measures nothing.
    print()
    print(f"Fichiers écartés : {len(skipped)}" + (" (aucun)" if not skipped else ""))
    for rid, reason in skipped:
        print(f"- {rid} : {reason}")
    if n_not_evaluated:
        print(f"Rendus non évalués (enveloppe critère 0) : {n_not_evaluated}")
    if args.dump:
        print()
        print("## Dump par constat (usage local uniquement)")
        print()
        print("\n".join(dump_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
