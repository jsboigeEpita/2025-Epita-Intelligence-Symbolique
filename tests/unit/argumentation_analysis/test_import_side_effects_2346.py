"""#2346: importing a module of the package leaves the process alone.

Before this file, importing ``argumentation_analysis.utils`` (which every
``argumentation_analysis.utils.*`` import runs, and which core modules such as
``agents/core/extract/extract_definitions.py`` reached through
``core/bootstrap``) did three things to the importing process:

- it called ``logging.basicConfig`` on the root logger, so an application's
  own ``basicConfig`` afterwards was silently ignored;
- it put directories *inside* the package on ``sys.path`` (``argumentation_analysis/``
  and ``argumentation_analysis/utils/``, one of them at position 0), so a
  top-level name such as ``api`` resolved to ``argumentation_analysis/api``
  instead of the root ``api`` package;
- it created ``logs/`` in the current directory and opened log files there and
  under ``_temp/logs/``.

Three checks hold the repair:

- an AST scan: no module of the package calls ``logging.basicConfig`` at import
  (scripts do it under ``if __name__ == "__main__":``);
- an AST scan: the modules that still change ``sys.path`` at import are exactly
  the named debt below; a new site reddens, and so does an entry whose site is
  gone. A script run as ``python path/to/file.py`` needs the repository root
  (#883, #1336): that bootstrap lives under ``if __name__ == "__main__":``,
  above the first package import;
- a fresh interpreter per module, started in an empty directory: importing it
  adds no directory inside the package to ``sys.path``, no handler to the root
  logger, no ``FileHandler`` anywhere, and writes nothing into that directory.
  The analysis runner is included because its unused environment-manager import
  previously configured the root logger transitively.
- a fresh interpreter where only the package is findable, as an installed
  package is: importing a module whose bootstrap is guarded leaves the
  repository root off ``sys.path`` (before the guard, each put it there, some at
  position 0);
- direct-file ``--help`` still works without ``PYTHONPATH`` for the launchers
  whose ``--help`` has no side effect.

The performance log of ``utils/performance_monitoring.py`` now opens on the
first measurement; a last check runs one measurement and reads the line back.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.isolated_script import run_without_editable_install

REPO = Path(__file__).resolve().parents[3]
PACKAGE = "argumentation_analysis"

# Keep an explicit empty census: any import-time sys.path insertion is new debt.
SYS_PATH_DEBT = {}

# Files launched directly whose repository-root bootstrap runs only under
# ``if __name__ == "__main__":`` (#2346). Imported as a package module they
# leave sys.path alone; launched as a file they still resolve the package.
MAIN_GUARDED_BOOTSTRAPS = [
    "argumentation_analysis/agents/initialize_cache.py",
    "argumentation_analysis/orchestration/analysis_runner_v2.py",
    "argumentation_analysis/orchestration/service_manager.py",
    "argumentation_analysis/pipelines/reporting_pipeline.py",
    "argumentation_analysis/plugins/analysis_tools/logic/rhetorical_result_visualizer.py",
    "argumentation_analysis/run_orchestration.py",
    "argumentation_analysis/scripts/run_fix_missing_first_letter.py",
    "argumentation_analysis/scripts/run_verify_extracts_llm.py",
]

# initialize_cache is left out: it imports ``ui.app``, which needs ``ipywidgets``,
# a notebook dependency declared nowhere (#2076), so the module does not import
# in the provisioned environments. The AST checks still hold its bootstrap.
PACKAGE_IMPORTABLE = [
    path[: -len(".py")].replace("/", ".")
    for path in MAIN_GUARDED_BOOTSTRAPS
    if not path.endswith("initialize_cache.py")
]

IMPORTED = [
    "argumentation_analysis.orchestration.analysis_runner_v2",
    "argumentation_analysis.pipelines.reporting_pipeline",
    "argumentation_analysis.utils",
    "argumentation_analysis.agents.core.extract.extract_definitions",
    "argumentation_analysis.services.definition_service",
    "argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator",
    "argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer",
    "argumentation_analysis.plugins.analysis_tools.logic.rhetorical_result_visualizer",
]


def _is_main_guard(node):
    return isinstance(node, ast.If) and "__main__" in ast.unparse(node.test)


def import_time_calls(tree):
    """(line, callee) for the calls that run when the module is imported.

    Function and class bodies do not run at import, nor does the
    ``if __name__ == "__main__":`` block. Module-level ``if``/``try``/``with``
    bodies do.
    """
    found = []

    def visit(stmts):
        for stmt in stmts:
            if isinstance(
                stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ) or _is_main_guard(stmt):
                continue
            nested = []
            for field in ("body", "orelse", "finalbody"):
                nested.extend(getattr(stmt, field, []) or [])
            for handler in getattr(stmt, "handlers", []) or []:
                nested.extend(handler.body)
            if nested:
                for header in ("test", "iter", "items"):
                    part = getattr(stmt, header, None)
                    for sub in part if isinstance(part, list) else [part]:
                        if sub is not None:
                            found.extend(_calls(sub))
                visit(nested)
            else:
                found.extend(_calls(stmt))

    visit(tree.body)
    return found


def _calls(node):
    return [
        (call.lineno, ast.unparse(call.func))
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
    ]


def _package_sources():
    listed = subprocess.run(
        ["git", "ls-files", f"{PACKAGE}/*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.splitlines()
    assert len(listed) > 400, len(listed)
    # A file that does not parse is reported, never skipped.
    return {
        path: ast.parse((REPO / path).read_text(encoding="utf-8-sig"), path)
        for path in listed
    }


def _sites(trees, callees):
    sites = {}
    for path, tree in trees.items():
        lines = [line for line, callee in import_time_calls(tree) if callee in callees]
        if lines:
            sites[path] = lines
    return sites


SYS_PATH_CALLEES = {"sys.path.insert", "sys.path.append", "sys.path.extend"}


def test_the_scanner_sees_import_time_calls_and_skips_the_rest():
    tree = ast.parse(
        "import logging, sys\n"
        "logging.basicConfig(level=10)\n"
        "try:\n"
        "    sys.path.insert(0, 'x')\n"
        "except ImportError:\n"
        "    sys.path.append('y')\n"
        "if True:\n"
        "    logging.basicConfig()\n"
        "def f():\n"
        "    logging.basicConfig()\n"
        "class C:\n"
        "    sys.path.append('z')\n"
        "if __name__ == '__main__':\n"
        "    logging.basicConfig()\n"
    )
    calls = [
        call
        for call in import_time_calls(tree)
        if call[1] in SYS_PATH_CALLEES | {"logging.basicConfig"}
    ]
    assert calls == [
        (2, "logging.basicConfig"),
        (4, "sys.path.insert"),
        (6, "sys.path.append"),
        (8, "logging.basicConfig"),
    ]


def test_no_module_configures_the_root_logger_at_import():
    sites = _sites(_package_sources(), {"logging.basicConfig"})
    assert sites == {}, (
        "logging.basicConfig at import configures the importing process's root "
        "logger; call it under `if __name__ == '__main__':` instead: "
        f"{sites}"
    )


def test_sys_path_changes_at_import_are_exactly_the_named_debt():
    sites = _sites(_package_sources(), SYS_PATH_CALLEES)
    new = sorted(set(sites) - set(SYS_PATH_DEBT))
    stale = sorted(set(SYS_PATH_DEBT) - set(sites))
    assert not new, f"new sys.path change at import: { {p: sites[p] for p in new} }"
    assert not stale, f"debt entry whose site is gone, remove it: {stale}"


def _import_time_statements(stmts):
    for stmt in stmts:
        if isinstance(
            stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ) or _is_main_guard(stmt):
            continue
        yield stmt
        for field in ("body", "orelse", "finalbody"):
            yield from _import_time_statements(getattr(stmt, field, []) or [])
        for handler in getattr(stmt, "handlers", []) or []:
            yield from _import_time_statements(handler.body)


def _imports_the_package(stmt):
    if isinstance(stmt, ast.Import):
        names = [alias.name for alias in stmt.names]
    elif isinstance(stmt, ast.ImportFrom) and not stmt.level:
        names = [stmt.module or ""]
    else:
        return False
    return any(name == PACKAGE or name.startswith(PACKAGE + ".") for name in names)


@pytest.mark.parametrize("path", MAIN_GUARDED_BOOTSTRAPS)
def test_the_guarded_bootstrap_precedes_the_first_package_import(path):
    tree = ast.parse((REPO / path).read_text(encoding="utf-8-sig"), path)
    bootstraps = [
        stmt.lineno
        for stmt in tree.body
        if _is_main_guard(stmt)
        and any(callee in SYS_PATH_CALLEES for _, callee in _calls(stmt))
    ]
    first_import = min(
        stmt.lineno
        for stmt in _import_time_statements(tree.body)
        if _imports_the_package(stmt)
    )
    assert len(bootstraps) == 1, bootstraps
    assert bootstraps[0] < first_import, (bootstraps, first_import)


_WITNESS = r"""
import json, logging, os, sys
package = os.path.normcase(os.path.join(sys.argv[2], "argumentation_analysis"))
norm = lambda p: os.path.normcase(os.path.abspath(p or os.curdir))
before = {norm(p) for p in sys.path}
root_before = len(logging.getLogger().handlers)
import importlib
module = importlib.import_module(sys.argv[1])
added = [norm(p) for p in sys.path if norm(p) not in before]
file_handlers = sorted(
    name
    for name, lg in logging.Logger.manager.loggerDict.items()
    if isinstance(lg, logging.Logger)
    and any(isinstance(h, logging.FileHandler) for h in lg.handlers)
)
if any(isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers):
    file_handlers.append("<root>")
