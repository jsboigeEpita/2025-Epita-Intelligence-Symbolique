"""#2720 — a tracked config file may not name a class that does not exist.

``config/orchestration_config.yaml`` declared ``agents.*.class`` entries
naming classes that exist nowhere (``EnhancedProjectManagerAgent`` — the
enhanced-PM stack retired in #2638/#2704 — and ``SynthesisAgent``, removed
by #2140); its only reader was a one-shot migration script nothing launches.
Both left with a Cleanup Gate table; this witness is the shape check the
issue asks for: every ``class:``/``class_name:`` value in every tracked
YAML config must be a class defined somewhere in the tracked Python
sources. No class list lives here — both sides are derived from the tree.

The tree is walked through ``tests.support.tree_walk.iter_files`` — the
#2607 common walk. It never follows directory symlinks, so the recursive
``node_modules`` link npm workspaces leave (present in CI, absent locally —
``WinError 1921``, run 36298081443) cannot kill collection, and the
vendored prefixes below keep the walk out of ``node_modules`` and the other
non-source trees.

A config that returns naming a dead class reddens this witness, whatever
the file.
"""

import re
from pathlib import Path

import pytest

from tests.support.tree_walk import iter_files

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


def _not_vcs_internal(path: Path) -> bool:
    # ``.git`` cannot be a skip_prefix: startswith(".git") also matches
    # ``.github``, which silently dropped six workflow YAMLs from this
    # witness's coverage (measured 18 vs 24 files).
    return ".git" not in path.parts


def _yaml_configs() -> list:
    return [
        p
        for p in list(iter_files(_REPO_ROOT, "*.yaml", skip_prefixes=_SKIPPED_PREFIXES))
        + list(iter_files(_REPO_ROOT, "*.yml", skip_prefixes=_SKIPPED_PREFIXES))
        if _not_vcs_internal(p)
    ]


def _defined_classes() -> set:
    names = set()
    for p in iter_files(_REPO_ROOT, "*.py", skip_prefixes=_SKIPPED_PREFIXES):
        if not _not_vcs_internal(p):
            continue
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
