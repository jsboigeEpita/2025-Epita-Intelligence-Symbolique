# -*- coding: utf-8 -*-
"""
#2459 — a library module never ends the importing process.

On ``main``, ``utils/cleanup_sensitive_files.py`` and ``utils/restore_config.py``
called ``sys.exit(1)`` at import when ``ui.extract_utils`` (which pulls
``services.crypto_service``) could not be imported. ``utils/__init__.py``
imports both, so ``import argumentation_analysis.utils.<anything>`` raised
``SystemExit(1)``. That is not an ``ImportError``, so no ``try/except
ImportError`` around the import could catch it.
``pipelines/unified_pipeline.py`` did the same around ``version_validator``.

The subprocess tests make ``crypto_service`` unimportable
(``sys.modules[name] = None``) in a fresh interpreter, so the test process
keeps its own modules. The import may still fail: ``services/__init__.py``
imports ``crypto_service`` without a guard, and ``utils/dev_tools`` reaches
it. What it may no longer do is end the process. The failure is an
``ImportError`` that names the missing module, which a caller can catch.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PACKAGE = REPO_ROOT / "argumentation_analysis"
EXIT_CALLS = {"sys.exit", "exit", "quit", "os._exit"}


def _run_without_crypto(statement: str) -> subprocess.CompletedProcess:
    code = (
        "import sys\n"
        "sys.modules['argumentation_analysis.services.crypto_service'] = None\n"
        "try:\n"
        f"    {statement}\n"
        "    print('IMPORTED')\n"
        "except ImportError as e:\n"
        "    print('IMPORT_ERROR', e)\n"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.parametrize(
    "statement",
    [
        "import argumentation_analysis.utils.version_validator",
        "import argumentation_analysis.utils.restore_config",
        "import argumentation_analysis.utils.cleanup_sensitive_files",
    ],
)
def test_a_missing_crypto_service_is_an_import_error_not_an_exit(statement):
    result = _run_without_crypto(statement)

    assert result.returncode == 0, result.stderr[-2000:]
    assert "IMPORTED" in result.stdout or (
        "IMPORT_ERROR" in result.stdout and "crypto_service" in result.stdout
    ), result.stdout[-2000:]


def _import_time_exits(source: str, name: str) -> list:
    """Exit calls that run when the module is imported: outside any function
    or lambda, and outside ``if __name__ == "__main__"``."""
    hits = []

    def walk(node, deferred):
        for child in ast.iter_child_nodes(node):
            child_deferred = deferred or isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
            )
            if isinstance(child, ast.If) and "__main__" in ast.unparse(child.test):
                child_deferred = True
            if (
                isinstance(child, ast.Call)
                and ast.unparse(child.func) in EXIT_CALLS
                and not deferred
            ):
                hits.append(f"{name}:{child.lineno}")
            walk(child, child_deferred)

    walk(ast.parse(source), False)
    return hits


def test_the_scanner_finds_an_import_time_exit():
    """Non-vacuity: the scanner flags the shape it looks for, and only it."""
    source = (
        "import sys\n"
        "try:\n"
        "    import missing\n"
        "except ImportError:\n"
        "    sys.exit(1)\n"
        "def main():\n"
        "    sys.exit(2)\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n"
    )
    assert _import_time_exits(source, "synthetic") == ["synthetic:5"]


def test_no_library_module_exits_at_import():
    files = sorted(PACKAGE.rglob("*.py"))
    assert len(files) > 100, f"only {len(files)} files under {PACKAGE}"

    hits = []
    for path in files:
        # utf-8-sig: some files start with a BOM. A file that does not parse
        # fails the test instead of being skipped.
        source = path.read_text(encoding="utf-8-sig")
        hits.extend(_import_time_exits(source, str(path.relative_to(REPO_ROOT))))

    assert hits == []
