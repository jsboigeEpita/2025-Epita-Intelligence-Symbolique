"""
Tests for the hierarchical ↔ Lego bridge (Issue #65).

Tests cover:
- RegistryBackedOperationalRegistry (discovery, invocation, task selection)
- objectives_to_workflow (conversion of strategic objectives to workflows)
- HierarchicalTurnStrategy (execution as a TurnStrategy)
- _match_capabilities helper
- Edge cases and backward compatibility

All tests mock the CapabilityRegistry — no real LLM or agent calls.
"""

import pytest
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentRegistration,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
)
from argumentation_analysis.orchestration.turn_protocol import (
    TurnResult,
    ConversationConfig,
)
from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
    HierarchicalTurnStrategy,
    RegistryBackedOperationalRegistry,
    objectives_to_workflow,
    _match_capabilities,
    _extract_confidence,
    _extract_questions,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_registry(*components):
    """Build a CapabilityRegistry with pre-registered components."""
    registry = CapabilityRegistry()
    for comp in components:
        registry.register(
            name=comp["name"],
            component_type=comp.get("type", ComponentType.AGENT),
            capabilities=comp.get("capabilities", []),
            invoke=comp.get("invoke"),
            metadata=comp.get("metadata", {}),
        )
    return registry


def make_component(
    name: str,
    capabilities: List[str],
    invoke=None,
    component_type=ComponentType.AGENT,
):
    """Shorthand for component dict."""
    return {
        "name": name,
        "type": component_type,
        "capabilities": capabilities,
        "invoke": invoke,
    }


# ---------------------------------------------------------------------------
# TestRegistryBackedOperationalRegistry
# ---------------------------------------------------------------------------


