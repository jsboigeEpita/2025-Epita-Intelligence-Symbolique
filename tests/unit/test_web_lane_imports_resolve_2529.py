# -*- coding: utf-8 -*-
"""#2529, #2532: every module our code imports exists.

#2529. Four scripts of ``services/web_api/`` imported ``scripts.webapp``, a
package deleted in ``1873e9d13`` (2025-06-21). Nothing ran them, so the gap
lasted fifteen months; ``health_check.py`` also hid it behind ``except
ImportError``.

#2532. The same class sat in the other roots: 15 sites on ``41ebd4aee``, each
naming a module the history deleted (``scripts.validation.mock_elimination``,
``SynthesisAgent``'s module, ``scripts/core/auto_env.py``...). Two of them broke
their module at import; one fabricated a passing score in its ``except
ImportError``.

Two rules, each with its root stated.

- **Web lane** (``services/web_api/``, ``api/``, ``interface_web/``), strict:
  every ``import X`` and every absolute ``from X import ...``, at any depth,
  names a module that ``importlib`` finds from the repository root, or a sibling
  of the file (a script run directly has its own directory on ``sys.path``).
  Measured on ``e6a3b476a``: 28 files, 4 unresolved sites.
- **Our other code** (``scripts/``, ``project_core/``, ``argumentation_analysis/``):
  the same resolution, but only imports of *ours* are judged. An import is ours
  when its top-level name is a package at the repository root, or when the git
  history deleted a module at that dotted path (``a.b`` is ``.../a/b.py`` or
  ``.../a/b/__init__.py``). A bare or partial name also resolves when a tracked
  module carries it (the script may put that module's directory on
  ``sys.path``). Third-party imports are not judged here: which ones must be
  installed is the environment files' business, and an optional one is
  legitimately guarded by a ``try``. Measured on ``41ebd4aee``: 970 files,
  15 dead sites.

In both rules an import inside ``try``/``except ImportError`` is not exempt.

The history rule reads ``git log``: a shallow clone would blind it without a
sound, so ``test_the_history_names_a_deleted_module`` must see a deletion first
(the CI test job checks out with ``fetch-depth: 0``).

The census runs in a fresh interpreter. In the test session, ``sys.modules``
may hold a mock (``--disable-jvm-session`` puts one at ``jpype``), and
``find_spec`` then answers for the mock, not for the environment.

The census runs no package's code for the rule on our other code (#2550).
``find_spec("a.b")`` imports ``a`` to find ``b``. On the CI runner, torch's DLLs
fail to load in a fresh interpreter, and ``spacy`` reaches torch through
``thinc``: the census died on ``OSError`` resolving a ``spacy`` submodule, a
third-party import this rule does not judge. It now decides whether an import
is ours before resolving it, and resolves ours from the repository tree.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ROOTS = ("services/web_api", "api", "interface_web")
OWN_ROOTS = ("scripts", "project_core", "argumentation_analysis")

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


def found(module, directory):
    head = module.split(".")[0]
    if (directory / (head + ".py")).exists() or (directory / head).is_dir():
        return True
    if head in packages:
        # Ours: the tree answers, and no __init__ runs on the way.
        target = Path(job["root"], *module.split("."))
        return target.with_suffix(".py").exists() or target.is_dir()
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def tails(paths):
    names = set()
    for name in paths:
        parts = name[: -len(".py")].split("/")
        if parts[-1] == "__init__":
            parts.pop()
        names.update(".".join(parts[i:]) for i in range(len(parts)))
    return names


job = json.loads(sys.stdin.read())
packages = set(job["packages"])
tracked = tails(job["tracked"])
deleted = tails(job["deleted"])


def ours(module):
    if module.split(".")[0] in packages:
        return True
    return module in deleted and module not in tracked


def dead(module, directory):
    if not job["strict"] and not ours(module):
        return False
    return not found(module, directory)


result = {}
for name in job["files"]:
    path = Path(name)
    source = path.read_text(encoding="utf-8-sig")
    result[name] = [
        [line, module]
        for line, module in sorted(imported(source))
        if dead(module, path.parent)
    ]
print("CENSUS " + json.dumps(result))
"""


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\n")


