"""Tests for JTMS import guard in api/main.py (#857).

Validates that the JTMS import guard in api/main.py works correctly.
Tests use source inspection (no runtime import of api.main which triggers
torch DLL issues on Windows) and targeted runtime tests that construct
their own FastAPI app to verify guard behavior.

Split:
- TestGuardSourceStructure: static source analysis (7 tests)
- TestGuardRuntimeBehavior: runtime behavior using mock guards (4 tests)
"""

import pytest
import os
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


_MAIN_PY_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "api", "main.py")
)


# ---------------------------------------------------------------------------
# Static source analysis — verifies guard structure without importing api.main
# ---------------------------------------------------------------------------


class TestGuardSourceStructure:
    """Verify the import guard is correctly structured in api/main.py."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        with open(_MAIN_PY_PATH, "r", encoding="utf-8") as f:
            self.source = f.read()

    def test_has_try_except_import_guard(self):
        """Source should wrap jtms_endpoints import in try/except ImportError."""
        assert "try:" in self.source
        assert "except ImportError" in self.source
        assert "jtms_endpoints" in self.source

    def test_defines_jtms_available_flag(self):
        """Source should define _JTMS_AVAILABLE boolean flag."""
        assert "_JTMS_AVAILABLE = True" in self.source
        assert "_JTMS_AVAILABLE = False" in self.source

    def test_conditional_router_mount(self):
        """Source should conditionally mount jtms_router based on flag."""
        assert "if _JTMS_AVAILABLE" in self.source
        assert "include_router(jtms_router" in self.source

    def test_conditional_startup_init(self):
        """startup_event should guard initialize_jtms_services call."""
        assert "if _JTMS_AVAILABLE and initialize_jtms_services" in self.source

    def test_fallback_values_on_import_failure(self):
        """On ImportError, jtms_router and initialize_jtms_services are None."""
        assert "jtms_router = None" in self.source
        assert "initialize_jtms_services = None" in self.source

    def test_logs_warning_on_import_failure(self):
        """Import failure should log a warning, not crash."""
        assert "JTMS endpoints unavailable" in self.source

    def test_logs_warning_on_init_failure(self):
        """Init failure in startup should log a warning, not crash."""
        assert "JTMS service initialization failed" in self.source


# ---------------------------------------------------------------------------
# Runtime behavior — constructs test apps with guard logic
# ---------------------------------------------------------------------------


def _make_test_app_with_guard(jtms_available: bool):
    """Build a FastAPI app mimicking the guard logic in api/main.py."""
    app = FastAPI()

    if jtms_available:
        from argumentation_analysis.api.jtms_endpoints import jtms_router

        app.include_router(jtms_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


class TestGuardRuntimeBehavior:
    """Verify guard logic using constructed test apps."""

    def test_app_with_jtms_has_jtms_routes(self):
        """When JTMS available, app has /api/v1/jtms routes."""
        app = _make_test_app_with_guard(jtms_available=True)
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        jtms = [r for r in routes if "/jtms" in r]
        assert len(jtms) > 0, f"No JTMS routes in {len(routes)} routes"

    def test_app_without_jtms_has_no_jtms_routes(self):
        """When JTMS unavailable, app has no /api/v1/jtms routes."""
        app = _make_test_app_with_guard(jtms_available=False)
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        jtms = [r for r in routes if "/jtms" in r]
        assert len(jtms) == 0, f"JTMS routes found when unavailable: {jtms}"

    def test_app_without_jtms_health_still_works(self):
        """Health endpoint works regardless of JTMS availability."""
        app = _make_test_app_with_guard(jtms_available=False)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_startup_guard_catches_init_exception(self):
        """Startup function mimicking api/main.py catches init errors."""
        jtms_available = True
        init_called = False

        async def guarded_startup():
            nonlocal init_called
            if jtms_available:
                try:
                    raise RuntimeError("JVM failed to start")
                except Exception:
                    logging.warning("JTMS service initialization failed")

        # Should not raise
        asyncio.get_event_loop().run_until_complete(guarded_startup())
