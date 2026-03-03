# -*- coding: utf-8 -*-
"""
Tests for TextAnalysisRouter — intelligent plugin/agent routing.

Covers: LLM-based routing (mocked), heuristic fallback, workflow building,
integration with run_unified_analysis(workflow_name="auto").
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.orchestration.router import (
    TextAnalysisRouter,
    RoutingResult,
    KNOWN_CAPABILITIES,
    CAPABILITY_DESCRIPTIONS,
    ROUTING_SYSTEM_PROMPT,
    LLM_TEXT_LIMIT,
)
from argumentation_analysis.orchestration.workflow_dsl import WorkflowDefinition


# ============================================================
# Helpers
# ============================================================


def _mock_openai_response(content: str):
    """Build a mock OpenAI ChatCompletion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_router(api_key="sk-test-key", model="gpt-5-mini"):
    """Create a TextAnalysisRouter with controlled env."""
    router = TextAnalysisRouter()
    router._api_key = api_key
    router._model = model
    return router


# ============================================================
# LLM-based routing
# ============================================================


class TestLLMRouting:
    @pytest.mark.asyncio
    async def test_llm_returns_valid_json(self):
        """LLM returns valid JSON → correct capabilities selected."""
        router = _make_router()
        llm_response = json.dumps({
            "capabilities": ["argument_quality", "counter_argument_generation"],
            "workflow_complexity": "standard",
        })
        mock_response = _mock_openai_response(llm_response)

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = client_instance

            workflow = await router.analyze_and_route_async("Test text for analysis.")

        assert isinstance(workflow, WorkflowDefinition)
        phase_names = [p.name for p in workflow.phases]
        assert "quality" in phase_names
        assert "counter" in phase_names

    @pytest.mark.asyncio
    async def test_llm_unknown_capabilities_filtered(self):
        """LLM returns unknown capabilities → filtered out."""
        router = _make_router()
        llm_response = json.dumps({
            "capabilities": ["argument_quality", "unknown_cap", "magic_analysis"],
            "workflow_complexity": "light",
        })
        mock_response = _mock_openai_response(llm_response)

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = client_instance

            workflow = await router.analyze_and_route_async("Test text.")

        phase_caps = [p.capability for p in workflow.phases]
        assert "unknown_cap" not in phase_caps
        assert "magic_analysis" not in phase_caps
        assert "argument_quality" in phase_caps

    @pytest.mark.asyncio
    async def test_llm_empty_capabilities_gives_quality_only(self):
        """LLM returns empty list → quality-only workflow."""
        router = _make_router()
        llm_response = json.dumps({
            "capabilities": [],
            "workflow_complexity": "light",
        })
        mock_response = _mock_openai_response(llm_response)

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = client_instance

            workflow = await router.analyze_and_route_async("Short text.")

        # argument_quality always ensured
        assert len(workflow.phases) >= 1
        assert workflow.phases[0].capability == "argument_quality"

    @pytest.mark.asyncio
    async def test_llm_invalid_json_falls_back_to_heuristics(self):
        """LLM response not valid JSON → falls back to heuristics."""
        router = _make_router()
        mock_response = _mock_openai_response("I think you should use quality analysis")

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = client_instance

            workflow = await router.analyze_and_route_async("Test text for analysis.")

        # Should still produce a valid workflow (via heuristic fallback)
        assert isinstance(workflow, WorkflowDefinition)
        assert len(workflow.phases) >= 1

    @pytest.mark.asyncio
    async def test_llm_exception_falls_back_to_heuristics(self):
        """LLM call raises exception → falls back to heuristics."""
        router = _make_router()

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(
                side_effect=RuntimeError("API down")
            )
            MockClient.return_value = client_instance

            workflow = await router.analyze_and_route_async(
                "Le vaccin est efficace car les études le montrent."
            )

        assert isinstance(workflow, WorkflowDefinition)
        assert len(workflow.phases) >= 1

    @pytest.mark.asyncio
    async def test_llm_routing_method_is_llm(self):
        """LLM routing sets routing_method='llm' in RoutingResult."""
        router = _make_router()
        llm_response = json.dumps({
            "capabilities": ["argument_quality", "adversarial_debate"],
            "workflow_complexity": "standard",
        })
        mock_response = _mock_openai_response(llm_response)

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = client_instance

            result = await router._route_with_llm("Test text.", KNOWN_CAPABILITIES)

        assert result.routing_method == "llm"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_llm_text_truncated(self):
        """Text is truncated to LLM_TEXT_LIMIT chars for the LLM call."""
        router = _make_router()
        long_text = "A" * 5000
        llm_response = json.dumps({
            "capabilities": ["argument_quality"],
            "workflow_complexity": "full",
        })
        mock_response = _mock_openai_response(llm_response)
        captured_messages = []

        async def capture_create(**kwargs):
            captured_messages.append(kwargs.get("messages", []))
            return mock_response

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(side_effect=capture_create)
            MockClient.return_value = client_instance

            await router.analyze_and_route_async(long_text)

        # User message should contain truncated text
        user_msg = captured_messages[0][1]["content"]
        # The text portion should be at most LLM_TEXT_LIMIT chars
        assert len(user_msg) < len(long_text)

    @pytest.mark.asyncio
    async def test_system_prompt_contains_capabilities(self):
        """System prompt includes all capability descriptions."""
        for cap in KNOWN_CAPABILITIES:
            assert cap in ROUTING_SYSTEM_PROMPT or cap in str(CAPABILITY_DESCRIPTIONS)

    @pytest.mark.asyncio
    async def test_llm_markdown_fences_stripped(self):
        """LLM wraps JSON in markdown fences → still parsed correctly."""
        router = _make_router()
        llm_response = '```json\n{"capabilities": ["argument_quality"], "workflow_complexity": "light"}\n```'
        mock_response = _mock_openai_response(llm_response)

        with patch("openai.AsyncOpenAI") as MockClient:
            client_instance = AsyncMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = client_instance

            workflow = await router.analyze_and_route_async("Test text.")

        assert isinstance(workflow, WorkflowDefinition)
        assert workflow.phases[0].capability == "argument_quality"


