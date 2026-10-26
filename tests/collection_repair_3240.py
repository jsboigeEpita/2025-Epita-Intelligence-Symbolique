# -*- coding: utf-8 -*-
"""#3240 — collection tolerates a vanished entry that ``norecursedirs`` owns.

## The frame

The traceback in #3240 is ``pathlib.py: lstat -> stat -> FileNotFoundError``
on a ``tests/_probe_race_<hex>`` path, under a child pytest collecting one
file (``P alone``). It is not the #3080 reconciliation port. On Windows,
``Dir.collect`` / ``Package.collect`` sees the probe as a directory, the
churner removes it, and the default ``pytest_ignore_collect`` hook can no
longer see a directory on which to apply ``norecursedirs``. A collector for
the vanished path enters the node list; ``Session.collect`` then matches the
initial file path with ``samefile_nofollow(node.path, ...)``, whose
``Path.lstat()`` raises.

## The repair

One shared iterator now serves both production collectors. For a directory
entry, the ``norecursedirs`` patterns are consulted **before** the plugin
ignore hook, so an ignored probe never becomes a node whose path can vanish
under ``samefile_nofollow``. Explicitly passed paths keep their existing
exemption (``isinitpath(..., with_parents=True)``). A missing ignored entry
whose type cannot even be read is skipped as well; every non-ignored entry,
and every non-vanished error, keeps propagating. The probe still lives under
``tests/`` and #2607's churner still runs in the real tree: what changes is
that collection pays no filesystem visit to a path it is configured to
ignore.

A stale probe left behind by a dead run is covered by the same early skip:
it is a stable ignored directory, so it contributes no node and its files
are never collected. It remains harmless on disk and is not removed here.

## Lifetime

This is a port of the repair into the gated pytest 9.1.1, on the #3080
pattern: a version guard, self-disabling at 9.1.2. If a later pytest still
carries the frame, the #3240 witness goes red against that version instead of
silently keeping a shim that no longer measures it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional

import pytest

import _pytest.main
import _pytest.python
from _pytest.pathlib import _ignore_error, fnmatch_ex, scandir

_GATED_VERSION = (9, 1, 1)


def _pytest_is_gated_version() -> bool:
    try:
        parts = tuple(int(part) for part in pytest.__version__.split(".")[:3])
    except ValueError:
        return False
    return parts == _GATED_VERSION


def _is_ignored_by_norecursedirs(collector, path: Path) -> bool:
    if collector.session.isinitpath(path, with_parents=True):
        return False
    return any(
        fnmatch_ex(pattern, path)
        for pattern in collector.config.getini("norecursedirs")
    )


def _directory_kind(entry, ignored: bool) -> Optional[bool]:
    """``True``/``False`` for a readable DirEntry, ``None`` if ignored/gone."""
    try:
        return entry.is_dir()
    except OSError as exc:
        if ignored and _ignore_error(exc):
            return None
        raise


def _collect_entries_3240(collector, sort_key=None) -> Iterator:
    """Yield the children of a directory collector, as pytest 9.1.1 does.

    This is the body of ``Dir.collect`` and ``Package.collect`` with one
    difference: an entry whose path is covered by ``norecursedirs`` is skipped
    by the configured pattern before any plugin hook can stat that path.
    """
    config = collector.config
    ihook = collector.ihook
    entries = (
        scandir(collector.path)
        if sort_key is None
        else scandir(collector.path, sort_key)
    )

    for direntry in entries:
        path = Path(direntry.path)
        ignored = _is_ignored_by_norecursedirs(collector, path)
        is_dir = _directory_kind(direntry, ignored)
        if is_dir is None:
            continue

        if is_dir:
            if not collector.session.isinitpath(path, with_parents=True):
                if ignored:
                    continue
                if ihook.pytest_ignore_collect(collection_path=path, config=config):
                    continue
            col = ihook.pytest_collect_directory(path=path, parent=collector)
            if col is not None:
                yield col

        elif direntry.is_file():
            if not collector.session.isinitpath(path):
                if ihook.pytest_ignore_collect(collection_path=path, config=config):
                    continue
            cols = ihook.pytest_collect_file(file_path=path, parent=collector)
            yield from cols


def _collect_dir_3240(self) -> Iterable:
    yield from _collect_entries_3240(self)


def _package_sort_key_3240(entry) -> object:
    return (entry.name != "__init__.py", entry.name)


def _collect_package_3240(self) -> Iterable:
    yield from _collect_entries_3240(self, _package_sort_key_3240)


def install_3240() -> None:
    """Install the shared collectors when this pytest is the measured version."""
    if not _pytest_is_gated_version():
        return
    if _pytest.main.Dir.collect is not _collect_dir_3240:
        _pytest.main.Dir.collect = _collect_dir_3240
    if _pytest.python.Package.collect is not _collect_package_3240:
        _pytest.python.Package.collect = _collect_package_3240
