"""#2696: every worker script under ``tests/`` has a launcher.

A ``worker_*.py`` file is never collected by pytest: its name does not
match ``test_*.py``. It runs only when a launcher, a ``test_*.py`` or
``conftest.py``, builds its path and hands it to a subprocess runner
(``run_in_jvm_subprocess`` and its kin). A worker that no launcher names
looks like coverage and has no path to run. #2696 found three that imported
a ``JvmManager`` the repository never defined; none had ever executed.

The census resolves launcher paths instead of matching file names. Two
workers share the name ``worker_minimal_jvm_startup.py``, and the launcher
in ``tests/integration/jpype_tweety/`` runs its own sibling, not the one in
``tests/integration/workers/`` (#2700). A path is read in the two forms the
launchers use: a ``Path(__file__)[.resolve()][.parent]* / "..."`` chain,
relative to the launcher, and ``os.path.join("tests", ...)`` with string
arguments only, relative to the repository root. A worker's file name that
appears in a launcher in any other form reddens the census rather than
counting as a launch or being skipped.

``PENDING_TRIAGE`` names the orphans the tree already carries, each with
the issue that owns its triage. It only shrinks: an entry reddens once its
worker gains a launcher or leaves the tree.
"""

import ast
import functools
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS = REPO_ROOT / "tests"

PENDING_TRIAGE: dict[str, str] = {
    "tests/integration/argumentation_analysis/workers/worker_hardening_cases.py": "#2700",
    "tests/integration/workers/worker_logic_puzzles_hardening.py": "#2700",
    "tests/integration/workers/worker_minimal_jvm_startup.py": "#2700",
    "tests/unit/api/workers/worker_dung_service.py": "#2700",
}


def _archived(path: Path) -> bool:
    return "_archived" in path.relative_to(TESTS).parts


def _workers() -> list[Path]:
    return sorted(p for p in TESTS.rglob("worker_*.py") if not _archived(p))


def _launch_files() -> list[Path]:
    return sorted(
        p
        for p in TESTS.rglob("*.py")
        if (p.name.startswith("test_") or p.name == "conftest.py") and not _archived(p)
    )


def _file_anchor(node: ast.AST, launcher: Path) -> Path | None:
    """``Path(__file__)``, ``.resolve()`` and ``.parent`` steps, or None."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "__file__"
    ):
        return launcher
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "resolve"
        and not node.args
    ):
        return _file_anchor(node.func.value, launcher)
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        anchor = _file_anchor(node.value, launcher)
        return anchor.parent if anchor is not None else None
    return None


def _resolve(node: ast.AST, launcher: Path) -> Path | None:
    """The path a launcher expression names, in one of the two known forms."""
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.right, ast.Constant)
        and isinstance(node.right.value, str)
    ):
        base = _resolve(node.left, launcher)
        return base / node.right.value if base is not None else None
    if (
        isinstance(node, ast.Call)
        and ast.unparse(node.func) == "os.path.join"
        and node.args
        and all(
            isinstance(a, ast.Constant) and isinstance(a.value, str) for a in node.args
        )
    ):
        return REPO_ROOT.joinpath(*(a.value for a in node.args))
    return _file_anchor(node, launcher)


@functools.lru_cache(maxsize=None)
def _census() -> tuple[list[Path], frozenset[Path], tuple[str, ...]]:
    """Workers, the worker paths some launcher resolves, unread mentions."""
    workers = _workers()
    names = {w.name for w in workers}
    launched: set[Path] = set()
    unread: list[str] = []
    for launcher in _launch_files():
        tree = ast.parse(launcher.read_text(encoding="utf-8-sig"), str(launcher))
        read: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.BinOp, ast.Call)):
                continue
            path = _resolve(node, launcher)
            if path is None or path.name not in names:
                continue
            launched.add(path.resolve())
            read.update(id(n) for n in ast.walk(node) if isinstance(n, ast.Constant))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node.value in names
                and id(node) not in read
            ):
                rel = launcher.relative_to(REPO_ROOT).as_posix()
                unread.append(f"{rel}:{node.lineno} names {node.value}")
    return workers, frozenset(launched), tuple(unread)


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def test_the_census_reads_every_launcher_mention():
    """A worker's name in a launcher, in a form the census cannot resolve."""
    _, _, unread = _census()
    assert not unread, (
        "a launcher names a worker in a form this census does not read; "
        "extend _resolve rather than letting the mention count or vanish: "
        f"{unread}"
    )


def test_every_worker_script_has_a_launcher():
    workers, launched, _ = _census()
    assert len(workers) >= 15, f"population collapsed: {len(workers)} workers"
    orphans = {_rel(w) for w in workers if w.resolve() not in launched}
    new = sorted(orphans - set(PENDING_TRIAGE))
    assert not new, (
        "worker scripts that no test_*.py or conftest.py launches by path "
        "(#2696): give each a launcher and run it, or retire it under the "
        f"Cleanup Gate naming the live test that covers it: {new}"
    )


def test_pending_entries_are_still_orphans():
    """Shrink-only: an entry goes once its worker is launched or retired."""
    workers, launched, _ = _census()
    present = {_rel(w): w for w in workers}
    stale = sorted(
        f"{path} ({owner})"
        for path, owner in PENDING_TRIAGE.items()
        if path not in present or present[path].resolve() in launched
    )
    assert not stale, f"remove these PENDING_TRIAGE entries: {stale}"


def test_the_census_resolves_both_launcher_forms():
    """Positive control: one launch of each form is seen, at its own path."""
    _, launched, _ = _census()
    by_file_chain = (
        TESTS / "integration/jpype_tweety/workers/worker_minimal_jvm_startup.py"
    )
    by_os_path_join = TESTS / "unit/api/workers/worker_api_endpoints.py"
    assert by_file_chain.resolve() in launched
    assert by_os_path_join.resolve() in launched
