# -*- coding: utf-8 -*-
"""#2486: a ``patch`` target names something the module it patches reads.

``patch("M.N")`` replaces ``N`` on module ``M``, so it acts only if ``M``
reads ``N`` from its globals. It acts on nothing in two ways:

* without ``create=True``, ``N`` is not bound in ``M``: the patch raises
  ``AttributeError`` when the test runs, which no one sees while the test
  stays outside the CI argv (#2483: 9 of 11 tests could not run);
* with ``create=True``, ``N`` is created on ``M``, but every load of ``N`` in
  ``M`` is bound by a function-level import: the mock is never read and the
  test runs against the real object (the 10 sites of #2486).

Static, no import of the patched modules. Population: every call named
``patch`` (``patch``, ``mock.patch``, ``mocker.patch``,
``unittest.mock.patch``; not ``patch.object`` / ``patch.dict``) whose target
is a string literal, in the ``tests/**/*.py`` files pytest collects. ``M`` is
the target's longest prefix that is a module file of this repo, ``N`` the
next segment. ``N`` is bound if ``M``'s top level assigns or imports it, if a
function of ``M`` declares it ``global`` and binds it, or if ``M`` is a
package and ``N`` one of its submodules. With ``create=True`` and ``N``
unbound, ``M`` must have a load of ``N`` that resolves to its globals.

Not decided here, and counted so that a zero is not silence: f-string and
non-literal targets, targets outside this repo, and modules with a star
import or a module ``__getattr__``. A name bound only under
``if TYPE_CHECKING:`` reads as bound.
"""

import ast
import symtable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

from tests.support.tree_walk import iter_files

import pytest

ROOT = Path(__file__).resolve().parents[2]

_PATCH_OWNERS = {"mock", "mocker", "unittest.mock"}


@dataclass(frozen=True)
class ModuleFacts:
    bound: frozenset
    global_loads: frozenset
    opaque: bool


@dataclass
class Census:
    files: int = 0
    literal: int = 0
    non_literal: int = 0
    outside_repo: int = 0
    opaque: int = 0
    decided: int = 0


def _is_patch_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "patch"
    if isinstance(func, ast.Attribute) and func.attr == "patch":
        return ast.unparse(func.value) in _PATCH_OWNERS
    return False


def _creates(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "create":
            return isinstance(keyword.value, ast.Constant) and bool(keyword.value.value)
    return False


def _module_file(root: Path, dotted: List[str]) -> Optional[Path]:
    base = root.joinpath(*dotted)
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _split(root: Path, target: str) -> Optional[Tuple[Path, str, bool]]:
    """(module file of ``M``, ``N``, whether ``N`` is the last segment), or
    None when no prefix of the target is a module file under ``root``."""
    parts = target.split(".")
    for end in range(len(parts) - 1, 0, -1):
        path = _module_file(root, parts[:end])
        if path is not None:
            return path, parts[end], end == len(parts) - 1
    return None


@lru_cache(maxsize=None)
def _facts(path: Path) -> ModuleFacts:
    source = path.read_text(encoding="utf-8-sig")
    top = symtable.symtable(source, str(path), "exec")
    bound, loads = set(), set()
    for symbol in top.get_symbols():
        if symbol.is_assigned() or symbol.is_imported():
            bound.add(symbol.get_name())
        if symbol.is_referenced():
            loads.add(symbol.get_name())

    def walk(table):
        for child in table.get_children():
            for symbol in child.get_symbols():
                name = symbol.get_name()
                if symbol.is_declared_global() and (
                    symbol.is_assigned() or symbol.is_imported()
                ):
                    bound.add(name)
                if symbol.is_referenced() and symbol.is_global():
                    loads.add(name)
            walk(child)

    walk(top)
    star = any(
        isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names)
        for node in ast.parse(source).body
    )
    return ModuleFacts(
        frozenset(bound), frozenset(loads), star or "__getattr__" in bound
    )


def _is_submodule(path: Path, name: str) -> bool:
    return path.name == "__init__.py" and _module_file(path.parent, [name]) is not None


def verdict(root: Path, target: str, create: bool) -> str:
    """``ok``, ``unbound``, ``never read``, ``outside`` or ``opaque``."""
    split = _split(root, target)
    if split is None:
        return "outside"
    path, name, last = split
    facts = _facts(path)
    if facts.opaque:
        return "opaque"
    if name in facts.bound or _is_submodule(path, name):
        return "ok"
    if not create:
        return "unbound"
    if last and name not in facts.global_loads:
        return "never read"
    return "ok"


def _collected_test_files(root: Path) -> List[Path]:
    # pytest.ini's norecursedirs skips every directory named ``_*`` or ``.*``.
    files = []
    for path in sorted(iter_files(root / "tests")):
        parts = path.relative_to(root / "tests").parts[:-1]
        if any(part.startswith(("_", ".")) for part in parts):
            continue
        files.append(path)
    return files


