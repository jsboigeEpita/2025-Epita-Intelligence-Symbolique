# -*- coding: utf-8 -*-
"""#2529: every module a web-lane file imports exists.

Four scripts of ``services/web_api/`` imported ``scripts.webapp``, a package
deleted in ``1873e9d13`` (2025-06-21). Nothing ran them, so the gap lasted
fifteen months; ``health_check.py`` also hid it behind ``except ImportError``.

The census, with its root stated: the tracked ``.py`` files under
``services/web_api/``, ``api/`` and ``interface_web/``. Every ``import X`` and
every absolute ``from X import ...`` in them, at any depth, must name a module
that ``importlib`` finds from the repository root, or a sibling of the file (a
script run directly has its own directory on ``sys.path``). An import inside
``try``/``except ImportError`` is not exempt. Measured on ``e6a3b476a``: 28
files, 4 unresolved sites, all ``scripts.webapp``.

The census runs in a fresh interpreter. In the test session, ``sys.modules``
may hold a mock (``--disable-jvm-session`` puts one at ``jpype``), and
``find_spec`` then answers for the mock, not for the environment.

The other roots are not covered here: ``scripts/``, ``project_core/`` and
``argumentation_analysis/`` carry unresolved imports of their own: #2532.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ROOTS = ("services/web_api", "api", "interface_web")

_CENSUS = r"""
import ast
import importlib.util
import json
import sys
from pathlib import Path


def imported(source):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def resolves(module, directory):
    head = module.split(".")[0]
    if (directory / (head + ".py")).exists() or (directory / head).is_dir():
        return True
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


found = {}
for name in sys.argv[1:]:
    path = Path(name)
    source = path.read_text(encoding="utf-8-sig")
    found[name] = [
        [line, module]
        for line, module in imported(source)
        if not resolves(module, path.parent)
    ]
print("CENSUS " + json.dumps(found))
"""


def _tracked_sources():
    listed = subprocess.run(
        ["git", "ls-files", "--", *(f"{root}/*.py" for root in ROOTS)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [ROOT / name for name in listed]


def census(paths):
    """``{path: [[line, module], ...]}``: the imports that do not resolve."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    done = subprocess.run(
        [sys.executable, "-c", _CENSUS, *map(str, paths)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    lines = [line for line in done.stdout.splitlines() if line.startswith("CENSUS ")]
    assert done.returncode == 0 and lines, done.stdout[-2000:] + done.stderr[-2000:]
    return {Path(k): v for k, v in json.loads(lines[-1][len("CENSUS ") :]).items()}


SOURCES = _tracked_sources()


@pytest.fixture(scope="module")
def web_lane_census():
    return census(SOURCES)


def test_the_census_sees_the_files_it_names():
    assert len(SOURCES) >= 20, SOURCES
    for root in ROOTS:
        assert any(
            path.relative_to(ROOT).as_posix().startswith(root + "/") for path in SOURCES
        ), root


def test_the_census_reports_a_missing_module(tmp_path):
    """Control: the instrument finds what #2529 found, even behind a try."""
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import os\n"
        "try:\n"
        "    from scripts.webapp.process_cleaner import ProcessCleaner\n"
        "except ImportError:\n"
        "    ProcessCleaner = None\n",
        encoding="utf-8",
    )

    assert census([probe]) == {probe: [[3, "scripts.webapp.process_cleaner"]]}


@pytest.mark.parametrize(
    "path", SOURCES, ids=lambda path: path.relative_to(ROOT).as_posix()
)
def test_every_import_resolves(path, web_lane_census):
    assert web_lane_census[path] == []
