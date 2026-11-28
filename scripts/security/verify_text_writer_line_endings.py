#!/usr/bin/env python3
"""The census of text-mode writers, and the guard that keeps it honest (#3723).

The defect this exists for
---------------------------
In text mode, ``"\\n"`` becomes the platform's line separator **at write
time**. A writer that does not say which separator it means therefore commits
the seat's line ending: on a Windows seat (``core.autocrlf=false``), the bytes
written are the bytes committed. Measured on ``origin/main``: 306 tracked
blobs carry a CR, and one of them is a report a script regenerates on every
run (``docs/reports/discourse_patterns.md``, 102 lines of CRLF).

The rule
--------
**A writer owns its bytes.** A text-mode write whose file git may keep must
declare ``newline=`` explicitly. The script that writes the file says which
separator it means; the seat does not decide.

The two rules the guard enforces
--------------------------------
Both are recomputed from the sources on every run. There is no pinned list of
offenders, so the census cannot rot by being left behind.

1. **Tracked** -- a writer whose target resolves to a file git tracks must
   declare ``newline=``.
2. **Rewriter** -- a writer whose target descends from a tree enumeration
   (the script picked the file it writes from a directory walk) must declare
   ``newline=``. Such a writer rewrites files it found; where they live is
   decided at run time, so the rule does not depend on reading the path.

What the census reports but does not enforce
---------------------------------------------
The remaining classes are measured on every run and printed, so that a new
one is noticed rather than inherited:

* ``in-repo``     the target resolves inside the tree, and git does not ignore
  it: ``git add`` would take it, though git does not track it today.
* ``runtime-*``   the target is computed at run time from a parameter or a
  command-line value, and does not descend from an enumeration. The static
  analysis cannot tell where it lands.

The known limit: a writer that receives its target through a function call
(the caller enumerates the tree, the callee writes) is not seen by the data
flow of this script. It lands in a ``runtime-*`` class: reported, not
flagged.

Exit codes: ``0`` clean, ``1`` violations found, ``2`` the census could not
run (not a git checkout, or git unavailable).

Usage::

    python scripts/security/verify_text_writer_line_endings.py
    python scripts/security/verify_text_writer_line_endings.py --verbose
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The write calls that produce a file in text mode.
WRITE_METHODS = ("write_text", "open")
# The calls that enumerate a tree; a writer fed by one of them writes
# repository files it picked at run time.
TREE_ENUMERATORS = ("rglob", "iglob", "walk", "glob", "iterdir", "listdir")
# Modules whose ``open`` writes bytes whatever the mode string says.
BINARY_OPEN_MODULES = frozenset(
    {
        "tarfile",
        "zipfile",
        "shelve",
        "dbm",
        "sqlite3",
        "h5py",
        "lmdb",
        "zmq",
        "serial",
        "socket",
        "wave",
        "urllib",
        "webbrowser",
    }
)


# --------------------------------------------------------------------------
# git facts
# --------------------------------------------------------------------------
def git_lines(*args: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.splitlines()


def tracked_paths() -> set[str]:
    """The repository-relative paths git tracks."""
    out = set()
    for line in git_lines("ls-files", "-z"):
        for path in line.split("\0"):
            if path:
                out.add(path.replace("\\", "/"))
    return out


def ignored_paths(candidates: list[str]) -> set[str]:
    """Which of these paths git ignores.

    ``git ls-files --others --ignored`` only lists what exists on disk, so an
    ignored directory that was never created would be invisible. ``check-ignore``
    reads the rules themselves, and answers for a path that does not exist.
    """
    if not candidates:
        return set()
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "--stdin", "-z"],
        input="\0".join(candidates) + "\0",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore failed: {proc.stderr.strip()}")
    return {p for p in proc.stdout.split("\0") if p}


# --------------------------------------------------------------------------
# path resolution
# --------------------------------------------------------------------------
class Scope:
    """The names visible where a statement sits, and their value nodes."""

    def __init__(self, parent: "Scope | None" = None) -> None:
        self.names: dict[str, ast.AST] = {}
        self.walks: dict[str, ast.Call] = {}
        self.parent = parent

    def bind(self, name: str, node: ast.AST) -> None:
        self.names[name] = node

    def lookup(self, name: str) -> ast.AST | None:
        if name in self.names:
            return self.names[name]
        return self.parent.lookup(name) if self.parent else None

    def walk_of(self, name: str) -> ast.Call | None:
        """The enumeration a name was read from, when it was."""
        if name in self.walks:
            return self.walks[name]
        return self.parent.walk_of(name) if self.parent else None

    def bind_body(self, body: list[ast.stmt]) -> None:
        """Bind every name the body assigns. The order does not matter."""
        for stmt in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    self._bind_target(target, stmt.value)
                walk = walk_call(stmt.value)
                if walk is not None:
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            self.walks[target.id] = walk
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                self._bind_target(stmt.target, stmt.value)
                walk = walk_call(stmt.value)
                if walk is not None and isinstance(stmt.target, ast.Name):
                    self.walks[stmt.target.id] = walk
            elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                targets = (
                    stmt.target.elts
                    if isinstance(stmt.target, ast.Tuple)
                    else [stmt.target]
                )
                for target in targets:
                    if isinstance(target, ast.Name):
                        self.bind(target.id, stmt.iter)
                walk = walk_call(stmt.iter)
                if walk is not None:
                    for target in targets:
                        if isinstance(target, ast.Name):
                            self.walks[target.id] = walk
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                for item in stmt.items:
                    if isinstance(item.optional_vars, ast.Name):
                        self.bind(item.optional_vars.id, item.context_expr)
                        walk = walk_call(item.context_expr)
                        if walk is not None:
                            self.walks[item.optional_vars.id] = walk

    def _bind_target(self, target: ast.AST, value: ast.AST | None) -> None:
        if value is None:
            return
        if isinstance(target, ast.Name):
            self.bind(target.id, value)
        elif (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            self.bind("self." + target.attr, value)


def walk_call(node: ast.AST | None, depth: int = 0) -> ast.Call | None:
    """The tree enumeration an expression reads from, when it reads one."""
    if node is None or depth > 8:
        return None
    if isinstance(node, ast.Call):
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else (func.id if isinstance(func, ast.Name) else None)
        )
        if name in TREE_ENUMERATORS:
            return node
        if name in ("list", "sorted", "set", "tuple") and node.args:
            return walk_call(node.args[0], depth + 1)
        return None
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        return any_walk(node.generators)
    return None


def any_walk(generators: list[ast.comprehension]) -> ast.Call | None:
    for generator in generators:
        walk = walk_call(generator.iter)
        if walk is not None:
            return walk
    return None


def walk_feeding(
    node: ast.AST | None, scope: "Scope | None", depth: int = 0
) -> ast.Call | None:
    """The enumeration a written path descends from, when it descends from one."""
    if node is None or scope is None or depth > 20:
        return None
    if isinstance(node, ast.Name):
        walk = scope.walk_of(node.id)
        if walk is not None:
            return walk
        return walk_feeding(scope.lookup(node.id), scope, depth + 1)
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            walk = scope.walk_of("self." + node.attr)
            if walk is not None:
                return walk
            return walk_feeding(scope.lookup("self." + node.attr), scope, depth + 1)
        return walk_feeding(node.value, scope, depth + 1)
    if isinstance(node, ast.BinOp):
        return walk_feeding(node.left, scope, depth + 1) or walk_feeding(
            node.right, scope, depth + 1
        )
    if isinstance(node, ast.Subscript):
        return walk_feeding(node.value, scope, depth + 1)
    if isinstance(node, ast.Call):
        for arg in node.args:
            walk = walk_feeding(arg, scope, depth + 1)
            if walk is not None:
                return walk
        if isinstance(node.func, ast.Attribute):
            return walk_feeding(node.func.value, scope, depth + 1)
    if isinstance(node, ast.JoinedStr):
        for value in node.values:
            walk = walk_feeding(value, scope, depth + 1)
            if walk is not None:
                return walk
    if isinstance(node, ast.FormattedValue):
        return walk_feeding(node.value, scope, depth + 1)
    return None


class Resolver:
    """Resolves a path expression to an absolute path, when it can.

    Every path is absolute from the start, so ``Path(__file__).parent.parent``
    lands where it lands at run time and ``..`` is normalised the same way.
    An expression that cannot be followed is reported as unresolved, never
    guessed.
    """

    def __init__(self, script_path: Path, scope: Scope) -> None:
        self.script_path = script_path
        self.scope = scope

    def resolve(self, node: ast.AST | None, depth: int = 0) -> str | None:
        if node is None or depth > 40:
            return None
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return self._absolute(node.value)
            return None
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                else:
                    parts.append("*")
            return self._absolute("".join(parts))
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return str(self.script_path)
            expr = self.scope.lookup(node.id)
            return None if expr is None else self.resolve(expr, depth + 1)
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                expr = self.scope.lookup("self." + node.attr)
                return None if expr is None else self.resolve(expr, depth + 1)
            base = self.resolve(node.value, depth + 1)
            if base is None:
                return None
            if node.attr == "parent":
                return os.path.dirname(base)
            if node.attr == "name":
                return os.path.basename(base)
            return None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "parents":
                base = self.resolve(node.value.value, depth + 1)
                index = (
                    node.slice.value if isinstance(node.slice, ast.Constant) else None
                )
                if base is None or not isinstance(index, int):
                    return None
                for _ in range(index + 1):
                    base = os.path.dirname(base)
                return base
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = self.resolve(node.left, depth + 1)
            right = self._fragment(node.right)
            if left is None or right is None:
                return None
            return os.path.normpath(os.path.join(left, right))
        if isinstance(node, ast.Call):
            return self._resolve_call(node, depth)
        return None

    def _resolve_call(self, node: ast.Call, depth: int) -> str | None:
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else (func.id if isinstance(func, ast.Name) else None)
        )
        if name in ("Path", "PurePath") and node.args:
            return self.resolve(node.args[0], depth + 1)
        if name == "str" and node.args:
            return self.resolve(node.args[0], depth + 1)
        if name == "resolve" and isinstance(func, ast.Attribute):
            return self.resolve(func.value, depth + 1)
        if name == "absolute" and isinstance(func, ast.Attribute):
            return self.resolve(func.value, depth + 1)
        if (
            name == "join"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "path"
        ):
            parts = []
            for arg in node.args:
                fragment = self._fragment(arg)
                parts.append(
                    fragment if fragment is not None else self.resolve(arg, depth + 1)
                )
            if any(p is None for p in parts):
                return None
            result = ""
            for part in parts:
                if os.path.isabs(part):
                    result = part
                else:
                    result = os.path.join(result, part) if result else part
            return os.path.normpath(result)
        if (
            name == "dirname"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "path"
        ):
            if not node.args:
                return None
            base = self.resolve(node.args[0], depth + 1)
            return None if base is None else os.path.dirname(base)
        if (
            name == "abspath"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "path"
        ):
            return self.resolve(node.args[0], depth + 1) if node.args else None
        if (
            name in ("normpath", "realpath")
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "path"
        ):
            if not node.args:
                return None
            base = self.resolve(node.args[0], depth + 1)
            if base is None:
                return None
            return os.path.normpath(base) if name == "normpath" else base
        return None

    def base_of(self, node: ast.AST | None, depth: int = 0) -> str | None:
        """The directory a computed path is built in, when it can be read.

        ``output_dir / f"{name}.md"`` writes in ``output_dir``: knowing that
        directory is enough to tell a write into an ignored directory from a
        write into the tree.
        """
        if node is None or depth > 40:
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.base_of(node.left, depth + 1) or self.resolve(
                node.left, depth + 1
            )
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr
                if isinstance(func, ast.Attribute)
                else (func.id if isinstance(func, ast.Name) else None)
            )
            if name == "join" and node.args:
                return self.base_of(node.args[0], depth + 1) or self.resolve(
                    node.args[0], depth + 1
                )
            return self.resolve(node, depth)
        if isinstance(node, ast.Attribute):
            if node.attr in ("parent", "name"):
                return self.resolve(node, depth)
            return self.base_of(node.value, depth + 1)
        return self.resolve(node, depth)

    def _absolute(self, value: str) -> str:
        """An absolute path, so a relative one is read against the repository."""
        if os.path.isabs(value):
            return os.path.normpath(value)
        return os.path.normpath(os.path.join(str(REPO_ROOT), value))

    def _fragment(self, node: ast.AST | None, depth: int = 0) -> str | None:
        """A path fragment as it is written, without being made absolute.

        The right side of ``a / b`` is a fragment of ``a``, not a path of its
        own: absolutising it against the repository would throw the prefix
        away.
        """
        if node is None or depth > 40:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                else:
                    parts.append("*")
            return "".join(parts)
        return None


# --------------------------------------------------------------------------
# the census
# --------------------------------------------------------------------------
class WriteSite:
    __slots__ = (
        "path",
        "lineno",
        "kind",
        "target_expr",
        "resolved",
        "classification",
        "declares_newline",
        "newline_value",
        "enumerates_tree",
        "target_expr_src",
        "base",
        "candidate_rel",
        "walk",
        "walk_root",
    )

    def __init__(
        self,
        path,
        lineno,
        kind,
        target_expr,
        target_expr_src,
        declares_newline,
        newline_value,
    ):
        self.path = path
        self.lineno = lineno
        self.kind = kind
        self.target_expr = target_expr
        self.target_expr_src = target_expr_src
        self.declares_newline = declares_newline
        self.newline_value = newline_value
        self.resolved: str | None = None
        self.classification = ""
        self.enumerates_tree = False
        self.base: str | None = None
        self.candidate_rel = ""
        self.walk: ast.Call | None = None
        self.walk_root: str | None = None

    @property
    def in_population(self) -> bool:
        """Whether the two enforced rules apply to this writer."""
        return self.classification == "tracked" or self.classification.startswith(
            "walk-"
        )

    @property
    def location(self) -> str:
        rel = relative_to_repo(str(self.path)) or str(self.path)
        return f"{rel}:{self.lineno}"


def write_sites(tree: ast.AST) -> list[WriteSite]:
    """The text-mode writes of a parsed file."""
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else (func.id if isinstance(func, ast.Name) else None)
        )
        if name not in WRITE_METHODS:
            continue
        if (
            name == "open"
            and isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in BINARY_OPEN_MODULES
        ):
            # ``tarfile.open(name, "w")`` writes bytes, not text: there is no
            # separator to own.
            continue
        newline_value = None
        for kw in node.keywords:
            if kw.arg == "newline" and isinstance(kw.value, ast.Constant):
                newline_value = kw.value.value
        # The rule names the value: the LF itself. ``newline=None`` is the
        # default that translates, and ``newline=os.linesep`` is the defect.
        declares = newline_value == "\n"
        if name == "write_text":
            # The target of write_text is the RECEIVER; the first argument is
            # the data. Reading it the other way round names the payload.
            target = func.value if isinstance(func, ast.Attribute) else None
            sites.append(
                WriteSite(None, node.lineno, name, target, "", declares, newline_value)
            )
            continue
        mode = None
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            mode = node.args[1].value
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = kw.value.value
        if not isinstance(mode, str) or not any(ch in mode for ch in "wxa+"):
            continue
        target = (
            node.args[0]
            if node.args
            else next((kw.value for kw in node.keywords if kw.arg == "file"), None)
        )
        sites.append(
            WriteSite(None, node.lineno, name, target, "", declares, newline_value)
        )
    return sites


def scope_at(tree: ast.AST, script_path: Path) -> tuple[Scope, dict[int, Scope]]:
    """The scope in force at each line: module, then class, then function."""
    module = Scope()
    module.bind_body(tree.body)  # type: ignore[attr-defined]
    scopes: dict[int, Scope] = {}

    def visit(node: ast.AST, scope: Scope) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inner = Scope(scope)
            inner.bind_body(node.body)
            for sub in ast.walk(node):
                lineno = getattr(sub, "lineno", None)
                if lineno is not None:
                    scopes.setdefault(lineno, inner)
            for stmt in node.body:
                visit(stmt, inner)
            return
        if isinstance(node, ast.ClassDef):
            inner = Scope(scope)
            inner.bind_body(node.body)
            for sub in ast.walk(node):
                lineno = getattr(sub, "lineno", None)
                if lineno is not None:
                    scopes.setdefault(lineno, inner)
            for stmt in node.body:
                visit(stmt, inner)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, scope)

    visit(tree, module)
    # What the module itself says: the lines no function or class claimed.
    for stmt in tree.body:  # type: ignore[attr-defined]
        for sub in ast.walk(stmt):
            lineno = getattr(sub, "lineno", None)
            if lineno is not None and lineno not in scopes:
                scopes[lineno] = module
    return module, scopes


def enumerates_tree(tree: ast.AST) -> bool:
    """Whether the file enumerates a tree (so a writer may pick repo files)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr
                if isinstance(func, ast.Attribute)
                else (func.id if isinstance(func, ast.Name) else None)
            )
            if name in TREE_ENUMERATORS:
                return True
    return False


