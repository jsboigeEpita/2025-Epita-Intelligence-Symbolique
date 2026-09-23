"""Non-vacuity for ``tests/support/withdrawn_modules.py`` (#2436): a directory
holding only caches reads as withdrawn, and anything else under it does not."""

import sys

from tests.support.withdrawn_modules import importable_files, still_importable


def test_cache_only_trees_hold_nothing_importable(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "gone.cpython-310.pyc").write_bytes(b"")
    (tmp_path / "sub" / "__pycache__").mkdir(parents=True)
    (tmp_path / "sub" / "__pycache__" / "x.cpython-310.pyc").write_bytes(b"")
    assert importable_files([tmp_path]) == []


def test_a_source_anywhere_under_the_tree_counts(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "revived.py").write_text("", encoding="utf-8")
    assert importable_files([tmp_path]) == ["sub/revived.py"]


def test_still_importable_on_real_names_and_leftovers(tmp_path, monkeypatch):
    root = tmp_path / "root"
    (root / "leftover_2436" / "__pycache__").mkdir(parents=True)
    (root / "revived_2436").mkdir()
    (root / "revived_2436" / "mod.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(root))
    monkeypatch.delitem(sys.modules, "leftover_2436", raising=False)

    assert still_importable("argumentation_analysis") is True
    assert still_importable("argumentation_analysis.no_such_module_2436") is False
    assert still_importable("no_such_parent_2436.child") is False
    # A cache-only directory resolves as a namespace, yet holds nothing.
    assert still_importable("leftover_2436") is False
    assert still_importable("revived_2436") is True
