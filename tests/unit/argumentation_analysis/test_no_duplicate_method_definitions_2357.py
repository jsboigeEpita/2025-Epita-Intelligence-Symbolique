# tests/unit/argumentation_analysis/test_no_duplicate_method_definitions_2357.py
"""Structural guard for #2357 — no class defines the same method name twice.

#2339 was the **malign** form: two ``invoke_single`` in ``ProjectManagerAgent``,
the survivor calling itself with an incompatible signature, so no PM path ever
completed (repaired in #2354). #2357 is the **benign** form — signatures agree
and the second body is a deliberate superset — which breaks nothing and is for
that reason more durable: the first definition is *dead by overwrite* while
keeping every appearance of being alive. A grep, a human reader, a doc
generator or an agent opening the file at the dead definition finds a body that
describes behaviour the program does not have. It is the "defect that preserves
the name" family: the symbol exists, the count is right, the meaning is false.

Three such sites were removed rather than merged (#2357), each after checking
mechanically that the dead definition carried **no effect and no dict key** the
survivor lacked:

* ``orchestration/group_chat.py::GroupChatOrchestration.cleanup_session`` (was L253, survivor L603)
* ``services/logic_service.py::LogicService.get_service_status`` (was L245, survivor L526)
* ``services/logic_service.py::LogicService.clear_cache`` (was L261, survivor L602)

Two traps this guard is built around, both measured while writing it:

1. **Accessors are excluded by construction, never by name.** A naive scan
   reddens on ``DebateAgent.strategy`` (``@property`` at L262 / ``@strategy.setter``
   at L267) — a perfectly legitimate pair. The pressure would then be to add a
   nominal exemption for a false positive, i.e. to ship an exemption list on day
   one. ``@property``/``@x.setter``/``@x.deleter``/``@x.getter``, ``@overload``
   and ``@singledispatchmethod``/``@x.register`` are therefore filtered
   structurally.

2. **The population is read in ``utf-8-sig`` and a parse failure FAILS the
   guard.** The first scan of this very issue read ``utf-8`` strict and did
   ``except SyntaxError: continue``. **13 files of the tree carry a UTF-8 BOM**;
   ``ast.parse`` raises on the resulting BOM character and the bare ``continue``
   dropped them without a trace — producing a clean-looking "3 sites" on an
   amputated population that said nothing about what it had skipped. The fourth
   site lived in one of those files. A guard that skips in silence is a guard
   that greens in silence, so this one refuses to report at all rather than
   report on a population it cannot name.

JVM/LLM-free: static AST walk. Non-vacuity is proved on synthetic sources, so
the guard cannot go quiet by the tree simply becoming clean.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_ROOT = REPO_ROOT / "argumentation_analysis"
EXCLUDE_DIR_NAMES = {"tests", "__pycache__", "__pypackages__"}

#: Duplicates that are known, triaged, and owned by another issue. This map
#: **shrinks** as those issues land and never grows to absorb new silence: a
#: stale entry (the duplicate is gone) reddens on its own, see
#: :func:`test_the_pending_triage_map_has_no_stale_entry`.
PENDING_TRIAGE: dict[tuple[str, str, str], str] = {
    # Divergent signatures AND return types on a lifecycle entry point; the
    # async/sync split is the subject of #2360, which carries its own born-red.
    (
        "agents/core/logic/fol_logic_agent.py",
        "FOLLogicAgent",
        "setup_agent_components",
    ): "#2360",
}

_ACCESSOR_SUFFIXES = {"setter", "deleter", "getter", "register"}
_ACCESSOR_NAMES = {"property", "overload", "singledispatchmethod", "cached_property"}


def _decorator_paths(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Dotted names of the decorators of *node* (``@a.b.c`` -> ``"a.b.c"``)."""
    paths: list[str] = []
    for deco in node.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        parts: list[str] = []
        while isinstance(target, ast.Attribute):
            parts.append(target.attr)
            target = target.value
        if isinstance(target, ast.Name):
            parts.append(target.id)
        if parts:
            paths.append(".".join(reversed(parts)))
    return paths


