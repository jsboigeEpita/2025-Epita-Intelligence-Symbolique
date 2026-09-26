"""#2691: no path in the gate's pytest argv sits inside another.

pytest 8.4.2 given a directory and a file inside it collects only the file:
the rest of the directory leaves the run, and the summary does not say so
(no ``deselected``, only a smaller "N passed"). A file admitted to the gate
argv under a directory it already lists (one file under ``tests/unit/``, say)
would shrink the whole directory to that file while the gate stays green.

The argv is read out of ``ci.yml`` rather than restated here, so the test
follows the argv as it changes (#1867 decides it; this test does not).
``test_pytest_collects_only_the_file`` pins the premise in an empty tmp dir:
a pytest upgrade that stops narrowing turns it red, and the guard can then be
reconsidered.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CI_YML = REPO / ".github" / "workflows" / "ci.yml"
# The gate lists 21 paths (2026-09-26); far fewer means the parse missed it.
MIN_GATE_PATHS = 10


def _gate_paths():
    """The path arguments of the ``pytest`` call that runs ``tests/unit/``."""
    calls = [
        line.split("pytest", 1)[1].split()
        for line in CI_YML.read_text(encoding="utf-8").splitlines()
        if re.search(r"\bpytest\s+tests/unit/", line)
    ]
    assert len(calls) == 1, f"one gate pytest call expected, found {len(calls)}"
    paths = [arg for arg in calls[0] if arg.startswith("tests/")]
    assert len(paths) >= MIN_GATE_PATHS, paths
    return paths


def _nested_pairs(paths):
    """Every (outer, inner) pair where ``inner`` lies inside ``outer``."""
    parts = {path: Path(path).parts for path in paths}
    return [
        (outer, inner)
        for outer in paths
        for inner in paths
        if outer != inner
        and len(parts[inner]) > len(parts[outer])
        and parts[inner][: len(parts[outer])] == parts[outer]
    ]


def test_no_gate_path_sits_inside_another():
    assert _nested_pairs(_gate_paths()) == []


def test_the_detector_finds_a_nested_pair():
    assert _nested_pairs(["tests/unit/", "tests/unit/api/test_x.py"]) == [
        ("tests/unit/", "tests/unit/api/test_x.py")
    ]
    assert _nested_pairs(["tests/integration/api/", "tests/integration/"]) == [
        ("tests/integration/", "tests/integration/api/")
    ]


def test_a_sibling_sharing_a_name_prefix_is_not_nested():
    assert _nested_pairs(["tests/unit", "tests/unit_extra/test_x.py"]) == []


def _collected(root, *args):
    run = subprocess.run(
        [sys.executable, "-m", "pytest", *args, "--collect-only", "-q"]
        + ["-p", "no:cacheprovider", "--rootdir", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return sorted(line for line in run.stdout.splitlines() if "::" in line)


def test_pytest_collects_only_the_file(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    folder = tmp_path / "d"
    folder.mkdir()
    (folder / "test_a.py").write_text(
        "def test_a1():\n    pass\n\n\ndef test_a2():\n    pass\n", encoding="utf-8"
    )
    (folder / "test_b.py").write_text("def test_b1():\n    pass\n", encoding="utf-8")

    assert _collected(tmp_path, "d") == [
        "d/test_a.py::test_a1",
        "d/test_a.py::test_a2",
        "d/test_b.py::test_b1",
    ]
    assert _collected(tmp_path, "d", "d/test_a.py") == [
        "d/test_a.py::test_a1",
        "d/test_a.py::test_a2",
    ]