def walk_root_expr(call: ast.Call) -> ast.AST | None:
    """The expression a tree enumeration starts from."""
    func = call.func
    name = (
        func.attr
        if isinstance(func, ast.Attribute)
        else (func.id if isinstance(func, ast.Name) else None)
    )
    if isinstance(func, ast.Attribute) and name in ("rglob", "iglob", "iterdir"):
        return func.value
    if call.args and (name in ("walk", "listdir", "glob", "iglob")):
        return call.args[0]
    return None


def walk_root(
    call: ast.Call, resolver: "Resolver", tree: ast.AST | None = None
) -> str | None:
    """The directory a tree enumeration starts from, when it can be read."""
    func = call.func
    name = (
        func.attr
        if isinstance(func, ast.Attribute)
        else (func.id if isinstance(func, ast.Name) else None)
    )
    expr = walk_root_expr(call)
    if expr is None:
        return None
    resolved = None
    if name in ("glob", "iglob") and not isinstance(func, ast.Attribute):
        # A module-level glob takes a pattern: its directory part is the root.
        resolved = resolver.base_of(expr) or str(REPO_ROOT)
    else:
        resolved = resolver.resolve(expr)
    if resolved is not None or tree is None:
        return resolved
    # The root is a parameter: its default, or what the callers pass.
    if not isinstance(expr, ast.Name):
        return None
    function = enclosing_function(tree, call.lineno)
    if function is None:
        return None
    args = function.args
    names = [arg.arg for arg in list(args.args) + list(args.kwonlyargs)]
    if expr.id not in names:
        return None
    defaults = list(args.defaults) + [d for d in args.kw_defaults if d is not None]
    for arg, default in zip(names[len(names) - len(defaults) :], defaults):
        if arg.arg == expr.id:
            return resolver.resolve(default)
    index = names.index(expr.id)
    for caller in ast.walk(tree):
        if not isinstance(caller, ast.Call):
            continue
        called = caller.func
        called_name = (
            called.attr
            if isinstance(called, ast.Attribute)
            else (called.id if isinstance(called, ast.Name) else None)
        )
        if called_name != function.name:
            continue
        if len(caller.args) > index:
            return resolver.resolve(caller.args[index])
        for kw in caller.keywords:
            if kw.arg == expr.id:
                return resolver.resolve(kw.value)
    return None


