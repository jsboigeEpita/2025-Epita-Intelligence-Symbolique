"""Run a script without a checkout supplied by cwd, PYTHONPATH, or an editable install."""

import os
import subprocess
import sys
from pathlib import Path

RUNNER = r"""
import os
import runpy
import sys

script, root, run_name, *args = sys.argv[1:]
sys.meta_path = [
    finder
    for finder in sys.meta_path
    if "editable" not in getattr(finder, "__module__", "").lower()
    and "editable" not in type(finder).__name__.lower()
    and "editable" not in getattr(type(finder), "__module__", "").lower()
]
sys.path[:] = [p for p in sys.path if os.path.normcase(os.path.abspath(p or ".")) != os.path.normcase(root)]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
sys.argv = [script, *args]
runpy.run_path(script, run_name=run_name)
"""


def run_without_editable_install(
    script: Path,
    root: Path,
    *,
    run_name: str = "__not_main__",
    args: tuple[str, ...] = (),
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Make the repository importable only if the script bootstraps its own path."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, "-c", RUNNER, str(script), str(root), run_name, *args],
        capture_output=True,
        text=True,
        cwd=root.parent,
        env=env,
        timeout=timeout,
    )
