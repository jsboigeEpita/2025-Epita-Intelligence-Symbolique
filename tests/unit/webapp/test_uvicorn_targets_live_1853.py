# -*- coding: utf-8 -*-
"""#1853 — every uvicorn launch target must resolve to a callable app.

The archived Flask module ``argumentation_analysis.services.web_api.app``
still exports a symbol *named* ``app`` — set to ``None`` since #217. A
launcher pointing at it imports cleanly, starts, serves HTTP 500s, and
passes any "did the process start" check. The only control that
discriminates is probing the loaded target itself: import the module,
take the attribute, assert it is callable.

#2480 — the same class, one launch form away. ``e2e_servers`` started
``[sys.executable, "-m", backend_module]``, with ``backend_module`` bound to a
module archived in February. No ``module:app`` string named it, so the census
below never saw it. The second census reads the ``-m <module>`` form.
"""

import ast
import importlib
import re
import subprocess
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# The two YAML files that feed an orchestrator's ``backend.module`` key.
CONFIG_FILES = [
    PROJECT_ROOT / "config" / "webapp_config.yml",
    PROJECT_ROOT / "argumentation_analysis" / "webapp" / "config" / "webapp_config.yml",
]

# Every launcher that writes its uvicorn target as a ``module:app`` string
# literal in code (config readers and hardcoders alike — the census is the
# point, see the site-by-site map in #1853).
LAUNCHER_FILES = [
    PROJECT_ROOT / "project_core" / "test_runner.py",
    PROJECT_ROOT / "scripts" / "apps" / "webapp" / "backend_manager.py",
    PROJECT_ROOT / "scripts" / "apps" / "webapp" / "launch_webapp_background.py",
    PROJECT_ROOT / "scripts" / "apps" / "webapp" / "unified_web_orchestrator.py",
    PROJECT_ROOT / "scripts" / "orchestration" / "orchestrate_webapp_detached.py",
    PROJECT_ROOT / "scripts" / "run_e2e_backend.py",
    PROJECT_ROOT / "scripts" / "verification" / "run_api_validation.py",
    PROJECT_ROOT / "tests" / "integration" / "webapp" / "conftest.py",
    PROJECT_ROOT / "tests" / "conftest.py",
]

APP_SPEC_RE = re.compile(r"^[A-Za-z_][\w.]*:app$")


def _config_targets():
    targets = []
    for path in CONFIG_FILES:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        module = config["backend"]["module"]
        targets.append((str(path.relative_to(PROJECT_ROOT)), module))
    return targets


def _launcher_targets():
    targets = []
    for path in LAUNCHER_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if APP_SPEC_RE.match(node.value):
                    targets.append((str(path.relative_to(PROJECT_ROOT)), node.value))
    return targets


ALL_TARGETS = _config_targets() + _launcher_targets()


def test_census_liveness():
    """An extraction regression must not go vacuous-green (#1852 lesson)."""
    assert len(_config_targets()) == len(CONFIG_FILES)
    files_with_spec = {source for source, _ in _launcher_targets()}
    missing = [
        str(path.relative_to(PROJECT_ROOT))
        for path in LAUNCHER_FILES
        if str(path.relative_to(PROJECT_ROOT)) not in files_with_spec
    ]
    assert not missing, (
        f"No ':app' target extracted from {missing}. Either the launcher "
        f"changed shape, or its uvicorn target is a bare module string — "
        f"which uvicorn resolves to the module's '.app' attribute and is "
        f"probed by no one. Normalize it to an explicit 'module:app' spec."
    )


@pytest.mark.parametrize(
    ("source", "spec"),
    ALL_TARGETS,
    ids=[f"{spec}@{source}" for source, spec in ALL_TARGETS],
)
def test_uvicorn_target_is_a_callable_app(source, spec):
    module_name, attr = spec.split(":", 1)
    module = importlib.import_module(module_name)
    exported = getattr(module, attr)
    assert callable(exported), (
        f"{source} launches '{spec}', but {module_name} exports "
        f"{attr}={exported!r} — not callable. The process starts and "
        f"serves HTTP 500s on every route (uvicorn routes through "
        f"middleware/asgi2.py for non-ASGI targets). Point the launcher "
        f"at the live app: 'api.main:app'."
    )


# --- #2480: the ``-m <module>`` launch form -----------------------------------
#
# Root: every tracked ``*.py`` file (``git ls-files``), except the archive
# directories, whose launchers point at archived modules on purpose. A launch
# is the first ``-m`` of an argv list, when the interpreter comes right before
# it (``sys.executable``, ``"python"``, a ``python_exe`` name) or when it opens
# the list (a fragment the interpreter is prepended to). Its target is a
# string, or a name bound to a single string in the same file. A target that
# starts with a tracked top-level directory is ours: it must still exist as a
# runnable module. Any other target is an installed module (``uvicorn``,
# ``pytest``), outside this class.

_ARCHIVE_DIRS = {"archives", "_archives"}
_MODULE_RE = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")
_INTERPRETER_RE = re.compile(r"^(python|py)(\d+(\.\d+)*)?(\.exe)?$")

