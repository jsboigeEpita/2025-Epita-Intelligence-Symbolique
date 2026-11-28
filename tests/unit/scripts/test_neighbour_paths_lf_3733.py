"""The `--paths` lines are paths a consumer can open (#3733).

`scripts/ci/neighbour_tests.py --paths` is the machine-readable face of the
neighbour set: one path per line. A text stream whose line end is left unset
turns each ``\\n`` into ``os.linesep``, so on a Windows seat every line a shell
or a ``subprocess`` consumer reads ends with a carriage return and names no
file. Measured on `main` `0e07e8359`, seat po-2023: 134 line ends, 134 CRLF, 0
of the 134 paths open as read, 134 once the CR is stripped.

The surface exercised is the real one: a subprocess whose stdout is read as
bytes. The line-end control is a measurement of the seat, not an assumption:
where a raw text-mode write carries no CR, the byte assertion is skipped with
that reason, because it cannot discriminate there.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from scripts.ci import neighbour_tests as nt

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "neighbour_tests.py"

# A change with a non-trivial neighbour set: the one the #3374 witness uses.
TOUCHED = "argumentation_analysis/core/reading_window.py"


def _seat_writes_cr() -> bool:
    """Does a raw text-mode write on this seat end its lines with CRLF?"""
    probe = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.write('a\\nb\\n')"],
        capture_output=True,
        check=False,
    )
    return b"\r\n" in probe.stdout


SEAT_WRITES_CR = _seat_writes_cr()


def _paths_run() -> subprocess.CompletedProcess:
    """`--paths` for a known change, its stdout kept as bytes."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--paths", "--files", TOUCHED],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )


def _lines(stdout: bytes) -> List[str]:
    """The printed lines, taken as a consumer takes them, nothing stripped."""
    return [line.decode("utf-8", "replace") for line in stdout.split(b"\n")[:-1]]


def test_every_printed_line_is_a_path_the_consumer_can_open():
    """Read as bytes, as a shell or a subprocess reads them: no residue."""
    done = _paths_run()

    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    assert done.stdout.endswith(b"\n"), "the output ends on a line end"
    lines = _lines(done.stdout)
    assert lines, "a non-vacuous set: this change has neighbours"
    missing = [line for line in lines if not (REPO_ROOT / line).is_file()]
    assert missing == [], "the line as read, carriage return and all, is the path"


@pytest.mark.skipif(
    not SEAT_WRITES_CR,
    reason="this seat's text-mode write carries no CR: the bytes cannot discriminate",
)
def test_the_line_end_is_lf_whatever_the_seat():
    done = _paths_run()

    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    assert b"\r" not in done.stdout


def test_an_empty_set_prints_no_line(monkeypatch, capsys):
    """`print("\\n".join([]))` wrote one empty line, that is one empty path."""
    monkeypatch.setattr(nt, "select", lambda *a, **k: nt.Neighbours())

    assert nt.main(["--paths", "--files", TOUCHED]) == nt.EXIT_OK
    assert capsys.readouterr().out == ""
