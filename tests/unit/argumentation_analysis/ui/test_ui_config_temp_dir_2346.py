"""``ui.config.TEMP_DOWNLOAD_DIR`` comes from the settings (#2346).

``settings.ui.temp_download_dir`` is a ``Path``. The module used to accept it
only as a ``str``, so every run fell back to ``_temp/downloads_mock``, and
``UI_TEMP_DOWNLOAD_DIR`` changed nothing.
"""

import os
import subprocess
import sys
import warnings
from pathlib import Path

from argumentation_analysis.config.settings import settings

ROOT = Path(__file__).resolve().parents[4]

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from argumentation_analysis.ui import config as ui_config


def test_the_directory_is_the_settings_value_under_the_project_root():
    assert ui_config.TEMP_DOWNLOAD_DIR == (
        ui_config.PROJECT_ROOT / settings.ui.temp_download_dir
    )


def test_the_environment_variable_reaches_the_directory(tmp_path):
    wanted = tmp_path / "downloads"
    env = {
        **os.environ,
        "UI_TEMP_DOWNLOAD_DIR": str(wanted),
        "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")]),
    }
    shown = subprocess.run(
        [
            sys.executable,
            "-W",
            "ignore",
            "-c",
            "from argumentation_analysis.ui import config; "
            "print('DIR=' + str(config.TEMP_DOWNLOAD_DIR))",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert shown.returncode == 0, shown.stderr[-2000:]
    lines = [line for line in shown.stdout.splitlines() if line.startswith("DIR=")]
    assert lines == [f"DIR={wanted}"], shown.stdout[-2000:]