# ============================================================
# Heuristic fallback
# ============================================================


class TestHeuristicFallback:
    def test_no_api_key_uses_heuristics(self):
        """No API key → heuristic routing directly."""
        router = _make_router(api_key=None)
        result = router._route_with_heuristics("Simple test text.", KNOWN_CAPABILITIES)
        assert result.routing_method == "heuristic"
        assert result.confidence == 0.5

    def test_short_text_light_complexity(self):
        """Short text (<50 words) → light complexity."""
        router = _make_router(api_key=None)
        result = router._route_with_heuristics("Bonjour.", KNOWN_CAPABILITIES)
        assert result.workflow_complexity == "light"

    def test_medium_text_standard_complexity(self):
        """Medium text (50-300 words) → standard complexity."""
        router = _make_router(api_key=None)
        text = " ".join(["argument"] * 100)
        result = router._route_with_heuristics(text, KNOWN_CAPABILITIES)
        assert result.workflow_complexity == "standard"

    def test_long_text_full_complexity(self):
        """Long text (>300 words) → full complexity + belief_maintenance."""
        router = _make_router(api_key=None)
        text = " ".join(["argument"] * 400)
        result = router._route_with_heuristics(text, KNOWN_CAPABILITIES)
        assert result.workflow_complexity == "full"
        assert "belief_maintenance" in result.selected_capabilities

    def test_french_text_activates_neural_fallacy(self):
        """French text with accents → neural_fallacy_detection included."""
        router = _make_router(api_key=None)
        text = "Les études montrent que la réalité économique est différente de ce que prétendent les médias."
        result = router._route_with_heuristics(text, KNOWN_CAPABILITIES)
        assert "neural_fallacy_detection" in result.selected_capabilities

    def test_governance_keywords_activate_governance(self):
        """Governance keywords → governance_simulation included."""
        router = _make_router(api_key=None)
        text = "Le vote par consensus des membres de l'assemblée a montré une majorité claire."
        result = router._route_with_heuristics(text, KNOWN_CAPABILITIES)
        assert "governance_simulation" in result.selected_capabilities

    def test_debate_markers_activate_debate(self):
        """Debate markers → adversarial_debate included."""
        router = _make_router(api_key=None)
        text = "Cependant, au contraire de ce que certains affirment, les données montrent le contraire. En revanche, d'autres experts réfutent cette thèse."
        result = router._route_with_heuristics(text, KNOWN_CAPABILITIES)
        assert "adversarial_debate" in result.selected_capabilities

    def test_minimal_text_quality_only(self):
        """Very short text → only argument_quality (and maybe counter)."""
        router = _make_router(api_key=None)
        result = router._route_with_heuristics("Hi.", KNOWN_CAPABILITIES)
        assert "argument_quality" in result.selected_capabilities

    def test_very_long_text_activates_indexing(self):
        """Very long text (>500 words) → semantic_indexing activated."""
        router = _make_router(api_key=None)
        text = " ".join(["word"] * 600)
        result = router._route_with_heuristics(text, KNOWN_CAPABILITIES)
        assert "semantic_indexing" in result.selected_capabilities

    @pytest.mark.asyncio
    async def test_no_api_key_async_uses_heuristics(self):
        """Async routing without API key uses heuristics directly."""
        router = _make_router(api_key=None)
        workflow = await router.analyze_and_route_async("Simple text.")
        assert isinstance(workflow, WorkflowDefinition)
        assert len(workflow.phases) >= 1


