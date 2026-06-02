"""Tests for local_llm workflow phase wiring (#835, A-10).

Validates:
- local_llm phase exists in standard and full workflows
- Phase is optional (graceful degradation when endpoint absent)
- Phase depends_on extract
- Phase capability matches registry service capability
- Registry can find service for local_llm capability
- Phase is skipped when invoke returns skipped status
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestLocalLLMWorkflowPhaseStandard:
    """Validate local_llm phase in standard workflow."""

    def test_standard_workflow_has_local_llm_phase(self):
        """Standard workflow includes local_llm phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "local_llm" in phase_names, (
            f"local_llm phase missing from standard workflow. "
            f"Available: {phase_names}"
        )

    def test_standard_local_llm_is_optional(self):
        """local_llm phase is optional in standard workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase = next(p for p in wf.phases if p.name == "local_llm")
        assert phase.optional is True, "local_llm phase should be optional"

    def test_standard_local_llm_depends_on_extract(self):
        """local_llm phase depends on extract in standard workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase = next(p for p in wf.phases if p.name == "local_llm")
        assert "extract" in phase.depends_on, (
            f"local_llm should depend on extract, got: {phase.depends_on}"
        )

    def test_standard_local_llm_capability(self):
        """local_llm phase uses 'local_llm' capability."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase = next(p for p in wf.phases if p.name == "local_llm")
        assert phase.capability == "local_llm"


class TestLocalLLMWorkflowPhaseFull:
    """Validate local_llm phase in full workflow."""

    def test_full_workflow_has_local_llm_phase(self):
        """Full workflow includes local_llm phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "local_llm" in phase_names

    def test_full_local_llm_is_optional(self):
        """local_llm phase is optional in full workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase = next(p for p in wf.phases if p.name == "local_llm")
        assert phase.optional is True

    def test_full_local_llm_depends_on_extract(self):
        """local_llm phase depends on extract in full workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase = next(p for p in wf.phases if p.name == "local_llm")
        assert "extract" in phase.depends_on


class TestLocalLLMRegistryWiring:
    """Verify local_llm_service is discoverable via registry."""

    def test_registry_finds_local_llm_service(self):
        """local_llm_service should be found for 'local_llm' capability."""
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=True)
        services = registry.find_services_for_capability("local_llm")
        names = [s.name for s in services]
        assert "local_llm_service" in names, (
            f"local_llm_service not found for local_llm capability. "
            f"Available: {names}"
        )

    def test_registry_finds_chat_completion(self):
        """local_llm_service should provide chat_completion capability."""
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=True)
        services = registry.find_services_for_capability("chat_completion")
        names = [s.name for s in services]
        assert "local_llm_service" in names

    def test_local_llm_service_has_invoke(self):
        """local_llm_service registration should have an invoke callable."""
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=True)
        services = registry.find_services_for_capability("local_llm")
        llm_service = next((s for s in services if s.name == "local_llm_service"), None)
        assert llm_service is not None
        assert llm_service.invoke is not None, (
            "local_llm_service should have an invoke callable"
        )

    async def test_invoke_skips_when_endpoint_unavailable(self):
        """Invoke callable returns skipped status when endpoint is unavailable."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=False)

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test input", {})

        assert result["status"] == "skipped: endpoint_unavailable"
        assert result.get("response") is None

    async def test_invoke_works_with_state_object(self):
        """Invoke callable writes to state when state object is available."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("test text")

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=False)

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test input", {"_state_object": state})

        assert len(state.local_llm_results) == 1
        assert state.local_llm_results[0]["status"] == "skipped: endpoint_unavailable"
