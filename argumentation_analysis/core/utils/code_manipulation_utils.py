# -*- coding: utf-8 -*-
"""
Utilities for programmatic code refactoring using Abstract Syntax Trees (AST).
"""

import ast
from pathlib import Path


class ImportUpdater(ast.NodeTransformer):
    """
    AST transformer to find and replace import paths.

    This transformer walks the AST of a Python module and replaces occurrences
    of a specified import module path with a new one.
    """

    def __init__(self, old_path: str, new_path: str):
        self.old_path = old_path
        self.new_path = new_path
        super().__init__()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """
        Visits an `ImportFrom` node.

        If the node's module path matches `old_path`, it is replaced with `new_path`.
        """
        if node.module and node.module == self.old_path:
            node.module = self.new_path
            # After modifying the tree, it's good practice to fix missing
            # line numbers and column offsets.
            ast.fix_missing_locations(node)
        return self.generic_visit(node)


def refactor_update_import(source_code: str, old_import: str, new_import: str) -> str:
    """
    Parses source code, updates a specific import path, and returns the modified code.

    This function is a high-level interface for the ImportUpdater.
    Using `ast.unparse` will lose original formatting (comments, whitespace).
    For more advanced use cases that preserve formatting, a library like LibCST
    would be required.

    Args:
        source_code: The Python source code as a string.
        old_import: The full import path to replace (e.g., 'a.b.c').
        new_import: The new import path (e.g., 'x.y.z').

    Returns:
        The refactored source code as a string.
    """
    tree = ast.parse(source_code)
    transformer = ImportUpdater(old_path=old_import, new_path=new_import)
    new_tree = transformer.visit(tree)
    return ast.unparse(new_tree)


class FunctionRenamer(ast.NodeTransformer):
    """
    AST transformer to find and rename function calls.

    This transformer walks the AST and renames a function call from
    `old_name` to `new_name`.
    """

    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name
        super().__init__()

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """
        Visits a `Call` node.

        If the function call name matches `old_name`, it is replaced with `new_name`.
        """
        if isinstance(node.func, ast.Name) and node.func.id == self.old_name:
            node.func.id = self.new_name
            ast.fix_missing_locations(node)
        return self.generic_visit(node)


def refactor_rename_function(source_code: str, old_name: str, new_name: str) -> str:
    """
    Parses source code, renames a function call, and returns the modified code.

    Args:
        source_code: The Python source code as a string.
        old_name: The name of the function call to rename.
        new_name: The new function name.

    Returns:
        The refactored source code as a string.
    """
    tree = ast.parse(source_code)
    transformer = FunctionRenamer(old_name=old_name, new_name=new_name)
    new_tree = transformer.visit(tree)
    return ast.unparse(new_tree)