# ============================================================
# Workflow building
# ============================================================


class TestWorkflowBuilding:
    def test_quality_only_workflow(self):
        """Single capability → quality-only workflow."""
        router = _make_router()
        result = RoutingResult(
            selected_capabilities=["argument_quality"],
            workflow_complexity="light",
        )
        workflow = router._build_workflow(result)
        assert len(workflow.phases) == 1
        assert workflow.phases[0].capability == "argument_quality"

    def test_counter_depends_on_quality(self):
        """Counter-argument phase depends on quality."""
        router = _make_router()
        result = RoutingResult(
            selected_capabilities=["argument_quality", "counter_argument_generation"],
            workflow_complexity="standard",
        )
        workflow = router._build_workflow(result)
        counter_phase = next(p for p in workflow.phases if p.name == "counter")
        assert "quality" in counter_phase.depends_on

    def test_debate_depends_on_counter_when_present(self):
        """Debate depends on counter when counter is present."""
        router = _make_router()
        result = RoutingResult(
            selected_capabilities=[
                "argument_quality",
                "counter_argument_generation",
                "adversarial_debate",
            ],
            workflow_complexity="standard",
        )
        workflow = router._build_workflow(result)
        debate_phase = next(p for p in workflow.phases if p.name == "debate")
        assert "counter" in debate_phase.depends_on

    def test_debate_depends_on_quality_when_no_counter(self):
        """Debate depends on quality when counter not present."""
        router = _make_router()
        result = RoutingResult(
            selected_capabilities=["argument_quality", "adversarial_debate"],
            workflow_complexity="standard",
        )
        workflow = router._build_workflow(result)
        debate_phase = next(p for p in workflow.phases if p.name == "debate")
        assert "quality" in debate_phase.depends_on

    def test_governance_always_depends_on_quality(self):
        """Governance always depends on quality (not counter)."""
        router = _make_router()
        result = RoutingResult(
            selected_capabilities=[
                "argument_quality",
                "counter_argument_generation",
                "governance_simulation",
            ],
            workflow_complexity="standard",
        )
        workflow = router._build_workflow(result)
        gov_phase = next(p for p in workflow.phases if p.name == "governance")
        assert "quality" in gov_phase.depends_on

    def test_all_capabilities_builds_full_workflow(self):
        """All capabilities → maximal workflow with correct structure."""
        router = _make_router()
        result = RoutingResult(
            selected_capabilities=list(KNOWN_CAPABILITIES),
            workflow_complexity="full",
        )
        workflow = router._build_workflow(result)
        phase_names = {p.name for p in workflow.phases}
        assert "quality" in phase_names
        assert "counter" in phase_names
        assert "debate" in phase_names
        assert "governance" in phase_names
        assert "jtms" in phase_names
        assert "neural_fallacy" in phase_names
        assert len(workflow.phases) >= 7

    def test_workflow_name_includes_complexity(self):
        """Workflow name reflects the routing complexity."""
        router = _make_router()
        for complexity in ("light", "standard", "full"):
            result = RoutingResult(
                selected_capabilities=["argument_quality"],
                workflow_complexity=complexity,
            )
            workflow = router._build_workflow(result)
            assert complexity in workflow.name


# ============================================================
# Capability discovery
# ============================================================


