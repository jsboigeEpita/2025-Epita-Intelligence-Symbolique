"""#2393 guard: no NEW unspecced kernel double lands in ``tests/``.

An unspecced double — ``MagicMock()`` / ``Mock()`` / ``AsyncMock()`` with no
positional argument and no ``spec``/``spec_set`` — accepts every attribute, so
a test that hands one to the code as a kernel stays green whatever kernel API
the code calls, dead or alive (#2389 found one instance of that class).

The census below re-derives the site list on every run. Sites that remain
after the #2393 triage are mapped in ``PENDING``, which can only shrink:

- a file carrying **more** sites than mapped reddens (a new unspecced double:
  use ``create_autospec(Kernel, instance=True)``, or a real ``sk.Kernel``, or
  justify the site here and grow — no, never grow — fix the site);
- a file carrying **fewer** sites than mapped reddens too: the entry is stale
  and the map must shrink (precedent: ``PENDING_TRIAGE`` in #1842).

The detector is nominal (the name must contain ``kernel``), so a double passed
under another name is not counted: the guard's zero is a floor, not a proof.
Non-nominal shapes resolvable same-file were measured at 0 on ``origin/main``
``9b9f55a2`` (see the #2393 PR). Files are read as ``utf-8-sig``; skipped files
and the walked count are printed with the failure, so a silent walk cannot
pass for a clean one.
"""

import ast
from pathlib import Path

from tests.support.tree_walk import iter_files

TESTS_ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {"__pycache__", "_archived"}

MOCK_CTORS = {"MagicMock", "Mock", "AsyncMock"}
EXEMPT_KWARGS = {"spec", "spec_set"}


def _is_unspecced_mock_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if not (isinstance(f, ast.Name) and f.id in MOCK_CTORS):
        return False
    if node.args:
        return False
    return not any(kw.arg in EXEMPT_KWARGS for kw in node.keywords)


def _name_has_kernel(name: str) -> bool:
    return "kernel" in name.lower()


def _assign_site(node: ast.Assign) -> bool:
    for tgt in node.targets:
        if isinstance(tgt, ast.Name) and _name_has_kernel(tgt.id):
            return True
        if isinstance(tgt, ast.Attribute) and _name_has_kernel(tgt.attr):
            return True
    return False


def _sites_in_tree(tree: ast.Module) -> list:
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_unspecced_mock_call(node.value):
            if _assign_site(node):
                sites.append(node.lineno)
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if (
                    kw.arg
                    and _name_has_kernel(kw.arg)
                    and _is_unspecced_mock_call(kw.value)
                ):
                    sites.append(kw.value.lineno)
            f = node.func
            if isinstance(f, ast.Name) and f.id == "patch" and node.args:
                arg0 = node.args[0]
                if (
                    isinstance(arg0, ast.Constant)
                    and isinstance(arg0.value, str)
                    and "Kernel" in arg0.value
                    and not any(
                        kw.arg in ("autospec", "spec", "new", "return_value")
                        for kw in node.keywords
                    )
                ):
                    sites.append(node.lineno)
    return sites


def _sites_in_func_returns(tree: ast.Module) -> list:
    out = []
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and _name_has_kernel(node.name):
            stack = list(node.body)
            while stack:
                sub = stack.pop()
                if isinstance(
                    sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    continue  # nested scope: not this function's own return
                if isinstance(sub, ast.Return) and _is_unspecced_mock_call(sub.value):
                    out.append(sub.lineno)
                stack.extend(ast.iter_child_nodes(sub))
    return out


def _census():
    walked = 0
    skipped = []
    per_file: dict[str, int] = {}
    for path in sorted(iter_files(TESTS_ROOT)):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        rel = path.relative_to(TESTS_ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            skipped.append(f"{rel}: {type(e).__name__}")
            continue
        walked += 1
        n = len(_sites_in_tree(tree)) + len(_sites_in_func_returns(tree))
        if n:
            per_file[rel] = n
    return walked, skipped, per_file


# Remaining sites, one count per file, each entry justified inline. Empty:
# the #2393 triage converted all 73 sites measured on origin/main 9b9f55a2.
# This map only ever shrinks; a stale entry reddens on its own. An entry is
# the last resort — prefer create_autospec(Kernel, instance=True), a real
# sk.Kernel, or a measured justification comment on the double itself.
PENDING: dict[str, int] = {}


def test_detector_positive_control():
    snippet = (
        "k = MagicMock()\n"
        "kernel = MagicMock()\n"
        "self_kernel = None\n"
        "class C:\n"
        "    def m(self):\n"
        "        self.kernel = Mock()\n"
        "kernel2 = MagicMock(spec=Kernel)\n"
    )
    tree = ast.parse(snippet)
    assert len(_sites_in_tree(tree)) == 2


def test_no_new_unspecced_kernel_doubles(capsys):
    walked, skipped, per_file = _census()
    print(f"walked={walked} skipped={len(skipped)}")
    for s in skipped:
        print(f"SKIP {s}")

    new_sites = {f: n for f, n in per_file.items() if n > PENDING.get(f, 0)}
    stale = {f: PENDING[f] for f in PENDING if per_file.get(f, 0) < PENDING[f]}

    assert not new_sites, (
        "new unspecced kernel double(s) in tests/: "
        f"{new_sites} — hand the code a create_autospec(Kernel, instance=True), "
        "a real sk.Kernel, or record the justification in PENDING (shrink-only)"
    )
    assert not stale, f"stale PENDING entries, shrink the map: {stale}"
