"""The installed wheel supplies only approved public runtime resources (#2758)."""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_PATHS = {
    "agents/core/quality/ressources_argumentatives.json",
    "data/argumentum_taxonomy_provenance.json",
    "data/argumentum_fallacies_taxonomy.csv",
    "plugin_framework/core/plugins/standard/taxonomy_explorer/data/fallacy_families.yaml",
}


def test_installed_wheel_runtime_resources(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(ROOT),
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
            if name.startswith("argumentation_analysis/")
            and name.endswith((".yaml", ".yml", ".json", ".csv", ".enc"))
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
from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import TaxonomyExplorerPlugin
installed = Path(__import__('argumentation_analysis').__file__).resolve()
assert installed.is_relative_to(Path(__import__('sys').argv[1]).resolve()), installed
assert len(quality_evaluator.RESOURCES['connecteurs_pertinence']) > 10
assert get_taxonomy_path().is_file()
assert validate_taxonomy_file()
assert pinned_taxonomy_source()[1]
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
