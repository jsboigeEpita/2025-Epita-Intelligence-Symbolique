"""#3161 — a session's JVM and e2e answers belong to that session's process.

``jvm_started`` (written by ``pytest_sessionstart``, read by the
``jvm_session`` fixture) and ``is_e2e_session`` (written by
``pytest_collection_finish``, read by the fixture and the #2021/#2862
skip-storm exemption) used to ride ``config.cache`` —
``<rootdir>/.pytest_cache/v/`` on disk, shared by EVERY pytest process
under the rootdir. A sibling ``--collect-only`` rewrote ``jvm_started``
under a session whose JVM was live (19 047 passed / 1 failed, the R1107
union: the oracle child skipped 14/14 with a live JVM); a sibling e2e
session could equally hand the skip-storm exemption to a JVM session —
the silent-green direction those guards exist to close. The conftest now
carries both keys in ``config.stash``: one process, one answer.

Each witness speaks whatever transport the conftest speaks — on main that
is the on-disk cache (and the race witnesses redden there by the race
itself, not by an import error); on the fix it is the stash. Routing a key
back through ``config.cache`` — the DoD's mutation — is exactly main's
shape, which the born-red run measures.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SIBLING_PLAIN = "tests/unit/test_conftest_argv_order_3080.py"
SIBLING_E2E = "tests/e2e/python/test_webapp_homepage.py"


def _jvm_transport():
    """(writer, reader) for jvm_started, in the conftest's own transport."""
    import tests.conftest as conftest

    if hasattr(conftest, "set_jvm_started"):  # the fix: config.stash
        return conftest.set_jvm_started, conftest.get_jvm_started
    disk = conftest._cache  # main: the shared on-disk cache
    return (
        lambda config, value: disk(config).set("jvm_started", value),
        lambda config: disk(config).get("jvm_started", False),
    )


def _e2e_transport():
    """(writer, reader) for is_e2e_session, in the conftest's own transport."""
    import tests.conftest as conftest

    if hasattr(conftest, "set_is_e2e_session"):
        return conftest.set_is_e2e_session, conftest.get_is_e2e_session
    disk = conftest._cache
    return (
        lambda config, value: disk(config).set("is_e2e_session", value),
        lambda config: disk(config).get("is_e2e_session", False),
    )


def _sibling(relative_target: str) -> subprocess.CompletedProcess:
    """A sibling pytest under the same rootdir — the race's other process."""
    if not (REPO_ROOT / relative_target).exists():
        pytest.skip(f"witness target absent: {relative_target}")
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = ""  # keyless idiom (#1167/R1167)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:randomly",
            relative_target,
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_a_sibling_collect_only_does_not_rewrite_jvm_started(request):
    """Born red on main: the sibling's sessionstart writes jvm_started=False
    to the shared disk before collecting anything, so a session whose JVM
    is live reads the sibling's answer — the oracle child's 14/14 skip."""
    write, read = _jvm_transport()
    write(request.config, True)  # what a booted session's sessionstart wrote
    assert read(request.config) is True  # control: this session's own answer
    done = _sibling(SIBLING_PLAIN)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert (
        read(request.config) is True
    ), "a sibling pytest process rewrote this session's jvm_started (#3161)"


def test_a_sibling_e2e_collection_does_not_rewrite_is_e2e_session(request):
    """Born red on main: the sibling's collection_finish writes
    is_e2e_session=True for its own e2e items; a non-e2e session reading
    the shared disk inherits the skip-storm exemption — #2021's
    silent-green direction."""
    write, read = _e2e_transport()
    write(request.config, False)  # this session collected no e2e item
    assert read(request.config) is False
    done = _sibling(SIBLING_E2E)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert (
        read(request.config) is False
    ), "a sibling e2e session rewrote this session's is_e2e_session (#3161)"


# The nested control runs a session with NO cacheprovider — on main that is
# #1820's _NullCache path, on the fix the stash; either way the session's
# own answer must round-trip (an INTERNALERROR there was the original #1820).
_NESTED_CONTROL = """
def test_the_session_key_round_trips_without_cacheprovider(request):
    import tests.conftest as conftest

    if hasattr(conftest, "get_jvm_started"):
        value = conftest.get_jvm_started(request.config)
    else:  # main: the _NullCache fallback
        value = conftest._cache(request.config).get("jvm_started", False)
    # sessionstart already ran with --disable-jvm-session: the JVM-less
    # choice is recorded, and readable, with no config.cache in sight.
    assert value is False
"""


def test_a_no_cacheprovider_session_still_carries_its_key(tmp_path):
    """Control (#1820 path): with the cacheprovider off there is no
    config.cache at all — the session key must survive on whatever
    in-process transport the conftest uses."""
    nested = tmp_path / "test_no_cacheprovider_3161.py"
    nested.write_text(_NESTED_CONTROL, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = ""
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(nested),
            "-c",
            str(tmp_path / "pytest.ini"),
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:randomly",
            "-p",
            "tests.conftest",
            "--disable-jvm-session",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert "1 passed" in done.stdout, done.stdout[-2000:]
