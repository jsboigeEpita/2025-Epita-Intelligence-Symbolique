"""#1820 — decide ``is_e2e_session`` from the collection argv, before collection.

The transport bug: ``pytest_collection_finish`` (``tests/conftest.py``) WRITES
``is_e2e_session`` but ``pytest_sessionstart`` READS it — the reader runs before
the writer, so on a cold cache it reads the default ``False`` and boots the JVM
even for an e2e session (the exact torch/JVM DLL crash that D3.1.1 exists to
avoid), and on a warm cache it reads a PRIOR run's value. The slot is not
reliable at ``pytest_sessionstart`` time; the argv (``--collect-only`` /
path / ``-m``) is.

This module answers the question "would the collected session contain an e2e
item?" from the argv alone, so ``pytest_sessionstart`` never touches the
cache slot. It is deliberately import-light (stdlib + a lazy ``_pytest``)
because ``tests/conftest.py`` loads it on every pytest bootstrap. It must stay
tolerant of the mock ``session.config`` objects the conftest tests feed to
``pytest_sessionstart`` (``test_conftest_jvm_return_1641.py``), returning
``False`` for them so that test keeps reaching the JVM-init path unmodified.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

_E2E_DIR = Path(__file__).resolve().parent / "e2e"

# pytest's ``-m`` grammar (``_pytest.mark.expression`` Scanner) treats these
# bare words as operators / builtin constants, not marker identifiers.
_MARK_OPERATORS = {"not", "and", "or", "True", "False", "None"}
_MARK_IDENT_RE = re.compile(r"(:?\w|:|\+|-|\.|\[|\]|\\|/)+")
# Guard against unbounded enumeration on absurdly-wide expressions.
_MAX_MARK_NAMES = 12


def _as_abs_path(raw: str):
    """Best-effort absolute ``Path``; never raises (garbage strings land in a
    non-matching Path, which is all the containment check needs)."""
    try:
        p = Path(str(raw))
        if not p.is_absolute():
            p = Path(os.path.abspath(str(p)))
        return p
    except Exception:
        return None


def _argv_reaches_e2e(roots) -> bool:
    """True if any collected root is ``tests/e2e``, inside it, or an ancestor
    that CONTAINS it (e.g. ``tests``). A sibling such as ``tests/unit`` does
    NOT reach it. Pure string/normcase containment — no filesystem calls."""
    e2e = _E2E_DIR
    for raw in roots:
        p = _as_abs_path(raw)
        if p is None:
            continue
        if p == e2e or e2e in p.parents or p in e2e.parents:
            return True
    return False


def _effective_collection_roots(config):
    """The collection roots, mirroring pytest: explicit ``config.args`` (pytest
    expands ``testpaths`` into it when no path is given), else the ``testpaths``
    ini, else the rootdir. Tolerant of the MagicMock ``config`` that the
    conftest tests pass: ``config.args`` is a MagicMock → not list/tuple →
    skipped, and the fallbacks yield a non-matching path, so the caller gets
    ``False`` and stays on the prod path."""
    args = getattr(config, "args", None)
    if isinstance(args, (list, tuple)) and args:
        return [str(a) for a in args]

    testpaths = None
    try:
        testpaths = config.getini("testpaths")
    except Exception:
        testpaths = None
    if isinstance(testpaths, (list, tuple)) and testpaths:
        return [str(a) for a in testpaths]

    root = getattr(config, "rootpath", None)
    if root is not None:
        return [str(root)]
    return []


def _get_markexpr(config):
    try:
        expr = getattr(config.option, "markexpr", None)
    except Exception:
        return None
    if not isinstance(expr, str) or not expr.strip():
        return None
    return expr.strip()


def _mark_ident_names(expr: str):
    names = []
    for m in _MARK_IDENT_RE.finditer(expr):
        tok = m.group(0)
        if tok in _MARK_OPERATORS:
            continue
        if tok not in names:
            names.append(tok)
    return names


def _markexpr_excludes_e2e(config) -> bool:
    """Would ``-m <expr>`` drop every e2e item from a path that reaches e2e?

    Post-collection ``session.items`` already reflects the markexpr, so a broad
    path plus ``-m "not e2e"`` is NOT an e2e session and the JVM must boot. We
    ask: is there ANY assignment of the non-e2e markers an item can carry under
    which the expr evaluates True while e2e=True? If none, every e2e item is
    excluded. Sound over the markers the expr names; degrades safely to
    'not excluded' on unparseable or absurdly-wide exprs — the conservative
    direction, because booting the JVM needlessly is harmless next to the
    torch/JVM DLL crash D3.1.1 exists to prevent."""
    expr = _get_markexpr(config)
    if not expr:
        return False
    try:
        from _pytest.mark.expression import Expression

        compiled = Expression.compile(expr)
    except Exception:
        return False

    others = [n for n in _mark_ident_names(expr) if n != "e2e"]
    if len(others) > _MAX_MARK_NAMES:
        return False

    n = len(others)
    for bits in range(1 << n):
        truth = {others[i]: bool(bits & (1 << i)) for i in range(n)}

        def matcher(name, /, **kwargs):
            if name == "e2e":
                return True
            return truth.get(name, False)

        try:
            if compiled.evaluate(matcher):
                return False  # an e2e item survives → not excluded
        except Exception:
            return False  # semantics surprise → conservative
    return True


def _argv_decides_e2e_session(config) -> bool:
    """Decide ``is_e2e_session`` from the collection argv, BEFORE collection.

    The session is E2E iff the effective collection roots reach ``tests/e2e``
    AND the ``-m`` expression does not remove every e2e item. Tolerant of the
    mock ``session.config`` objects fed to ``pytest_sessionstart`` by the
    conftest tests: for those it returns ``False`` (reach the JVM-init path),
    the only value that keeps ``test_conftest_jvm_return_1641.py`` green
    unmodified."""
    roots = _effective_collection_roots(config)
    if not roots:
        return False
    if not _argv_reaches_e2e(roots):
        return False
    return not _markexpr_excludes_e2e(config)
