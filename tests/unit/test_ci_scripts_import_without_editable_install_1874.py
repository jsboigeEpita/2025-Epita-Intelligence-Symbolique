"""#1874: a `scripts/ci/*.py` step must import the package the way CI does.

`python scripts/ci/x.py` puts `scripts/ci/` on `sys.path[0]` -- never the repo
root -- and the CI conda env installs no editable copy of the package
(`environment.yml` carries no `-e .`). Every developer machine here *does* carry
a stray editable install, which resolves `argumentation_analysis` to whatever
checkout that install points at. So the failure is invisible locally and fatal
in CI, and worse: locally it can resolve to a *different* checkout than the one
under test, which is how a control on the merge silently measured `main`.

Measured before the fix, with the editable finder removed:
``ModuleNotFoundError: No module named 'argumentation_analysis'``. The cache-key
step would then print an empty key, its own `if (-not $key) { exit 1 }` would
fire, and the job would go red at the first of the three new steps.

The harness runs each script with ``run_name`` other than ``"__main__"``, so
imports and definitions execute while the side effects behind the
``if __name__ == "__main__"`` guard -- a Maven assembly, a JDK download -- do
not.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CI_SCRIPTS = ROOT / "scripts" / "ci"

# Reproduces the CI import condition: no editable finder, no repo root on the
# path, cwd-independent. What survives is what the script does for itself.
RUNNER = r"""
import os
import runpy
import sys

script = sys.argv[1]
sys.meta_path = [
    f
    for f in sys.meta_path
    if "editable" not in getattr(f, "__module__", "").lower()
    and "editable" not in type(f).__name__.lower()
    and "editable" not in getattr(type(f), "__module__", "").lower()
]
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(script))))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != root]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name="__not_main__")
"""


def _run_as_ci(script: Path) -> subprocess.CompletedProcess:
    """Execute `script` with the repo root unreachable except by its own doing."""
    return subprocess.run(
        [sys.executable, "-c", RUNNER, str(script)],
        capture_output=True,
        text=True,
        cwd=str(ROOT.parent),  # never the repo root: cwd must not rescue it
    )


def _ci_scripts() -> list[Path]:
    return sorted(p for p in CI_SCRIPTS.glob("*.py") if p.name != "__init__.py")


def test_the_population_is_not_empty():
    """A guard whose population is empty passes while measuring nothing."""
    scripts = _ci_scripts()
    assert len(scripts) >= 3, (
        f"expected at least the three #1874 CI scripts under {CI_SCRIPTS}, "
        f"found {len(scripts)}: {[p.name for p in scripts]}"
    )


def test_the_harness_can_fail(tmp_path):
    """Degenerate substitution: without the bootstrap, the harness MUST redden.

    Without this, a green above would be indistinguishable from a harness that
    cannot produce a red at all -- the shape where the repo root leaks back in
    through cwd, PYTHONPATH, or a finder the stripper missed.
    """
    naked = tmp_path / "scripts" / "ci" / "naked.py"
    naked.parent.mkdir(parents=True)
    naked.write_text(
        "from argumentation_analysis.config.settings import settings" + chr(10),
        encoding="utf-8",
    )
    result = _run_as_ci(naked)
    assert result.returncode != 0, (
        "a script with no sys.path bootstrap imported the package anyway -- the "
        "harness is not reproducing the CI condition, so every pass below is "
        "vacuous:" + chr(10) + result.stdout + result.stderr
    )
    assert "ModuleNotFoundError" in result.stderr, (
        "expected the CI failure mode, got:" + chr(10) + result.stderr
    )


@pytest.mark.parametrize("script", _ci_scripts(), ids=lambda p: p.name)
def test_ci_script_imports_without_an_editable_install(script):
    result = _run_as_ci(script)
    assert result.returncode == 0, (
        f"{script.relative_to(ROOT)} cannot import its dependencies the way CI "
        f"runs it (`python {script.relative_to(ROOT).as_posix()}`), so the step "
        f"would fail on the runner while passing on any machine that carries a "
        f"stray editable install:" + chr(10) + result.stdout + result.stderr
    )
