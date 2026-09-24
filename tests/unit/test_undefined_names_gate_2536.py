"""#2536: an undefined name fails a gate that can fail.

The CI lint step runs flake8 with ``continue-on-error: true``, so its green
says nothing about undefined names. This test is the gate for that one code:
it runs flake8's F821 check, with the repository's configuration, over every
tracked root that holds Python files, and expects no site.

Its control is the blind spot #2536 measured. While ``.flake8`` listed F821 in
``ignore``, ``flake8 --select=F821`` printed nothing for a file with an
undefined name. The control runs the same command on such a file and expects
the site.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOUND = 300


def _tracked_python_roots():
    listed = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.splitlines()
    roots = sorted({path.split("/", 1)[0] for path in listed})
    assert "argumentation_analysis" in roots and "tests" in roots, roots
    return roots


def _f821(*paths):
    return subprocess.run(
        [sys.executable, "-m", "flake8", "--select=F821", *paths],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=BOUND,
    )


def test_the_check_sees_an_undefined_name(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text("def f():\n    return undefined_name_2536\n", encoding="utf-8")
    result = _f821(str(probe))
    assert "F821 undefined name 'undefined_name_2536'" in result.stdout, (
        result.stdout + result.stderr
    )


def test_no_tracked_root_has_an_undefined_name():
    result = _f821(*_tracked_python_roots())
    assert result.returncode == 0 and not result.stdout.strip(), (
        result.stdout + result.stderr
    )
