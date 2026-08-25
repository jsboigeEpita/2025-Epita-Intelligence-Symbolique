# -*- coding: utf-8 -*-
"""Guard for #1891: no mock in tests/mocks/ hijacks sys.modules at import.

The deleted files (bootstrap, pytest_mock, networkx_mock, torch_mock,
tensorflow_mock, pydantic_mock, semantic_kernel_mock,
semantic_kernel_agents_mock, matplotlib_mock) had ZERO importers but wrote
into ``sys.modules`` at MODULE level — importing any of them (by accident,
via a widened glob, via a tool that imports the whole package) would
silently replace pytest, pydantic, networkx or semantic_kernel for the rest
of the process.

The legitimate sys.modules manipulation in this package (``numpy_setup.py``,
``pandas_setup.py``) happens INSIDE functions, activated explicitly by a
fixture or a call — never as an import side effect. The guard pins exactly
that distinction: module-level writes are forbidden, function-level ones are
the sanctioned pattern.
"""

import ast
from pathlib import Path

MOCKS_DIR = Path(__file__).resolve().parents[2] / "mocks"


def _sys_modules_writes(tree: ast.AST):
    """Yield every ``sys.modules[...] = x`` assignment node in a subtree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Attribute)
                    and target.value.attr == "modules"
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "sys"
                ):
                    yield node


class TestNoModuleLevelSysModulesHijack:
    def test_no_mock_writes_sys_modules_at_module_level(self):
        assert MOCKS_DIR.is_dir(), f"#1891 guard: {MOCKS_DIR} disappeared"
        offenders = []
        for py in sorted(MOCKS_DIR.glob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8-sig"))
            # Only statements directly in the module body count as import
            # side effects. A def/class statement is machinery DEFINED at
            # module level but activated by an explicit call — its body is
            # out of scope (that's the sanctioned numpy_setup / pandas_setup
            # pattern). Anything else (bare Assign, Try, If...) executes at
            # import time.
            for stmt in tree.body:
                if isinstance(
                    stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    continue
                for _ in _sys_modules_writes(stmt):
                    offenders.append(py.name)
                    break
        assert not offenders, (
            "#1891: module-level sys.modules write in tests/mocks/ — "
            f"{offenders}. A mock that hijacks sys.modules as an import "
            "side effect shadows a real dependency process-wide. Move the "
            "write inside a function activated explicitly (numpy_setup / "
            "pandas_setup pattern), or delete the mock if nothing imports it."
        )