def script_files() -> list[Path]:
    """The Python files of the repository, under ``scripts/``.

    Only the files git TRACKS are listed: a helper a seat keeps locally
    (ignored by git) is not part of the repository, and its bytes never reach
    a commit -- the census is of the repository, not of every seat's desk.
    """
    paths = []
    for line in git_lines("ls-files", "-z", "--", "scripts"):
        for entry in line.split("\0"):
            if entry.endswith(".py"):
                paths.append(REPO_ROOT / entry)
    return sorted(paths)


def census() -> tuple[list[WriteSite], dict[str, list[str]]]:
    """Every text-mode write under scripts/, classified."""
    tracked = tracked_paths()
    sites: list[WriteSite] = []
    runtime_files: dict[str, list[str]] = {}
    candidates: list[str] = []

    for path in script_files():
        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        module_scope, scopes = scope_at(tree, path)
        file_enumerates = enumerates_tree(tree)
        script_rel = relative_to_repo(str(path)) or str(path)
        for site in write_sites(tree):
            site.path = path
            site.target_expr_src = (
                ast.unparse(site.target_expr) if site.target_expr is not None else ""
            )
            scope = scopes.get(site.lineno, module_scope)
            resolver = (
                Resolver(path, scope) if scope is not None else Resolver(path, Scope())
            )
            resolved = resolver.resolve(site.target_expr)
            site.resolved = resolved
            site.enumerates_tree = file_enumerates
            sites.append(site)
            if resolved is None:
                # The target is computed while the script runs.
                walk = walk_feeding(site.target_expr, scope)
                default = default_target(tree, site, path, scope)
                if walk is not None:
                    # A rewriter: the written path descends from a file the
                    # script enumerated. It is in the population unless the
                    # enumeration's root is provably outside what git keeps.
                    site.walk = walk
                    site.walk_root = walk_root(walk, resolver, tree)
                    root_rel = (
                        relative_to_repo(site.walk_root) if site.walk_root else None
                    )
                    if root_rel is not None and not root_rel.startswith(".."):
                        candidates.append(root_rel)
                        candidates.append(root_rel.rstrip("/") + "/probe")
                    site.classification = "walk"
                elif default is not None:
                    resolved = default
                    site.resolved = default
                else:
                    base = resolver.base_of(site.target_expr)
                    site.base = base
                    base_rel = relative_to_repo(base) if base else None
                    if base_rel is not None and not base_rel.startswith(".."):
                        candidates.append(base_rel)
                        candidates.append(base_rel.rstrip("/") + "/probe")
                        site.classification = "runtime-base"
                    elif base_rel is not None:
                        site.classification = "runtime-outside"
                    elif file_enumerates:
                        site.classification = "runtime-tree"
                    else:
                        site.classification = "runtime-unknown"
                    runtime_files.setdefault(script_rel, []).append(site.location)
                    continue
                runtime_files.setdefault(script_rel, []).append(site.location)
                if walk is not None:
                    continue
            rel = relative_to_repo(resolved)
            if rel is None:
                site.classification = "outside"
                continue
            if rel.startswith(".."):
                site.classification = "outside"
                continue
            if any(ch in rel for ch in "*?["):
                # A pattern: it is in the population when a tracked file
                # matches it.
                site.classification = (
                    "tracked" if matches_tracked(rel, tracked) else "in-repo"
                )
                continue
            site.candidate_rel = rel
            candidates.append(rel)
            candidates.append(rel.rstrip("/") + "/probe")
    ignored = ignored_paths(sorted(set(candidates)))
    for site in sites:
        if site.classification == "walk":
            root_rel = relative_to_repo(site.walk_root) if site.walk_root else None
            if root_rel is None:
                # The enumeration's root cannot be read: nothing proves the
                # written bytes stay out of the repository.
                site.classification = "walk-unknown"
            elif (
                root_rel.startswith("..")
                or root_rel == ".git"
                or root_rel.startswith(".git/")
            ):
                site.classification = "walk-outside"
            elif root_rel in ignored or root_rel.rstrip("/") + "/probe" in ignored:
                site.classification = "walk-ignored"
            else:
                site.classification = "walk-in-repo"
        elif site.classification == "runtime-base":
            base_rel = relative_to_repo(site.base) if site.base else None
            if base_rel is not None and (
                base_rel in ignored or base_rel.rstrip("/") + "/probe" in ignored
            ):
                site.classification = "runtime-ignored"
            else:
                site.classification = "runtime-base-in-repo"
        elif site.classification == "":
            rel = site.candidate_rel
            if rel in tracked:
                site.classification = "tracked"
            elif rel in ignored or rel.rstrip("/") + "/probe" in ignored:
                site.classification = "ignored"
            else:
                site.classification = "in-repo"
    return sites, runtime_files