print(json.dumps({
    "file": norm(module.__file__),
    "inside_package": [p for p in added if p == package or p.startswith(package + os.sep)],
    "root_handlers_added": len(logging.getLogger().handlers) - root_before,
    "file_handlers": file_handlers,
}))
"""


def _import_in_fresh_interpreter(module, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    done = subprocess.run(
        [sys.executable, "-c", _WITNESS, module, str(REPO)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("module", IMPORTED)
def test_importing_leaves_the_process_alone(module, tmp_path):
    seen = _import_in_fresh_interpreter(module, tmp_path)
    # The witness measured this checkout, not another one on the path.
    assert seen["file"].startswith(os.path.normcase(str(REPO))), seen["file"]
    assert seen["inside_package"] == [], seen
    assert seen["root_handlers_added"] == 0, seen
    assert seen["file_handlers"] == [], seen
    assert list(tmp_path.iterdir()) == [], "the import wrote into the current directory"


_MEASURE = r"""
from argumentation_analysis.utils.performance_monitoring import monitor_performance

@monitor_performance()
def measured():
    return 42

assert measured() == 42
"""


_PACKAGE_ONLY = r"""
import importlib, importlib.machinery, json, os, sys
module, root = sys.argv[1], sys.argv[2]
norm = lambda p: os.path.normcase(os.path.abspath(p or os.curdir))
sys.path[:] = [p for p in sys.path if norm(p) != norm(root)]
sys.meta_path[:] = [
    finder
    for finder in sys.meta_path
    if "editable" not in getattr(finder, "__module__", "").lower()
    and "editable" not in type(finder).__name__.lower()
    and "editable" not in getattr(type(finder), "__module__", "").lower()
]


