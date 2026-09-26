"""#2610 — the jpype_tweety workers start the JVM the way production does.

Each of the eight workers under ``tests/integration/jpype_tweety/workers/``
built its own classpath from one file, ``tweety-full-*-with-dependencies.jar``.
That fat JAR is no longer provisioned (#1874), and the eight copies went red
together without anyone seeing it: the directory is outside the gate argv
(#1814, #1867). This guard is inside the argv. It reads the workers' AST:
none of them starts a JVM or names a jar itself; each one calls ``start_jvm``
from ``_production_jvm``, which calls ``jvm_setup.initialize_jvm``.
"""

import ast
from pathlib import Path

WORKERS = (
    Path(__file__).resolve().parents[1] / "integration" / "jpype_tweety" / "workers"
)


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _workers() -> list:
    found = sorted(WORKERS.glob("worker_*.py"))
    assert len(found) >= 8, f"{len(found)} worker(s) under {WORKERS}: expected 8"
    return found


def _imports(tree: ast.AST, module: str, name: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == module
        and any(alias.name == name for alias in node.names)
        for node in ast.walk(tree)
    )


def _calls(tree: ast.AST, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
        for node in ast.walk(tree)
    )


def test_no_worker_starts_the_jvm_or_names_a_jar():
    offenders = []
    for path in _workers():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Attribute) and node.attr in {
                "startJVM",
                "getDefaultJVMPath",
            }:
                offenders.append(f"{path.name}:{node.lineno} .{node.attr}")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and ".jar" in node.value
            ):
                offenders.append(f"{path.name}:{node.lineno} {node.value!r}")
    assert not offenders, (
        "A worker builds its own JVM or classpath again; start it with "
        f"_production_jvm.start_jvm(): {offenders}"
    )


def test_every_worker_starts_through_the_production_helper():
    missing = [
        path.name
        for path in _workers()
        if not (
            _imports(_tree(path), "_production_jvm", "start_jvm")
            and _calls(_tree(path), "start_jvm")
        )
    ]
    assert not missing, f"Workers that do not call _production_jvm.start_jvm: {missing}"


def test_the_helper_is_production_initialize_jvm():
    tree = _tree(WORKERS / "_production_jvm.py")
    assert _imports(tree, "argumentation_analysis.core.jvm_setup", "initialize_jvm")
    assert _calls(tree, "initialize_jvm")