def relative_to_repo(path: str) -> str | None:
    """The repository-relative form of a path, or None when it is elsewhere."""
    try:
        return os.path.relpath(path, str(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return None


def matches_tracked(pattern: str, tracked: set[str]) -> bool:
    """Whether a tracked file matches a path pattern."""
    import fnmatch

    return any(fnmatch.fnmatch(path, pattern) for path in tracked)


def default_target(
    tree: ast.AST, site: "WriteSite", path: Path, scope: Scope | None
) -> str | None:
    """The path a runtime-computed target is given by default, when known.

    A writer that takes its target from a parameter is given a default at the
    call site or in the signature. When that default resolves outside the
    repository (or into an ignored directory), the writer's bytes are never
    committed, and the seat's separator does not matter.
    """
    if site.target_expr is None:
        return None
    root = site.target_expr
    while isinstance(root, (ast.Attribute, ast.Subscript)):
        root = root.value
    if not isinstance(root, ast.Name):
        return None
    resolver = Resolver(path, scope if scope is not None else Scope())
    function = enclosing_function(tree, site.lineno)
    if function is not None:
        args = function.args
        names = list(args.args) + list(args.kwonlyargs)
        defaults = list(args.defaults) + [d for d in args.kw_defaults if d is not None]
        for arg, default in zip(names[len(names) - len(defaults) :], defaults):
            if arg.arg == root.id:
                return resolver.resolve(default)
    # A command-line value: the parser's default is the target's home.
    default = argparse_default(tree, root.id)
    if default is not None:
        return resolver.resolve(default)
    return None


def argparse_default(tree: ast.AST, name: str) -> ast.AST | None:
    """The default value an ``add_argument`` gives to an option."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = (
            func.attr
            if isinstance(func, ast.Attribute)
            else (func.id if isinstance(func, ast.Name) else None)
        )
        if called != "add_argument":
            continue
        dest = None
        default = None
        for index, arg in enumerate(node.args):
            if (
                index == 0
                and isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
            ):
                dest = arg.value.lstrip("-").replace("-", "_")
        for kw in node.keywords:
            if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                dest = kw.value.value
            elif kw.arg == "default":
                default = kw.value
        if dest == name and default is not None:
            return default
    return None


def enclosing_function(tree: ast.AST, lineno: int) -> ast.AST | None:
    """The function a line sits in, the innermost one."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end:
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--verbose", action="store_true", help="list every site, conforming or not"
    )
    args = parser.parse_args(argv)

    try:
        sites, runtime_files = census()
    except RuntimeError as exc:
        print(f"census could not run: {exc}", file=sys.stderr)
        return 2

    violations = [s for s in sites if s.in_population and not s.declares_newline]
    # A site that cannot be resolved and whose file does not enumerate a tree
    # may still write into the repository (a path built at run time from a
    # command-line value). It is in the population, and it is reported.
    population = [s for s in sites if s.in_population]

    print(f"text-mode writes under scripts/: {len(sites)}")
    counts: dict[str, int] = {}
    for site in sites:
        counts[site.classification] = counts.get(site.classification, 0) + 1
    print("classification: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"in the population: {len(population)}")
    print(f"declaring newline=: {sum(1 for s in population if s.declares_newline)}")
    print(f"violations: {len(violations)}")

    if args.verbose:
        for site in sorted(sites, key=lambda s: (str(s.path), s.lineno)):
            mark = "ok " if site.declares_newline else "!! "
            print(
                f"  {mark}{site.location} [{site.classification}] {site.target_expr_src[:80]}"
            )

    for site in violations:
        print(
            f"VIOLATION {site.location}: a writer of a file git may keep "
            f"({site.classification}) declares no newline="
        )
        print(f"    target: {site.target_expr_src[:120]}")
        if site.resolved:
            print(f"    resolves to: {site.resolved}")
    if runtime_files and args.verbose:
        print("runtime targets (target computed while the script runs):")
        for rel, locations in sorted(runtime_files.items()):
            print(f"  {rel}: {len(locations)} site(s)")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
