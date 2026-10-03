"""Calibration of the #1914 criteria-2/3/4 act controls on real renders.

Dispatch R1059: a control firing on ~100 % or ~0 % of real acts does not
discriminate — say so and do NOT wire it as a verdict. This producer walks
the seat's real restitution renders (gitignored evaluation results), runs
the three controls per act, and prints the aggregate table with OPAQUE ids
only (privacy HARD: no render text reaches any indexed surface; counts and
ids are the whole output).

Usage:
    python scripts/evaluation/calibrate_act_reader_contract_1914.py \
        [--results-dir argumentation_analysis/evaluation/results]

Output goes to stdout (aggregate table). Provenance: this header IS the
provenance record — rerun with the same tree for the same numbers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from argumentation_analysis.reporting.restitution.act_reader_contract_check import (  # noqa: E402
    check_act_reader_contract,
)

_ACT_MARKER = "## Acte "


def _real_act_renders(results_dir: Path):
    """Markdown files under the results dir whose body carries the three-act
    headings — opaque id = path stem + short hash of the relative path."""
    import hashlib

    for path in sorted(results_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        if text.count(_ACT_MARKER) < 3:
            continue
        digest = hashlib.sha1(str(path.relative_to(results_dir)).encode()).hexdigest()
        yield f"render_{digest[:8]}", text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        default="argumentation_analysis/evaluation/results",
        help="gitignored evaluation results dir (opaque ids in output)",
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
    for render_id, text in _real_act_renders(results_dir):
        n_acts += 1
        findings = check_act_reader_contract(text)
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

    print(f"# Calibration #1914 critères 2-4 — {n_acts} rendus réels (ids opaques)")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
