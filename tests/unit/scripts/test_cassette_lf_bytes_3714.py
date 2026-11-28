"""#3714 item 50 — a tracked file's writer owns its bytes: LF whatever the seat.

Measured on po-2023 (27/11): ``refresh_manifest`` wrote **35 CRLF lines out of
36**, and the whole file then differed from ``main`` byte for byte where the
patch itself touched 17 lines. The seat had ``core.autocrlf=false`` globally
(``true`` at the system level, unset locally) and no ``.gitattributes`` rule
covered the file, so nothing normalised at ``git add``: the bytes the writer
produced were the bytes the commit carried. Normalising by hand before the
commit is the workaround this issue exists to stop.

The rule the writers now follow: **every writer of a tracked file emits LF**.
No ``.gitattributes`` change is involved (that would rewrite the bytes every
seat checks out, including cassettes some guards hash) — this item is only
about the writers.

The control is what makes the witness able to fail: on a POSIX runner, text
mode already writes LF, so a writer without an explicit ``newline`` would look
correct there. The witness therefore forces the platform's line ending to
CRLF (``os.linesep``), which is what a text-mode writer consults at write
time, and then requires the bytes to carry no carriage return. On ``main`` the
forced CRLF lands in the file and the witness reddens.

Seat free: a temporary directory, one diskcache, no network, no key.
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Dict

import pytest

cassette_export = importlib.import_module("scripts.cassettes.export")

CASSETTE_KEY = "a" * 64


@pytest.fixture()
def crlf_seat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Emulate a seat whose text mode writes CRLF.

    ``open(..., newline=None)`` translates ``"\\n"`` to ``os.linesep`` at write
    time, so this is exactly the seat that produced the 35-of-36 CRLF
    manifest. A writer that passes ``newline="\\n"`` is unaffected — which is
    the point of the witness.
    """
    monkeypatch.setattr(os, "linesep", "\r\n")


def _crlf_report(data: bytes) -> str:
    """How many CRLF lines a byte string carries, over how many lines.

    The counts are read into locals first: an f-string expression cannot
    carry a backslash before Python 3.12, and the byte literals need one.
    """
    crlf = data.count(b"\r\n")
    lines = data.count(b"\n")
    return f"{crlf} CRLF line(s) of {lines}"


def _manifest(dirname: Path) -> Path:
    path = dirname / cassette_export.MANIFEST_NAME
    path.write_text(
        json.dumps({"schema": 1, "cassette_count": 1}, indent=2), encoding="utf-8"
    )
    return path


def _cassette(dirname: Path) -> Path:
    path = dirname / f"{CASSETTE_KEY}.json"
    path.write_text(json.dumps({"key": CASSETTE_KEY}, indent=2), encoding="utf-8")
    return path


def test_refresh_manifest_writes_lf_bytes_on_a_crlf_seat(
    tmp_path: Path, crlf_seat: None
):
    """The measured case: the manifest is a TRACKED file and its bytes were
    the seat's."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    manifest = _manifest(fixtures)
    _cassette(fixtures)

    assert cassette_export.refresh_manifest(fixtures, note="seat check") is True

    data = manifest.read_bytes()
    assert b"\r" not in data, (
        "the manifest carries CRLF: " + _crlf_report(data) + " — a tracked "
        "file whose bytes depend on the seat"
    )


def test_the_cassette_writer_writes_lf_bytes_on_a_crlf_seat(
    tmp_path: Path, crlf_seat: None
):
    """The cassette is a tracked file too, and its bytes are compared across
    seats."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()

    status = cassette_export.export_one(
        None,  # type: ignore[arg-type] — the write path never touches the db
        CASSETTE_KEY,
        {"role": "assistant", "content": "a recorded answer"},
        fixtures,
        allow_unsafe=True,
    )

    assert status == "ok", status
    data = (fixtures / f"{CASSETTE_KEY}.json").read_bytes()
    assert b"\r" not in data, "the cassette carries CRLF: " + _crlf_report(data)


