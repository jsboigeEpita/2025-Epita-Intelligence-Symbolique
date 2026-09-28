"""The Dung wrapper must report the child verdict to its caller (#2752)."""

import subprocess
import sys
from pathlib import Path

import pytest

WRAPPER = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "orchestration"
    / "run_dung_validation.py"
)


@pytest.mark.parametrize("child_code", [7, 0])
def test_wrapper_preserves_child_status_and_log(tmp_path, child_code):
    scripts = tmp_path / "scripts" / "orchestration"
    scripts.mkdir(parents=True)
    wrapper = scripts / WRAPPER.name
    wrapper.write_bytes(WRAPPER.read_bytes())

    project = tmp_path / "abs_arg_dung"
    project.mkdir()
    (project / "validate_project.py").write_text(
        f"import sys\nprint('synthetic stdout')\n"
        f"print('synthetic stderr', file=sys.stderr)\nsys.exit({child_code})\n",
        encoding="utf-8",
    )
    # No scripts/explore_dung_env.py: the legacy deletion path is never exercised.
    result = subprocess.run(
        [sys.executable, str(wrapper)], cwd=tmp_path, capture_output=True, text=True
    )

    assert result.returncode == child_code
    log = (project / "validation_output.log").read_bytes()
    assert b"synthetic stdout" in log
    assert b"synthetic stderr" in log
    assert str(child_code) in result.stdout
