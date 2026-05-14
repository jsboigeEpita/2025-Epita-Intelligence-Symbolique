#!/usr/bin/env python3
"""Regenerate the OpenAPI snapshot used by contract tests.

Usage:
    python scripts/api/regenerate_openapi_snapshot.py

Outputs api/openapi.snapshot.json from the FastAPI app with JPype mocked
(no JVM needed). Run this when intentionally adding/removing/changing endpoints,
then commit the updated snapshot.
"""
import json
import os
import sys
import unittest.mock as m

# Fix Windows DLL load order: torch/transformers must load before jpype (#WinError 182)
# Mock heavy NLP libs that trigger torch import chains which fail outside pytest
sys.modules.setdefault("spacy", m.MagicMock())
sys.modules.setdefault("spacy.tokens", m.MagicMock())
sys.modules.setdefault("spacy.language", m.MagicMock())

try:
    import torch  # noqa: F401
    import transformers  # noqa: F401
except (ImportError, OSError):
    pass

# Project root = two levels up from this script
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Mock JPype BEFORE any api imports that might trigger JVM
_jpype_mock = m.MagicMock()
_jpype_mock.isJVMStarted = m.MagicMock(return_value=False)
sys.modules.setdefault("jpype", _jpype_mock)
sys.modules.setdefault("jpype._core", m.MagicMock())
sys.modules.setdefault("jpype.imports", m.MagicMock())
sys.modules.setdefault("jpype.types", m.MagicMock())

# Mock bootstrap to avoid real JVM initialization
sys.modules.setdefault("argumentation_analysis.core.bootstrap", m.MagicMock())

os.environ.setdefault("PYTEST_CURRENT_TEST", "gen_openapi_snapshot")

from api.factory import create_app
from api.endpoints import router as api_router, framework_router, informal_router


def build_app():
    """Build the FastAPI app without JVM-dependent startup."""
    app = create_app(
        title="Argumentation Analysis API",
        description="API d'analyse argumentative multi-agents.",
        version="2.0.0",
    )
    app.include_router(api_router, prefix="/api")
    app.include_router(framework_router)
    app.include_router(informal_router)

    # Include optional routers
    for _module, _router, _kwargs in [
        ("api.proposal_endpoints", "proposal_router", {"prefix": "/api"}),
        ("api.mobile_endpoints", "mobile_router", {"prefix": "/api"}),
        ("api.agent_routes", "agent_router", {}),
        ("api.websocket_routes", "ws_router", {}),
        ("argumentation_analysis.api.jtms_endpoints", "jtms_router", {}),
    ]:
        try:
            mod = __import__(_module, fromlist=[_router])
            app.include_router(getattr(mod, _router), **_kwargs)
        except Exception:
            pass

    return app


def main():
    app = build_app()
    spec = app.openapi()

    # Normalize: sort paths and schemas for deterministic diffs
    if "paths" in spec:
        spec["paths"] = dict(sorted(spec["paths"].items()))
    if "components" in spec and "schemas" in spec["components"]:
        spec["components"]["schemas"] = dict(
            sorted(spec["components"]["schemas"].items())
        )

    output_path = os.path.join(_PROJECT_ROOT, "api", "openapi.snapshot.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)

    n_paths = len(spec.get("paths", {}))
    n_schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"Snapshot written to {output_path}")
    print(f"  Paths: {n_paths}")
    print(f"  Schemas: {n_schemas}")


if __name__ == "__main__":
    main()