def _tracked_sources(roots):
    listed = _git("ls-files", "--", *(f"{root}/*.py" for root in roots))
    return [ROOT / name for name in listed if name]


def _history():
    """The modules the history deleted, the tracked ones, the root packages."""
    deleted = _git(
        "log",
        "HEAD",
        "--no-renames",
        "--diff-filter=D",
        "--name-only",
        "--format=",
        "--",
        "*.py",
    )
    tracked = _git("ls-files", "--", "*.py")
    top = {name.split("/")[0] for name in _git("ls-files") if name}
    packages = {
        name[: -len(".py")] if name.endswith(".py") else name
        for name in top
        if (ROOT / name).is_dir() or name.endswith(".py")
    }
    return {
        "deleted": sorted({name for name in deleted if name}),
        "tracked": [name for name in tracked if name],
        "packages": sorted(name for name in packages if name.isidentifier()),
    }


def census(paths, strict=True):
    """``{path: [[line, module], ...]}``: the imports judged dead."""
    job = dict(
        _history(), files=[str(path) for path in paths], strict=strict, root=str(ROOT)
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    done = subprocess.run(
        [sys.executable, "-c", _CENSUS],
        cwd=ROOT,
        env=env,
        input=json.dumps(job),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    lines = [line for line in done.stdout.splitlines() if line.startswith("CENSUS ")]
    assert done.returncode == 0 and lines, done.stdout[-2000:] + done.stderr[-2000:]
    return {Path(k): v for k, v in json.loads(lines[-1][len("CENSUS ") :]).items()}


SOURCES = _tracked_sources(ROOTS)


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


def test_the_history_names_a_deleted_module():
    """Control: without history, the rule for our other code judges nothing."""
    history = _history()

    assert (
        "project_core/webapp_from_scripts/simple_web_orchestrator.py"
        in history["deleted"]
    ), "git log sees no deletion: a shallow clone? (#2532 needs fetch-depth: 0)"
    assert set(OWN_ROOTS) <= set(history["packages"])


def test_the_census_judges_only_what_is_ours(tmp_path):
    """Control: what #2532 found is reported, even behind a try; the rest is not.

    ``jvm_setup`` is carried by a tracked module; the last name is nobody's.
    """
    probe = tmp_path / "probe.py"
    probe.write_text(
        "try:\n"
        "    from simple_web_orchestrator import SimpleWebOrchestrator\n"
        "except ImportError:\n"
        "    SimpleWebOrchestrator = None\n"
        "from scripts.validation.mock_elimination import MockEliminator\n"
        "import jvm_setup\n"
        "import some_optional_vendor_sdk_2532\n",
        encoding="utf-8",
    )

    assert census([probe], strict=False) == {
        probe: [
            [2, "simple_web_orchestrator"],
            [5, "scripts.validation.mock_elimination"],
        ]
    }


def test_the_census_runs_no_third_party_code(tmp_path, monkeypatch):
    """Control (#2550): an import that is not ours is not imported to judge it.

    The vendor package stands in for ``spacy`` on the CI runner, whose import
    reaches torch and raises ``OSError`` there.
    """
    site = tmp_path / "site"
    (site / "vendor_pkg_2550").mkdir(parents=True)
    (site / "vendor_pkg_2550" / "__init__.py").write_text(
        'raise OSError("stands in for a DLL that fails to load")\n',
        encoding="utf-8",
    )
    (site / "vendor_pkg_2550" / "sub.py").write_text("", encoding="utf-8")
    code = tmp_path / "code"
    code.mkdir()
    probe = code / "probe.py"
    probe.write_text("from vendor_pkg_2550.sub import thing\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(site))

    assert census([probe], strict=False) == {probe: []}


@pytest.mark.parametrize("root", OWN_ROOTS)
def test_no_import_of_ours_is_dead(root):
    sources = _tracked_sources([root])
    assert len(sources) >= 40, (root, len(sources))

    dead = {
        path.relative_to(ROOT).as_posix(): sites
        for path, sites in census(sources, strict=False).items()
        if sites
    }

    assert dead == {}
