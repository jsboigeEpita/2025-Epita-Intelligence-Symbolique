"""Every fixture module under ``tests/fixtures/`` imports, and every doc import from it resolves (#2416).

``tests/fixtures/agent_fixtures.py`` could not be imported from 2025-07-31 (91d4440e moved
the analysers it imported) until its removal. Pytest never collects a module not named
``test_*``, and nothing imported it, so no suite reddened for 14 months. Three guides
meanwhile pointed readers at it with an import that raised. Both guards below make that class
of rot red.

Scope, stated with the count: every ``*.py`` under ``tests/fixtures/`` (recursively, minus
``__init__``); every ``from tests.fixtures.<module> import ...`` line in the ``*.md`` files
under ``docs/``, ``tests/`` and the repository root, minus paths containing ``archive``.
"""

import importlib
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
DOC_IMPORT = re.compile(
    r"^\s*from (tests\.fixtures\.[A-Za-z_][\w.]*) import ([^\n]+)$", re.MULTILINE
)


def _fixture_files():
    return sorted(
        p
        for p in FIXTURES.rglob("*.py")
        if p.stem != "__init__" and "__pycache__" not in p.parts
    )


def _doc_files():
    docs = (
        list((ROOT / "docs").rglob("*.md"))
        + list((ROOT / "tests").rglob("*.md"))
        + list(ROOT.glob("*.md"))
    )
    return sorted(
        p
        for p in docs
        if not any("archive" in part.lower() for part in p.relative_to(ROOT).parts)
    )


def _doc_imports():
    found = []
    for doc in _doc_files():
        text = doc.read_text(encoding="utf-8-sig", errors="replace")
        for match in DOC_IMPORT.finditer(text):
            names = [
                n.strip().split(" as ")[0].strip()
                for n in match.group(2).strip().strip("()").split(",")
                if n.strip()
            ]
            found.append((doc.relative_to(ROOT).as_posix(), match.group(1), names))
    return found


FIXTURE_FILES = _fixture_files()
DOC_IMPORTS = _doc_imports()


def test_populations_are_not_empty():
    # Floors, not exact counts: the populations may grow, never silently vanish.
    assert len(FIXTURE_FILES) >= 8, [p.name for p in FIXTURE_FILES]
    assert len(DOC_IMPORTS) >= 4, DOC_IMPORTS


@pytest.mark.parametrize(
    "path", FIXTURE_FILES, ids=lambda p: p.relative_to(FIXTURES).as_posix()
)
def test_fixture_module_imports(path):
    name = "_fixture_probe_" + "_".join(
        path.relative_to(FIXTURES).with_suffix("").parts
    )
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


@pytest.mark.parametrize(
    "doc, module, names",
    DOC_IMPORTS,
    ids=[f"{doc}:{module.rsplit('.', 1)[-1]}" for doc, module, _ in DOC_IMPORTS],
)
def test_doc_import_resolves(doc, module, names):
    imported = importlib.import_module(module)
    missing = [n for n in names if not hasattr(imported, n)]
    assert not missing, f"{doc}: `from {module} import` names {missing}, absent"
