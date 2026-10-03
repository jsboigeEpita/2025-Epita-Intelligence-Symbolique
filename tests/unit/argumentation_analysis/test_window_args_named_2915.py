"""#2915 — a reading-window width is a named constant, never a bare literal.

The #2913 review measured the drift this guard closes: 29 of 31
``selected_text``/``select_reading_head`` calls under ``argumentation_analysis/``
passed an integer literal, and five of them copied the 8000 that #2913 had
just named in another module — the same drift, reopened between files. A
comment that says "same as X" names a copy, and a copy drifts.

The class guard: the window argument of every ``selected_text`` /
``select_reading_head`` call in the package must not be an integer literal
(one named constant per MEANING — shared meanings in
``core/reading_window.py``, file-local meanings in their file). The positive
control plants a literal in a synthetic module and requires the finder to
see it; a name (or any non-literal expression) passes. Born red on the
pre-#2915 tree (29 literal sites), shown in the PR.
"""

import ast
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PACKAGE = "argumentation_analysis"
_FUNCS = {"selected_text", "select_reading_head"}


def _window_arg(call: ast.Call):
    """The window argument node: 2nd positional, else the ``window`` keyword."""
    if len(call.args) >= 2:
        return call.args[1]
    for kw in call.keywords:
        if kw.arg == "window":
            return kw.value
    return None


def _literal_sites(tree: ast.Module, path: str):
    """(path, lineno, value) for every call whose window arg is an int."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else (node.func.id if isinstance(node.func, ast.Name) else None)
        )
        if name not in _FUNCS:
            continue
        arg = _window_arg(node)
        if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
            found.append((path, node.lineno, arg.value))
    return found


def _package_trees():
    listed = subprocess.run(
        ["git", "ls-files", f"{PACKAGE}/*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.splitlines()
    assert len(listed) > 400, len(listed)
    for path in listed:
        # A file that does not parse is reported, never skipped.
        yield path, ast.parse((REPO / path).read_text(encoding="utf-8-sig"), path)


def test_no_reading_window_call_passes_an_integer_literal():
    sites = []
    for path, tree in _package_trees():
        sites.extend(_literal_sites(tree, path))
    assert sites == [], (
        "a reading-window width must be a named constant (one per meaning, "
        "#2915), never an integer literal — a literal copies a bound and a "
        f"copy drifts: {sites}"
    )


def test_the_finder_sees_a_planted_literal_positive_control():
    planted = ast.parse(
        "from argumentation_analysis.core.reading_window import selected_text\n"
        "def f(text):\n"
        "    return selected_text(text, 4000, 'planted')\n",
        "synthetic_planted.py",
    )
    assert _literal_sites(planted, "synthetic_planted.py") == [
        ("synthetic_planted.py", 3, 4000)
    ]


def test_a_named_constant_passes_the_finder():
    named = ast.parse(
        "from argumentation_analysis.core.reading_window import (\n"
        "    LOGIC_READING_WINDOW,\n"
        "    selected_text,\n"
        ")\n"
        "def f(text):\n"
        "    return selected_text(text, LOGIC_READING_WINDOW, 'named')\n",
        "synthetic_named.py",
    )
    assert _literal_sites(named, "synthetic_named.py") == []
