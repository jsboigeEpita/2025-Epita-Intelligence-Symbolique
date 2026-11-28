"""#3727 item 50c — the guard on committed bytes: no tracked text file gains a CR.

The writer census (#3723) fences 43 writers of a tracked file. It cannot see
the writer whose target it cannot place (173 ``runtime-*`` sites, 102
``in-repo``), an editor, a copy, or a seat with ``core.autocrlf=false``. What
all of those share is the outcome: a carriage return reaches the index.
``scripts/security/verify_committed_line_endings.py`` reads that outcome, from
``git ls-files --eol`` (the ``i/`` column, which does not depend on the seat's
checkout).

Measured on ``main`` ``0e07e8359``: 306 tracked files carry a CR (301
``i/crlf``, 5 ``i/mixed``) out of 5 310. They are the census, one path per
line in ``scripts/security/crlf_committed_census.txt``, and the census only
shrinks.

The witnesses below build real commits in a temporary repository, so the
reader is exercised on what git actually stores rather than on a hand-made
table. The fixture passes ``core.autocrlf=false`` explicitly: on a seat whose
git normalises at ``git add``, a CRLF file would never reach the index and the
"reddens" witnesses would pass for the wrong reason.

Seat free: a temporary directory, git, no network, no key.
"""

from __future__ import annotations

import importlib
import os
import subprocess
from pathlib import Path

import pytest

guard = importlib.import_module("scripts.security.verify_committed_line_endings")

REPO_ROOT = Path(__file__).resolve().parents[4]

CRLF = b"one\r\ntwo\r\n"
LF = b"one\ntwo\n"

# Variables that would point the fixture's git at another repository.
_SCRUBBED = (
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_WORK_TREE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CONFIG",
)


def _git(repo: Path, *args: str) -> bytes:
    """Run git in the fixture repository, with the seat's line endings out of it."""
    env = {k: v for k, v in os.environ.items() if k not in _SCRUBBED}
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "core.autocrlf=false",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=" + str(repo / ".no-hooks"),
            "-c",
            "user.name=guard-3727",
            "-c",
            "user.email=guard-3727@example.invalid",
            *args,
        ],
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return proc.stdout


def _commit(repo: Path, name: str, data: bytes) -> None:
    (repo / name).write_bytes(data)
    _git(repo, "add", "--", name)
    _git(repo, "commit", "-q", "-m", f"add {name}")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A repository with one file that carries a CR and one that does not."""
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, "keep.txt", CRLF)
    _commit(tmp_path, "clean.txt", LF)
    return tmp_path


def _judge(repo: Path, census: list[str]):
    return guard.judge(guard.read_index_eol(repo), census)


def test_a_census_file_passes_and_a_lf_file_is_not_a_carrier(repo: Path) -> None:
    report = _judge(repo, ["keep.txt"])
    assert report.carriers == ("keep.txt",)
    assert report.ok


def test_a_new_file_that_carries_a_crlf_reddens(repo: Path) -> None:
    _commit(repo, "new.txt", CRLF)
    report = _judge(repo, ["keep.txt"])
    assert report.new == ("new.txt",)
    assert not report.ok


def test_the_same_file_in_lf_passes(repo: Path) -> None:
    _commit(repo, "new.txt", LF)
    report = _judge(repo, ["keep.txt"])
    assert report.new == ()
    assert report.ok


def test_a_file_removed_from_the_census_while_it_carries_a_crlf_reddens(
    repo: Path,
) -> None:
    report = _judge(repo, [])
    assert report.new == ("keep.txt",)
    assert not report.ok


def test_a_census_entry_whose_file_no_longer_carries_a_crlf_reddens_until_removed(
    repo: Path,
) -> None:
    _commit(repo, "keep.txt", LF)
    report = _judge(repo, ["keep.txt"])
    assert report.carriers == ()
    assert report.stale == ("keep.txt",)
    assert not report.ok
    assert _judge(repo, []).ok


def test_a_census_entry_whose_file_is_gone_reddens(repo: Path) -> None:
    _git(repo, "rm", "-q", "keep.txt")
    _git(repo, "commit", "-q", "-m", "rm keep.txt")
    assert _judge(repo, ["keep.txt"]).stale == ("keep.txt",)


def test_a_mixed_file_is_a_carrier(repo: Path) -> None:
    _commit(repo, "mixed.txt", b"one\r\ntwo\n")
    assert guard.read_index_eol(repo)["mixed.txt"] == "mixed"
    assert _judge(repo, ["keep.txt"]).new == ("mixed.txt",)


def test_a_batch_file_and_a_binary_file_are_not_carriers(repo: Path) -> None:
    _commit(repo, "run.bat", CRLF)
    _commit(repo, "blob.bin", b"\x00\r\n\x00")
    index_eol = guard.read_index_eol(repo)
    # Controls first: git did store a CR in both, and the rule is what excludes
    # them -- not a git class that was never reached.
    assert index_eol["run.bat"] == "crlf"
    assert index_eol["blob.bin"] == "-text"
    assert _judge(repo, ["keep.txt"]).new == ()


def test_the_index_is_read_never_the_working_tree(repo: Path) -> None:
    # A CR written in the working tree and never added is invisible.
    (repo / "clean.txt").write_bytes(CRLF)
    assert _judge(repo, ["keep.txt"]).ok
    # A file normalised in the working tree and never added still carries its
    # CR where it was committed.
    (repo / "keep.txt").write_bytes(LF)
    assert _judge(repo, []).new == ("keep.txt",)


def test_the_census_only_shrinks() -> None:
    index = {f"file{i}.txt": "crlf" for i in range(guard.CENSUS_CEILING)}
    assert guard.judge(index, list(index)).ok
    grown = {**index, "one-more.txt": "crlf"}
    report = guard.judge(grown, list(index) + ["one-more.txt"])
    assert report.new == () and report.stale == ()
    assert report.census_too_large
    assert not report.ok


def test_a_census_that_lists_a_path_twice_is_an_error() -> None:
    with pytest.raises(guard.GuardError):
        guard.judge({"a.txt": "crlf"}, ["a.txt", "a.txt"])


def test_parse_census_ignores_comments_and_blank_lines() -> None:
    assert guard.parse_census("# a comment\n\nkeep.txt\n  \nclean.txt\n") == (
        "keep.txt",
        "clean.txt",
    )


# --------------------------------------------------------------------------
# the repository itself
# --------------------------------------------------------------------------
def test_no_tracked_text_file_carries_a_cr_outside_the_census() -> None:
    index_eol = guard.read_index_eol(REPO_ROOT)
    census = guard.load_census()
    report = guard.judge(index_eol, census)
    print(
        f"tracked={report.tracked} carriers={len(report.carriers)} "
        f"census={report.census_size} ceiling={guard.CENSUS_CEILING}"
    )
    assert report.tracked > 0, "git ls-files --eol listed nothing: nothing was read"
    assert census == tuple(sorted(census)), (
        "the census file is not sorted: one path per line, sorted, so two "
        "branches that remove different entries merge without a conflict"
    )
    assert not report.new, (
        "file(s) that carry a CR in the index and are not in the census:\n  "
        + "\n  ".join(report.new)
        + '\nWrite LF (a writer of a tracked file declares newline="\\n"), '
        "or normalise the file; do not add it to the census."
    )
    assert not report.stale, "stale census entries -- remove them:\n  " + "\n  ".join(
        report.stale
    )
    assert not report.census_too_large, (
        f"the census holds {report.census_size} paths, more than the ceiling "
        f"{guard.CENSUS_CEILING}"
    )
