# tests/unit/argumentation_analysis/core/communication/test_no_naked_middleware_in_production_1574.py
"""P2 guard for #1574 — no bare ``MessageMiddleware()`` in production code.

The R652/#1571 defect family is a ``MessageMiddleware()`` constructed with **no
channel registered** (or only a partial set): ``send_message`` then logs
``Channel not found: <type>`` and the bus stays silent. ``initialize_communication_middleware``
(#1574) was one such site; ``orchestration/engine/test_pipeline.py`` was another
(1 channel only). The single source of truth is :func:`create_default_middleware`,
which registers HIERARCHICAL + DATA.

This guard walks ``argumentation_analysis/`` (excluding ``*/tests/*`` and
``__pycache__``) and fails if any ``MessageMiddleware()`` **constructor call**
appears outside a test context without a matching ``.register_channel`` in the
same scope. It therefore catches the re-introduction of a naked bus in a
production module while leaving:

* :func:`create_default_middleware` (which builds ``MessageMiddleware(config=...)``
  then calls ``register_channel`` twice) — passes,
* test modules (``*/tests/*``) — excluded,
* any prod site that builds a middleware and registers at least one channel —
  passes (the channel set is checked elsewhere; this guard only forbids *zero*
  registration).

JVM/LLM-free: static AST walk, opaque probe module used to prove the guard
bites.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
PKG_ROOT = REPO_ROOT / "argumentation_analysis"
EXCLUDE_DIR_NAMES = {"tests", "__pycache__", "__pypackages__"}


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _enclosing_scope(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST | None:
    """Nearest FunctionDef/AsyncFunctionDef or Module enclosing *node*."""
    current: ast.AST | None = node
    while current is not None:
        current = parents.get(current)
        if current is None:
            return None
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return current
    return None


def _scope_is_test_context(scope: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    """A scope is test context if it is a ``test_*`` function or a ``Test*`` method."""
    if isinstance(scope, ast.Module):
        return False
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if scope.name.startswith("test"):
            return True
        # method of a Test* class
        parent: ast.AST | None = scope
        while parent is not None:
            parent = parents.get(parent)
            if isinstance(parent, ast.ClassDef) and parent.name.startswith("Test"):
                return True
    return False


def _scope_has_register_channel(scope: ast.AST) -> bool:
    """True if *scope* contains a ``.register_channel(...)`` call anywhere in it."""
    for child in ast.walk(scope):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "register_channel"
        ):
            return True
    return False


def _is_messagemiddleware_ctor(node: ast.AST) -> bool:
    """A direct ``MessageMiddleware(...)`` constructor call (Name, not attribute)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "MessageMiddleware"
    )


def _iter_pkg_py_files() -> list[Path]:
    files: list[Path] = []
    for path in PKG_ROOT.rglob("*.py"):
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def _find_naked_middleware_violations() -> list[str]:
    violations: list[str] = []
    for py_file in _iter_pkg_py_files():
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            # Do not let an unparseable file mask the guard; skip it (other CI
            # gates catch syntax errors).
            continue
        parents = _parent_map(tree)
        for node in ast.walk(tree):
            if not _is_messagemiddleware_ctor(node):
                continue
            scope = _enclosing_scope(node, parents)
            if scope is None:
                violations.append(f"{py_file}: unscoped MessageMiddleware() call")
                continue
            if _scope_is_test_context(scope, parents):
                continue
            if _scope_has_register_channel(scope):
                continue
            rel = py_file.relative_to(REPO_ROOT)
            violations.append(
                f"{rel}: MessageMiddleware() without a register_channel in the "
                f"same scope — use create_default_middleware() instead (#1574)."
            )
    return violations


# ── the guard ──


class TestNoNakedMiddlewareInProduction:
    def test_no_bare_messagemiddleware_ctor_in_package(self) -> None:
        """No production module under ``argumentation_analysis/`` may build a
        ``MessageMiddleware()`` without registering a channel. DoD #1574 P2.
        """
        violations = _find_naked_middleware_violations()
        assert not violations, (
            "Naked MessageMiddleware() re-introduced in production "
            "(R652/#1571 defect family):\n  - " + "\n  - ".join(violations)
        )

    def test_create_default_middleware_passes_the_guard(self) -> None:
        """Sanity: the factory itself (``MessageMiddleware(config=...)`` +
        ``register_channel``) is not flagged. If this fails, the guard is wrong,
        not the factory.
        """
        factory = PKG_ROOT / "core" / "communication" / "middleware.py"
        tree = ast.parse(factory.read_text(encoding="utf-8"), filename=str(factory))
        parents = _parent_map(tree)
        ctors = [n for n in ast.walk(tree) if _is_messagemiddleware_ctor(n)]
        assert ctors, "expected create_default_middleware to build a MessageMiddleware"
        for node in ctors:
            scope = _enclosing_scope(node, parents)
            assert scope is not None
            # Either it registers a channel, or the guard logic is broken.
            assert _scope_has_register_channel(scope), (
                "create_default_middleware no longer registers a channel — guard "
                "would flag the factory itself, which means the factory regressed."
            )

    def test_guard_bites_on_a_naked_ctor_probe(self, tmp_path: Path) -> None:
        """Falsifiable control: synthesize a module with a naked ctor and prove
        the detector flags it. If this passes but the main test fails, the guard
        genuinely caught a regression (not a false alarm).
        """
        naked_src = textwrap.dedent("""
            from argumentation_analysis.core.communication.middleware import MessageMiddleware

            def build_bus():
                mw = MessageMiddleware()
                return mw
            """)
        tree = ast.parse(naked_src, filename="probe.py")
        parents = _parent_map(tree)
        ctors = [n for n in ast.walk(tree) if _is_messagemiddleware_ctor(n)]
        assert len(ctors) == 1
        scope = _enclosing_scope(ctors[0], parents)
        assert scope is not None
        assert not _scope_is_test_context(scope, parents)
        assert not _scope_has_register_channel(scope)

    def test_guard_accepts_registered_ctor_probe(self, tmp_path: Path) -> None:
        """Symmetric control: a ctor followed by ``register_channel`` is NOT a
        violation (the channel-set quality is a separate concern).
        """
        registered_src = textwrap.dedent("""
            from argumentation_analysis.core.communication.middleware import MessageMiddleware
            from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel

            def build_bus():
                mw = MessageMiddleware()
                mw.register_channel(HierarchicalChannel("c"))
                return mw
            """)
        tree = ast.parse(registered_src, filename="probe.py")
        parents = _parent_map(tree)
        ctors = [n for n in ast.walk(tree) if _is_messagemiddleware_ctor(n)]
        scope = _enclosing_scope(ctors[0], parents)
        assert scope is not None
        assert _scope_has_register_channel(scope)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
