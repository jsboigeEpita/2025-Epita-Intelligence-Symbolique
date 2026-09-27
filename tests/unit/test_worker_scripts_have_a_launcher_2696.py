"""#2696: every worker script under ``tests/`` has a launcher.

A ``worker_*.py`` file is never collected by pytest: its name does not
match ``test_*.py``. It runs only when a launcher, a ``test_*.py`` or
``conftest.py``, builds its path and hands it to a subprocess runner
(``run_in_jvm_subprocess`` and its kin). A worker that no launcher names
looks like coverage and has no path to run. #2696 found three that imported
a ``JvmManager`` the repository never defined; none had ever executed.

The census resolves launcher paths instead of matching file names. Two
workers once shared the name ``worker_minimal_jvm_startup.py``: the launcher
in ``tests/integration/jpype_tweety/`` ran its own sibling, not the one in
``tests/integration/workers/``, which no launcher named and #2700 retired.
The tree no longer holds such a pair, so a synthetic tree keeps the case
under test. A path is read in the two forms the
launchers use: a ``Path(__file__)[.resolve()][.parent]* / "..."`` chain,
relative to the launcher, and ``os.path.join("tests", ...)`` with string
arguments only, relative to the repository root. A worker's file name that
appears in a launcher in any other form reddens the census rather than
counting as a launch or being skipped.

The orphans the census found when it landed were triaged under #2700 and
all four retired; there is no exemption list. A new orphan is launched, or
retired under the Cleanup Gate.
"""

import ast
import functools
from pathlib import Path

from tests.support.tree_walk import iter_files

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS = REPO_ROOT / "tests"


def _archived(path: Path, root: Path) -> bool:
    return "_archived" in path.relative_to(root).parts


def _workers(root: Path) -> list[Path]:
    return sorted(p for p in iter_files(root, "worker_*.py") if not _archived(p, root))


def _launch_files(root: Path) -> list[Path]:
    return sorted(
        p
        for p in iter_files(root)
        if (p.name.startswith("test_") or p.name == "conftest.py")
        and not _archived(p, root)
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
def _census(
    root: Path = TESTS,
) -> tuple[list[Path], frozenset[Path], tuple[str, ...]]:
    """Workers, the worker paths some launcher resolves, unread mentions."""
    workers = _workers(root)
    names = {w.name for w in workers}
    launched: set[Path] = set()
    unread: list[str] = []
    for launcher in _launch_files(root):
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
    orphans = sorted(_rel(w) for w in workers if w.resolve() not in launched)
    assert not orphans, (
        "worker scripts that no test_*.py or conftest.py launches by path "
        "(#2696): give each a launcher and run it, or retire it under the "
        f"Cleanup Gate naming the live test that covers it: {orphans}"
    )


def test_a_launcher_launches_its_own_path_not_every_worker_of_that_name(tmp_path):
    """Two workers share a name, one launcher names one of them by path.

    The tree held this case until #2700 retired the unlaunched twin of
    ``worker_minimal_jvm_startup.py``; a census matching names would have
    counted both as launched.
    """
    launched_twin = tmp_path / "a" / "workers" / "worker_twin.py"
    orphan_twin = tmp_path / "b" / "workers" / "worker_twin.py"
    for worker in (launched_twin, orphan_twin):
        worker.parent.mkdir(parents=True)
        worker.write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "a" / "test_twin.py").write_text(
        "from pathlib import Path\n"
        "WORKER = Path(__file__).parent / 'workers' / 'worker_twin.py'\n",
        encoding="utf-8",
    )
    workers, launched, unread = _census(tmp_path)
    assert len(workers) == 2 and not unread
    assert launched_twin.resolve() in launched
    assert orphan_twin.resolve() not in launched


def test_the_census_resolves_both_launcher_forms():
    """Positive control: one launch of each form is seen, at its own path."""
    _, launched, _ = _census()
    by_file_chain = (
        TESTS / "integration/jpype_tweety/workers/worker_minimal_jvm_startup.py"
    )
    by_os_path_join = TESTS / "unit/api/workers/worker_api_endpoints.py"
    assert by_file_chain.resolve() in launched
    assert by_os_path_join.resolve() in launched
