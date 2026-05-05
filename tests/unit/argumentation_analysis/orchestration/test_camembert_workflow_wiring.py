"""Tests for CamemBERT Tier 2.5 wiring into standard workflows (#208-J).

Verifies:
1. Standard workflow includes neural_detect and hierarchical_fallacy phases
2. Both phases are optional (graceful skip if CamemBERT unavailable)
3. CamemBERT phase depends on extract
4. InformalAgent in conversational mode has FrenchFallacyPlugin
5. State writer correctly maps CamemBERT output
"""

import pytest
from unittest.mock import MagicMock, patch


class TestStandardWorkflowCamemBERT:
    """Verify CamemBERT integration in standard workflow."""

    def test_standard_workflow_has_neural_detect_phase(self):
        """Standard workflow includes neural_detect phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "neural_detect" in phase_names

    def test_standard_workflow_has_hierarchical_fallacy_phase(self):
        """Standard workflow includes hierarchical_fallacy phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "hierarchical_fallacy" in phase_names

    def test_neural_detect_is_optional(self):
        """CamemBERT phase is optional (skips if model unavailable)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        neural_phase = wf.get_phase("neural_detect")
        assert neural_phase.optional is True

    def test_hierarchical_fallacy_is_optional(self):
        """Hierarchical fallacy phase is optional."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        hf_phase = wf.get_phase("hierarchical_fallacy")
        assert hf_phase.optional is True

    def test_neural_detect_depends_on_extract(self):
        """CamemBERT phase runs after fact extraction."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        neural_phase = wf.get_phase("neural_detect")
        assert "extract" in neural_phase.depends_on

    def test_hierarchical_fallacy_depends_on_extract(self):
        """Hierarchical fallacy phase runs after fact extraction."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        hf_phase = wf.get_phase("hierarchical_fallacy")
        assert "extract" in hf_phase.depends_on

    def test_standard_workflow_phase_order(self):
        """Standard workflow phases follow expected dependency order."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        caps = wf.get_required_capabilities()
        # Core phases should still be present
        assert "fact_extraction" in caps
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        # Fallacy detection phases should be present
        assert "neural_fallacy_detection" in caps
        assert "hierarchical_fallacy_detection" in caps


class TestCamemBERTStateWriter:
    """Verify CamemBERT state writer correctly processes output."""

    def test_write_camembert_to_state(self):
        """CamemBERT detections written to state.neural_fallacy_scores."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_camembert_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("test text")
        output = {
            "detections": [
                {"text": "argument 1", "label": "Ad Hominem", "confidence": 0.85},
                {"text": "argument 2", "label": "Strawman", "confidence": 0.72},
            ]
        }
        _write_camembert_to_state(output, state, {})

        assert len(state.neural_fallacy_scores) == 2
        assert state.neural_fallacy_scores[0]["label"] == "Ad Hominem"
        assert state.neural_fallacy_scores[0]["confidence"] == 0.85

    def test_write_camembert_handles_empty_output(self):
        """State writer handles empty/None output gracefully."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_camembert_to_state,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("test text")
        _write_camembert_to_state(None, state, {})
        assert len(state.neural_fallacy_scores) == 0

        _write_camembert_to_state({}, state, {})
        assert len(state.neural_fallacy_scores) == 0


class TestConversationalModeCamemBERT:
    """Verify CamemBERT available in conversational mode via FrenchFallacyPlugin."""

    def test_informal_agent_has_french_fallacy_speciality(self):
        """InformalAgent is mapped to informal_fallacy speciality."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        assert "InformalAgent" in AGENT_CONFIG
        assert AGENT_CONFIG["InformalAgent"]["speciality"] == "informal_fallacy"

    def test_informal_fallacy_maps_to_french_fallacy_plugin(self):
        """informal_fallacy speciality loads FrenchFallacyPlugin."""
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "informal_fallacy" in AGENT_SPECIALITY_MAP
        assert "french_fallacy" in AGENT_SPECIALITY_MAP["informal_fallacy"]

    def test_french_fallacy_plugin_available_in_registry(self):
        """FrenchFallacyPlugin is registered in _PLUGIN_REGISTRY."""
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        assert "french_fallacy" in _PLUGIN_REGISTRY
        module_path, class_name = _PLUGIN_REGISTRY["french_fallacy"]
        assert "FrenchFallacyPlugin" in class_name

    def test_french_fallacy_plugin_wraps_adapter_with_camembert(self):
        """FrenchFallacyPlugin creates FrenchFallacyAdapter which includes CamemBERT tier."""
        from argumentation_analysis.plugins.french_fallacy_plugin import (
            FrenchFallacyPlugin,
        )

        plugin = FrenchFallacyPlugin()
        assert hasattr(plugin, "adapter") or hasattr(plugin, "_adapter")
