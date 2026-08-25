"""A worker spawned as a subprocess must be able to report a failure.

`run_in_jvm_subprocess` decides pass/fail from the child's **exit code**. A
worker whose ``__main__`` calls ``pytest.main(...)`` as a bare expression
throws that code away, so the process exits 0 -- and the launcher reports PASS
whatever its tests did. A worker with no ``__main__`` at all is worse: it
defines its tests, runs none of them, and exits 0.

Measured before the fix: of 17 spawned workers, 5 discarded the code and 1 had
no ``__main__`` (14 tests defined, 0 run). Verified on a toy worker holding one
failing test -- ``rc=0`` without ``sys.exit``, ``rc!=0`` with it.

This guard is not a name list: it derives the population from the launchers
themselves, so a worker added tomorrow is covered without editing anything
here.
"""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER_REF = re.compile(r'"(worker_[A-Za-z0-9_]+\.py)"')


def _spawned_workers():
    """Every script a launcher hands to `run_in_jvm_subprocess`."""
    found = set()
    for path in (ROOT / "tests").rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        if "run_in_jvm_subprocess(" not in text:
            continue
        for match in WORKER_REF.finditer(text):
            found.update((ROOT / "tests").rglob(match.group(1)))
    return sorted(found)


def _main_block(tree):
    for node in tree.body:
        if isinstance(node, ast.If) and "__main__" in ast.dump(node.test):
            return node
    return None


def _module_functions(tree):
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _can_report_failure(path: Path):
    """(verdict, why) — can this script turn a test failure into rc != 0?

    The exit may live one hop away: several workers use ``__main__: main()``
    and carry ``sys.exit`` inside ``main``. Reading only the ``__main__`` body
    reported those as broken -- a false positive from an instrument whose
    granularity was coarser than the thing it judged. So a single call to a
    module-level function is followed into that function.
    """
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    block = _main_block(tree)
    if block is None:
        return (
            False,
            "aucun bloc __main__ : lancé comme script, il ne lance aucun test et sort 0",
        )

    functions = _module_functions(tree)
    sources = [ast.unparse(block)]
    for node in ast.walk(block):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            target = functions.get(node.func.id)
            if target is not None:
                sources.append(ast.unparse(target))
    body = "\n".join(sources)

    exits = "sys.exit" in body or "SystemExit" in body or re.search(r"exit\(", body)
    if "pytest.main(" in body and not exits:
        return (
            False,
            "pytest.main() en expression nue : son code de retour est jeté, le script sort 0",
        )
    if not exits:
        return (
            False,
            "__main__ sans sys.exit : aucun échec ne peut atteindre le code de sortie",
        )
    return True, ""


def test_the_population_is_not_empty():
    """Non-vacuity: an empty population would make the guard below pass while
    checking nothing -- the shape a zero from an unproven instrument has."""
    workers = _spawned_workers()
    assert len(workers) >= 15, (
        f"only {len(workers)} spawned worker(s) discovered; the launcher sweep "
        "is not reaching them, so this guard measures nothing"
    )


@pytest.mark.parametrize("worker", _spawned_workers(), ids=lambda p: p.name)
def test_a_spawned_worker_can_report_a_failure(worker):
    ok, why = _can_report_failure(worker)
    assert ok, (
        f"#1872: {worker.relative_to(ROOT).as_posix()} cannot report a failure "
        f"to its launcher.\n  {why}\n"
        "  run_in_jvm_subprocess reads the exit code, so this worker's launcher "
        "reports PASS whatever its tests do.\n"
        "  Fix: wrap the call — sys.exit(pytest.main([...]))"
    )
