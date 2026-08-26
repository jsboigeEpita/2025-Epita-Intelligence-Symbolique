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

#1895: the guard scans ``tests/mocks/`` RECURSIVELY (``rglob``), not just the
top level. A single-level ``glob`` missed ``jpype_components/imports.py``,
which writes ``sys.modules["jpype.imports"]`` at module level. It is the ONE
exempted file — not because the rule is softened, but because it is load-bearing
rather than dead like the nine deleted: it has a real importer
(``jpype_setup.py:80``), and the write only fires when the jpype mock package is
imported while ``USE_REAL_JPYPE`` is not ``"true"``.
"""

import ast
from pathlib import Path

MOCKS_DIR = Path(__file__).resolve().parents[2] / "mocks"

# The single deliberate module-level write that remains, exempted BY NAME.
# Cause: unique importer is jpype_setup.py:80 (reached only in the mock branch
# of USE_REAL_JPYPE), and imports_module exists only in that branch of
# imports.py — so moving the write into a function would change the load
# contract of a load-bearing mock. Removing this entry must make the guard
# redden: the file really is a module-level write.
ALLOWLIST = {"jpype_components/imports.py"}


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


def _has_module_level_write(path) -> bool:
    """True when *path* writes ``sys.modules`` as an import side effect.

    Only statements directly in the module body count. A def/class statement is
    machinery DEFINED at module level but activated by an explicit call -- its
    body is out of scope (that's the sanctioned numpy_setup / pandas_setup
    pattern). Anything else (bare Assign, Try, If...) executes at import time.
    """
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for _ in _sys_modules_writes(stmt):
            return True
    return False


class TestNoModuleLevelSysModulesHijack:
    def test_no_mock_writes_sys_modules_at_module_level(self):
        assert MOCKS_DIR.is_dir(), f"#1891 guard: {MOCKS_DIR} disappeared"
        # #1895: recursive scan. The widening must actually descend into
        # subpackages — if rglob returned no subpackage .py (e.g. the mutation
        # didn't take, a typo in the path), a single-level glob would also have
        # returned none, so the recursion check is what proves it bit.
        all_py = [
            p for p in sorted(MOCKS_DIR.rglob("*.py")) if "__pycache__" not in p.parts
        ]
        sub_py = [p for p in all_py if p.parent != MOCKS_DIR]
        assert sub_py, (
            "#1895: rglob found no .py under a subpackage of tests/mocks/ — "
            "the #1895 widening did not take"
        )
        # Every allowlisted entry must still exist AND must still earn its
        # exemption. Existence alone is not enough: the day someone moves
        # imports.py's write into a function (the real fix #1895 offered), the
        # file becomes clean and the entry would silently exempt a file that no
        # longer needs it — a permanent hole nobody would ever reopen. Pinning
        # "the exemption is earned" turns that into a red test naming the fix.
        for entry in sorted(ALLOWLIST):
            target = MOCKS_DIR / entry
            assert target.is_file(), (
                "#1895: allowlist entry "
                f"{entry!r} no longer exists under {MOCKS_DIR} — remove it"
            )
            assert _has_module_level_write(target), (
                f"#1895: {entry!r} is allowlisted but no longer writes "
                "sys.modules at module level — the exemption is no longer "
                "earned. Remove it from ALLOWLIST so the file is guarded "
                "again like every other."
            )
        offenders = []
        for py in all_py:
            rel = py.relative_to(MOCKS_DIR).as_posix()
            if rel in ALLOWLIST:
                continue
            if _has_module_level_write(py):
                offenders.append(rel)
        assert not offenders, (
            "#1891: module-level sys.modules write in tests/mocks/ — "
            f"{offenders}. A mock that hijacks sys.modules as an import "
            "side effect shadows a real dependency process-wide. Move the "
            "write inside a function activated explicitly (numpy_setup / "
            "pandas_setup pattern), or delete the mock if nothing imports it."
        )
