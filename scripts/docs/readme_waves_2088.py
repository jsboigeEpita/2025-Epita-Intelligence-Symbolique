"""Mechanical wave computation for the #2088 README DAG (PR #2091, 3rd review).

The hand-built waves grouped nodes by lot intention and placed
``plugin_framework/core`` (wave 2) before its own work-child
``plugin_framework/core/plugins`` (wave 3). This script recomputes everything
from the directory tree so that mistake cannot recur silently:

- **creations** are re-derived from git exactly like
  ``inventory_argumentation_readmes.py`` (substantial dirs without ``README.md``);
- **renovations** are the 29 non-``courant`` verdicts of report §4
  (18 partiels + 11 périmés), embedded as constants;
- **links-only** is ``pipelines/orchestration`` (verdict courant — no
  renovation, but a links touch accompanies wave 2, so its parent must wait);
- **exclusions** are the report §5 explicit list: light/residual dirs whose
  dependency is satisfied — work edges pass *through* them.

Rule (report §5): ``wave(node) = 1 + max(wave of its work children)``, leaves
= 1, where a work child's work-parent is the nearest strict ancestor carrying
work (excluded ancestors are skipped). The instrument then checks EVERY work
edge mechanically: ``wave(parent) > wave(child)`` — exit 1 on any violation.

Usage:
    python scripts/docs/readme_waves_2088.py
"""

from __future__ import annotations

import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBTREE = "argumentation_analysis"
VENDORED_ROOTS = ("libs", "portable_jdk")
SUBSTANTIAL_MIN_FILES = 3

# Report §4 — the 29 READMEs to renovate (18 partiels + 11 périmés), relative
# to argumentation_analysis/.
RENOVATIONS = {
    # 11 périmés
    "agents",
    "agents/tools",
    "agents/tools/analysis",
    "agents/tools/analysis/new",
    "plugin_framework/agents",
    "plugin_framework/core/plugins",
    "scripts",
    "services/web_api",
    "ui",
    "ui/extract_editor",
    "utils/extract_repair",
    # 18 partiels
    "agents/core",
    "agents/core/informal",
    "agents/core/logic",
    "agents/core/pl",
    "agents/core/pm",
    "agents/docs",
    "config",
    "core",
    "core/communication",
    "orchestration",
    "orchestration/hierarchical",
    "orchestration/hierarchical/interfaces",
    "orchestration/hierarchical/operational",
    "orchestration/hierarchical/strategic",
    "pipelines",
    "services",
    "services/mcp_server",
    "utils",
}

# Report §5 — courant, no renovation; a links touch accompanies wave 2.
LINKS_ONLY = {"pipelines/orchestration"}

# Report §5 — explicit exclusions: light/residual dirs whose dependency is
# satisfied before their parents; work edges pass through them.
EXCLUSIONS = {
    "pipelines/orchestration/orchestrators",  # residual shell (#2055)
    "data/datasets",  # light shell around legacy_fixtures/
    "evaluation/corpus",  # light (<3 files, 0 .py)
    "agents/prompts",  # light, with subdirs
    "webapp/config",  # light
}


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    )
    return out.stdout


def _derive_creations() -> set[str]:
    """Substantial tracked dirs without README.md (git-only, as the inventory)."""
    files = _git("ls-files", "--", SUBTREE).splitlines()
    dirs: dict[str, set[str]] = defaultdict(set)
    for f in files:
        parts = f.split("/")
        if len(parts) < 3:  # file directly under argumentation_analysis/
            continue
        dirs["/".join(parts[1:-1])].add(f)
    creations = set()
    for d, members in dirs.items():
        if d.replace("\\", "/").split("/")[0] in VENDORED_ROOTS:
            continue
        py = any(m.endswith(".py") for m in members)
        if (
            len(members) >= SUBSTANTIAL_MIN_FILES or py
        ) and f"{SUBTREE}/{d}/README.md" not in members:
            creations.add(d)
    return creations


def _work_parent(node: str, work: set[str]) -> str | None:
    """Nearest strict ancestor carrying work, skipping excluded dirs."""
    parts = node.split("/")
    for i in range(len(parts) - 1, 0, -1):
        anc = "/".join(parts[:i])
        if anc in EXCLUSIONS:
            continue
        if anc in work:
            return anc
    return None


def main() -> int:
    creations = _derive_creations()
    work = creations | RENOVATIONS | LINKS_ONLY

    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for n in work:
        p = _work_parent(n, work)
        if p is None:
            roots.append(n)
        else:
            children[p].append(n)

    # wave(node) = 1 + max(wave of work children); leaves = 1.
    waves: dict[str, int] = {}

    def _wave(n: str) -> int:
        if n not in waves:
            waves[n] = 1 + max((_wave(c) for c in children[n]), default=0)
        return waves[n]

    for n in work:
        _wave(n)

    # Mechanical control: every work edge must be strictly increasing.
    violations = [
        (c, p) for p, cs in children.items() for c in cs if waves[p] <= waves[c]
    ]

    by_wave: dict[int, list[str]] = defaultdict(list)
    for n, w in waves.items():
        by_wave[w].append(n)

    print(
        f"# Waves over {len(work)} work nodes "
        f"({len(creations)} creations + {len(RENOVATIONS)} renovations "
        f"+ {len(LINKS_ONLY)} links-only)"
    )
    for w in sorted(by_wave):
        nodes = sorted(by_wave[w])
        creations_w = [n for n in nodes if n in creations]
        renovations_w = [n for n in nodes if n in RENOVATIONS]
        links_w = [n for n in nodes if n in LINKS_ONLY]
        print(
            f"\n## Vague {w} — {len(nodes)} nœuds "
            f"({len(creations_w)} créations, {len(renovations_w)} rénovations"
            + (f", {len(links_w)} liens" if links_w else "")
            + ")"
        )
        for label, group in (
            ("créations", creations_w),
            ("rénovations", renovations_w),
            ("liens", links_w),
        ):
            if group:
                print(f"- {label} : {', '.join(group)}")

    print("\n## Contrôle mécanique — chaque arête de travail")
    edge_ok = 0
    for p in sorted(children):
        for c in sorted(children[p]):
            ok = waves[p] > waves[c]
            edge_ok += ok
            print(
                f"- {'PASS' if ok else 'FAIL'} — {c} (v{waves[c]}) → {p} (v{waves[p]})"
            )
    print(
        f"\n{edge_ok}/{edge_ok + len(violations)} arêtes PASS ; "
        f"fermeture créations {sum(1 for n in creations if n in waves)}/{len(creations)}, "
        f"rénovations {sum(1 for n in RENOVATIONS if n in waves)}/{len(RENOVATIONS)}"
    )

    if violations:
        print(f"\n{len(violations)} arête(s) VIOLÉE(S) — DAG non topologique.")
        return 1
    print("\nToutes les arêtes de travail sont strictement croissantes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