def _is_accessor_or_overload(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Structural test: does a decorator make a repeated name legitimate?

    Matches ``@property``/``@overload``/``@singledispatchmethod`` by final
    segment, and ``@<name>.setter``/``.deleter``/``.getter``/``.register`` by
    suffix — so a new accessor pair passes without anyone editing this guard.
    """
    for path in _decorator_paths(node):
        segments = path.split(".")
        if segments[-1] in _ACCESSOR_NAMES:
            return True
        if len(segments) > 1 and segments[-1] in _ACCESSOR_SUFFIXES:
            return True
    return False


def _production_py_files() -> list[Path]:
    return sorted(
        path
        for path in PKG_ROOT.rglob("*.py")
        if not any(part in EXCLUDE_DIR_NAMES for part in path.parts)
    )


def duplicate_method_definitions(
    source: str, filename: str = "<synthetic>"
) -> list[tuple[str, str, int, int]]:
    """``(class, method, first_lineno, overwriting_lineno)`` for *source*.

    Raises ``SyntaxError`` on unparseable input: callers decide, nothing is
    swallowed here.
    """
    tree = ast.parse(source, filename=filename)
    found: list[tuple[str, str, int, int]] = []
    for class_def in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        seen: dict[str, int] = {}
        for item in class_def.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if _is_accessor_or_overload(item):
                continue
            if item.name in seen:
                found.append((class_def.name, item.name, seen[item.name], item.lineno))
            seen[item.name] = item.lineno
    return found


def _scan_production_tree() -> tuple[list[str], int]:
    """All duplicates in the package, plus the size of the population walked."""
    violations: list[str] = []
    files = _production_py_files()
    for py_file in files:
        rel = py_file.relative_to(PKG_ROOT).as_posix()
        # utf-8-sig, and a parse failure is raised, never skipped: the count is
        # only readable next to the population it was measured on.
        source = py_file.read_text(encoding="utf-8-sig")
        for class_name, method, first, second in duplicate_method_definitions(
            source, str(py_file)
        ):
            if PENDING_TRIAGE.get((rel, class_name, method)):
                continue
            violations.append(
                f"{rel}::{class_name}.{method} — defined at L{first}, "
                f"overwritten at L{second} (the L{first} body is dead)"
            )
    return violations, len(files)


def test_no_class_defines_the_same_method_twice() -> None:
    """#2357: the tree carries no untriaged dead-by-overwrite definition."""
    violations, population = _scan_production_tree()
    assert not violations, (
        f"{len(violations)} duplicate method definition(s) over {population} "
        "files walked:\n" + "\n".join(f"  - {v}" for v in violations)
    )


def test_every_production_file_parses_so_the_population_is_whole() -> None:
    """The count above is worthless without the population it was taken on.

    This is the #2357 lesson made executable: reading ``utf-8`` strict and
    swallowing ``SyntaxError`` hid 13 BOM-bearing files — including the one
    holding the fourth site.
    """
    unparseable: list[str] = []
    for py_file in _production_py_files():
        try:
            ast.parse(py_file.read_text(encoding="utf-8-sig"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError) as exc:
            unparseable.append(f"{py_file.relative_to(PKG_ROOT).as_posix()}: {exc}")
    assert not unparseable, (
        "files the duplicate scan could not parse — it must not report a count "
        "over a population it silently amputated:\n" + "\n".join(unparseable)
    )


def test_the_pending_triage_map_has_no_stale_entry() -> None:
    """A triaged entry whose duplicate is gone must redden, not rot silently."""
    stale: list[str] = []
    for (rel, class_name, method), owner in PENDING_TRIAGE.items():
        path = PKG_ROOT / rel
        if not path.exists():
            stale.append(f"{rel} (file gone) — drop the {owner} entry")
            continue
        duplicates = duplicate_method_definitions(
            path.read_text(encoding="utf-8-sig"), str(path)
        )
        if not any(c == class_name and m == method for c, m, _, _ in duplicates):
            stale.append(
                f"{rel}::{class_name}.{method} is no longer duplicated — "
                f"{owner} landed, remove the entry"
            )
    assert not stale, "stale PENDING_TRIAGE entries:\n" + "\n".join(
        f"  - {s}" for s in stale
    )


def test_the_three_repaired_sites_are_defined_once() -> None:
    """Regression on the exact sites #2357 removed."""
    for rel, class_name, method in (
        ("orchestration/group_chat.py", "GroupChatOrchestration", "cleanup_session"),
        ("services/logic_service.py", "LogicService", "get_service_status"),
        ("services/logic_service.py", "LogicService", "clear_cache"),
    ):
        source = (PKG_ROOT / rel).read_text(encoding="utf-8-sig")
        duplicates = duplicate_method_definitions(source, rel)
        assert not any(
            c == class_name and m == method for c, m, _, _ in duplicates
        ), f"{rel}::{class_name}.{method} is defined twice again"


# --------------------------------------------------------------------------
# Non-vacuity — the guard is shown to bite, and to stay silent where it must.
# --------------------------------------------------------------------------


def test_the_scan_detects_a_synthetic_duplicate() -> None:
    """Negative control: a green above could otherwise just mean "found nothing"."""
    source = (
        "class Probe:\n"
        "    def run(self):\n"
        "        return 1\n"
        "\n"
        "    def run(self):\n"
        "        return 2\n"
    )
    assert duplicate_method_definitions(source) == [("Probe", "run", 2, 5)]


def test_a_property_setter_pair_is_not_reported() -> None:
    """The ``DebateAgent.strategy`` shape — excluded by construction, not by name."""
    source = (
        "class Probe:\n"
        "    @property\n"
        "    def strategy(self):\n"
        "        return self._s\n"
        "\n"
        "    @strategy.setter\n"
        "    def strategy(self, value):\n"
        "        self._s = value\n"
    )
    assert duplicate_method_definitions(source) == []


def test_an_overload_group_is_not_reported() -> None:
    source = (
        "from typing import overload\n"
        "class Probe:\n"
        "    @overload\n"
        "    def f(self, x: int) -> int: ...\n"
        "    @overload\n"
        "    def f(self, x: str) -> str: ...\n"
        "    def f(self, x):\n"
        "        return x\n"
    )
    assert duplicate_method_definitions(source) == []


def test_a_bom_bearing_source_is_read_not_skipped() -> None:
    """The #2357 trap itself: strict utf-8 raises, utf-8-sig reads."""
    raw = (
        "class Probe:\n"
        "    def run(self):\n"
        "        pass\n"
        "\n"
        "    def run(self):\n"
        "        pass\n"
    ).encode("utf-8-sig")

    with pytest.raises(SyntaxError):
        ast.parse(raw.decode("utf-8"))

    assert duplicate_method_definitions(raw.decode("utf-8-sig")) == [
        ("Probe", "run", 2, 5)
    ]