# The launches whose target the census cannot read, and why.
_UNREAD_LAUNCHES = {
    ("scripts/apps/webapp/backend_manager.py", "self.module"): (
        "the else branch for a server_type other than uvicorn; neither "
        "webapp_config.yml sets server_type, so it is never taken"
    ),
    (
        "tests/integration/_test_consolidation_demo_epita.py",
        "self.demo_principal.replace('.py', '').replace('/', '.')",
    ): "computed from the demo script's path",
    ("tests/unit/test_gate_deselects_egress_leakers_1879.py", "marker"): (
        "a pytest marker expression, not an interpreter launch"
    ),
}


def _tracked_py():
    out = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split()


def _is_archived(rel):
    return any(
        part in _ARCHIVE_DIRS or part.startswith("_archived") for part in rel.split("/")
    )


def _is_interpreter(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(_INTERPRETER_RE.match(node.value))
    text = ast.unparse(node)
    return text == "sys.executable" or "python" in text.lower()


def _string_bindings(tree):
    bound = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            bound.setdefault(node.targets[0].id, set()).add(node.value.value)
    return bound


def _launches_in(rel, text):
    """``(launches, unread)`` for one file: ``launches`` holds
    ``(file, line, module)``, ``unread`` holds ``(file, target expression)``."""
    tree = ast.parse(text)
    launches, unread, bound = [], [], None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        items = node.elts
        flags = [
            i
            for i, item in enumerate(items[:-1])
            if isinstance(item, ast.Constant) and item.value == "-m"
        ]
        if not flags:
            continue
        i = flags[0]
        if i > 0 and not _is_interpreter(items[i - 1]):
            continue
        target = items[i + 1]
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            module = target.value
        elif isinstance(target, ast.Name):
            if bound is None:
                bound = _string_bindings(tree)
            values = bound.get(target.id, set())
            if len(values) != 1:
                unread.append((rel, ast.unparse(target)))
                continue
            (module,) = values
        else:
            unread.append((rel, ast.unparse(target)))
            continue
        if _MODULE_RE.match(module):
            launches.append((rel, node.lineno, module))
    return launches, unread


def _module_launches():
    """``(launches, unread, skipped)`` over the root; ``skipped`` holds the
    archived files."""
    launches, unread, skipped = [], [], []
    for rel in _tracked_py():
        if _is_archived(rel):
            skipped.append(rel)
            continue
        found, not_read = _launches_in(
            rel, (PROJECT_ROOT / rel).read_text(encoding="utf-8-sig")
        )
        launches += found
        unread += not_read
    return launches, unread, skipped


def _top_levels(tracked):
    """Our top-level packages and modules: a target starting with one is ours."""
    return {rel.split("/")[0] for rel in tracked if "/" in rel} | {
        rel[: -len(".py")] for rel in tracked if "/" not in rel
    }


def _dead(launches, tracked):
    top_levels = _top_levels(tracked)
    return [
        f"{rel}:{line} -m {module}"
        for rel, line, module in launches
        if module.split(".")[0] in top_levels
        and f"{module.replace('.', '/')}.py" not in tracked
        and f"{module.replace('.', '/')}/__main__.py" not in tracked
    ]


_TRACKED = set(_tracked_py())
_LAUNCHES, _UNREAD, _SKIPPED = _module_launches()


def test_every_module_launched_from_our_tree_still_exists():
    dead = _dead(_LAUNCHES, _TRACKED)
    assert not dead, (
        f"launches of a module that is no longer in the tree: {dead}. The "
        f"process exits at once with 'No module named ...'. Point the "
        f"launcher at a live module; for a web backend, uvicorn on "
        f"'api.main:app'. (Archived files skipped: {len(_SKIPPED)}.)"
    )


def test_every_launch_target_is_read_or_named():
    """A launch the census cannot read is a launch it does not check."""
    unread = set(_UNREAD)
    unnamed = sorted(unread - set(_UNREAD_LAUNCHES))
    assert not unnamed, (
        f"-m launches whose target is neither a string nor a name bound to "
        f"one: {unnamed}. Bind the target to a string, or name the launch in "
        f"_UNREAD_LAUNCHES with the reason it cannot be read."
    )
    stale = sorted(set(_UNREAD_LAUNCHES) - unread)
    assert not stale, f"_UNREAD_LAUNCHES entries that no longer occur: {stale}"


def test_the_census_reads_the_2480_shape_and_calls_it_dead():
    """Control, on the functions the census runs: a target held in a name
    resolves, and the archived module is reported against the real tree."""
    launches, unread = _launches_in(
        "probe.py",
        'backend_module = "services.web_api_from_libs.app"\n'
        'backend_command = [sys.executable, "-m", backend_module]\n',
    )
    assert unread == []
    assert launches == [("probe.py", 2, "services.web_api_from_libs.app")]
    assert _dead(launches, _TRACKED) == ["probe.py:2 -m services.web_api_from_libs.app"]


def test_the_module_launch_census_is_not_empty():
    """Control: the census reaches our own modules and installed ones.
    Measured on 2026-09-24: 2 of ours, 60 installed."""
    top_levels = _top_levels(_TRACKED)
    ours = [launch for launch in _LAUNCHES if launch[2].split(".")[0] in top_levels]
    assert len(ours) >= 2, ours
    assert len(_LAUNCHES) - len(ours) >= 50, _LAUNCHES
