"""Born-red guards for #2432: the FOL adapter module is retired.

``agents/core/logic/first_order_logic_agent_adapter.py`` held four classes, and
each returned results that no reasoner had computed:

- ``FOLLogicAgent``: a fixed belief set labelled "Conversion réussie";
- ``LogicAgentFactory``: built the adapters below;
- ``PropositionalLogicAgentAdapter`` and ``ModalLogicAgentAdapter``: "ACCEPTED
  (True)" for any query.

No module outside ``tests/`` imported it. Two of its class names shadowed the
real ones, ``fol_logic_agent.FOLLogicAgent`` and
``logic_factory.LogicAgentFactory``, so grepping for either name mixed the two.
Its tests now run against the real agent and factory. The #2338 verdict
contract moved to ``test_fol_agent_verdict_2338.py``.
"""

import ast
import importlib.util
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
ADAPTER = "first_order_logic_agent_adapter"
ADAPTER_PATH = f"argumentation_analysis/agents/core/logic/{ADAPTER}.py"
# This guard names the module it looks for, so its own ``ADAPTER`` literal
# reads as a dotted-path import. It is the one file the scan skips; the
# non-vacuity test below proves the detector still bites.
THIS_FILE = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()

# Point-in-time snapshots keep the historical path; living docs must not.
SNAPSHOT_DIRS = ("docs/reports/", "docs/archives/")
PRODUCTION_ROOTS = (
    "argumentation_analysis/",
    "api/",
    "scripts/",
    "project_core/",
    "interface_web/",
)
# Each name has one class in production, in the module production imports.
SINGLE_HOMES = {
    "FOLLogicAgent": "argumentation_analysis/agents/core/logic/fol_logic_agent.py",
    "LogicAgentFactory": "argumentation_analysis/agents/core/logic/logic_factory.py",
}

_MODULE_PATH_LITERAL = re.compile(r"^[\w.]+$")
_TEXT_IMPORT = re.compile(
    rf"(?:^|\s)(?:import|from)\s+[\w.]*\b{ADAPTER}\b", re.MULTILINE
)


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _read(path: Path) -> str:
    # utf-8-sig: a BOM must not turn a file into a parse failure.
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _imports_adapter(source: str) -> bool:
    """True when ``source`` imports the adapter: through a statement, relative
    or absolute, or through a dotted-path literal such as
    ``importlib.import_module("…")``. Prose that names it does not count."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Not excluded: a file that does not parse is read as text.
        return bool(_TEXT_IMPORT.search(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            paths = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            paths = [node.module or ""]
            paths += [f"{node.module or ''}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if not _MODULE_PATH_LITERAL.match(node.value):
                continue
            paths = [node.value]
        else:
            continue
        if any(ADAPTER in path.split(".") for path in paths):
            return True
    return False


def _class_homes(name: str, files: list[str]) -> list[str]:
    homes = []
    for rel in files:
        source = _read(REPO_ROOT / rel)
        if f"class {name}" not in source:
            continue
        tree = ast.parse(source)
        homes += [
            rel
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == name
        ]
    return homes


def test_the_adapter_module_is_gone():
    assert ADAPTER_PATH not in _tracked_files()
    assert (
        importlib.util.find_spec(f"argumentation_analysis.agents.core.logic.{ADAPTER}")
        is None
    )


def test_no_tracked_module_imports_the_adapter():
    python_files = [
        rel for rel in _tracked_files() if rel.endswith(".py") and rel != THIS_FILE
    ]
    assert len(python_files) > 1000, "the scan must cover the tracked tree"
    offenders = [
        rel for rel in python_files if _imports_adapter(_read(REPO_ROOT / rel))
    ]
    assert (
        not offenders
    ), f"these tracked modules import the retired adapter: {offenders}"


def test_the_import_detector_can_fail():
    """Non-vacuity: every import shape reddens, prose does not."""
    for source in (
        f"from argumentation_analysis.agents.core.logic.{ADAPTER} import FOLLogicAgent\n",
        f"from .{ADAPTER} import LogicAgentFactory\n",
        f"from . import {ADAPTER}\n",
        f"import argumentation_analysis.agents.core.logic.{ADAPTER} as a\n",
        f"importlib.import_module('argumentation_analysis.agents.core.logic.{ADAPTER}')\n",
        f"def broken(:\n    from .{ADAPTER} import X\n",
    ):
        assert _imports_adapter(source), source
    assert not _imports_adapter(f'"""The {ADAPTER} module was retired (#2432)."""\n')


def test_each_logic_class_name_has_one_production_home():
    """The adapter defined a second ``FOLLogicAgent`` and a second
    ``LogicAgentFactory``. A second class under either name in production
    brings back the confusion #2360 and #2432 had to untangle."""
    production = [
        rel
        for rel in _tracked_files()
        if rel.endswith(".py") and rel.startswith(PRODUCTION_ROOTS)
    ]
    for name, home in SINGLE_HOMES.items():
        assert _class_homes(name, production) == [home], name


def test_no_living_doc_points_at_the_adapter():
    offenders = [
        rel
        for rel in _tracked_files()
        if rel.endswith(".md")
        and not rel.startswith(SNAPSHOT_DIRS)
        and ADAPTER in _read(REPO_ROOT / rel)
    ]
    assert not offenders, f"living docs still cite the retired adapter: {offenders}"
