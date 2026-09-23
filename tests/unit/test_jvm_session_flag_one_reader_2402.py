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

import pytest

from tests import _jvm_session_flag as flag


class TestEnvVarChannel:
    def test_propagator_exports_argv_decision_to_env(self, monkeypatch):
        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        monkeypatch.setattr(sys, "argv", ["pytest", "--disable-jvm-session"])
        flag.propagate_argv_to_env()
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

    def test_propagator_inert_without_flag(self, monkeypatch):
        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        monkeypatch.setattr(sys, "argv", ["pytest", "-q", "tests/unit"])
        flag.propagate_argv_to_env()
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_worker_style_argv_never_carries_the_flag(self, monkeypatch):
        """#2402 root: an xdist worker argv does not carry the flag. The
        propagator must not invent a decision from a worker argv; the env
        var inherited from the controller is the channel."""
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

    def test_export_from_parsed_option(self, monkeypatch):
        class _FlagOn:
            def getoption(self, name):
                return name == "--disable-jvm-session"

        class _FlagOff:
            def getoption(self, name):
                return False

        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        flag.export_flag_from_config(_FlagOn())
        assert os.environ.get(flag.JVM_SESSION_DISABLED_ENV) == "1"

        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
        flag.export_flag_from_config(_FlagOff())
        assert flag.JVM_SESSION_DISABLED_ENV not in os.environ

    def test_export_tolerant_of_mock_config(self, monkeypatch):
        """The conftest unit tests hand mock configs around (same tolerance
        as ``_e2e_session_decision``): no getoption must not blow up and
        must not leak an export."""
        monkeypatch.delenv(flag.JVM_SESSION_DISABLED_ENV, raising=False)
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
