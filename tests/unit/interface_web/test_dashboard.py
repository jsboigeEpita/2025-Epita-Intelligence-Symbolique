"""Tests for the unified dashboard frontend (#171).

Validates:
- Dashboard template exists and contains expected sections
- Starlette /dashboard route returns HTML
- FastAPI /dashboard route returns HTML
- Navigation links target all expected capabilities
- API endpoint mapping is complete
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Template file tests (no server needed)
# ---------------------------------------------------------------------------

TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "interface_web"
    / "templates"
    / "dashboard.html"
)


class TestDashboardTemplate:
    def test_template_exists(self):
        assert (
            TEMPLATE_PATH.exists()
        ), f"Dashboard template not found at {TEMPLATE_PATH}"

    def test_template_is_valid_html(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content

    def test_template_has_sidebar_navigation(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert 'class="sidebar"' in content
        assert 'data-page="overview"' in content
        assert 'data-page="quality"' in content
        assert 'data-page="debate"' in content
        assert 'data-page="governance"' in content

    def test_template_has_all_capability_pages(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        expected_pages = [
            "page-overview",
            "page-quality",
            "page-counter-args",
            "page-fallacy",
            "page-debate",
            "page-collaborative",
            "page-governance",
            "page-jtms",
            "page-full-analysis",
            "page-status",
        ]
        for page_id in expected_pages:
            assert f'id="{page_id}"' in content, f"Missing page section: {page_id}"

    def test_template_has_input_forms(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        expected_inputs = [
            "input-quality",
            "input-counter-args",
            "input-debate",
            "input-governance",
            "input-collaborative",
            "input-full-analysis",
        ]
        for input_id in expected_inputs:
            assert f'id="{input_id}"' in content, f"Missing input form: {input_id}"

    def test_template_has_result_boxes(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        expected_results = [
            "result-quality",
            "result-counter-args",
            "result-debate",
            "result-governance",
            "result-collaborative",
            "result-full-analysis",
        ]
        for result_id in expected_results:
            assert f'id="{result_id}"' in content, f"Missing result box: {result_id}"

    def test_template_has_api_endpoint_map(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "ENDPOINT_MAP" in content
        assert "/api/v1/agents/quality" in content
        assert "/api/v1/agents/counter-arguments" in content
        assert "/api/v1/agents/debate" in content
        assert "/api/v1/agents/governance" in content

    def test_template_has_bootstrap_and_fontawesome(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "bootstrap" in content.lower()
        assert "font-awesome" in content.lower() or "fontawesome" in content.lower()

    def test_template_has_jtms_links(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "/jtms/dashboard" in content
        assert "/jtms/playground" in content
        assert "/jtms/tutorial" in content

    def test_template_has_spinner_overlays(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "spinner-overlay" in content
        assert "spinner-quality" in content

    def test_capability_cards_on_overview(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        expected_cards = [
            "Argument Quality",
            "Counter-Arguments",
            "Fallacy Detection",
            "Adversarial Debate",
            "Collaborative Analysis",
            "Governance",
            "JTMS",
            "Full Pipeline",
        ]
        for card_name in expected_cards:
            assert card_name in content, f"Missing capability card: {card_name}"


# ---------------------------------------------------------------------------
# Route registration tests
# ---------------------------------------------------------------------------


class TestDashboardRouteRegistration:
    def test_starlette_app_has_dashboard_route(self):
        """Verify the Starlette app includes a /dashboard route."""
        from interface_web.app import app

        route_paths = []
        for route in app.routes:
            if hasattr(route, "path"):
                route_paths.append(route.path)
        assert "/dashboard" in route_paths

    def test_fastapi_app_has_dashboard_route(self):
        """Verify the FastAPI app includes a /dashboard route."""
        from api.main import app

        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/dashboard" in route_paths


# ---------------------------------------------------------------------------
# Dashboard endpoint behavior
# ---------------------------------------------------------------------------


class TestDashboardEndpointBehavior:
    def test_starlette_dashboard_returns_html(self):
        """Test that the Starlette dashboard endpoint returns HTML content."""
        from starlette.testclient import TestClient

        from interface_web.app import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "<!DOCTYPE html>" in response.text
        assert "Argumentation" in response.text
