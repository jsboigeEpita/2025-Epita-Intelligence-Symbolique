"""#2720 — a tracked config file may not name a class that does not exist.

``config/orchestration_config.yaml`` declared ``agents.*.class`` entries
naming classes that exist nowhere (``EnhancedProjectManagerAgent`` — the
enhanced-PM stack retired in #2638/#2704 — and ``SynthesisAgent``, removed
by #2140); its only reader was a one-shot migration script nothing launches.
Both left with a Cleanup Gate table; this witness is the shape check the
issue asks for: every ``class:``/``class_name:`` value in every tracked
YAML config must be a class defined somewhere in the tracked Python
sources. No class list lives here — both sides are derived from the tree.

A config that returns naming a dead class reddens this witness, whatever
the file.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CLASS_KEY = re.compile(
    r"^\s*(?:class|class_name):\s*[\"']?([A-Za-z_]\w+)[\"']?\s*$", re.MULTILINE
)
_DEFINED_CLASS = re.compile(r"^\s*class\s+([A-Za-z_]\w+)", re.MULTILINE)
_EXCLUDED_DIRS = {
    "node_modules",
    "build",
    "dist",
    ".git",
    "__pycache__",
    "portable_jdk",
    "libs",
}


def _yaml_configs() -> list:
    return [
        p
        for p in _REPO_ROOT.rglob("*.y*ml")
        if not any(part in _EXCLUDED_DIRS for part in p.parts)
    ]


def _defined_classes() -> set:
    names = set()
    for p in _REPO_ROOT.rglob("*.py"):
        if any(part in _EXCLUDED_DIRS for part in p.parts):
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
