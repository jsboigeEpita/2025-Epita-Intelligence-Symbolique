# -*- coding: utf-8 -*-
"""#2607 — a walk of the suite must not die of a probe passing through.

``tests/nested_pytest.py::run_probe`` creates
``tests/_probe_<label>_<uuid>/``, runs a session inside it (about 20 s), then
deletes it. A walk that has already listed that directory and tries to enter
it after the deletion raises ``FileNotFoundError``. Measured 2026-09-26 on a
loop: **97 raises over 400 walks** against 248 creations. On xdist, a test
that walks ``tests/`` on one worker therefore fails intermittently while a
probe runs on another — the failure seen on
``test_ci_guard_signature_contract_1873.py``.

`tests/support/tree_walk.iter_files` is the walk the guards share: it does not
enter a probe, and a directory that disappears mid-walk is an ordinary event.

A single run is not evidence of a race, so the witness below drives the
creation and deletion in a loop and counts what raised. It exercises a **real
walker** (``tests/integration/triage/test_import_does_not_seed_env.py``), not
the helper alone: on the pre-fix tree that walker called
``TESTS_ROOT.rglob("test_*.py")``, so the witness failed with the real
``FileNotFoundError`` rather than with a missing import.
"""

import shutil
import threading
import uuid
from pathlib import Path

from tests.support.tree_walk import (
    PROBE_PREFIX,
    iter_files,
    prefix_is_skipped_by_collection,
)

TESTS_ROOT = Path(__file__).resolve().parents[1]
PYTEST_INI = TESTS_ROOT.parent / "pytest.ini"

# Enough turns for an unfavourable interleaving to happen: the measurement
# above saw 97 raises over 400 walks. At 60 the walkers have always met one.
WALKS = 60


class _ChurningProbe(threading.Thread):
    """Creates and deletes ``tests/_probe_race_<uuid>/``, as ``run_probe`` does.

    A real probe lasts about 20 s; what matters here is only that the
    directory exists while another walk may be running, and that it goes away.
    """

    def __init__(self):
        super().__init__(daemon=True)
        self.made = 0
        # Not ``_stop``: that name is ``threading.Thread``'s own, and
        # shadowing it breaks the thread's shutdown.
        self._done = threading.Event()

    def run(self):
        while not self._done.is_set():
            probe = TESTS_ROOT / f"{PROBE_PREFIX}race_{uuid.uuid4().hex[:8]}"
            try:
                probe.mkdir()
                (probe / "probe_race.py").write_text("x = 1", encoding="utf-8")
                self.made += 1
            except OSError:
                pass
            shutil.rmtree(probe, ignore_errors=True)
            self._done.wait(0.0005)

    def stop(self):
        self._done.set()
        self.join(timeout=10)


def test_a_walk_of_the_suite_survives_a_probe_churning():
    """The triage guard's own walker, while a probe is created and deleted.

    On the pre-fix tree this walker walked with ``rglob`` and the assertion
    failed with ``FileNotFoundError`` — the real defect, not a broken import.
    """
    from tests.integration.triage.test_import_does_not_seed_env import (
        _iter_test_files,
    )

    probe = _ChurningProbe()
    probe.start()
    try:
        raised = []
        for _ in range(WALKS):
            try:
                list(_iter_test_files())
            except OSError as exc:  # FileNotFoundError, the #2607 shape
                raised.append(repr(exc))
    finally:
        probe.stop()

    # Non-vacuity: a watcher that saw no probe cannot prove the walk survives
    # one. Without this line a machine too slow to interleave passes for free.
    assert probe.made > 0, "the probe never created its directory: nothing ran"
    assert not raised, f"{len(raised)} of {WALKS} walks raised: {raised[:3]}"


def test_the_shared_walk_sees_the_same_files_as_rglob(tmp_path):
    """A stable tree makes coverage comparable without racing live probes."""
    for relative in (
        "pkg/__init__.py",
        "pkg/a/b/t.py",
        "_archived/x.py",
        "_probe_x/p.py",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1", encoding="utf-8")

    expected = {p for p in tmp_path.rglob("*.py") if "_probe_x" not in p.parts}
    assert set(iter_files(tmp_path)) == expected
    assert {p.relative_to(tmp_path).as_posix() for p in expected} == {
        "pkg/__init__.py",
        "pkg/a/b/t.py",
        "_archived/x.py",
    }


def test_a_file_whose_name_starts_like_a_probe_is_still_walked():
    """Only **directories** are skipped. ``rglob`` returns ``__init__.py``.

    Filtering on the name alone would lose every ``tests/**/__init__.py``
    (measured: 1225 files against 1406), which is the kind of silent
    shrinkage the equivalence test above exists to catch.
    """
    names = {p.name for p in iter_files(TESTS_ROOT)}
    assert "__init__.py" in names
    assert not any(name.startswith(PROBE_PREFIX) for name in names)


def test_the_probe_prefix_is_one_collection_skips():
    """The prefix a walk skips must be one ``norecursedirs`` already skips.

    Read back from ``pytest.ini`` rather than restated here: a restated
    convention is the one that drifts. If it drifted, the probes would be
    collected by the suite itself.
    """
    verdict, entries = prefix_is_skipped_by_collection(PYTEST_INI)
    assert verdict, f"norecursedirs={entries} does not cover {PROBE_PREFIX!r}"
