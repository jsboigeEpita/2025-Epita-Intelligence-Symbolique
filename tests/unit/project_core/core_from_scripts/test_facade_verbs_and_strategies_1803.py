# -*- coding: utf-8 -*-
"""#1803 (étapes 1-2): façade verbs reach the implementation; the 5 repair
strategies are covered by discriminating controls.

Step 1 -- the wiring. A verb that PARSES is not a verb that CALLS: each test
below drives the full ``main()`` argv and spies on the IMPLEMENTATION
(``EnvironmentManager.fix_dependencies``, ``SystemValidationEngine.*``), never
on argparse. Born-red on the pre-#1803 tree: argparse rejected ``fix-deps``
(SystemExit 2, "invalid choice") and ``validate`` did not exist.

Step 2 -- the strategies. Every strategy funnels through
``manager_env.run_command_in_conda_env(command) -> exit_code``; the tests stub
that single seam. The degenerate substitution is built in: exit 1 must flip the
verdict to False, and the recorded command must name the package and the
strategy's distinctive flag -- an ``assert isinstance(result, bool)`` here would
be exactly the #1588/#1593 motif this dispatch forbids.

Nothing real is invoked: no network, no conda, no install subprocess. The egress
counter must read 0 on this file's band.
"""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from project_core.core_from_scripts.common_utils import Logger
from project_core.core_from_scripts.strategies.default_install_strategy import (
    DefaultInstallStrategy,
)
from project_core.core_from_scripts.strategies.msvc_build_strategy import (
    MsvcBuildStrategy,
)
from project_core.core_from_scripts.strategies.no_binary_strategy import (
    NoBinaryStrategy,
)
from project_core.core_from_scripts.strategies.simple_install_strategy import (
    SimpleInstallStrategy,
)
from project_core.core_from_scripts.strategies.wheel_install_strategy import (
    WheelInstallStrategy,
)

MODULE = "project_core.core_from_scripts.project_setup"


def _fake_manager(exit_code):
    """A manager_env double whose single seam records commands and returns a
    fixed exit code -- the degenerate-substitution instrument."""
    calls = []

    def run(command):
        calls.append(command)
        return exit_code

    return SimpleNamespace(run_command_in_conda_env=run), calls


class TestFacadeVerbs(unittest.TestCase):
    """Étape 1: les verbes arrivent à l'implémentation."""

    def _run_main(self, argv):
        with patch(f"{MODULE}.EnvironmentManager") as MockEnvManager, patch(
            f"{MODULE}.ValidationEngine"
        ) as MockRulesEngine, patch(
            f"{MODULE}.SystemValidationEngine"
        ) as MockSystemEngine, patch.object(
            sys, "argv", argv
        ):
            env_manager = MockEnvManager.return_value
            system_validator = MockSystemEngine.return_value
            with self.assertRaises(SystemExit) as ctx:
                __import__(
                    "project_core.core_from_scripts.project_setup",
                    fromlist=["main"],
                ).main()
        return ctx.exception.code, env_manager, system_validator

    def test_fix_deps_verb_reaches_fix_dependencies(self):
        code, env_manager, _ = self._run_main(
            [
                "setup_manager",
                "fix-deps",
                "--package",
                "JPype1",
                "--strategy",
                "aggressive",
            ]
        )
        env_manager.fix_dependencies.assert_called_once_with(
            packages=["JPype1"], requirements_file=None, strategy_name="aggressive"
        )
        self.assertEqual(code, 0)

    def test_fix_deps_requirements_variant_passes_the_file(self):
        code, env_manager, _ = self._run_main(
            ["setup_manager", "fix-deps", "--requirements", "requirements.txt"]
        )
        env_manager.fix_dependencies.assert_called_once_with(
            packages=None,
            requirements_file="requirements.txt",
            strategy_name="default",
        )
        self.assertEqual(code, 0)

    def test_validate_jvm_verb_reaches_validate_jvm_bridge(self):
        _, _, system_validator = self._run_main(
            ["setup_manager", "validate", "--component", "jvm"]
        )
        system_validator.validate_jvm_bridge.assert_called_once_with()

    def test_validate_build_tools_verb_reaches_validate_build_tools(self):
        _, _, system_validator = self._run_main(
            ["setup_manager", "validate", "--component", "build-tools"]
        )
        system_validator.validate_build_tools.assert_called_once_with()

    def test_validate_failure_exits_nonzero(self):
        code, _, system_validator = self._run_main(
            ["setup_manager", "validate", "--component", "jvm"]
        )
        system_validator.validate_jvm_bridge.return_value = {
            "status": "failure",
            "message": "JPype n'est pas installé.",
        }
        # Re-run with the failing payload wired BEFORE main() executes.
        with patch(f"{MODULE}.EnvironmentManager"), patch(
            f"{MODULE}.ValidationEngine"
        ), patch(f"{MODULE}.SystemValidationEngine") as MockSystemEngine, patch.object(
            sys,
            "argv",
            ["setup_manager", "validate", "--component", "jvm"],
        ):
            MockSystemEngine.return_value.validate_jvm_bridge.return_value = {
                "status": "failure",
                "message": "JPype n'est pas installé.",
            }
            with self.assertRaises(SystemExit) as ctx:
                __import__(
                    "project_core.core_from_scripts.project_setup",
                    fromlist=["main"],
                ).main()
        self.assertEqual(ctx.exception.code, 1)

    def test_install_project_uses_the_system_validator_not_the_rules_engine(self):
        """The latent AttributeError fix: install_project must call
        validate_build_tools on the class that HAS it."""
        with patch(f"{MODULE}.EnvironmentManager") as MockEnvManager, patch(
            f"{MODULE}.ValidationEngine"
        ) as MockRulesEngine, patch(
            f"{MODULE}.SystemValidationEngine"
        ) as MockSystemEngine:
            setup = __import__(
                "project_core.core_from_scripts.project_setup",
                fromlist=["ProjectSetup"],
            ).ProjectSetup(logger=MagicMock(spec=Logger))
            MockSystemEngine.return_value.validate_build_tools.return_value = {
                "status": "failure",
                "message": "manquants",
            }
            result = setup.install_project()
        MockSystemEngine.return_value.validate_build_tools.assert_called_once_with()
        MockRulesEngine.return_value.assert_not_called()
        self.assertFalse(result)


