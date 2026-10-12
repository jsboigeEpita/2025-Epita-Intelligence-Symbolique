# -*- coding: utf-8 -*-
"""#3019 — a variable the caller neutralised stays neutralised in every child.

Measured on Windows (CPython 3.10, ``projet-is-lock``): restoring ``os.environ``
(``clear()`` + ``update(saved)``) — and ``patch.dict(os.environ, {}, clear=True)``
— erases every variable whose saved value is ``""`` from the process block.
Python's dict still says ``""``, but a child spawned with the default
``env=None`` inherits no name at all, and its loader then fills the key from the
root ``.env``: a replay band test routes to another provider (the cache key
drifts, the cassette misses) and, outside replay, a neutralised run spends
through ``.env`` (the R1073 incident class).

The guarantee (#3019, issue candidate 1): the caller-empty names travel to
children in a non-empty carrier (``env_loader._CALLER_EMPTY_NAMES_VAR``) a
restore does not erase, and every import of ``env_loader`` re-asserts them as
``""`` before capturing ``_CALLER_ENVIRONMENT``.

Synthetic witnesses, the #2472 shape: the caller's environment is what a
process is started with, so the restoring process and the child it spawns are
real child processes. The contract witnesses are born red on Windows — on
POSIX a restore keeps the ``""`` in the block, so the pre-fix tree passes them
there; the platform is named in the failing message.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import argumentation_analysis.config.env_loader as em

REPO = Path(__file__).resolve().parents[4]

NEUTRALISED = "ISSUE_3019_NEUTRALISED"  # the caller sets it to ""
# getattr: the module must collect on the pre-fix tree so the contract witness
# can redden on the DEFECT (the child taking the .env value), not on an import.
CARRIER = getattr(em, "_CALLER_EMPTY_NAMES_VAR", "CALLER_EMPTY_NAMES")

# The restorer plays the contaminating test: it imports env_loader (the carrier
# is exported here, as tests/conftest.py does first thing), defeats os.environ
# the named way, and spawns the child with the default env=None — the boundary
# the erase reaches. The child asks the loader for the neutralised name, with a
# .env in reach that would fill it.
_RESTORER = r"""
import os, subprocess, sys
from unittest import mock
sys.path.insert(0, sys.argv[1])
import argumentation_analysis.config.env_loader  # noqa: F401 - exports the carrier
if sys.argv[5] == "patch-dict":
    with mock.patch.dict(os.environ, {}, clear=True):
        pass
else:
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(saved)
proc = subprocess.run(
    [sys.executable, sys.argv[2], sys.argv[1], sys.argv[3], sys.argv[4]],
    capture_output=True, text=True,
)
sys.stdout.write(proc.stdout)
sys.stderr.write(proc.stderr)
raise SystemExit(proc.returncode)
"""

_CHILD = r"""
import json, os, sys
sys.path.insert(0, sys.argv[1])
import argumentation_analysis.config.env_loader as em
em.load_env_file(sys.argv[2])
print("CHILD=" + json.dumps({
    "value": os.environ.get(sys.argv[3]),
    "by_caller": em.set_by_caller(sys.argv[3]),
}))
"""


def _caller_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in (NEUTRALISED, CARRIER)}
    env[NEUTRALISED] = ""  # the caller's neutralisation, present-but-empty
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra)
    return env


def _run_restorer(tmp_path: Path, erase: str, **extra: str) -> dict:
    env_file = tmp_path / "root.env"
    env_file.write_text(f"{NEUTRALISED}=from-dotenv\n", encoding="utf-8")
    child = tmp_path / "child.py"
    child.write_text(_CHILD, encoding="utf-8")
    restorer = tmp_path / "restorer.py"
    restorer.write_text(_RESTORER, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(restorer),
            str(REPO),
            str(child),
            str(env_file),
            NEUTRALISED,
            erase,
        ],
        capture_output=True,
        text=True,
        env=_caller_env(**extra),
        cwd=str(REPO),
        timeout=300,
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("CHILD=")]
    assert (
        lines
    ), f"no child output - rc={proc.returncode}, stderr tail: {proc.stderr[-600:]!r}"
    return json.loads(lines[-1][len("CHILD=") :])


@pytest.mark.parametrize("erase", ["clear-and-update", "patch-dict"])
def test_a_restore_of_environ_keeps_the_caller_neutralisation(tmp_path, erase):
    """The caller set it to ``""``; a test defeats ``os.environ`` the named way;
    the child's loader must still see the caller's ``""`` and must not fill the
    name from a ``.env`` in reach. Born red on Windows, on both erases."""
    seen = _run_restorer(tmp_path, erase)
    assert seen == {"value": "", "by_caller": True}, (
        "the caller's neutralisation did not survive the boundary - the child "
        f"took the .env value instead (born red on Windows): {seen!r}"
    )


def test_an_explicit_value_outranks_the_carrier(tmp_path):
    """A spawner that hands the child a real value keeps it: the carrier only
    re-asserts the names the boundary erased, never overrides a present one."""
    seen = _run_restorer(tmp_path, "clear-and-update", **{NEUTRALISED: "from-spawner"})
    assert seen == {"value": "from-spawner", "by_caller": True}


def test_the_caller_empty_names_are_exported_for_children(monkeypatch):
    """No carrier present (a fresh caller): the names of the variables the
    caller left empty are exported, so children can re-assert them."""
    monkeypatch.delenv(CARRIER, raising=False)
    monkeypatch.setenv(NEUTRALISED, "")
    em._carry_caller_empty_names()
    assert CARRIER in os.environ
    assert os.environ[CARRIER], "the carrier must be non-empty to survive a restore"
    assert NEUTRALISED in os.environ[CARRIER].split(",")


def test_an_absent_carried_name_is_reasserted(monkeypatch):
    """A child that lost the name at the boundary (the Windows erase) gets the
    caller's ``""`` back before ``_CALLER_ENVIRONMENT`` is captured."""
    monkeypatch.setenv(CARRIER, NEUTRALISED)
    monkeypatch.delenv(NEUTRALISED, raising=False)
    em._carry_caller_empty_names()
    assert os.environ.get(NEUTRALISED) == ""


def test_a_carried_name_that_holds_a_value_is_left_alone(monkeypatch):
    """Only the erased names are re-asserted: a child holding a value — an
    explicit ``env=``, or a state a caller deliberately built — keeps it."""
    monkeypatch.setenv(CARRIER, NEUTRALISED)
    monkeypatch.setenv(NEUTRALISED, "explicit")
    em._carry_caller_empty_names()
    assert os.environ[NEUTRALISED] == "explicit"