class OnlyThePackage:
    # What an installed package gives: the package, and nothing else of the root.
    @classmethod
    def find_spec(cls, name, path=None, target=None):
        if name == "argumentation_analysis":
            return importlib.machinery.PathFinder.find_spec(name, [root])
        return None


sys.meta_path.insert(0, OnlyThePackage)
imported = importlib.import_module(module)
print(json.dumps({
    "file": norm(imported.__file__),
    "root_on_path": norm(root) in [norm(p) for p in sys.path],
    "central_port_manager_available": getattr(imported, "CENTRAL_PORT_MANAGER_AVAILABLE", None),
}))
"""


def _import_package_only(module, root, cwd):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    done = subprocess.run(
        [sys.executable, "-c", _PACKAGE_ONLY, module, str(root)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("module", PACKAGE_IMPORTABLE)
def test_importing_from_an_installed_package_leaves_the_root_off_sys_path(
    module, tmp_path
):
    seen = _import_package_only(module, REPO, tmp_path)
    assert seen["file"].startswith(os.path.normcase(str(REPO))), seen["file"]
    assert seen["root_on_path"] is False, seen


def test_webapp_import_does_not_insert_checkout_root(tmp_path):
    seen = _import_package_only(
        "argumentation_analysis.webapp.orchestrator", REPO, tmp_path
    )
    assert seen["root_on_path"] is False, seen
    assert seen["central_port_manager_available"] is False, seen


def test_webapp_direct_file_launcher_still_resolves_project_imports():
    done = run_without_editable_install(
        REPO / "argumentation_analysis/webapp/orchestrator.py",
        REPO,
        run_name="__main__",
        args=("--help",),
        timeout=120,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    assert "--help" in done.stdout
    assert "Gestionnaire centralisé des ports non disponible" not in done.stdout


def test_webapp_module_launcher_still_resolves_project_imports(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    done = subprocess.run(
        [sys.executable, "-m", "argumentation_analysis.webapp.orchestrator", "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    assert "--help" in done.stdout
    assert "Gestionnaire centralisé des ports non disponible" not in done.stdout


def test_package_only_harness_sees_a_root_insertion(tmp_path):
    package = tmp_path / PACKAGE
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "inserts_root.py").write_text(
        f"import sys\nsys.path.insert(0, {str(tmp_path)!r})\n", encoding="utf-8"
    )
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    seen = _import_package_only(f"{PACKAGE}.inserts_root", tmp_path, cwd)
    assert seen["root_on_path"] is True, seen


@pytest.mark.parametrize(
    "script",
    [
        "argumentation_analysis/orchestration/analysis_runner_v2.py",
        "argumentation_analysis/pipelines/reporting_pipeline.py",
        "argumentation_analysis/run_orchestration.py",
        "argumentation_analysis/scripts/run_fix_missing_first_letter.py",
    ],
)
def test_direct_file_launchers_still_resolve_project_imports(script):
    done = run_without_editable_install(
        REPO / script, REPO, run_name="__main__", args=("--help",), timeout=120
    )
    assert done.returncode == 0, done.stderr[-3000:]
    assert "--help" in done.stdout


def test_direct_launcher_harness_can_fail(tmp_path):
    naked = tmp_path / "argumentation_analysis" / "pipelines" / "naked.py"
    naked.parent.mkdir(parents=True)
    naked.write_text(
        "from argumentation_analysis.config.settings import settings\n",
        encoding="utf-8",
    )
    done = run_without_editable_install(
        naked, tmp_path, run_name="__main__", args=("--help",)
    )
    assert done.returncode != 0, done.stdout + done.stderr
    assert "ModuleNotFoundError" in done.stderr, done.stderr


def test_the_performance_log_opens_on_the_first_measurement(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    done = subprocess.run(
        [sys.executable, "-c", _MEASURE],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    lines = (tmp_path / "logs" / "oracle_performance.log").read_text().splitlines()
    assert len(lines) == 1, lines
    assert json.loads(lines[0])["message"]["function_name"] == "measured"
