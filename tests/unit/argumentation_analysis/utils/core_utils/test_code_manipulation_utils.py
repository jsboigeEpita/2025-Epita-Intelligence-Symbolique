# tests/unit/argumentation_analysis/utils/core_utils/test_code_manipulation_utils.py
"""Tests for AST-based code manipulation utilities."""

import pytest

from argumentation_analysis.core.utils.code_manipulation_utils import (
    ImportUpdater,
    FunctionRenamer,
    refactor_update_import,
    refactor_rename_function,
)


# ── ImportUpdater ──

class TestImportUpdater:
    def test_init(self):
        updater = ImportUpdater("old.path", "new.path")
        assert updater.old_path == "old.path"
        assert updater.new_path == "new.path"

    def test_replaces_matching_import(self):
        import ast
        code = "from old.module import something"
        tree = ast.parse(code)
        updater = ImportUpdater("old.module", "new.module")
        new_tree = updater.visit(tree)
        result = ast.unparse(new_tree)
        assert "new.module" in result
        assert "old.module" not in result

    def test_no_match_unchanged(self):
        import ast
        code = "from other.module import something"
        tree = ast.parse(code)
        updater = ImportUpdater("old.module", "new.module")
        new_tree = updater.visit(tree)
        result = ast.unparse(new_tree)
        assert "other.module" in result

    def test_multiple_imports(self):
        import ast
        code = "from old.mod import a\nfrom old.mod import b\nfrom keep.mod import c"
        tree = ast.parse(code)
        updater = ImportUpdater("old.mod", "new.mod")
        new_tree = updater.visit(tree)
        result = ast.unparse(new_tree)
        assert result.count("new.mod") == 2
        assert "keep.mod" in result


# ── refactor_update_import ──

class TestRefactorUpdateImport:
    def test_basic_replacement(self):
        code = "from old.path import MyClass"
        result = refactor_update_import(code, "old.path", "new.path")
        assert "new.path" in result
        assert "MyClass" in result

    def test_no_match(self):
        code = "from other.path import MyClass"
        result = refactor_update_import(code, "old.path", "new.path")
        assert "other.path" in result

    def test_preserves_names(self):
        code = "from old.module import Foo, Bar, Baz"
        result = refactor_update_import(code, "old.module", "new.module")
        assert "Foo" in result
        assert "Bar" in result
        assert "Baz" in result
        assert "new.module" in result

    def test_empty_code(self):
        result = refactor_update_import("", "old", "new")
        assert result == ""

    def test_no_imports(self):
        code = "x = 1\ny = 2"
        result = refactor_update_import(code, "old", "new")
        assert "x = 1" in result

    def test_regular_import_not_affected(self):
        code = "import old.module"
        result = refactor_update_import(code, "old.module", "new.module")
        # ImportUpdater only handles ImportFrom, not Import
        assert "old.module" in result


# ── FunctionRenamer ──

class TestFunctionRenamer:
    def test_init(self):
        renamer = FunctionRenamer("old_fn", "new_fn")
        assert renamer.old_name == "old_fn"
        assert renamer.new_name == "new_fn"

    def test_renames_matching_call(self):
        import ast
        code = "old_fn(x, y)"
        tree = ast.parse(code)
        renamer = FunctionRenamer("old_fn", "new_fn")
        new_tree = renamer.visit(tree)
        result = ast.unparse(new_tree)
        assert "new_fn" in result
        assert "old_fn" not in result

    def test_no_match_unchanged(self):
        import ast
        code = "other_fn(x)"
        tree = ast.parse(code)
        renamer = FunctionRenamer("old_fn", "new_fn")
        new_tree = renamer.visit(tree)
        result = ast.unparse(new_tree)
        assert "other_fn" in result

    def test_attribute_call_not_affected(self):
        import ast
        code = "obj.old_fn(x)"
        tree = ast.parse(code)
        renamer = FunctionRenamer("old_fn", "new_fn")
        new_tree = renamer.visit(tree)
        result = ast.unparse(new_tree)
        # Attribute calls (obj.old_fn) use ast.Attribute, not ast.Name
        assert "old_fn" in result


# ── refactor_rename_function ──

class TestRefactorRenameFunction:
    def test_basic_rename(self):
        code = "result = compute(a, b)"
        result = refactor_rename_function(code, "compute", "calculate")
        assert "calculate" in result
        assert "compute" not in result

    def test_no_match(self):
        code = "result = other(a)"
        result = refactor_rename_function(code, "compute", "calculate")
        assert "other" in result

    def test_multiple_calls(self):
        code = "x = fn(1)\ny = fn(2)"
        result = refactor_rename_function(code, "fn", "new_fn")
        assert result.count("new_fn") == 2

    def test_preserves_arguments(self):
        code = "fn(a, b, c=1, *args, **kwargs)"
        result = refactor_rename_function(code, "fn", "new_fn")
        assert "new_fn" in result
        assert "a" in result
        assert "kwargs" in result

    def test_empty_code(self):
        result = refactor_rename_function("", "fn", "new_fn")
        assert result == ""

    def test_nested_calls(self):
        code = "outer(inner(x))"
        result = refactor_rename_function(code, "inner", "new_inner")
        assert "new_inner" in result
        assert "outer" in result
