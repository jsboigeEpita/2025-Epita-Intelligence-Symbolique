# -*- coding: utf-8 -*-
"""#2346 (`services/web_api/services/fallacy_service.py:60`): one missing analyzer takes only itself down.

``fallacy_service`` imported its three analyzers inside one ``try``: the first
``ImportError`` set **all three** to ``None``, and ``_initialize_analyzers`` then
still set ``is_initialized = True``. Each witness runs in a subprocess that
blocks one module before the import, so the module under test is imported
fresh and the test process's own copy stays untouched.
"""

import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 6))

_SEVERITY = (
    "argumentation_analysis.plugins.analysis_tools.logic.fallacy_severity_evaluator"
)
_BASE = "argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer"

_WITNESS = r"""
import json, logging, sys
logging.disable(logging.CRITICAL)
sys.modules[sys.argv[1]] = None  # importing it now raises ImportError
from argumentation_analysis.services.web_api.services import fallacy_service as m
service = m.FallacyService()
print(json.dumps({
    "base": m.ContextualFallacyAnalyzer is not None,
    "severity": m.FallacySeverityEvaluator is not None,
    "enhanced": m.EnhancedContextualAnalyzer is not None,
    "initialized": service.is_initialized,
}))
"""


def _import_without(module: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _WITNESS, module],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_a_missing_severity_evaluator_leaves_the_base_analyzer():
    # The enhanced analyzer goes down with it: both live in
    # ``plugins/analysis_tools/logic/``, whose ``__init__`` imports every
    # submodule. That coupling is the package's, not this module's, so it is
    # not asserted here.
    state = _import_without(_SEVERITY)
    assert state["severity"] is False
    assert state["base"] is True
    assert state["initialized"] is True


def test_without_a_base_detector_the_service_is_not_initialized():
    state = _import_without(_BASE)
    assert state["base"] is False
    assert state["initialized"] is False