class TestRepairStrategyCoverage(unittest.TestCase):
    """Étape 2: les 5 stratégies, chacune avec un contrôle qui discrimine."""

    def test_default_install_success_and_command_shape(self):
        strategy, calls = _fake_manager(0)
        self.assertTrue(DefaultInstallStrategy(strategy).execute("JPype1"))
        self.assertEqual(calls, ["pip install --force-reinstall --no-cache-dir JPype1"])

    def test_default_install_degenerate_failure_bites(self):
        strategy, _ = _fake_manager(1)
        self.assertFalse(DefaultInstallStrategy(strategy).execute("JPype1"))

    def test_simple_install_success_and_command_shape(self):
        strategy, calls = _fake_manager(0)
        self.assertTrue(SimpleInstallStrategy(strategy).execute("JPype1"))
        self.assertEqual(calls, ['pip install "JPype1"'])

    def test_simple_install_degenerate_failure_bites(self):
        strategy, _ = _fake_manager(1)
        self.assertFalse(SimpleInstallStrategy(strategy).execute("JPype1"))

    def test_no_binary_carries_its_distinctive_flag(self):
        strategy, calls = _fake_manager(0)
        self.assertTrue(NoBinaryStrategy(strategy).execute("JPype1"))
        self.assertEqual(len(calls), 1)
        self.assertIn("--no-binary :all:", calls[0])
        self.assertIn("JPype1", calls[0])

    def test_no_binary_degenerate_failure_bites(self):
        strategy, _ = _fake_manager(1)
        self.assertFalse(NoBinaryStrategy(strategy).execute("JPype1"))

    def test_wheel_install_success_downloads_a_jpype_wheel(self):
        strategy, calls = _fake_manager(0)
        self.assertTrue(WheelInstallStrategy(strategy).execute("JPype1"))
        self.assertEqual(len(calls), 1)
        self.assertIn("files.pythonhosted.org", calls[0])
        self.assertIn("JPype1-", calls[0])

    def test_wheel_install_degenerate_failure_bites(self):
        strategy, _ = _fake_manager(1)
        self.assertFalse(WheelInstallStrategy(strategy).execute("JPype1"))

    def test_wheel_install_refuses_non_jpype_packages_without_invoking_pip(self):
        """The heuristic guard: a package it cannot guess a wheel for must
        fail WITHOUT launching any command -- silently guessing wrong would
        install the wrong thing."""
        strategy, calls = _fake_manager(0)
        self.assertFalse(WheelInstallStrategy(strategy).execute("requests"))
        self.assertEqual(calls, [])

    def test_msvc_build_returns_false_even_when_vcvars_is_found(self):
        """Contract pin: the automatic MSVC build is NOT implemented; the
        strategy must keep saying so instead of pretending to succeed."""
        with patch.dict(
            os.environ, {"ProgramFiles(x86)": str(self._fake_vs_install())}
        ):
            strategy, calls = _fake_manager(0)
            self.assertFalse(MsvcBuildStrategy(strategy).execute("JPype1"))
            self.assertEqual(calls, [])

    def test_msvc_build_returns_false_when_vcvars_is_absent(self):
        strategy, calls = _fake_manager(0)
        with patch.dict(
            os.environ,
            {"ProgramFiles(x86)": str(Path(self.mkdtemp_not_existing()))},
        ):
            self.assertFalse(MsvcBuildStrategy(strategy).execute("JPype1"))
        self.assertEqual(calls, [])

    # -- helpers ------------------------------------------------------------

    def _fake_vs_install(self):
        import tempfile

        root = (
            Path(tempfile.mkdtemp()) / "Microsoft Visual Studio" / "2022" / "BuildTools"
        )
        vcvars = root / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        vcvars.parent.mkdir(parents=True, exist_ok=True)
        vcvars.write_text("@echo off", encoding="utf-8")
        return root.parents[3]

    @staticmethod
    def mkdtemp_not_existing():
        import tempfile

        return Path(tempfile.mkdtemp()) / "nowhere"


if __name__ == "__main__":
    unittest.main()