def scan(root: Path) -> Tuple[List[str], Census]:
    dead, census = [], Census()
    for path in _collected_test_files(root):
        census.files += 1
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_patch_call(node)):
                continue
            if not node.args:
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                census.non_literal += 1
                continue
            census.literal += 1
            create = _creates(node)
            found = verdict(root, first.value, create)
            if found == "outside":
                census.outside_repo += 1
                continue
            if found == "opaque":
                census.opaque += 1
                continue
            census.decided += 1
            if found != "ok":
                where = path.relative_to(root).as_posix()
                flag = ", create=True" if create else ""
                dead.append(f"{where}:{node.lineno} {first.value}{flag}: {found}")
    return dead, census


@pytest.fixture(scope="module")
def repo_scan():
    return scan(ROOT)


def test_every_patch_target_is_read(repo_scan):
    dead, _census = repo_scan
    assert dead == [], (
        "patch targets the patched module never reads; patch the name where "
        "the code under test resolves it (#2486):\n" + "\n".join(dead)
    )


def test_the_scan_decides_a_population(repo_scan):
    """Non-vacuity: measured 1240 files and 1509 literal targets on
    2026-09-23, 1073 of them decided. A floor well under that catches a scan
    that stopped looking (a moved root, a changed call shape)."""
    _dead, census = repo_scan
    assert census.files > 1000, census
    assert census.decided > 800, census


def _module(root: Path, dotted: str, source: str) -> None:
    path = root.joinpath(*dotted.split(".")).with_suffix(".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    for parent in path.relative_to(root).parents:
        init = root / parent / "__init__.py"
        if parent != Path(".") and not init.exists():
            init.write_text("", encoding="utf-8")
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    "source, target, create, expected",
    [
        ("from os import path\n", "pkg.mod.path", False, "ok"),
        ("def f():\n    pass\n", "pkg.mod.f", False, "ok"),
        ("def f():\n    return 1\n", "pkg.mod.Gone", False, "unbound"),
        (
            "def f():\n    from os import path\n    return path\n",
            "pkg.mod.path",
            True,
            "never read",
        ),
        ("def f():\n    return path\n", "pkg.mod.path", True, "ok"),
        (
            "class C:\n    def m(self):\n        return path\n",
            "pkg.mod.path",
            True,
            "ok",
        ),
        (
            "def f():\n    path = 1\n\n    def g():\n        return path\n",
            "pkg.mod.path",
            True,
            "never read",
        ),
        ("def f():\n    global _y\n    _y = 1\n", "pkg.mod._y", False, "ok"),
        (
            "def f():\n    global path\n    from os import path\n",
            "pkg.mod.path",
            False,
            "ok",
        ),
        ("from os import *\n", "pkg.mod.Anything", False, "opaque"),
        ("import os\n", "pkg.mod.os.path", False, "ok"),
        ("x = 1\n", "somewhere_else.Thing", False, "outside"),
        ("x = 1\n", "pkg.sibling", False, "unbound"),
    ],
)
def test_the_rule(tmp_path, source, target, create, expected):
    _module(tmp_path, "pkg.mod", source)
    _facts.cache_clear()
    assert verdict(tmp_path, target, create) == expected


def test_a_submodule_is_bound_only_in_its_package(tmp_path):
    _module(tmp_path, "pkg.sub", "x = 1\n")
    _module(tmp_path, "pkg.mod", "y = 1\n")
    _facts.cache_clear()
    assert verdict(tmp_path, "pkg.sub", False) == "ok"
    assert verdict(tmp_path, "pkg.nope", False) == "unbound"
    # A sibling module is not an attribute of ``pkg.mod``.
    assert verdict(tmp_path, "pkg.mod.sub", False) == "unbound"


def test_the_scan_reads_each_call_shape(tmp_path):
    """The scan end to end: which calls are patches, what ``create=True``
    changes, and which files pytest would not collect."""
    _module(tmp_path, "pkg.mod", "def f():\n    from os import path\n    return path\n")
    tests = tmp_path / "tests"
    (tests / "_archived").mkdir(parents=True)
    (tests / "test_x.py").write_text(
        "from unittest import mock\n"
        "from unittest.mock import patch\n"
        "patch('pkg.mod.path', create=True)\n"
        "mock.patch('pkg.mod.Gone')\n"
        "mocker.patch('pkg.mod.Gone2')\n"
        "patch('pkg.mod.f')\n"
        "patch('pkg.mod.path', create=False)\n"
        "patch.object(pkg, 'Gone3')\n"
        "patch(f'pkg.mod.{name}')\n",
        encoding="utf-8",
    )
    (tests / "_archived" / "test_y.py").write_text(
        "patch('pkg.mod.Gone4')\n", encoding="utf-8"
    )
    _facts.cache_clear()

    dead, census = scan(tmp_path)

    assert dead == [
        "tests/test_x.py:3 pkg.mod.path, create=True: never read",
        "tests/test_x.py:4 pkg.mod.Gone: unbound",
        "tests/test_x.py:5 pkg.mod.Gone2: unbound",
        "tests/test_x.py:7 pkg.mod.path: unbound",
    ]
    assert (census.files, census.literal, census.non_literal) == (1, 5, 1)