class TestCapabilityDiscovery:
    def test_no_registry_returns_all_known(self):
        """No registry → all known capabilities returned."""
        router = _make_router()
        caps = router._get_available_capabilities(None)
        assert set(caps) == set(KNOWN_CAPABILITIES)

    def test_registry_filters_to_available(self):
        """Registry with limited providers → only those returned."""
        router = _make_router()
        registry = MagicMock()

        def mock_find(cap):
            if cap in ("argument_quality", "counter_argument_generation"):
                return [MagicMock()]
            return []

        registry.find_for_capability = MagicMock(side_effect=mock_find)

        caps = router._get_available_capabilities(registry)
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        assert "adversarial_debate" not in caps

    def test_argument_quality_always_included(self):
        """argument_quality is always in available caps even if not in registry."""
        router = _make_router()
        registry = MagicMock()
        registry.find_for_capability = MagicMock(return_value=[])

        caps = router._get_available_capabilities(registry)
        assert "argument_quality" in caps


# ============================================================
# Integration with run_unified_analysis
# ============================================================


class TestRouterIntegration:
    @pytest.mark.asyncio
    async def test_auto_workflow_name_works(self):
        """workflow_name='auto' in run_unified_analysis() uses the router."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)

        # Mock the LLM call in the router
        llm_response = json.dumps({
            "capabilities": ["argument_quality", "counter_argument_generation"],
            "workflow_complexity": "light",
        })
        mock_response = _mock_openai_response(llm_response)

        with patch("openai.AsyncOpenAI") as MockClient:
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
                client_instance = AsyncMock()
                client_instance.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )
                MockClient.return_value = client_instance

                result = await run_unified_analysis(
                    "Les vaccins sont efficaces.",
                    workflow_name="auto",
                    registry=registry,
                    create_state=False,
                )

        assert "auto" in result["workflow_name"]
        assert "phases" in result

    @pytest.mark.asyncio
    async def test_auto_falls_back_to_standard_on_failure(self):
        """Auto-routing falls back to standard workflow on total failure."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)

        with patch(
            "argumentation_analysis.orchestration.router.TextAnalysisRouter"
        ) as MockRouter:
            instance = MagicMock()
            instance.analyze_and_route_async = AsyncMock(
                side_effect=RuntimeError("Router crashed")
            )
            MockRouter.return_value = instance

            result = await run_unified_analysis(
                "Test text.",
                workflow_name="auto",
                registry=registry,
                create_state=False,
            )

        # Falls back to standard
        assert result["workflow_name"] == "standard_analysis"

    @pytest.mark.asyncio
    async def test_existing_workflow_names_unchanged(self):
        """Existing workflow names ('light', 'standard', 'full') still work."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)

        for name in ("light", "standard", "full"):
            result = await run_unified_analysis(
                "Test text.",
                workflow_name=name,
                registry=registry,
                create_state=False,
            )
            assert "phases" in result


# ============================================================
# RoutingResult dataclass
# ============================================================


class TestRoutingResult:
    def test_default_values(self):
        """RoutingResult has sensible defaults."""
        result = RoutingResult(selected_capabilities=["argument_quality"])
        assert result.workflow_complexity == "standard"
        assert result.routing_method == "heuristic"
        assert result.confidence == 0.5

    def test_custom_values(self):
        """RoutingResult stores custom values correctly."""
        result = RoutingResult(
            selected_capabilities=["argument_quality", "adversarial_debate"],
            workflow_complexity="full",
            routing_method="llm",
            confidence=0.95,
        )
        assert len(result.selected_capabilities) == 2
        assert result.workflow_complexity == "full"
        assert result.routing_method == "llm"
        assert result.confidence == 0.95


# ============================================================
# Constants validation
# ============================================================


class TestConstants:
    def test_all_capabilities_have_descriptions(self):
        """Every known capability has a description."""
        for cap in KNOWN_CAPABILITIES:
            assert cap in CAPABILITY_DESCRIPTIONS
            assert len(CAPABILITY_DESCRIPTIONS[cap]) > 10

    def test_routing_prompt_is_well_formed(self):
        """Routing system prompt contains placeholder and JSON format instruction."""
        assert "{capability_list}" in ROUTING_SYSTEM_PROMPT
        assert "JSON" in ROUTING_SYSTEM_PROMPT

    def test_llm_text_limit_reasonable(self):
        """LLM text limit is reasonable (1000-5000 chars)."""
        assert 1000 <= LLM_TEXT_LIMIT <= 5000
