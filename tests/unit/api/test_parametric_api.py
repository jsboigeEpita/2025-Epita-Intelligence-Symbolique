"""Tests for parametric selector exposure in the FastAPI API (#903, #910).

Validates that CustomWorkflowRequest accepts parametric fields
(fallacy_tier, shield_preset, vote_method, consensus_threshold)
and that they propagate correctly to the pipeline context with the
EXACT keys consumed by invoke_callables.py.
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
        assert req.vote_method == "copeland"
        assert req.consensus_threshold == 0.7

    def test_explicit_values(self):
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="Some argument text",
            workflow="full",
            fallacy_tier="taxonomy",
            shield_preset="strict",
            vote_method="schulze",
            consensus_threshold=0.5,
        )
        assert req.fallacy_tier == "taxonomy"
        assert req.shield_preset == "strict"
        assert req.vote_method == "schulze"
        assert req.consensus_threshold == 0.5

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

    def test_all_vote_methods(self):
        from api.proposal_models import CustomWorkflowRequest

        for method in ("copeland", "approval", "stv", "schulze", "kemeny_young"):
            req = CustomWorkflowRequest(
                text="test text", workflow="light", vote_method=method
            )
            assert req.vote_method == method

    def test_consensus_threshold_bounds(self):
        from api.proposal_models import CustomWorkflowRequest

        for val in (0.0, 0.3, 0.5, 0.7, 1.0):
            req = CustomWorkflowRequest(
                text="test text", workflow="light", consensus_threshold=val
            )
            assert req.consensus_threshold == val

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

    def test_invalid_vote_method_rejected(self):
        from api.proposal_models import CustomWorkflowRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CustomWorkflowRequest(
                text="test text", workflow="light", vote_method="borda"
            )

    def test_invalid_consensus_threshold_rejected(self):
        from api.proposal_models import CustomWorkflowRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CustomWorkflowRequest(
                text="test text", workflow="light", consensus_threshold=1.5
            )

    def test_consensus_threshold_negative_rejected(self):
        from api.proposal_models import CustomWorkflowRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CustomWorkflowRequest(
                text="test text", workflow="light", consensus_threshold=-0.1
            )


# ──── Context propagation tests ────


class TestContextPropagation:
    """Test that selectors build correct context dict."""

    def test_default_context_no_overrides(self):
        """Defaults produce minimal context (only fallacy_tier)."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(text="test", workflow="light")
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.shield_preset != "off":
            context["shield_config"] = {"preset": req.shield_preset}
        if req.vote_method != "copeland":
            context["vote_method"] = req.vote_method
        if req.consensus_threshold != 0.7:
            context["consensus_threshold"] = req.consensus_threshold

        assert context == {"fallacy_tier": "llm"}

    def test_vote_method_propagated(self):
        """Non-default vote_method appears in context."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="test", workflow="light", vote_method="schulze"
        )
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.vote_method != "copeland":
            context["vote_method"] = req.vote_method
        if req.consensus_threshold != 0.7:
            context["consensus_threshold"] = req.consensus_threshold

        assert context["vote_method"] == "schulze"

    def test_consensus_threshold_propagated(self):
        """Non-default consensus_threshold appears in context."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="test", workflow="light", consensus_threshold=0.5
        )
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.vote_method != "copeland":
            context["vote_method"] = req.vote_method
        if req.consensus_threshold != 0.7:
            context["consensus_threshold"] = req.consensus_threshold

        assert context["consensus_threshold"] == 0.5

    def test_all_selectors_propagated(self):
        """All selectors propagated together."""
        from api.proposal_models import CustomWorkflowRequest

        req = CustomWorkflowRequest(
            text="test",
            workflow="full",
            fallacy_tier="full",
            shield_preset="strict",
            vote_method="kemeny_young",
            consensus_threshold=0.3,
        )
        context = {}
        context["fallacy_tier"] = req.fallacy_tier
        if req.shield_preset != "off":
            context["shield_config"] = {"preset": req.shield_preset}
        if req.vote_method != "copeland":
            context["vote_method"] = req.vote_method
        if req.consensus_threshold != 0.7:
            context["consensus_threshold"] = req.consensus_threshold

        assert context["fallacy_tier"] == "full"
        assert context["shield_config"] == {"preset": "strict"}
        assert context["vote_method"] == "kemeny_young"
        assert context["consensus_threshold"] == 0.3


# ──── API endpoint tests (mocked pipeline) ────


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
    async def test_endpoint_with_fallacy_shield_selectors(self):
        """Endpoint passes fallacy_tier + shield_preset to pipeline context."""
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

    @pytest.mark.asyncio
    async def test_endpoint_vote_method_consumer(self):
        """CONSUMPTION TEST: vote_method=schulze reaches pipeline context.

        Consumer: invoke_callables.py:1378 reads context.get("vote_method", "copeland").
        This test proves the key name is EXACTLY what the consumer expects.
        """
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
                    "vote_method": "schulze",
                },
            )
            assert response.status_code == 200

            # Verify EXACT key consumed by invoke_callables.py:1378
            call_kwargs = mock_pipeline.call_args
            context = call_kwargs.kwargs.get("context")
            assert context is not None, "Pipeline context must be passed"
            assert context.get("vote_method") == "schulze"

    @pytest.mark.asyncio
    async def test_endpoint_consensus_threshold_consumer(self):
        """CONSUMPTION TEST: consensus_threshold=0.5 reaches pipeline context.

        Consumer: invoke_callables.py:1529 reads context.get("consensus_threshold", 0.7).
        This test proves the key name is EXACTLY what the consumer expects.
        """
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
                    "consensus_threshold": 0.5,
                },
            )
            assert response.status_code == 200

            # Verify EXACT key consumed by invoke_callables.py:1529
            call_kwargs = mock_pipeline.call_args
            context = call_kwargs.kwargs.get("context")
            assert context is not None, "Pipeline context must be passed"
            assert context.get("consensus_threshold") == 0.5

    @pytest.mark.asyncio
    async def test_endpoint_all_selectors_consumer(self):
        """CONSUMPTION TEST: all selectors reach pipeline context together."""
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
                    "shield_preset": "advanced",
                    "vote_method": "kemeny_young",
                    "consensus_threshold": 0.3,
                },
            )
            assert response.status_code == 200

            # Verify ALL keys reach the pipeline context with exact names
            call_kwargs = mock_pipeline.call_args
            context = call_kwargs.kwargs.get("context")
            assert context is not None
            assert context["fallacy_tier"] == "taxonomy"
            assert context["shield_config"] == {"preset": "advanced"}
            assert context["vote_method"] == "kemeny_young"
            assert context["consensus_threshold"] == 0.3
