"""The installed wheel supplies only approved public runtime resources (#2758)."""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_PATHS = {
    "agents/core/quality/ressources_argumentatives.json",
    "data/argumentum_taxonomy_provenance.json",
    "data/argumentum_fallacies_taxonomy.csv",
    "data/taxonomy_medium.csv",
    "data/taxonomy_full.csv",
    "plugin_framework/core/plugins/standard/taxonomy_explorer/data/fallacy_families.yaml",
}


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
    subprocess.run(
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
        timeout=120,
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
    subprocess.run(
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
        timeout=60,
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
    result = subprocess.run(
        [sys.executable, "-c", script, str(target)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
