"""#2720 — a tracked config file may not name a class that does not exist.

``config/orchestration_config.yaml`` declared ``agents.*.class`` entries
naming classes that exist nowhere (``EnhancedProjectManagerAgent`` — the
enhanced-PM stack retired in #2638/#2704 — and ``SynthesisAgent``, removed
by #2140); its only reader was a one-shot migration script nothing launches.
Both left with a Cleanup Gate table; this witness is the shape check the
issue asks for: every ``class:``/``class_name:`` value in every tracked
YAML config must be a class defined somewhere in the tracked Python
sources. No class list lives here — both sides are derived from the tree.

The tree is read through ``tests.support.tree_walk.iter_tracked_files`` —
the population comes from the git index, not the filesystem (#2821). A
filesystem walk also read gitignored seat-local files: this census collected
31 cases on a seat holding ``.playwright-mcp/`` page snapshots against 24 in
a clean worktree of the same commit, and a config naming a class that exists
only in a seat-local untracked file passed here while failing on CI. The
index lists neither, and never enters ``.git`` either. The vendored prefixes
below stay: ``libs`` and ``portable_jdk`` are tracked, so the index still
needs them named.

A config that returns naming a dead class reddens this witness, whatever
the file.
"""

import re
from pathlib import Path

import pytest

from tests.support.tree_walk import iter_tracked_files

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CLASS_KEY = re.compile(
    r"^\s*(?:class|class_name):\s*[\"']?([A-Za-z_]\w+)[\"']?\s*$", re.MULTILINE
)
_DEFINED_CLASS = re.compile(r"^\s*class\s+([A-Za-z_]\w+)", re.MULTILINE)
_SKIPPED_PREFIXES = (
    "_probe_",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    "portable_jdk",
    "libs",
)


def _yaml_configs(root: Path = _REPO_ROOT) -> list:
    return list(
        iter_tracked_files(root, "*.yaml", skip_prefixes=_SKIPPED_PREFIXES)
    ) + list(iter_tracked_files(root, "*.yml", skip_prefixes=_SKIPPED_PREFIXES))


def _defined_classes(root: Path = _REPO_ROOT) -> set:
    names = set()
    for p in iter_tracked_files(root, "*.py", skip_prefixes=_SKIPPED_PREFIXES):
        try:
            names.update(
                _DEFINED_CLASS.findall(p.read_text(encoding="utf-8", errors="replace"))
            )
        except OSError:
            continue
    return names


@pytest.mark.parametrize(
    "config_path", _yaml_configs(), ids=lambda p: str(p.relative_to(_REPO_ROOT))
)
def test_config_class_names_exist(config_path: Path) -> None:
    declared = _CLASS_KEY.findall(
        config_path.read_text(encoding="utf-8", errors="replace")
    )
    if not declared:
        pytest.skip("no class: keys in this config")
    defined = _defined_classes()
    dead = [name for name in declared if name not in defined]
    assert not dead, (
        f"{config_path.relative_to(_REPO_ROOT)} names classes that exist nowhere "
        f"in the tracked sources: {dead}. A config entry pointing at a missing "
        "class is dead surface — fix or retire the entry (Cleanup Gate if the "
        "whole file goes)."
    )
