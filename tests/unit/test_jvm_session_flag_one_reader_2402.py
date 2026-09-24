# -*- coding: utf-8 -*-
"""#2402 — the ``--disable-jvm-session`` flag has ONE reader.

The defect: conftest had argv readers (module-level jpype mock, integration-
fixtures decision) that an xdist worker never satisfies — the worker argv
does not carry the flag — while the hook sites read ``config.getoption``.
Inside a worker jpype stayed real and the JVM was never started: 7 false
reds at ``-n 1`` and ``-n 4``, all green serially (measured in the issue).

The repair (``tests/_jvm_session_flag.py``): the decision is made once —
``pytest_configure`` exports it from the parsed option to an env var that
workers inherit — and every consumer reads that env var (or the option
where a config is in scope). These witnesses cover the export/read
contract; the run-level verdict (same 3 files green at serial, ``-n 1``
and ``-n 4``) belongs to the issue's DoD and is executed as a session.

Anti-pendulum: ``sys.argv`` is not read anywhere for this flag except the
explicit pre-parse propagator, documented as controller-bootstrap-only.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

from tests import _jvm_session_flag as flag
from tests.nested_pytest import both, run_probe

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

_XDIST_WORKER_MARKER = "PYTEST_XDIST_WORKER"


@pytest.fixture
def flag_absent(monkeypatch):
    """The variable starts absent, and what the code under test writes to it
    is undone at teardown.

    ``monkeypatch.delenv(..., raising=False)`` alone records nothing when the
    variable is already absent. The ``"1"`` that the propagator then wrote
    outlived the test, and every pytest session spawned later in the suite
    mocked jpype (#2530). ``setenv`` records the value to restore first.
    """
    monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "")
    monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV)
    return monkeypatch


@pytest.fixture
def controller(monkeypatch):
    """Model a controller: the bootstrap branches on the xdist worker marker,
    which an ambient ``-n`` run sets in every test of this file."""
    monkeypatch.delenv(_XDIST_WORKER_MARKER, raising=False)
    return monkeypatch


class TestEnvVarChannel:
    def test_propagator_exports_argv_decision_to_env(self, flag_absent, controller):
        monkeypatch = flag_absent
        monkeypatch.setattr(sys, "argv", ["pytest", "--disable-jvm-session"])
        flag.propagate_argv_to_env()
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

    def test_propagator_inert_without_flag(self, flag_absent, controller):
        monkeypatch = flag_absent
        monkeypatch.setattr(sys, "argv", ["pytest", "-q", "tests/unit"])
        flag.propagate_argv_to_env()
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_worker_style_argv_never_carries_the_flag(self, monkeypatch):
        """#2402 root: an xdist worker argv does not carry the flag, and the
        worker marker tells the bootstrap not to touch the inherited
        decision — the env var from the controller is the channel."""
        monkeypatch.setenv(_XDIST_WORKER_MARKER, "gw0")
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "1")
        monkeypatch.setattr(
            sys, "argv", ["-c", "--workerinput", "pytest", "tests/unit"]
        )
        flag.propagate_argv_to_env()
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        monkeypatch.setattr(
            sys, "argv", ["-c", "--workerinput", "pytest", "tests/unit"]
        )
        flag.propagate_argv_to_env()
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_jvm_session_disabled_reads_env_only(self, monkeypatch):
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "1")
        assert flag.jvm_session_disabled() is True
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "0")
        assert flag.jvm_session_disabled() is False
        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        assert flag.jvm_session_disabled() is False

    def test_export_from_parsed_option(self, flag_absent):
        monkeypatch = flag_absent

        class _FlagOn:
            def getoption(self, name):
                return name == "--disable-jvm-session"

        class _FlagOff:
            def getoption(self, name):
                return False

        flag.export_flag_from_config(_FlagOn())
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        flag.export_flag_from_config(_FlagOff())
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_export_tolerant_of_mock_config(self, flag_absent):
        """The conftest unit tests hand mock configs around (same tolerance
        as ``_e2e_session_decision``): no getoption must not blow up and
        must not leak an export."""
        flag.export_flag_from_config(object())
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ


class TestConftestConsumesTheEnvDecision:
    def test_module_level_decisions_track_the_env(self, monkeypatch):
        """The two conftest module-level decisions (jpype mock, integration
        fixtures) read ``jvm_session_disabled()`` — the same env var — so a
        controller export reaches a worker that has not run any hook yet."""
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "1")
        assert flag.jvm_session_disabled() is True
        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        assert flag.jvm_session_disabled() is False


class TestPutBack:
    """#2530: the per-test guard in ``tests/conftest.py`` calls ``put_back``."""

    def test_nothing_moved(self, flag_absent):
        assert flag.put_back(None) is None
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_a_written_flag_is_removed_and_named(self, flag_absent):
        os.environ[flag.JVM_SESSION_DISABLED_ENV] = "1"

        message = flag.put_back(None)

        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ
        assert f"{flag.JVM_SESSION_DISABLED_ENV}='1'" in message
        assert "it was None when the test started" in message

    def test_a_removed_flag_is_restored(self, flag_absent):
        message = flag.put_back("1")

        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"
        assert f"{flag.JVM_SESSION_DISABLED_ENV}=None" in message


class TestTheParsedOptionOutvotesAnInheritedValue:
    """#2402, what remained after #2465: ``setdefault`` let an inherited value
    win over the parsed option.

    Measured: ``PYTEST_JVM_SESSION_DISABLED=0`` with the flag kept the #2402
    split serially and silently; ``=1`` without the flag left jpype mocked
    under a session that never asked. The option decides, so the export
    overwrites, and clears."""

    class _FlagOn:
        def getoption(self, name):
            return name == "--disable-jvm-session"

    class _FlagOff:
        def getoption(self, name):
            return False

    def test_export_overwrites_an_inherited_zero(self, flag_absent):
        monkeypatch = flag_absent
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "0")
        flag.export_flag_from_config(self._FlagOn())
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

    def test_export_clears_an_inherited_one_when_the_option_is_off(self, flag_absent):
        monkeypatch = flag_absent
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "1")
        flag.export_flag_from_config(self._FlagOff())
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_bootstrap_overwrites_an_inherited_zero(self, flag_absent, controller):
        monkeypatch = flag_absent
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "0")
        monkeypatch.setattr(sys, "argv", ["pytest", "--disable-jvm-session"])
        flag.propagate_argv_to_env()
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

    def test_bootstrap_clears_an_inherited_one_without_the_flag(
        self, flag_absent, controller
    ):
        monkeypatch = flag_absent
        monkeypatch.setenv(flag.JVM_SESSION_DISABLED_ENV, "1")
        monkeypatch.setattr(sys, "argv", ["pytest", "-q", "tests/unit"])
        flag.propagate_argv_to_env()
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ


