"""One ``run_shell_command`` in ``core/utils`` (#2345, item ``run_shell_command`` ×2).

``shell_utils.run_shell_command`` (5 consumers) and ``system_utils.run_shell_command``
(no production consumer) were two implementations of one job. The orphan carried the
only timeout: it moves into the survivor, and the orphan goes. Its removal also ends an
import side effect. ``system_utils`` called ``logging.basicConfig`` on import, so
importing anything from ``argumentation_analysis.core.utils`` configured the root
logger, and an application's own later ``basicConfig`` became a silent no-op.
"""

import ast
import inspect
import logging
import subprocess
import sys
from pathlib import Path

from argumentation_analysis.core.utils.shell_utils import run_shell_command

ROOT = Path(__file__).resolve().parents[5]
CORE_UTILS = ROOT / "argumentation_analysis" / "core" / "utils"


def test_one_definition_in_core_utils():
    definitions = []
    for path in sorted(CORE_UTILS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        definitions += [
            path.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "run_shell_command"
        ]
    assert definitions == ["shell_utils.py"]


def test_importing_core_utils_leaves_the_root_logger_alone():
    probe = (
        "import logging; r = logging.getLogger(); "
        "import argumentation_analysis.core.utils; "
        "print('PROBE', len(r.handlers), r.level)"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    line = [l for l in out.stdout.splitlines() if l.startswith("PROBE")][-1]
    assert line.split()[1:] == ["0", str(logging.WARNING)]


def test_no_timeout_by_default():
    assert inspect.signature(run_shell_command).parameters["timeout"].default is None


def test_timeout_returns_minus_nine_with_the_partial_output():
    code, out, _ = run_shell_command(
        [
            sys.executable,
            "-c",
            "import time; print('before', flush=True); time.sleep(30)",
        ],
        timeout=2,
    )
    assert code == -9
    assert out == "before"


def test_negative_control_command_within_its_timeout_succeeds():
    code, out, err = run_shell_command(
        [sys.executable, "-c", "print('ok')"], timeout=60
    )
    assert (code, out, err) == (0, "ok", "")


def test_empty_command_fails_with_the_os_error_instead_of_raising():
    # Edge case pinned by the removed orphan's suite (#1407): an empty command
    # is an OS error, reported through the return code, never raised.
    code, out, err = run_shell_command("")
    assert code < 0
    assert out == ""
    assert err
