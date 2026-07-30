# -*- coding: utf-8 -*-
"""Tests for #1567 — the speech-to-text fallacy service advertises no lying tier.

The former tier 1 ("Advanced Services") was DEAD: it imported a module removed
in ``d2fef7b4`` (``argumentation_analysis.orchestration.analysis_runner``), the
``AnalysisRunner`` class exists in NO module, the assigned instance was never
read, and the kernel was built with a FAKE key (``api_key="mock_key"``). So
repairing the import alone would have flipped an honestly-OFF tier into a tier
that LIES about being available then fails on the first real call (motif #1019).
Decision: REMOVE the tier (#1567).

These tests prove the removal holds and is structural (not just behavioural):
  * ``check_health()`` can no longer advertise the tier that lied.
  * No phantom advanced-tier attribute lingers on the instance.
  * No executable code passes ``api_key`` (the fake key was consumed only by the
    removed kernel build; the docstring documenting the removal is a string
    Constant, not a Call kwarg, so the AST walk over Calls excludes it).
  * Every ``except ImportError`` is reachability-gated (calls ``check_health``)
    so no tier can mask its own unavailability (anti-#1019).
  * The dead importer is referenced in NO executable Name/Attribute (only in the
    docstring).
  * The always-on pattern tier delivers honest success.

No-LLM, no-JVM. ``speech-to-text/`` is outside the CI gate (#1563); this test
lives in ``tests/unit/`` (inside the gate) and imports the service by file path.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_PATH = REPO_ROOT / "speech-to-text" / "services" / "fallacy_detector.py"


def _load_service_module():
    """Import fallacy_detector by file path (independent of package wiring).

    The relative ``from .web_api_client`` import has no package context under a
    file-path load, so it raises ImportError — which the service catches
    honestly (the web-API tier stays OFF). That is exactly the honest-degraded
    behaviour under test.
    """
    spec = importlib.util.spec_from_file_location(
        "fallacy_detector_1567", str(SERVICE_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _ast_tree():
    return ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))


def _is_import_error(node):
    if node is None:
        return False  # bare `except:` is not an ImportError handler
    names = []
    if isinstance(node, ast.Name):
        names = [node.id]
    elif isinstance(node, ast.Tuple):
        names = [e.id for e in node.elts if isinstance(e, ast.Name)]
    return "ImportError" in names


# --- Behavioural: the lying tier is gone from the health report ---


def test_check_health_advertises_no_advanced_tier():
    """DoD: check_health() cannot announce a tier that would fail on first call."""
    svc = _load_service_module().get_fallacy_detection_service()
    health = svc.check_health()
    assert (
        "advanced_services" not in health
    ), "check_health must not advertise the dead/lying advanced-services tier"
    assert health["pattern_matching"] is True  # the always-on honest tier
    assert "web_api" in health  # reports availability honestly (True only if up)


def test_no_phantom_advanced_attributes():
    """The removed tier left no attribute on the instance."""
    svc = _load_service_module().get_fallacy_detection_service()
    for attr in ("use_advanced_services", "informal_agent", "analysis_runner"):
        assert not hasattr(svc, attr), f"phantom attribute {attr!r} lingers"


def test_pattern_tier_delivers_honest_success():
    """The always-on tier works with no LLM/JVM/key (opaque synthetic probe)."""
    svc = _load_service_module().get_fallacy_detection_service()
    result = svc.detect_fallacies("c est un idiot cet individu la")
    assert result["status"] == "success"
    assert result["summary"]["analysis_method"] == "pattern_matching"


# --- Structural (AST): the removal cannot regress via executable code ---


def test_no_executable_code_passes_api_key():
    """No Call passes ``api_key`` — the fake key was the removed kernel's only
    consumer. The docstring documenting the removal is a string Constant, so an
    AST walk of Calls sees none."""
    tree = _ast_tree()
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "api_key":
                    offenders.append(ast.unparse(node))
    assert offenders == [], f"executable code still passes api_key: {offenders}"


def test_every_importerror_tier_is_reachability_gated():
    """Anti-#1019: any ``except ImportError`` must guard a tier whose try-body
    probes reachability (``check_health``). No tier may mask its own
    unavailability then claim ready."""
    tree = _ast_tree()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if _is_import_error(handler.type):
                    try_src = ast.unparse(node)
                    assert "check_health" in try_src, (
                        "except ImportError without a check_health() reachability "
                        "gate would mask an unavailable tier (anti-#1019)"
                    )


def test_no_dead_importer_reference_in_executable_code():
    """The removed dead importer (analysis_runner module / AnalysisRunner class)
    must not appear in any executable Name/Attribute. It may appear in the
    docstring documenting the removal — AST Names/Attributes exclude docstrings."""
    tree = _ast_tree()
    referenced = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {
            "AnalysisRunner",
            "analysis_runner",
        }:
            referenced.append(node.id)
        if isinstance(node, ast.Attribute) and node.attr in {
            "AnalysisRunner",
            "analysis_runner",
        }:
            referenced.append(node.attr)
    assert (
        referenced == []
    ), f"executable code still references the dead importer: {referenced}"
