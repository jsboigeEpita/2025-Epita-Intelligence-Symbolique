# -*- coding: utf-8 -*-
"""#2345 — ``core/bootstrap.py`` does not re-import its top-level modules.

``initialize_project_environment`` carried a "Re-tenter les imports" block that
re-imported three modules the top of the file already imports (same module,
same alias), each under ``except ImportError: pass``. The block ran only when
``project_root`` was None, i.e. when ``__file__`` is undefined for the module,
which does not happen to an imported module. Reached anyway, it re-imported
``argumentation_analysis.*`` modules from a package that was already
importable, so the top-level error would have recurred, swallowed this time.

The guard reads the source's AST. "Top level" means the module body,
including its ``try`` blocks, but not the inside of a function, a class or
the ``if __name__ == "__main__":`` script block. A lazy import that exists
only in those scopes (``jpype``: two functions and the script block, never at
the top) is legitimate and is not counted as a duplicate.
"""

import ast
from collections import Counter
from pathlib import Path
from typing import Iterator, Tuple

import argumentation_analysis.core.bootstrap as bootstrap

SOURCE = Path(bootstrap.__file__)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _is_main_block(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and any(
            isinstance(c, ast.Constant) and c.value == "__main__"
            for c in node.test.comparators
        )
    )


def _modules_of(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.ImportFrom) and node.module:
        yield node.module
    elif isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name


def _imports() -> Tuple[Counter, Counter]:
    """(top-level imports, imports inside functions or classes)."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"), filename=str(SOURCE))
    top: Counter = Counter()
    nested: Counter = Counter()

    def visit(node: ast.AST, inside: bool) -> None:
        for module in _modules_of(node):
            (nested if inside else top)[module] += 1
        for child in ast.iter_child_nodes(node):
            visit(child, inside or isinstance(node, _SCOPES) or _is_main_block(node))

    visit(tree, False)
    return top, nested


def test_the_census_sees_both_levels():
    # Positive controls: the walk reaches top-level imports nested in ``try``
    # blocks, and imports inside functions. Without them the two tests below
    # could pass on an empty census.
    top, nested = _imports()
    for module in (
        "argumentation_analysis.core.jvm_setup",
        "argumentation_analysis.services.crypto_service",
        "argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector",
    ):
        assert top[module] >= 1, f"{module} not seen at top level"
    assert nested["jpype"] >= 1, "the lazy jpype imports were not seen"


def test_each_top_level_module_is_imported_once_at_top_level():
    top, _ = _imports()
    duplicated = {m: n for m, n in top.items() if n > 1}
    assert duplicated == {}, f"imported more than once at top level: {duplicated}"


def test_no_function_re_imports_a_top_level_module():
    top, nested = _imports()
    reimported = sorted(set(top) & set(nested))
    assert (
        reimported == []
    ), f"top-level modules imported again inside a function: {reimported}"


def test_project_root_is_set_when_the_module_is_imported():
    # The removed block hid behind ``project_root is None``. Pin the invariant
    # that made it unreachable: an imported bootstrap knows its root.
    assert bootstrap.project_root is not None
    assert (Path(bootstrap.project_root) / "argumentation_analysis").is_dir()
