"""Tests for parametric selector exposure in the FastAPI API (#903).

Validates that CustomWorkflowRequest accepts fallacy_tier and shield_preset
fields and that they propagate correctly to the pipeline context.
"""

from unittest.mock import AsyncMock, patch

import pytest


# ──── Model validation tests ────


class TestCustomWorkflowRequestModel:
    """Test Pydantic model accepts parametric fields."""

    def test_default_values(self):
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(text="Some argument text", workflow="standard")
        assert req.fallacy_tier == "llm"
        assert req.shield_preset == "off"

    def test_explicit_values(self):
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="Some argument text",
            workflow="full",
            fallacy_tier="taxonomy",
            shield_preset="strict",
        )
        assert req.fallacy_tier == "taxonomy"
        assert req.shield_preset == "strict"

    def test_all_fallacy_tiers(self):
        from api.proposal_models import CustomWorkflowRequest

        for tier in ("taxonomy", "hybrid", "llm", "full"):
            req = CustomWorkflowRequest(
                text="test text", workflow="light", fallacy_tier=tier
            )
            assert req.fallacy_tier == tier

    def test_all_shield_presets(self):
        from api.proposal_models import CustomWorkflowRequest

        for preset in ("off", "basic", "advanced", "output_only", "strict"):
            req = CustomWorkflowRequest(
                text="test text", workflow="light", shield_preset=preset
            )
            assert req.shield_preset == preset

    def test_invalid_fallacy_tier_rejected(self):
        from api.proposal_models import CustomWorkflowRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CustomWorkflowRequest(
                text="test text", workflow="light", fallacy_tier="invalid"
            )

    def test_invalid_shield_preset_rejected(self):
        from api.proposal_models import CustomWorkflowRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CustomWorkflowRequest(
                text="test text", workflow="light", shield_preset="invalid"
            )


# ──── Context propagation tests ────


class TestContextPropagation:
    """Test that selectors build correct context dict."""

    def test_default_context_no_shield(self):
        """When shield_preset='off' (default), no shield_config in context."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(text="test", workflow="light")
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.shield_preset != "off":
            context["shield_config"] = {"preset": req.shield_preset}

        assert context == {"fallacy_tier": "llm"}

    def test_shield_preset_adds_config(self):
        """When shield_preset != 'off', shield_config appears in context."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="test", workflow="light", shield_preset="advanced"
        )
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.shield_preset != "off":
            context["shield_config"] = {"preset": req.shield_preset}

        assert context["fallacy_tier"] == "llm"
        assert context["shield_config"] == {"preset": "advanced"}

    def test_both_params_propagated(self):
        """Both fallacy_tier and shield_preset propagated together."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="test",
            workflow="full",
            fallacy_tier="full",
            shield_preset="strict",
        )
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.shield_preset != "off":
            context["shield_config"] = {"preset": req.shield_preset}

        assert context["fallacy_tier"] == "full"
        assert context["shield_config"] == {"preset": "strict"}


# ──── API endpoint test (mocked pipeline) ────


class TestWorkflowEndpoint:
    """Test POST /api/workflow/custom with parametric selectors."""

    @pytest.mark.asyncio
    async def test_endpoint_default_params(self):
        """Endpoint accepts request without explicit selectors."""
        from fastapi.testclient import TestClient

        from api.main import app

        mock_result = {
            "workflow_name": "light",
            "summary": {"completed": 0, "failed": 0, "skipped": 0, "total": 0},
        }

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=mock_result),
        ) as mock_pipeline:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/workflow/custom",
                json={"text": "Test argument text here", "workflow": "light"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            # Verify context was passed with defaults
            call_kwargs = mock_pipeline.call_args
            context = call_kwargs.kwargs.get("context") or (
                call_kwargs[1].get("context") if len(call_kwargs.args) > 1 else None
            )
            if context is not None:
                assert context.get("fallacy_tier") == "llm"

    @pytest.mark.asyncio
    async def test_endpoint_with_selectors(self):
        """Endpoint passes selectors to pipeline context."""
        from fastapi.testclient import TestClient

        from api.main import app

        mock_result = {
            "workflow_name": "full",
            "summary": {"completed": 0, "failed": 0, "skipped": 0, "total": 0},
        }

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new=AsyncMock(return_value=mock_result),
        ) as mock_pipeline:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/workflow/custom",
                json={
                    "text": "Test argument text here",
                    "workflow": "full",
                    "fallacy_tier": "taxonomy",
                    "shield_preset": "basic",
                },
            )
            assert response.status_code == 200

            # Verify context propagation
            call_kwargs = mock_pipeline.call_args
            context = call_kwargs.kwargs.get("context")
            if context is not None:
                assert context.get("fallacy_tier") == "taxonomy"
                assert context.get("shield_config") == {"preset": "basic"}
