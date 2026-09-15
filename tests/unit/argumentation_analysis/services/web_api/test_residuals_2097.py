"""Né-rouge guards for #2097 residual anomalies #2, #3, #5 (and the #2 inversion).

Measured on the pristine tree (base ``6dfa3a96``):

- #2 (INVERTED): the issue called ``LogicService.text_to_belief_set`` +
  ``interpret_results`` a dead pair. Re-verification says half the opposite:
  the MCP tool ``create_belief_set`` (``main.py:500``) calls
  ``logic_service.create_belief_set`` — a method that DOES NOT EXIST on
  ``LogicService`` (AttributeError at first use; no integration test covers
  it; the archived Flask route ``/api/logic/belief-set`` called
  ``text_to_belief_set``, the exact signature the tool needs). The truly dead
  half is ``interpret_results`` + ``LogicInterpretationResponse`` (no
  production caller, archived route only).
- #5: ``validation_service.validate_argument`` carries a formal branch whose
  condition tests ``request.logic_type`` — a field ``ValidationRequest`` does
  not define, so the branch never executes (the in-code comment says it was
  made deliberately unreachable). Its helper
  ``LogicService.validate_argument_from_components`` reads the same missing
  field — it would AttributeError even if reached.
- #3: ``FrameworkAnalysisRequest`` exists twice (``api/models.py:48`` — the
  live FastAPI contract — and ``web_api/models/request_models.py:339`` — zero
  production consumers, one construction test).

#4 (double Dung surface) is NOT guarded here: both surfaces are alive with
distinct engines (TweetyBridge vs EnhancedDungAgent) and distinct apps
(MCP vs ``api/``) — the fix is cross-reference documentation, not removal.
"""

import importlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
MAIN_PY = REPO_ROOT / "argumentation_analysis" / "services" / "mcp_server" / "main.py"
SERVICES_DIR = REPO_ROOT / "argumentation_analysis" / "services" / "web_api"

SERVICE_CLASSES = {
    "logic_service": (
        "argumentation_analysis.services.web_api.services.logic_service",
        "LogicService",
    ),
    "analysis_service": (
        "argumentation_analysis.services.web_api.services.analysis_service",
        "AnalysisService",
    ),
    "validation_service": (
        "argumentation_analysis.services.web_api.services.validation_service",
        "ValidationService",
    ),
    "fallacy_service": (
        "argumentation_analysis.services.web_api.services.fallacy_service",
        "FallacyService",
    ),
    "framework_service": (
        "argumentation_analysis.services.web_api.services.framework_service",
        "FrameworkService",
    ),
}


def test_every_mcp_tool_service_call_resolves():
    """#2097-2: each ``self.services.X.Y(...)`` in main.py must exist on X."""
    src = MAIN_PY.read_text(encoding="utf-8", errors="replace")
    calls = sorted(set(re.findall(r"self\.services\.(\w+)\.(\w+)\(", src)))
    assert calls, "main.py must call its services container"
    for attr, method in calls:
        assert attr in SERVICE_CLASSES, f"unknown services attr: {attr}"
        module_path, class_name = SERVICE_CLASSES[attr]
        cls = getattr(importlib.import_module(module_path), class_name)
        assert hasattr(cls, method), (
            f"main.py calls services.{attr}.{method}() but {class_name} "
            f"defines no such method"
        )


def test_validation_service_has_no_never_executing_branch():
    """#2097-5: no condition on a field ValidationRequest does not define."""
    src = (SERVICES_DIR / "services" / "validation_service.py").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "logic_type" not in src, (
        "validation_service references logic_type — ValidationRequest does "
        "not define that field, so any such branch never executes"
    )


def test_dead_logic_pair_is_removed():
    """#2097-2: interpret_results + its response model + the broken helper."""
    from argumentation_analysis.services.web_api.services.logic_service import (
        LogicService,
    )
    from argumentation_analysis.services.web_api.models import response_models

    assert not hasattr(LogicService, "interpret_results")
    assert not hasattr(
        LogicService, "validate_argument_from_components"
    ), "its only caller was the never-executing formal branch (#2097-5)"
    assert not hasattr(response_models, "LogicInterpretationResponse")


def test_framework_analysis_request_collision_is_resolved():
    """#2097-3: the web_api twin (zero production consumers) is gone."""
    from argumentation_analysis.services.web_api.models import request_models

    assert not hasattr(
        request_models, "FrameworkAnalysisRequest"
    ), "the live contract lives in api/models.py; the web_api twin had zero production consumers"
