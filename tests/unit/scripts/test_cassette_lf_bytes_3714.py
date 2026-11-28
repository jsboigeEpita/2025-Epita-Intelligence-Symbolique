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

Two instruments, and why two
----------------------------
**Bytes, where the seat can discriminate.** A byte witness only means
something on a seat whose text mode writes CRLF: on a POSIX runner text mode
already writes LF, so a writer that omits ``newline=`` would look correct
there. The seat is therefore *measured*, not assumed — a raw text-mode write,
read back in bytes — and the four byte witnesses skip with that reason on a
seat that cannot discriminate. (An earlier version of this file patched
``os.linesep`` to force the outcome. That is inert: CPython's C
``TextIOWrapper`` never reads ``os.linesep``, measured on po-2023 under both
``projet-is`` and ``projet-is-lock`` — the write still emitted CRLF after the
patch, whether it was applied before or after ``open``. A control that cannot
change the result is not a control.)

**The census, everywhere.** ``test_every_named_writer_declares_its_separator``
parses the source with ``ast`` and requires each named writer to pass
``newline`` explicitly, with a mutation control proving the assertion can fail:
the same AST with the keyword dropped in memory reddens, without touching the
file. It is deliberately independent of
``scripts/security/verify_text_writer_line_endings`` (the census guard of
#3723): that module resolves *which* writes reach a tracked file — a question
this witness does not ask. This one asks whether the named writers fix their
separator, and that is readable from the four files themselves. It runs on any
seat.

Seat free: a temporary directory, one diskcache, no network, no key.
"""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
from typing import Dict, Tuple

import pytest

cassette_export = importlib.import_module("scripts.cassettes.export")

CASSETTE_KEY = "a" * 64

# One key per writer -- ``(script, function)``. An earlier table keyed the
# dict by script path, so ``scripts/cassettes/export.py`` appeared twice and
# only the second row survived: two of the three writers were never checked.
WRITERS: Tuple[Tuple[str, str], ...] = (
    ("scripts/cassettes/export.py", "refresh_manifest"),
    ("scripts/cassettes/export.py", "export_one"),
    ("scripts/cassettes/export.py", "main"),
    ("scripts/api/regenerate_openapi_snapshot.py", "write_snapshot"),
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _text_mode_bytes(directory: Path) -> bytes:
    """What a plain text-mode write produces on this seat."""
    path = directory / "probe.text-mode.txt"
    path.write_text("a\nb\n", encoding="utf-8")
    return path.read_bytes()


def _pinned_bytes(directory: Path) -> bytes:
    """The same content, written with an explicit ``newline="\\n"``."""
    path = directory / "probe.pinned.txt"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("a\nb\n")
    return path.read_bytes()


def _seat_is_discriminating(directory: Path) -> bool:
    """Whether this seat's text mode turns ``"\\n"`` into CRLF (measured)."""
    return b"\r\n" in _text_mode_bytes(directory)


@pytest.fixture()
def crlf_seat(tmp_path: Path) -> None:
    """Run the byte witnesses only on a seat where they can fail.

    Skipping is the honest outcome on a seat whose text mode already writes
    LF: the witness would pass for every writer, including a broken one.
    """
    if not _seat_is_discriminating(tmp_path):
        pytest.skip(
            "this seat's text mode already writes LF: a writer that omits "
            "newline= would look correct here, so the byte witnesses cannot "
            "discriminate -- the source census covers this seat"
        )


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
        assert b"\r" not in data, f"{path.name} carries CRLF: " + _crlf_report(data)


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


def test_the_seat_probe_separates_the_text_mode_from_the_explicit_separator(
    tmp_path: Path,
) -> None:
    """Non-vacuity of the probe the fixture above relies on.

    Two writes of the same content, one through the seat's text mode and one
    with ``newline="\\n"``. The pinned one never carries a CR -- if it did,
    the witnesses would blame a writer that is correct. And the text-mode one
    settles which of the two situations this seat is in, so the fixture's
    skip is a measurement and not a guess.
    """
    plain = _text_mode_bytes(tmp_path)
    pinned = _pinned_bytes(tmp_path)

    assert b"\r" not in pinned, (
        'an explicit newline="\\n" still carried a CR: the byte witnesses '
        "would redden on a writer that is right"
    )
    if _seat_is_discriminating(tmp_path):
        assert b"\r\n" in plain, (
            "the probe says this seat discriminates, and its own text-mode "
            "write carries no CRLF: the probe and the write disagree"
        )
    else:
        assert b"\r\n" not in plain, (
            "the probe says this seat cannot discriminate, and its text-mode "
            "write carries CRLF: the byte witnesses ran for nothing"
        )


# --------------------------------------------------------------------------
# the census: one key per writer, and an assertion able to fail
# --------------------------------------------------------------------------
def _enclosing_function(tree: ast.AST, lineno: int) -> str:
    """The name of the innermost function a line sits in."""
    best: ast.AST | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end and (
                best is None or node.lineno > getattr(best, "lineno", 0)
            ):
                best = node
    return getattr(best, "name", "")


def _is_write(node: ast.AST) -> bool:
    """Whether a call writes text: ``write_text``, or ``open`` in a write mode."""
    if not isinstance(node, ast.Call):
        return False
    name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
    if name == "write_text":
        return True
    if name != "open":
        return False
    mode: ast.AST | None = node.args[1] if len(node.args) >= 2 else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    return (
        isinstance(mode, ast.Constant)
        and isinstance(mode.value, str)
        and any(flag in mode.value for flag in ("w", "a", "x"))
    )


def _write_calls(source: str, function: str) -> list[ast.Call]:
    """The text-mode writes of one named function."""
    tree = ast.parse(source)
    return [
        node
        for node in ast.walk(tree)
        if _is_write(node) and _enclosing_function(tree, node.lineno) == function
    ]


def _declares_newline(call: ast.Call) -> bool:
    """Whether a write fixes its separator instead of taking the seat's."""
    return any(keyword.arg == "newline" for keyword in call.keywords)


def _undeclared(source: str, function: str) -> list[int]:
    """The lines of writes in one function that do not fix their separator."""
    return [
        call.lineno
        for call in _write_calls(source, function)
        if not _declares_newline(call)
    ]


def test_every_named_writer_declares_its_separator() -> None:
    """One row per writer, and each row's function passes ``newline``.

    The row also asserts the count: a second write appearing in one of these
    functions fails here rather than slipping past a table that only names
    functions. Adding a writer means adding its row, deliberately.
    """
    assert len(WRITERS) == len(set(WRITERS)), "a writer is listed twice"
    for script, function in WRITERS:
        path = REPO_ROOT / script
        assert path.is_file(), script
        calls = _write_calls(path.read_text(encoding="utf-8"), function)
        assert len(calls) == 1, (
            f"{script}:{function} carries {len(calls)} write calls: the table "
            "names one writer per row, so a new write needs its own row"
        )
        call = calls[0]
        assert _declares_newline(call), (
            f"{script}:{function} writes at line {call.lineno} without an "
            'explicit newline="\\n": its bytes would be the seat\'s'
        )


def test_the_census_check_reddens_when_a_writer_drops_its_separator() -> None:
    """The mutation control: same source, keyword removed in memory."""
    script, function = "scripts/cassettes/export.py", "main"
    source = (REPO_ROOT / script).read_text(encoding="utf-8")
    assert _undeclared(source, function) == [], "the real file is undefended"

    tree = ast.parse(source)
    dropped = False
    for node in ast.walk(tree):
        if _is_write(node) and _enclosing_function(tree, node.lineno) == function:
            keywords = [kw for kw in node.keywords if kw.arg == "newline"]
            if keywords:
                node.keywords.remove(keywords[0])
                dropped = True
                break
    assert dropped, f"no newline= keyword found in {script}:{function}"

    mutated = ast.unparse(tree)
    assert _undeclared(mutated, function), (
        "dropping newline= in memory did not redden the census assertion: "
        "the assertion cannot fail"
    )


def test_the_writers_named_and_left_alone_still_exist() -> None:
    """The writers named and left outside the population, with their reason.

    Their bytes are not committed, so the rule does not apply -- but they are
    still named, so that a later move of one of them into a tracked path is
    noticed instead of being rediscovered from a byte diff.
    """
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
        assert (REPO_ROOT / script).is_file(), script
        assert reason