_AGREEMENT_PROBE = """
import sys
from unittest.mock import MagicMock


def test_jpype_mocked_if_and_only_if_the_option_is_set(request):
    option_on = bool(request.config.getoption("--disable-jvm-session"))
    mocked = isinstance(sys.modules.get("jpype"), MagicMock)
    assert mocked == option_on, (
        "#2402: jpype is mocked=%r while --disable-jvm-session=%r - the flag "
        "has more than one reader" % (mocked, option_on)
    )
"""


class TestTheAgreementHoldsUnderXdist:
    """The guard the unit tests above cannot be: every ``sys.argv`` reader unit
    test passes, and the session still splits inside a worker. The probe
    asserts the invariant where it matters — jpype mocked ⇔ the parsed
    option. With the flag it reddens on the pre-#2465 conftest (a worker's
    argv carries no flag); with an inherited ``0`` it reddens on the
    ``setdefault`` export. Measured A/B by stashing the repair."""

    def test_under_xdist_with_the_flag(self):
        returncode, out, err = run_probe(
            "2402",
            {"probe_2402_agreement.py": _AGREEMENT_PROBE},
            "-n",
            "1",
            "--disable-jvm-session",
        )
        assert returncode == 0 and "1 passed" in out, both(out, err)

    def test_under_xdist_when_the_controller_inherited_a_zero(self):
        returncode, out, err = run_probe(
            "2402",
            {"probe_2402_agreement.py": _AGREEMENT_PROBE},
            "-n",
            "1",
            "--disable-jvm-session",
            env={flag.JVM_SESSION_DISABLED_ENV: "0"},
        )
        assert returncode == 0 and "1 passed" in out, both(out, err)

    @pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2402: the probe starts a real JVM (parent runs JVM-less)",
    )
    def test_when_the_controller_inherited_a_one_without_the_flag(self):
        returncode, out, err = run_probe(
            "2402",
            {"probe_2402_agreement.py": _AGREEMENT_PROBE},
            env={flag.JVM_SESSION_DISABLED_ENV: "1"},
        )
        assert returncode == 0 and "1 passed" in out, both(out, err)
