"""#2619: a nested pytest session is a controller of its own.

``run_bounded`` used to pass the caller's whole environment to the child. From
an xdist worker, that included ``PYTEST_XDIST_WORKER``, which
``tests/_jvm_session_flag.py`` reads as "this process is a worker": the child
then kept an inherited JVM decision its own argv should have made, and the
#2402 agreement witness was red under ``-n``. These tests run in the serial
gate, where the ambient marker is absent, so they set it themselves.
"""

import json
import sys

from tests.nested_pytest import run_bounded

_SHOW = (
    "import json, os; print(json.dumps({k: os.environ.get(k) for k in "
    "('PYTEST_XDIST_WORKER', 'PYTEST_XDIST_WORKER_COUNT', 'ISSUE_2619_KEPT')}))"
)


def _child_env(**env):
    done = run_bounded([sys.executable, "-c", _SHOW], env=env or None)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_the_callers_worker_identity_does_not_reach_the_child(monkeypatch):
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")
    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "6")
    seen = _child_env(ISSUE_2619_KEPT="kept")
    assert seen["PYTEST_XDIST_WORKER"] is None
    assert seen["PYTEST_XDIST_WORKER_COUNT"] is None
    assert seen["ISSUE_2619_KEPT"] == "kept"


def test_an_explicit_value_still_reaches_the_child(monkeypatch):
    """A test that models a worker passes the marker on purpose (#2472)."""
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    seen = _child_env(PYTEST_XDIST_WORKER="gw0")
    assert seen["PYTEST_XDIST_WORKER"] == "gw0"
