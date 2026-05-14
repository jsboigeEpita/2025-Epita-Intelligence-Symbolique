"""OpenAPI contract test — detect breaking API changes via snapshot diff.

Boots the FastAPI app (with JPype mocked), fetches /openapi.json, and diffs
against the committed snapshot. Fails on removed paths or changed required
params. Additions are allowed (non-breaking).
"""
import json
import os
import sys
import unittest.mock as m

import pytest

# Mock JPype and heavy NLP libs before any API imports
_jpype_mock = m.MagicMock()
_jpype_mock.isJVMStarted = m.MagicMock(return_value=False)
sys.modules.setdefault("jpype", _jpype_mock)
sys.modules.setdefault("jpype._core", m.MagicMock())
sys.modules.setdefault("jpype.imports", m.MagicMock())
sys.modules.setdefault("jpype.types", m.MagicMock())
sys.modules.setdefault("argumentation_analysis.core.bootstrap", m.MagicMock())
sys.modules.setdefault("spacy", m.MagicMock())
sys.modules.setdefault("spacy.tokens", m.MagicMock())
sys.modules.setdefault("spacy.language", m.MagicMock())

from fastapi.testclient import TestClient

from api.factory import create_app
from api.endpoints import router as api_router, framework_router, informal_router

_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)
SNAPSHOT_PATH = os.path.join(_PROJECT_ROOT, "api", "openapi.snapshot.json")


def _build_test_client():
    app = create_app(
        title="Argumentation Analysis API",
        description="API d'analyse argumentative multi-agents.",
        version="2.0.0",
    )
    app.include_router(api_router, prefix="/api")
    app.include_router(framework_router)
    app.include_router(informal_router)

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

    return TestClient(app)


@pytest.fixture(scope="module")
def client():
    return _build_test_client()


@pytest.fixture(scope="module")
def live_spec(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def snapshot_spec():
    assert os.path.exists(SNAPSHOT_PATH), (
        f"Snapshot not found at {SNAPSHOT_PATH}. "
        "Run: python scripts/api/regenerate_openapi_snapshot.py"
    )
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestOpenAPIContract:
    """Detect breaking changes against the committed snapshot."""

    def test_no_removed_paths(self, live_spec, snapshot_spec):
        """Fail if any path present in snapshot is missing in live spec."""
        live_paths = set(live_spec.get("paths", {}).keys())
        snap_paths = set(snapshot_spec.get("paths", {}).keys())
        removed = snap_paths - live_paths
        assert not removed, f"Removed endpoints: {sorted(removed)}"

    def test_no_removed_methods(self, live_spec, snapshot_spec):
        """Fail if any HTTP method on an existing path was removed."""
        errors = []
        for path, methods in snapshot_spec.get("paths", {}).items():
            live_methods = live_spec.get("paths", {}).get(path, {})
            for method in methods:
                if method not in live_methods:
                    errors.append(f"{method.upper()} {path}")
        assert not errors, f"Removed methods: {errors}"

    def test_no_removed_required_params(self, live_spec, snapshot_spec):
        """Fail if any required parameter was removed or made optional."""
        errors = []
        for path, methods in snapshot_spec.get("paths", {}).items():
            for method, details in methods.items():
                if "parameters" not in details:
                    continue
                live_details = (
                    live_spec.get("paths", {}).get(path, {}).get(method, {})
                )
                live_params = {
                    p.get("name"): p
                    for p in live_details.get("parameters", [])
                }
                for param in details["parameters"]:
                    if not param.get("required", False):
                        continue
                    name = param.get("name")
                    if name not in live_params:
                        errors.append(f"Removed required param '{name}' in {method.upper()} {path}")
                    elif not live_params[name].get("required", False):
                        errors.append(f"Required param '{name}' became optional in {method.upper()} {path}")
        assert not errors, f"Breaking param changes: {errors}"

    def test_no_removed_request_body_fields(self, live_spec, snapshot_spec):
        """Fail if required request body fields were removed."""
        errors = []
        for path, methods in snapshot_spec.get("paths", {}).items():
            for method, details in methods.items():
                snap_body = details.get("requestBody")
                if not snap_body:
                    continue
                live_details = (
                    live_spec.get("paths", {}).get(path, {}).get(method, {})
                )
                live_body = live_details.get("requestBody")
                if not live_body:
                    errors.append(f"Removed request body in {method.upper()} {path}")
                    continue
                # Check required fields in JSON schema
                snap_content = snap_body.get("content", {})
                live_content = live_body.get("content", {})
                for content_type, ct_details in snap_content.items():
                    snap_schema = ct_details.get("schema", {})
                    live_ct = live_content.get(content_type, {})
                    live_schema = live_ct.get("schema", {})
                    snap_required = set(snap_schema.get("required", []))
                    live_required = set(live_schema.get("required", []))
                    missing = snap_required - live_required
                    if missing:
                        errors.append(
                            f"Removed required body fields {missing} in {method.upper()} {path} ({content_type})"
                        )
        assert not errors, f"Breaking body changes: {errors}"

    def test_additions_allowed(self, live_spec, snapshot_spec):
        """New paths, methods, and optional params are allowed (non-breaking)."""
        # This test always passes — it documents that additions are OK
        live_paths = set(live_spec.get("paths", {}).keys())
        snap_paths = set(snapshot_spec.get("paths", {}).keys())
        added = live_paths - snap_paths
        # Just verify we can observe additions without failing
        assert isinstance(added, set)

    def test_app_boots(self, client):
        """Smoke test: the app boots and responds to /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert "paths" in spec
        assert len(spec["paths"]) > 0
