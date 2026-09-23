# -*- coding: utf-8 -*-
"""#2344 family (b) — the bootstrap's ImportError degradations live in the state.

Every dependency import used to leave a ``None`` that call sites skipped
silently — the only trace was an ERROR log line at import time, and the
caller of ``initialize_project_environment`` could not know WHAT had been
skipped. The named state (``BOOTSTRAP_IMPORT_FAILURES``, mirrored on the
ProjectContext as ``import_failures``) is the repair: doctrine #1019, the
degradation lives in the state, not only in the log.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from argumentation_analysis.core.bootstrap import (
    BOOTSTRAP_IMPORT_FAILURES,
    ProjectContext,
    initialize_project_environment,
)


class TestProjectContextFailures:
    def test_context_defaults_to_empty_failures(self):
        assert ProjectContext().import_failures == {}


class TestFailuresFlowToTheContext:
    """A degraded import registry is mirrored, named, on the context."""

    @pytest.fixture(autouse=True)
    def _reset_jvm_flag(self):
        original = getattr(sys, "_jvm_initialized", None)
        if hasattr(sys, "_jvm_initialized"):
            delattr(sys, "_jvm_initialized")
        yield
        if original is not None:
            sys._jvm_initialized = original
        elif hasattr(sys, "_jvm_initialized"):
            delattr(sys, "_jvm_initialized")

    def test_registry_entries_reach_the_context(self):
        with patch(
            "argumentation_analysis.core.bootstrap._pre_init_safety_checks",
            return_value=True,
        ), patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ), patch.dict(
            BOOTSTRAP_IMPORT_FAILURES,
            {"initialize_jvm_func": "simulated missing module"},
        ):
            ctx = initialize_project_environment(root_path_str="/tmp/test")
        assert ctx.import_failures == {
            "initialize_jvm_func": "simulated missing module"
        }, "the caller must see exactly which imports were skipped"

    def test_clean_registry_means_empty_failures(self):
        with patch(
            "argumentation_analysis.core.bootstrap._pre_init_safety_checks",
            return_value=True,
        ), patch(
            "argumentation_analysis.core.bootstrap.initialize_jvm_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.CryptoService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.DefinitionService_class", None
        ), patch(
            "argumentation_analysis.core.bootstrap.create_llm_service_func", None
        ), patch(
            "argumentation_analysis.core.bootstrap.sk_module", None
        ), patch(
            "argumentation_analysis.core.bootstrap.settings", None
        ), patch(
            "argumentation_analysis.core.bootstrap.ContextualFallacyDetector_class",
            None,
        ), patch.dict(
            BOOTSTRAP_IMPORT_FAILURES, clear=True
        ):
            ctx = initialize_project_environment(root_path_str="/tmp/test")
        assert ctx.import_failures == {}


_PROBE_SCRIPT = """\
import json
import sys

sys.path.insert(0, sys.argv[1])
# A REAL unimportable module, not an injected registry: `None` in sys.modules
# makes any later `import argumentation_analysis.core.jvm_setup` raise
# ImportError, so the bootstrap's own except-branch is what must name it.
sys.modules["argumentation_analysis.core.jvm_setup"] = None
import argumentation_analysis.core.bootstrap as bootstrap

ctx = bootstrap.initialize_project_environment(root_path_str=sys.argv[1])
print(
    "PROBE:"
    + json.dumps(
        {
            "registry": sorted(bootstrap.BOOTSTRAP_IMPORT_FAILURES),
            "context": sorted(ctx.import_failures),
        }
    )
)
"""


class TestARealImportFailureIsNamed:
    """The witness the injected-registry tests above cannot be.

    Those patch ``BOOTSTRAP_IMPORT_FAILURES`` themselves: delete every write
    site in ``bootstrap.py`` and they stay green. Here a real import fails in
    a subprocess — if the except-branch stops recording, the registry comes
    back without the symbol and this test reddens.
    """

    def test_unimportable_jvm_setup_is_named_in_the_state(self):
        repo = Path(__file__).resolve().parents[4]
        result = subprocess.run(
            [sys.executable, "-c", _PROBE_SCRIPT, str(repo)],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"probe crashed:\n{result.stderr[-2000:]}"
        lines = [ln for ln in result.stdout.splitlines() if ln.startswith("PROBE:")]
        assert lines, f"probe printed no registry line:\n{result.stdout[-2000:]}"
        payload = json.loads(lines[-1][len("PROBE:") :])
        assert "initialize_jvm_func" in payload["registry"], (
            f"a real import failure left no named entry in "
            f"BOOTSTRAP_IMPORT_FAILURES (got {payload['registry']}) — the "
            "degradation is back to being log-only"
        )
        assert "initialize_jvm_func" in payload["context"], (
            f"the named degradation never reached the caller's context "
            f"(got {payload['context']}) — the state link is broken"
        )
