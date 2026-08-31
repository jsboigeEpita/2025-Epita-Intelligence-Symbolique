# -*- coding: utf-8 -*-
"""Guard for #1874 (arbitration point 5): the Provision step's failure orients the reader.

⚠ Retuned by #1959. This guard pins the *presence* of the host name and the
three artifact names -- it cannot detect that the sentence around them has
become false, and it did not: the annotation went on calling
tweetyproject.org/mvn/ "la SEULE source" after the default exclusions removed
all three artifacts from the closure, and this guard stayed green through it.
Keep the assertions, but read the copy when the assembly story changes.

The Python error chain already names tweetyproject.org (AssemblyError in
``tweety_assembly.py``, logged by ``download_tweety_jars``), but that text sits
mid-log. The surface whoever lands on the red run page actually sees is the
GitHub annotation strip, which without a ``::error::`` workflow command shows
only "Process completed with exit code 1" -- three investigations have restarted
from zero on that generic line. The guard pins both the annotation copy and the
behavior: ``main()`` must emit it ON STDOUT (GitHub parses workflow commands
from stdout only) exactly when provisioning fails, and stay silent on success.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "provision_tweety.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("provision_tweety_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def provision(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "download_tweety_jars", lambda: False)
    return module


class TestProvisionFailureNamesSPOF:
    def test_annotation_is_a_workflow_error_naming_the_spof(self, provision):
        text = provision.failure_annotation()
        assert text.startswith("::error::"), (
            "#1874: the failure annotation must be a GitHub workflow error "
            "command, or it never reaches the run-page annotation strip"
        )
        assert "tweetyproject.org" in text, (
            "#1874/#1959: the annotation must still name the host, but the "
            "reason inverted. It named it as the SPOF to go check; since the "
            "default exclusions put the closure at 74/74 on Central it names "
            "it as the host NOT to go check. Naming it either way is what "
            "stops the reader re-deriving where the jars come from"
        )
        assert "jspf" in text and "gurobi" in text, (
            "#1959: the three artifacts stay named, for a reason that "
            "outlived their exclusion -- seeing one of them in a provisioning "
            "error now means tweety_excluded_modules was emptied or "
            "overridden, which is a different defect from a Central outage "
            "and has a different fix"
        )

    def test_main_emits_annotation_on_stdout_when_provisioning_fails(
        self, provision, capsys
    ):
        rc = provision.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "::error::" in out and "tweetyproject.org" in out, (
            "#1874: main() must print the workflow command to STDOUT (GitHub "
            "parses ::error:: from stdout only) when provisioning fails"
        )

    def test_main_stays_silent_on_success(self, monkeypatch, capsys):
        module = _load_module()
        monkeypatch.setattr(module, "download_tweety_jars", lambda: True)
        rc = module.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "::error::" not in out, (
            "#1874: the annotation must not fire on a successful provision -- "
            "a always-on error annotation is noise that hides the real one"
        )
