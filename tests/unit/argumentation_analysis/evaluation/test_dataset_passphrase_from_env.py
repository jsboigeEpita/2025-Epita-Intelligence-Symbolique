"""The dataset passphrase comes from the environment, never from a tracked file.

Scripts, docs and skill snippets read ``TEXT_CONFIG_PASSPHRASE``. Test
fixtures that encrypt synthetic data use a synthetic passphrase. This module
takes the real value from the environment and looks for it in every tracked
file, on the lines that use it as a secret: a line that also says
``passphrase``, ``password``, ``secret`` or ``key``. A line where the same
characters are ordinary vocabulary does not count.

Failure output names paths and line numbers, never the value.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

_SECRET_CONTEXT = re.compile(
    rb"passphrase|password|secret|\bkey\b|phrase secr", re.IGNORECASE
)


class _Secret(bytes):
    """Bytes whose repr hides them, so neither an assertion rewrite nor
    ``--showlocals`` can print the value into a public CI log."""

    def __repr__(self):
        return "<hidden>"


def _secret_lines(data, secret):
    """The 1-based numbers of the lines of ``data`` that hold ``secret`` as a
    secret."""
    if secret not in data:
        return []
    return [
        number
        for number, line in enumerate(data.splitlines(), 1)
        if secret in line and _SECRET_CONTEXT.search(line)
    ]


@pytest.fixture(scope="module")
def passphrase():
    value = os.environ.get("TEXT_CONFIG_PASSPHRASE")
    if not value:
        if os.environ.get("CI"):
            pytest.fail(
                "the CI test step provides TEXT_CONFIG_PASSPHRASE; without it "
                "this check cannot run"
            )
        pytest.skip("needs TEXT_CONFIG_PASSPHRASE")
    return _Secret(value.encode("utf-8"))


def test_the_matcher_tells_a_secret_from_a_word(passphrase):
    # Built in memory: nothing here writes the value anywhere.
    assignment = _Secret(b'passphrase="' + passphrase + b'"')
    vocabulary = _Secret(b"https://en.wikipedia.org/wiki/" + passphrase + b"#Types")

    flagged = _secret_lines(assignment, passphrase)
    ignored = _secret_lines(vocabulary, passphrase)

    assert flagged == [1], "an assignment to a passphrase must be flagged"
    assert ignored == [], "the value as a word in a URL must not be flagged"


def test_no_tracked_line_holds_the_passphrase(passphrase):
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    found = []
    for path in tracked:
        file = REPO_ROOT / path
        if file.is_file():
            found += [
                f"{path}:{n}" for n in _secret_lines(file.read_bytes(), passphrase)
            ]

    assert found == [], "read the passphrase from TEXT_CONFIG_PASSPHRASE instead"
