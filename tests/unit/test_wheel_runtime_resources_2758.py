"""The installed wheel supplies only approved public runtime resources (#2758)."""

import ast
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_PATHS = {
    "agents/core/quality/ressources_argumentatives.json",
    "data/argumentum_taxonomy_provenance.json",
    "data/argumentum_fallacies_taxonomy.csv",
    "data/taxonomy_medium.csv",
    "data/taxonomy_full.csv",
    "plugin_framework/core/plugins/standard/taxonomy_explorer/data/fallacy_families.yaml",
}

# The three external steps carry a hang guard, not a performance assertion: their
# cost follows what the machine shares (disk, CPU, virus scanner), not the property
# guarded here. Measured 2026-11-26 (#3698): the wheel step takes 59 s alone and
# overran a fixed 120 s under four xdist workers.
BASE_BUDGETS = {"wheel": 120, "install": 60, "import": 60}
# The cap keeps the three steps under `pytest.ini`'s own `--timeout`: a wider inner
# budget would let pytest kill the test before the guard names the step that hung.
MAX_WORKER_FACTOR = 3


def _hang_guard(step: str) -> int:
    """The budget of one step, scaled by the xdist workers that share the machine."""
    workers = int(os.environ.get("PYTEST_XDIST_WORKER_COUNT") or 1)
    return BASE_BUDGETS[step] * max(1, min(workers, MAX_WORKER_FACTOR))


def _run(
    step: str, argv: list[str], **kwargs: Any
) -> "subprocess.CompletedProcess[Any]":
    try:
        return subprocess.run(argv, timeout=_hang_guard(step), **kwargs)
    except subprocess.TimeoutExpired as exc:
        budget = _hang_guard(step)
        raise AssertionError(
            f"the {step} step exceeded its {budget}s hang guard "
            f"({BASE_BUDGETS[step]}s base, {budget // BASE_BUDGETS[step]} shared workers); "
            "a hang guard firing says the machine was slow, not that the wheel is wrong"
        ) from exc


def test_installed_wheel_runtime_resources(tmp_path: Path) -> None:
    # The checkout's build/lib and egg-info must not affect this distribution.
    source = tmp_path / "source"
    source.mkdir()
    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--",
            "argumentation_analysis",
            "pyproject.toml",
            "README.md",
            "LICENSE",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    for name in tracked.decode("utf-8").split("\0"):
        if not name:
            continue
        if name == "argumentation_analysis/data/extract_sources.json.gz.enc":
            placeholder = source / name
            placeholder.parent.mkdir(parents=True, exist_ok=True)
            placeholder.write_bytes(b"packaging exclusion sentinel")
            continue
        original = ROOT / name
        if original.is_file():
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination)
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    _run(
        "wheel",
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(source),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_dir.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        packaged = {
            name.removeprefix("argumentation_analysis/")
            for name in names
            if name.startswith("argumentation_analysis/") and not name.endswith(".py")
        }
        assert packaged == RESOURCE_PATHS
        assert not any(
            "extract_sources" in name or "/results/" in name for name in names
        )

    target = tmp_path / "installed"
    _run(
        "install",
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target),
            str(wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    script = """
from pathlib import Path
from argumentation_analysis.utils.taxonomy_loader import (
    get_taxonomy_path, pinned_taxonomy_source, validate_taxonomy_file,
)
from argumentation_analysis.agents.core.quality import quality_evaluator
from argumentation_analysis.adapters import french_fallacy_adapter
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import _load_name_to_family
from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import TaxonomyExplorerPlugin
installed = Path(__import__('argumentation_analysis').__file__).resolve()
assert installed.is_relative_to(Path(__import__('sys').argv[1]).resolve()), installed
assert len(quality_evaluator.RESOURCES['connecteurs_pertinence']) > 10
assert get_taxonomy_path().is_file()
assert validate_taxonomy_file()
assert pinned_taxonomy_source()[1]
assert len(french_fallacy_adapter._load_taxonomy_labels()) > 13
assert french_fallacy_adapter._load_taxonomy_hierarchy()
assert _load_name_to_family()
plugin = TaxonomyExplorerPlugin.__new__(TaxonomyExplorerPlugin)
plugin.families = {}
import logging
plugin.logger = logging.getLogger('wheel-test')
plugin._load_families()
assert len(plugin.families) >= 8
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(target)
    env["OPENAI_API_KEY"] = ""
    env["OPENROUTER_API_KEY"] = ""
    result = _run(
        "import",
        [sys.executable, "-c", script, str(target)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-2000:]


# --- the hang guard of the three external steps (#3698) ---------------------


def _suite_timeout_seconds() -> int:
    """The outer bound `pytest.ini` poses; the inner guards must stay under it."""
    text = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    match = re.search(r"--timeout=(\d+)", text)
    assert match, "pytest.ini no longer declares a --timeout: the outer bound is gone"
    return int(match.group(1))


def test_hang_guard_scales_with_the_workers_that_share_the_machine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_XDIST_WORKER_COUNT", raising=False)
    alone = _hang_guard("wheel")
    assert alone == BASE_BUDGETS["wheel"]
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "3")
    assert _hang_guard("wheel") == alone * 3
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "4")
    assert _hang_guard("wheel") == alone * MAX_WORKER_FACTOR


def test_hang_guard_is_capped_below_the_suite_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "1")
    alone = {step: _hang_guard(step) for step in BASE_BUDGETS}
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "12")
    crowded = {step: _hang_guard(step) for step in BASE_BUDGETS}
    assert crowded == {step: alone[step] * MAX_WORKER_FACTOR for step in BASE_BUDGETS}
    assert sum(crowded.values()) < _suite_timeout_seconds(), (
        f"the three steps would take {sum(crowded.values())}s of budgets while pytest kills "
        f"the test at {_suite_timeout_seconds()}s: the step that hung would never be named"
    )


def test_a_fired_guard_names_its_step_and_its_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "1")
    monkeypatch.setitem(BASE_BUDGETS, "wheel", 1)
    with pytest.raises(AssertionError) as excinfo:
        _run(
            "wheel",
            [sys.executable, "-c", "import time; time.sleep(10)"],
            capture_output=True,
            text=True,
        )
    message = str(excinfo.value)
    assert "wheel" in message, message
    assert "1s" in message, message


def test_every_external_step_routes_through_the_hang_guard() -> None:
    """A fixed `timeout=` on a subprocess call is the defect this file guards."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    guarded: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "_run":
            first = node.args[0] if node.args else None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                guarded.add(first.value)
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "run"):
            continue
        for keyword in node.keywords:
            if keyword.arg != "timeout":
                continue
            # Only the derived guard may feed a timeout: a literal is the defect,
            # including a literal reintroduced inside `_run` itself.
            assert (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "_hang_guard"
            ), f"line {node.lineno}: a subprocess call carries a fixed timeout"
    assert guarded == set(BASE_BUDGETS), guarded
