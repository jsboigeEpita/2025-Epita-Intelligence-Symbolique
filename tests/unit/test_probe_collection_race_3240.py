# -*- coding: utf-8 -*-
"""#3240 — a probe vanishing mid-collection is ordinary, not a child-pytest death.

``tests/nested_pytest.run_probe`` and the #2607 churner both create
``tests/_probe_*`` directories and remove them. When a probe is deleted after
a collector has listed it but before ``Session.collect`` has matched its
initial-path walk, the node it produced is gone by the time the frame below
runs (``_pytest/main.py``, ``Session.collect``, Windows only)::

    if sys.platform == "win32" and not is_match:
        is_match = samefile_nofollow(node.path, matchparts[0])

``samefile_nofollow`` calls ``node.path.lstat()`` and the vanished entry kills
the child collection (``FileNotFoundError`` / ``WinError 2``), exactly the
unrecoverable empty verdict of #3176 named in #3240. The entry reaches the
node list because ``Dir.collect`` and ``Package.collect`` call
``DirEntry.is_dir()`` before ``pytest_ignore_collect``: Windows keeps the
cached directory bit after the removal, the ignore hook then cannot see a
directory to apply ``norecursedirs`` to, and a collector is built for the
vanished path.

The witness is deterministic: a churner thread removes the probe once
``DirEntry.is_dir()`` has said it is a directory, then the real collector
continues. A real child pytest runs on a temporary ``tests/`` subtree, so the
root conftest and production collectors are those under test. Two modes name
the two frames: ``dir`` puts the probe under the case root (``Dir``), and
``package`` puts it under a package (``Package``).

Born red on pristine main: one vanished-entry error per child collection.
Green once the shared repair keeps an ignored ``norecursedirs`` entry out of
the node list without ever calling a filesystem predicate on its vanished
path.
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUNDS = 3
MODES = ("dir", "package")
VERDICT_PREFIX = "PROBE_COLLECTION_VERDICT "

# Run inside a fresh interpreter. The case tree is created under the real
# ``tests/`` tree so ``tests/conftest.py`` is loaded exactly as in production;
# it is itself a ``_probe_*`` directory and is removed in ``finally``.
_DRIVER = r'''
import json
import os
import shutil
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(sys.argv[1])
TOKEN = sys.argv[2]
ROUND = int(sys.argv[3])
MODE = sys.argv[4]
TESTS_ROOT = REPO_ROOT / "tests"
CASE = TESTS_ROOT / f"_probe_race_case_{TOKEN}_{ROUND}_{MODE}"
PKG = CASE / "pkg"
LEAF = PKG / "leaf"
TARGET = LEAF / "test_target.py"
STALE_PROBE = CASE / "_probe_race_stale"

if MODE == "dir":
    SCAN_PARENT = CASE
    PROBE = CASE / "_probe_race_listed"
else:
    SCAN_PARENT = PKG
    PROBE = PKG / "_probe_race_listed"

for directory in (LEAF, PROBE, STALE_PROBE):
    directory.mkdir(parents=True)
(PKG / "__init__.py").write_text("", encoding="utf-8")
(LEAF / "__init__.py").write_text("", encoding="utf-8")
TARGET.write_text(
    "def test_target():\n    assert True\n", encoding="utf-8"
)
(PROBE / "test_never_collected.py").write_text(
    "def test_never_collected():\n    assert False\n", encoding="utf-8"
)
(STALE_PROBE / "test_never_collected.py").write_text(
    "def test_never_collected():\n    assert False\n", encoding="utf-8"
)


class Churner(threading.Thread):
    """Removes the probe once its DirEntry has been classified."""

    def __init__(self):
        super().__init__(daemon=True)
        self._request = threading.Event()
        self._deleted = threading.Event()
        self._done = threading.Event()
        self._path = None
        self.deleted = 0

    def remove_after_is_dir(self, path):
        self._path = path
        self._request.set()
        if not self._deleted.wait(30):
            raise TimeoutError(f"churner did not remove {path}")
        self._deleted.clear()

    def run(self):
        while not self._done.is_set():
            if not self._request.wait(0.1):
                continue
            self._request.clear()
            shutil.rmtree(self._path)
            self.deleted += 1
            self._deleted.set()

    def stop(self):
        self._done.set()
        self.join(timeout=10)


class RemovingEntry:
    """The real DirEntry, removed after is_dir() and before its node is used."""

    def __init__(self, entry, churner):
        self._entry = entry
        self._churner = churner

    def __getattr__(self, name):
        return getattr(self._entry, name)

    def is_file(self):
        return self._entry.is_file()

    def is_dir(self):
        is_dir = self._entry.is_dir()
        if is_dir:
            self._churner.remove_after_is_dir(self._entry.path)
        return is_dir


class EntryIterator:
    def __init__(self, iterator, target, churner):
        self._iterator = iterator
        self._target = target
        self._churner = churner

    def __enter__(self):
        self._iterator.__enter__()
        return self

    def __exit__(self, *exc):
        return self._iterator.__exit__(*exc)

    def __iter__(self):
        return self

    def __next__(self):
        entry = next(self._iterator)
        if entry.name == self._target:
            return RemovingEntry(entry, self._churner)
        return entry


class Verdict:
    def __init__(self, case, pkg):
        self.case = case
        self.pkg = pkg
        self.errors = []
        self.collectors = []
        self.items = []

    def pytest_collectreport(self, report):
        if report.failed:
            self.errors.append(
                {"nodeid": report.nodeid, "text": str(report.longrepr)}
            )

    def pytest_collectstart(self, collector):
        path = Path(str(collector.path))
        if path in (self.case, self.pkg):
            self.collectors.append(type(collector).__name__)

    def pytest_collection_finish(self, session):
        self.items = [item.nodeid for item in session.items]


churner = Churner()
real_scandir = os.scandir


def racing_scandir(path):
    iterator = real_scandir(path)
    if Path(path) == SCAN_PARENT:
        return EntryIterator(iterator, PROBE.name, churner)
    return iterator


verdict = Verdict(CASE, PKG)
returncode = None
unhandled = None
try:
    os.scandir = racing_scandir
    churner.start()
    returncode = int(
        pytest.main(
            [
                str(TARGET),
                "-c",
                str(REPO_ROOT / "pytest.ini"),
                "--rootdir",
                str(REPO_ROOT),
                "--collect-only",
                "--continue-on-collection-errors",
                "-p",
                "no:cacheprovider",
                "--disable-jvm-session",
                "-q",
            ],
            plugins=[verdict],
        )
    )
except BaseException as exc:  # the verdict must survive an instrument failure
    unhandled = repr(exc)
finally:
    churner.stop()
    shutil.rmtree(CASE, ignore_errors=True)

print(
    "PROBE_COLLECTION_VERDICT "
    + json.dumps(
        {
            "returncode": returncode,
            "unhandled": unhandled,
            "deleted": churner.deleted,
            "errors": verdict.errors,
            "collectors": verdict.collectors,
            "items": verdict.items,
            "mode": MODE,
        }
    )
)
'''


def _run_child(tmp_path: Path, round_index: int, mode: str) -> dict:
    token = uuid.uuid4().hex[:8]
    driver = tmp_path / f"driver_3240_{round_index}_{mode}.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    env = dict(os.environ)
    # No live call has any part in collection; keep the child keyless (#1167).
    env["OPENAI_API_KEY"] = ""
    proc = subprocess.run(
        [
            sys.executable,
            str(driver),
            str(REPO_ROOT),
            token,
            str(round_index),
            mode,
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    payloads = [
        json.loads(line.removeprefix(VERDICT_PREFIX))
        for line in proc.stdout.splitlines()
        if line.startswith(VERDICT_PREFIX)
    ]
    assert payloads, (
        f"no verdict from round {round_index} mode {mode} "
        f"(rc={proc.returncode})\n"
        f"--- stdout tail ---\n{proc.stdout[-3000:]}\n"
        f"--- stderr tail ---\n{proc.stderr[-3000:]}"
    )
    payload = payloads[0]
    payload["child_returncode"] = proc.returncode
    payload["stderr"] = proc.stderr[-3000:]
    return payload


def _race_errors(payload: dict) -> list:
    """Collection errors whose trail is the vanished entry, not another cause."""
    return [
        error
        for error in payload["errors"]
        if "FileNotFoundError" in error["text"] or "WinError 2" in error["text"]
    ]


def test_a_child_collection_survives_vanishing_ignored_probes(tmp_path):
    runs = [
        _run_child(tmp_path, round_index, mode)
        for round_index in range(ROUNDS)
        for mode in MODES
    ]

    # Non-vacuity: every child must have classified its probe as a directory,
    # removed it, and started the frame the mode names. A fast machine that
    # never interleaved proves nothing, so the event itself is asserted.
    assert all(run["unhandled"] is None for run in runs), runs
    assert sum(run["deleted"] for run in runs) == len(runs), runs
    for run in runs:
        assert "Dir" in run["collectors"], run
        if run["mode"] == "package":
            assert "Package" in run["collectors"], run

    # The witness's verdict comes first: the vanished entry must be the only
    # failure reported, and every one of its occurrences has to be counted
    # before a secondary assertion can hide the measurement.
    raises = [error for run in runs for error in _race_errors(run)]
    assert not raises, (
        f"{len(raises)} vanished-entry raises over {len(runs)} child "
        f"collections ({sum(run['deleted'] for run in runs)} deletions): "
        f"{[(run['mode'], error['nodeid']) for run in runs for error in _race_errors(run)]}"
    )
    other = [error for run in runs for error in run["errors"] if error not in raises]
    assert not other, f"unrelated collection errors: {other}"

    # Neither the vanished probe nor the stale probe may contribute tests.
    for run in runs:
        names = [item.rsplit("::", 1)[-1] for item in run["items"]]
        assert names == ["test_target"], run


def test_the_repair_is_installed_on_the_gated_pytest_version():
    """The shim is version-gated, as for #3080; the witness above stays black-box.

    On a newer pytest this test does not assert the shim's shape: the
    black-box witness is then the only authority, and a regression in the
    upstream collector reddens it directly.
    """
    if not pytest.__version__.startswith("9.1.1"):
        pytest.skip(f"shim is gated to pytest 9.1.1 (installed {pytest.__version__})")

    from tests.collection_repair_3240 import (
        _collect_dir_3240,
        _collect_package_3240,
    )
    import _pytest.main
    import _pytest.python

    assert _pytest.main.Dir.collect is _collect_dir_3240
    assert _pytest.python.Package.collect is _collect_package_3240


class _RaisingEntry:
    def __init__(self, exc):
        self._exc = exc

    def is_dir(self):
        raise self._exc


def test_only_ignored_disappearance_is_tolerated():
    """The helper skips ENOENT for an ignored entry, not every OSError."""
    from tests.collection_repair_3240 import _directory_kind

    gone = FileNotFoundError(2, "gone")
    denied = PermissionError(13, "denied")

    assert _directory_kind(_RaisingEntry(gone), ignored=True) is None
    with pytest.raises(PermissionError):
        _directory_kind(_RaisingEntry(denied), ignored=True)
    with pytest.raises(FileNotFoundError):
        _directory_kind(_RaisingEntry(gone), ignored=False)