class TestRegistryBackedOperationalRegistry:
    """Tests for RegistryBackedOperationalRegistry."""

    def test_find_for_capability_returns_provider(self):
        registry = make_registry(
            make_component("agent_a", ["cap_x", "cap_y"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        result = op.find_for_capability("cap_x")
        assert result is not None
        assert result.name == "agent_a"

    def test_find_for_capability_returns_none_when_missing(self):
        registry = make_registry(
            make_component("agent_a", ["cap_x"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        assert op.find_for_capability("cap_z") is None

    def test_find_all_for_capability(self):
        registry = make_registry(
            make_component("agent_a", ["cap_x"]),
            make_component("agent_b", ["cap_x", "cap_y"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        results = op.find_all_for_capability("cap_x")
        assert len(results) == 2

    def test_get_all_capabilities(self):
        registry = make_registry(
            make_component("a", ["cap_1", "cap_2"]),
            make_component("b", ["cap_2", "cap_3"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        caps = op.get_all_capabilities()
        assert set(caps) == {"cap_1", "cap_2", "cap_3"}

    def test_has_capability(self):
        registry = make_registry(
            make_component("a", ["cap_1"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        assert op.has_capability("cap_1") is True
        assert op.has_capability("cap_missing") is False

    @pytest.mark.asyncio
    async def test_invoke_capability_success(self):
        invoke_fn = AsyncMock(return_value={"result": "ok"})
        registry = make_registry(
            make_component("a", ["cap_x"], invoke=invoke_fn),
        )
        op = RegistryBackedOperationalRegistry(registry)
        result = await op.invoke_capability("cap_x", "hello", {"key": "val"})
        assert result == {"result": "ok"}
        invoke_fn.assert_awaited_once_with("hello", {"key": "val"})

    @pytest.mark.asyncio
    async def test_invoke_capability_no_provider(self):
        registry = make_registry()
        op = RegistryBackedOperationalRegistry(registry)
        result = await op.invoke_capability("cap_missing", "text")
        assert result is None

    @pytest.mark.asyncio
    async def test_invoke_capability_no_invoke(self):
        registry = make_registry(
            make_component("a", ["cap_x"], invoke=None),
        )
        op = RegistryBackedOperationalRegistry(registry)
        result = await op.invoke_capability("cap_x", "text")
        assert result is None

    @pytest.mark.asyncio
    async def test_invoke_capability_default_context(self):
        invoke_fn = AsyncMock(return_value="ok")
        registry = make_registry(
            make_component("a", ["cap_x"], invoke=invoke_fn),
        )
        op = RegistryBackedOperationalRegistry(registry)
        await op.invoke_capability("cap_x", "text")
        # Should pass empty dict as default context
        invoke_fn.assert_awaited_once_with("text", {})


class TestRegistryBackedTaskSelection:
    """Tests for select_agent_for_task and map_agent_capabilities."""

    def test_select_agent_single_capability(self):
        registry = make_registry(
            make_component("a", ["cap_1"]),
            make_component("b", ["cap_2"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        selected = op.select_agent_for_task(["cap_1"])
        assert selected is not None
        assert selected.name == "a"

    def test_select_agent_multi_capability_scoring(self):
        registry = make_registry(
            make_component("a", ["cap_1"]),
            make_component("b", ["cap_1", "cap_2", "cap_3"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        selected = op.select_agent_for_task(["cap_1", "cap_2"])
        # b covers both capabilities, a only one
        assert selected is not None
        assert selected.name == "b"

    def test_select_agent_no_match(self):
        registry = make_registry(
            make_component("a", ["cap_1"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        assert op.select_agent_for_task(["cap_z"]) is None

    def test_select_agent_empty_capabilities(self):
        registry = make_registry(
            make_component("a", ["cap_1"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        assert op.select_agent_for_task([]) is None

    def test_map_agent_capabilities(self):
        registry = make_registry(
            make_component("fallacy_agent", ["fallacy_detection"]),
            make_component("extract_agent", ["text_extraction"]),
        )
        op = RegistryBackedOperationalRegistry(registry)
        legacy = {
            "informal_analyzer": ["fallacy_detection", "rhetorical_analysis"],
            "extract_processor": ["text_extraction"],
        }
        mapping = op.map_agent_capabilities(legacy)
        assert "informal_analyzer" in mapping
        assert len(mapping["informal_analyzer"]) == 1
        assert mapping["informal_analyzer"][0].name == "fallacy_agent"
        assert len(mapping["extract_processor"]) == 1
        assert mapping["extract_processor"][0].name == "extract_agent"


# ---------------------------------------------------------------------------
# TestObjectivesToWorkflow
# ---------------------------------------------------------------------------


class TestObjectivesToWorkflow:
    """Tests for objectives_to_workflow conversion."""

    def test_simple_objective_creates_phases(self):
        registry = make_registry(
            make_component("extract", ["fact_extraction"]),
        )
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments du texte",
                "priority": "high",
            }
        ]
        wf = objectives_to_workflow(objectives, registry)
        assert isinstance(wf, WorkflowDefinition)
        assert len(wf.phases) >= 1
        # Phase should use fact_extraction capability
        caps = [p.capability for p in wf.phases]
        assert "fact_extraction" in caps

    def test_fallacy_objective(self):
        registry = make_registry(
            make_component("fallacy", ["fallacy_detection"]),
        )
        objectives = [
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans le texte",
                "priority": "medium",
            }
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "fallacy_detection" in caps

    def test_quality_objective(self):
        registry = make_registry(
            make_component("quality", ["argument_quality"]),
        )
        objectives = [
            {
                "id": "obj-3",
                "description": "Évaluer la qualité des arguments",
                "priority": "low",
            }
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "argument_quality" in caps
        # Low priority → optional
        assert any(p.optional for p in wf.phases)

    def test_multiple_objectives_create_ordered_phases(self):
        registry = make_registry(
            make_component("extract", ["fact_extraction"]),
            make_component("fallacy", ["fallacy_detection"]),
            make_component("quality", ["argument_quality"]),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
            {"id": "o2", "description": "Détecter les sophismes", "priority": "medium"},
            {"id": "o3", "description": "Évaluer la qualité", "priority": "low"},
        ]
        wf = objectives_to_workflow(objectives, registry)
        assert len(wf.phases) >= 3
        # Phases should have dependencies forming a chain
        assert wf.phases[0].depends_on == []
        for i in range(1, len(wf.phases)):
            assert len(wf.phases[i].depends_on) > 0

    def test_unmatched_objective_becomes_optional(self):
        registry = make_registry()  # Empty registry
        objectives = [
            {"id": "obj-x", "description": "Some unknown task", "priority": "medium"}
        ]
        wf = objectives_to_workflow(objectives, registry)
        assert len(wf.phases) == 1
        assert wf.phases[0].optional is True
        assert wf.phases[0].capability.startswith("objective_")

    def test_workflow_metadata(self):
        registry = make_registry(
            make_component("a", ["fact_extraction"]),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
        ]
        wf = objectives_to_workflow(objectives, registry, workflow_name="test_wf")
        assert wf.name == "test_wf"
        assert wf.metadata.get("source") == "hierarchical_bridge"
        assert wf.metadata.get("objective_count") == 1

    def test_only_registry_available_capabilities_included(self):
        """If a keyword matches multiple capabilities but registry only has one,
        only the available one is included."""
        registry = make_registry(
            make_component("extract", ["fact_extraction"]),
            # text_extraction NOT registered
        )
        objectives = [
            {"id": "o1", "description": "Extraire les faits", "priority": "high"},
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "fact_extraction" in caps
        assert "text_extraction" not in caps


class TestMatchCapabilities:
    """Tests for _match_capabilities helper."""

    def test_identifier_keyword(self):
        registry = make_registry(
            make_component("a", ["fact_extraction"]),
            make_component("b", ["text_extraction"]),
        )
        result = _match_capabilities("identifier les arguments", registry)
        assert "fact_extraction" in result
        assert "text_extraction" in result

    def test_no_match(self):
        registry = make_registry(
            make_component("a", ["cap_z"]),
        )
        result = _match_capabilities("random text with no keywords", registry)
        assert result == []

    def test_deduplication(self):
        """Same capability shouldn't appear twice even if multiple keywords match."""
        registry = make_registry(
            make_component("a", ["fallacy_detection"]),
        )
        # Both "détecter" and "sophisme" map to fallacy_detection
        result = _match_capabilities("détecter les sophismes", registry)
        assert result.count("fallacy_detection") == 1

    def test_only_available_capabilities(self):
        """Capabilities not in registry are filtered out."""
        registry = make_registry()  # Empty
        result = _match_capabilities("identifier les arguments", registry)
        assert result == []


# ---------------------------------------------------------------------------
# TestHierarchicalTurnStrategy
# ---------------------------------------------------------------------------


class TestHierarchicalTurnStrategy:
    """Tests for HierarchicalTurnStrategy."""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        invoke_fn = AsyncMock(
            return_value={"confidence": 0.9, "analysis": "done"}
        )
        registry = make_registry(
            make_component("extract", ["fact_extraction"], invoke=invoke_fn),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
        ]
        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        context = {"turn_number": 1}
        result = await strategy.execute_turn("Analyze this text", context)

        assert isinstance(result, TurnResult)
        assert result.turn_number == 1
        assert result.confidence == 0.9
        assert result.needs_refinement is False
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_failed_phase_sets_needs_refinement(self):
        invoke_fn = AsyncMock(side_effect=Exception("LLM error"))
        registry = make_registry(
            make_component("fallacy", ["fallacy_detection"], invoke=invoke_fn),
        )
        objectives = [
            {"id": "o1", "description": "Détecter les sophismes", "priority": "high"},
        ]
        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        result = await strategy.execute_turn("text", {"turn_number": 2})

        assert result.needs_refinement is True
        assert any(
            r.status == PhaseStatus.FAILED
            for r in result.phase_results.values()
        )

    @pytest.mark.asyncio
    async def test_state_passed_to_executor(self):
        invoke_fn = AsyncMock(return_value={"result": "ok"})
        registry = make_registry(
            make_component("a", ["fact_extraction"], invoke=invoke_fn),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
        ]
        mock_state = MagicMock()
        mock_state.store_workflow_result = MagicMock()

        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        result = await strategy.execute_turn(
            "text", {"turn_number": 1}, state=mock_state
        )
        assert isinstance(result, TurnResult)

    @pytest.mark.asyncio
    async def test_multiple_objectives(self):
        call_count = 0

        async def counting_invoke(input_data, ctx):
            nonlocal call_count
            call_count += 1
            return {"confidence": 0.7}

        registry = make_registry(
            make_component("extract", ["fact_extraction"], invoke=counting_invoke),
            make_component("fallacy", ["fallacy_detection"], invoke=counting_invoke),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
            {"id": "o2", "description": "Détecter les sophismes", "priority": "medium"},
        ]
        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        result = await strategy.execute_turn("text", {"turn_number": 1})

        assert call_count >= 2
        assert len(result.phase_results) >= 2

    @pytest.mark.asyncio
    async def test_empty_objectives_produces_empty_result(self):
        registry = make_registry()
        strategy = HierarchicalTurnStrategy(
            objectives=[],
            capability_registry=registry,
        )
        result = await strategy.execute_turn("text", {"turn_number": 1})
        assert isinstance(result, TurnResult)
        assert len(result.phase_results) == 0

    @pytest.mark.asyncio
    async def test_questions_extracted(self):
        invoke_fn = AsyncMock(
            return_value={
                "user_question": "What is the source of claim X?",
                "confidence": 0.6,
            }
        )
        registry = make_registry(
            make_component("extract", ["fact_extraction"], invoke=invoke_fn),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
        ]
        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        result = await strategy.execute_turn("text", {"turn_number": 1})
        assert len(result.questions_for_user) >= 1
        assert "source" in result.questions_for_user[0].lower()


# ---------------------------------------------------------------------------
# TestConfidenceExtraction
# ---------------------------------------------------------------------------


class TestConfidenceExtraction:
    """Tests for _extract_confidence helper."""

    def test_average_confidence(self):
        results = {
            "a": PhaseResult(
                phase_name="a",
                status=PhaseStatus.COMPLETED,
                capability="cap",
                output={"confidence": 0.8},
            ),
            "b": PhaseResult(
                phase_name="b",
                status=PhaseStatus.COMPLETED,
                capability="cap",
                output={"confidence": 0.6},
            ),
        }
        assert _extract_confidence(results) == pytest.approx(0.7)

    def test_no_confidence_defaults_half(self):
        results = {
            "a": PhaseResult(
                phase_name="a",
                status=PhaseStatus.COMPLETED,
                capability="cap",
                output={"data": "no confidence"},
            ),
        }
        assert _extract_confidence(results) == 0.5

    def test_failed_phases_ignored(self):
        results = {
            "a": PhaseResult(
                phase_name="a",
                status=PhaseStatus.FAILED,
                capability="cap",
                output={"confidence": 0.1},
            ),
            "b": PhaseResult(
                phase_name="b",
                status=PhaseStatus.COMPLETED,
                capability="cap",
                output={"confidence": 0.9},
            ),
        }
        assert _extract_confidence(results) == pytest.approx(0.9)

    def test_empty_results(self):
        assert _extract_confidence({}) == 0.5


class TestQuestionExtraction:
    """Tests for _extract_questions helper."""

    def test_extracts_questions(self):
        results = {
            "a": PhaseResult(
                phase_name="a",
                status=PhaseStatus.COMPLETED,
                capability="cap",
                output={"user_question": "What about X?"},
            ),
        }
        questions = _extract_questions(results)
        assert questions == ["What about X?"]

    def test_no_questions(self):
        results = {
            "a": PhaseResult(
                phase_name="a",
                status=PhaseStatus.COMPLETED,
                capability="cap",
                output={"data": "no question"},
            ),
        }
        assert _extract_questions(results) == []


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and integration tests."""

    def test_objective_with_counter_argument_keyword(self):
        registry = make_registry(
            make_component("ca", ["counter_argument_generation"]),
        )
        objectives = [
            {
                "id": "o1",
                "description": "Générer un contre-argument",
                "priority": "high",
            },
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "counter_argument_generation" in caps

    def test_objective_with_debate_keyword(self):
        registry = make_registry(
            make_component("debate", ["debate_management"]),
        )
        objectives = [
            {"id": "o1", "description": "Organiser un débat", "priority": "medium"},
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "debate_management" in caps

    def test_objective_with_governance_keyword(self):
        registry = make_registry(
            make_component("gov", ["governance_voting"]),
        )
        objectives = [
            {
                "id": "o1",
                "description": "Évaluer par gouvernance",
                "priority": "medium",
            },
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "governance_voting" in caps

    def test_objective_with_synthesis_keyword(self):
        registry = make_registry(
            make_component("synth", ["synthesis"]),
        )
        objectives = [
            {
                "id": "o1",
                "description": "Synthétiser les résultats",
                "priority": "low",
            },
        ]
        wf = objectives_to_workflow(objectives, registry)
        caps = [p.capability for p in wf.phases]
        assert "synthesis" in caps

    @pytest.mark.asyncio
    async def test_hierarchical_strategy_with_pipeline(self):
        """Integration: HierarchicalTurnStrategy works with ConversationalPipeline."""
        from argumentation_analysis.orchestration.conversational_executor import (
            ConversationalPipeline,
        )

        invoke_fn = AsyncMock(
            return_value={"confidence": 0.95, "result": "high quality"}
        )
        registry = make_registry(
            make_component("a", ["fact_extraction"], invoke=invoke_fn),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
        ]
        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        config = ConversationConfig(max_rounds=3, confidence_threshold=0.9)
        pipeline = ConversationalPipeline(strategy, config=config)

        result = await pipeline.execute("Analyze this text")
        assert result["status"] == "high_confidence"
        assert len(result["rounds"]) == 1

    def test_workflow_phases_dependencies_form_chain(self):
        """All phases should form a linear dependency chain."""
        registry = make_registry(
            make_component("a", ["fact_extraction"]),
            make_component("b", ["fallacy_detection"]),
            make_component("c", ["argument_quality"]),
        )
        objectives = [
            {"id": "o1", "description": "Identifier les arguments", "priority": "high"},
            {"id": "o2", "description": "Détecter les sophismes", "priority": "high"},
            {"id": "o3", "description": "Évaluer la qualité", "priority": "high"},
        ]
        wf = objectives_to_workflow(objectives, registry)
        # First phase has no deps
        assert wf.phases[0].depends_on == []
        # Subsequent phases depend on previous
        for i in range(1, len(wf.phases)):
            assert len(wf.phases[i].depends_on) > 0

    @pytest.mark.asyncio
    async def test_registry_backed_concurrent_invocations(self):
        """Multiple concurrent invocations should work independently."""
        import asyncio

        call_log = []

        async def tracking_invoke(input_data, ctx):
            call_log.append(input_data)
            await asyncio.sleep(0.01)
            return {"result": input_data}

        registry = make_registry(
            make_component("a", ["cap_x"], invoke=tracking_invoke),
        )
        op = RegistryBackedOperationalRegistry(registry)

        results = await asyncio.gather(
            op.invoke_capability("cap_x", "text1"),
            op.invoke_capability("cap_x", "text2"),
            op.invoke_capability("cap_x", "text3"),
        )
        assert len(results) == 3
        assert len(call_log) == 3
