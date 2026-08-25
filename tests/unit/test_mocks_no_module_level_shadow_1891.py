"""Guard #1891: nothing under tests/mocks/ may shadow a library at import time.

The poison mechanism (measured on the #1891 dead mocks): a module-level
statement writing into ``sys.modules`` — ``pytest_mock.py:41`` replaced
pytest itself, ``networkx_mock.py:422-435`` installed 15 ``networkx.*``
entries — so any future import of the file silently swaps a real
dependency for a mock, process-wide. The 8 dead self-installers were
deleted; this guard reddens if the pattern comes back.

Measured exceptions, both PRE-EXISTING jpype-shadow infrastructure (the
package's declared purpose — conftest boots the JVM through it):

- ``bootstrap.py`` — module-level ``sys.modules["jpype"]`` writes behind an
  env guard. Measured zero-importer as of #1891 and flagged to the
  coordinator for its own arbitration round; kept because the issue listed
  it "Vivants (ne PAS toucher)".
- ``jpype_components/imports.py`` — installs the fake ``jpype.imports``;
  load-bearing: ``jpype_setup.py:82`` imports it at module level.

Writes INSIDE functions are legitimate (numpy_setup.py installs matplotlib
mocks inside a function): the AST walk does not descend into function or
class bodies, so only import-time statements count.

Non-vacuity: the scan must see the mocks package itself — if tests/mocks/
vanishes or the allowlisted files are deleted wholesale, the guard reddens
rather than blessing an empty set.
"""

import ast
from pathlib import Path

MOCKS_DIR = Path(__file__).resolve().parents[2] / "tests" / "mocks"

ALLOWED_SHADOW_FILES = {
    "bootstrap.py": "pre-existing jpype bootstrap, #1891 flagged dead-but-untouchable",
    "jpype_components/imports.py": "load-bearing jpype.imports shadow (jpype_setup.py)",
}

_CALL_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _is_sys_modules_subscript(target: ast.expr) -> bool:
    return (
        isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Attribute)
        and target.value.attr == "modules"
        and isinstance(target.value.value, ast.Name)
        and target.value.value.id == "sys"
    )


def _import_time_shadow_writes(tree: ast.Module) -> list[int]:
    """Lineno of every sys.modules[...] assignment executed at import time."""
    hits: list[int] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _CALL_SCOPES):
                continue
            if isinstance(child, ast.Assign):
                if any(_is_sys_modules_subscript(t) for t in child.targets):
                    hits.append(child.lineno)
            elif isinstance(child, (ast.AnnAssign, ast.AugAssign)):
                if child.target is not None and _is_sys_modules_subscript(child.target):
                    hits.append(child.lineno)
            visit(child)

    visit(tree)
    return hits


def test_no_import_time_sys_modules_shadow_in_mocks():
    py_files = sorted(MOCKS_DIR.rglob("*.py"))
    assert py_files, (
        "#1891: tests/mocks/ has no Python files — the scan would be vacuous. "
        "If the package was deliberately removed, delete this guard with it."
    )

    offenders: dict[str, list[int]] = {}
    for path in py_files:
        rel = path.relative_to(MOCKS_DIR).as_posix()
        if rel in ALLOWED_SHADOW_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        writes = _import_time_shadow_writes(tree)
        if writes:
            offenders[rel] = writes

    assert not offenders, (
        "#1891: module-level sys.modules write(s) at import time under "
        "tests/mocks/ — this is the self-install poison (a single import "
        "silently swaps a real library process-wide). Move the write into "
        "a function the caller invokes deliberately:\n"
        + "\n".join(f"  {rel}: lines {lines}" for rel, lines in offenders.items())
    )


def test_allowlisted_shadow_files_still_exist():
    """Population control: the allowlist must track reality both ways.

    A vanished allowlisted file means the exception is stale — remove it
    from ALLOWED_SHADOW_FILES so the scan covers the package honestly.
    """
    stale = sorted(
        rel for rel in ALLOWED_SHADOW_FILES if not (MOCKS_DIR / rel).exists()
    )
    assert not stale, (
        "#1891: allowlisted files no longer exist — prune ALLOWED_SHADOW_FILES: "
        f"{stale}"
    )
