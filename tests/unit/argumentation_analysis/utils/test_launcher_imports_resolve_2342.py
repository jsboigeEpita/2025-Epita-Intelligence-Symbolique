# -*- coding: utf-8 -*-
"""#2342 — every documented entry-point launcher imports modules that exist.

The class defect: a launcher whose lazy import points at a module deleted by a
refactor (``repair_extract_markers``, ``verify_extracts`` — both removed when
their logic moved to ``dev_tools``). The breakage is invisible to ``import
argumentation_analysis.utils`` (``utils/__init__`` imports the launcher MODULE,
not the dead symbol) and the verify launcher fails SILENTLY (exit 0) — the
worst shape, a chained caller believes it completed normally.

Resolution mirrors the three sys.path shapes a launcher really has: the repo
root (absolute ``argumentation_analysis.…`` imports), the file's own directory
and its parent (the CWD-relative ``from extract_repair.…`` pattern, made valid
by the launcher's own ``sys.path.insert``). An import is dangling only when NO
base resolves it. Third-party and stdlib names never match a directory next to
the file, so they are skipped by construction — no hardcoded allowlist to
drift.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
INTRA_REPO_TOP = {"argumentation_analysis", "project_core"}
LAUNCHER_DIRS = (
    REPO_ROOT / "argumentation_analysis" / "utils",
    REPO_ROOT / "scripts" / "orchestration",
    REPO_ROOT / "argumentation_analysis" / "scripts",
)


def _launcher_population():
    found = []
    for directory in LAUNCHER_DIRS:
        if directory.is_dir():
            found.extend(sorted(directory.glob("run_*.py")))
    return found


def _module_exists(base: Path, dotted: str) -> bool:
    candidate = base.joinpath(*dotted.split("."))
    return (candidate.with_suffix(".py")).is_file() or (
        candidate.is_dir() and (candidate / "__init__.py").is_file()
    )


def _is_intra_repo(module: str, file_dir: Path, file_parent: Path) -> bool:
    first = module.split(".")[0]
    if first in INTRA_REPO_TOP:
        return True
    return (file_dir / first).is_dir() or (file_parent / first).is_dir()


def _dangling_imports(path: Path):
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    file_dir = path.parent
    file_parent = path.parent.parent
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.append((node.module, node.lineno))
        elif isinstance(node, ast.Import):
            modules.extend((alias.name, node.lineno) for alias in node.names)
        for module, lineno in modules:
            if not _is_intra_repo(module, file_dir, file_parent):
                continue
            bases = [REPO_ROOT, file_dir, file_parent]
            if not any(_module_exists(base, module) for base in bases):
                yield module, lineno


def test_every_launcher_imports_modules_that_exist():
    population = _launcher_population()
    assert len(population) >= 5, (
        f"only {len(population)} launchers found under {LAUNCHER_DIRS} — "
        "the sweep surface is too small to mean anything"
    )

    dangling = {
        str(path.relative_to(REPO_ROOT)): list(_dangling_imports(path))
        for path in population
    }
    dangling = {rel: mods for rel, mods in dangling.items() if mods}

    assert not dangling, (
        "entry-point launchers importing modules absent from the tree "
        "(each entry: (module, line); a launcher that points into the void is "
        "silent debt — and one that exits 0 while broken is worse, #2342): "
        + "; ".join(f"{rel} -> {mods}" for rel, mods in sorted(dangling.items()))
    )


@pytest.mark.parametrize(
    "rel",
    [
        "scripts/orchestration/run_extract_repair.py",
        "scripts/orchestration/run_verify_extracts.py",
        "argumentation_analysis/scripts/run_verify_extracts_llm.py",
    ],
)
def test_known_launchers_stay_in_the_population(rel):
    """Population witnesses: the live launchers the #2342 verdict measured.

    The two superseded ``argumentation_analysis/utils/`` launchers were
    deleted by #2342's own fix; if one of these three moves or is renamed,
    the sweep above keeps running on whatever ``run_*.py`` exists — this
    witness reddens so the move is a decision, not drift.
    """
    assert (
        REPO_ROOT / rel
    ).exists(), f"{rel} disappeared — update the #2342 verdict if it was deliberate"
