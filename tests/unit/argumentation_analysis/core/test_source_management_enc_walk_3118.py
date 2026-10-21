"""#3118 — the encrypted-corpus listing walks only the corpus directories.

Measured on seat po-2023 (2026-10-21, lock env): ``list_available_sources``
ended with ``project_root.glob("**/*.enc")``, descending ``node_modules``,
``.git``, ``portable_jdk`` and caches to produce a status listing. The #2451
ecosystem probe timed out at 900 s inside that walk; in xdist gates the same
test appeared for three rounds as "worker gwN crashed", which reads like a
native crash and is really this timeout.

The listing feeds ``source_tests["enc_files"]`` — a status dict whose only
consumer logs the dict's key names — so nothing needs the whole checkout. The
walk is bounded to the directories that can legitimately hold a corpus:
``argumentation_analysis/data`` (``settings.config_dir`` /
``ui.CONFIG_DIR`` / ``paths.DATA_DIR`` all point there) and the historical
checkout-root ``data/``. The ``.enc`` fixtures under ``tests/`` are not user
corpora and are no longer listed.

Witness 1 replays a fake checkout that plants ``.enc`` files in the ignored
trees: the old unbounded walk lists them, the bounded one does not.
Witness 2 holds the real checkout's canonical corpus in the listing and bounds
the call's duration.
"""

from __future__ import annotations

import time
import types
from pathlib import Path

from argumentation_analysis.core import source_management
from argumentation_analysis.core.source_management import (
    UnifiedSourceConfig,
    UnifiedSourceManager,
    UnifiedSourceType,
)


def _plant(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a real corpus")


def _listing(monkeypatch, module_file: Path | None = None) -> dict:
    """Call the real lister, skipping the passphrase-gated complex branch."""
    monkeypatch.setattr(
        source_management, "settings", types.SimpleNamespace(passphrase=None)
    )
    if module_file is not None:
        # The walk root derives from the module's ``__file__``; pointing it at
        # a fake checkout keeps the replay off the real tree.
        monkeypatch.setattr(source_management, "__file__", str(module_file))
    manager = UnifiedSourceManager(
        UnifiedSourceConfig(source_type=UnifiedSourceType.SIMPLE)
    )
    return manager.list_available_sources()


def test_encrypted_corpora_are_listed_only_from_the_corpus_dirs(tmp_path, monkeypatch):
    fake_module = tmp_path / "argumentation_analysis" / "core" / "source_management.py"
    _plant(fake_module)
    _plant(tmp_path / "argumentation_analysis" / "data" / "corpus_A.enc")
    _plant(tmp_path / "argumentation_analysis" / "data" / "nested" / "corpus_B.enc")
    for ignored in (
        tmp_path / "node_modules" / "pkg" / "vendored.enc",
        tmp_path / ".git" / "objects" / "loose.enc",
        tmp_path / "portable_jdk" / "jdk-17" / "cached.enc",
        tmp_path / "_temp" / "run" / "scratch.enc",
        tmp_path / "tests" / "fixture.enc",
    ):
        _plant(ignored)

    sources = _listing(monkeypatch, module_file=fake_module)

    assert [Path(p) for p in sources["enc_files"]] == [
        Path("argumentation_analysis/data/corpus_A.enc"),
        Path("argumentation_analysis/data/nested/corpus_B.enc"),
    ], (
        "the listing must come from the corpus directories only: a planted "
        ".enc from node_modules/.git/portable_jdk/_temp/tests in this list "
        "means the walk still descends the whole checkout (#3118)"
    )


def test_the_real_checkout_lists_its_canonical_corpus(monkeypatch):
    started = time.monotonic()
    sources = _listing(monkeypatch)
    elapsed = time.monotonic() - started

    listed = [Path(p) for p in sources["enc_files"]]
    assert (
        Path("argumentation_analysis/data/extract_sources.json.gz.enc") in listed
    ), f"the canonical corpus left the listing: {listed}"
    assert elapsed < 60, (
        f"the listing took {elapsed:.1f}s on this checkout — it is still "
        "walking beyond the corpus directories (the #2451 probe timed out at "
        "900 s on a loaded seat)"
    )
