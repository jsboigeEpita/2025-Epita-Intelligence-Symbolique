# -*- coding: utf-8 -*-
"""#1853 — every uvicorn launch target must resolve to a callable app.

The archived Flask module ``argumentation_analysis.services.web_api.app``
still exports a symbol *named* ``app`` — set to ``None`` since #217. A
launcher pointing at it imports cleanly, starts, serves HTTP 500s, and
passes any "did the process start" check. The only control that
discriminates is probing the loaded target itself: import the module,
take the attribute, assert it is callable.
"""

import ast
import importlib
import re
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