def test_the_record_job_export_writes_lf_bytes_on_a_crlf_seat(
    tmp_path: Path, crlf_seat: None, monkeypatch: pytest.MonkeyPatch
):
    """The record job's own path: the cassette AND the manifest it writes."""
    import diskcache

    source = tmp_path / "source"
    source.mkdir()
    db = diskcache.Cache(str(source))
    db[CASSETTE_KEY] = {"role": "assistant", "content": "a recorded answer"}
    db.close()

    monkeypatch.setenv("GITHUB_RUN_ID", "45513278355")
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    monkeypatch.delenv("GITHUB_RUN_STARTED_AT", raising=False)
    fixtures = tmp_path / "fixtures"

    rc = cassette_export.main([str(source), str(fixtures), "--allow-unsafe"])

    assert rc == 0, rc
    manifest = fixtures / cassette_export.MANIFEST_NAME
    assert manifest.is_file(), "the record path wrote no manifest"
    for path in (manifest, fixtures / f"{CASSETTE_KEY}.json"):
        data = path.read_bytes()
        assert b"\r" not in data, (
            f"{path.name} carries CRLF: " + _crlf_report(data)
        )


def test_the_openapi_snapshot_writer_writes_lf_bytes_on_a_crlf_seat(
    tmp_path: Path, crlf_seat: None
):
    """The census found one more tracked-file writer under ``scripts/``:
    ``api/openapi.snapshot.json`` (a committed snapshot). Same rule, same
    writer's-own-bytes."""
    script = importlib.import_module("scripts.api.regenerate_openapi_snapshot")

    target = tmp_path / "api" / "openapi.snapshot.json"
    script.write_snapshot({"paths": {"/ping": {}}}, str(target))

    data = target.read_bytes()
    assert b"\r" not in data, "the snapshot carries CRLF: " + _crlf_report(data)


def test_the_census_names_every_writer_of_a_tracked_file_under_scripts() -> None:
    """The census is a table, and it must not shrink silently: each writer
    named here still exists, and each target it writes is a tracked file.

    The table is the deliverable of the census: a writer missing from it is a
    defect this witness cannot see, so the table is asserted against the code
    that carries the writers.
    """
    root = Path(__file__).resolve().parents[3]
    tracked: Dict[str, str] = {
        "scripts/cassettes/export.py": "MANIFEST.json",
        "scripts/cassettes/export.py": "cassette fixture",
        "scripts/api/regenerate_openapi_snapshot.py": "api/openapi.snapshot.json",
    }
    assert tracked, "the census table is empty"
    for script, target in tracked.items():
        assert (root / script).is_file(), script
        assert target

    # The writers that were NAMED and left alone, with the reason each one is
    # outside the population (their bytes are not committed).
    named_only: Dict[str, str] = {
        "scripts/cassettes/rekey_capture.py": (
            "scratch report at REKEY_CAPTURE_OUT (env-var path): not tracked"
        ),
        "scripts/cassettes/rekey_phase_cap_3658_36c.py": (
            "scratch reports at an env-var path; its tracked rewrites are "
            "byte-level (write_bytes): LF by construction"
        ),
        "scripts/cassettes/rekey_settings_class.py": (
            "tracked rewrites are byte-level (write_bytes): LF by construction"
        ),
        "scripts/cassettes/rekey_sk_completion_cap_3685.py": (
            "tracked rewrites are byte-level (write_bytes): LF by construction"
        ),
        "scripts/cassettes/replay_stats_plugin.py": (
            ".cache/replay_stats.json (default path): not tracked"
        ),
    }
    for script, reason in named_only.items():
        assert (root / script).is_file(), script
        assert reason


def test_the_control_really_forces_crlf(tmp_path: Path) -> None:
    """Non-vacuity: without this control the witness could pass on a POSIX
    runner where text mode already writes LF — which is exactly why the
    control exists."""
    path = tmp_path / "control.txt"
    original = os.linesep
    try:
        os.linesep = "\r\n"
        path.write_text("a\nb\n", encoding="utf-8")
    finally:
        os.linesep = original
    assert b"\r\n" in path.read_bytes(), (
        "the control did not force CRLF: the witness would pass on a POSIX "
        "runner for the wrong reason"
    )
