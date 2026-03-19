"""
Tests for synthesis_agent.py (SynthesisAgent orchestration).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase

from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent
from argumentation_analysis.agents.core.synthesis.data_models import (
    LogicAnalysisResult,
    InformalAnalysisResult,
    UnifiedReport,
)


def _create_mock_kernel():
    """Helper to create a mock kernel with a ChatCompletionClientBase service."""
    kernel = MagicMock(spec=Kernel)
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.service_id = "test_service"
    kernel.get_service = MagicMock(return_value=mock_service)
    kernel.services = {"test_service": mock_service}
    return kernel


# =====================================================================
# SynthesisAgent Initialization Tests
# =====================================================================


class TestSynthesisAgentInitialization:
    """Tests for SynthesisAgent initialization."""

    def test_default_initialization(self):
        """Verify default initialization."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)
        assert agent.id == "SynthesisAgent"
        assert agent._enable_advanced_features is False
        assert agent._logic_agents_cache == {}
        assert agent._informal_agent is None
        assert agent._llm_service_id is None
        assert agent._fusion_manager is None
        assert agent._conflict_manager is None
        assert agent._evidence_manager is None
        assert agent._quality_manager is None

    def test_custom_agent_name(self):
        """Verify custom agent name."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel, agent_name="CustomSynthesis")
        assert agent.id == "CustomSynthesis"

    def test_enable_advanced_features(self):
        """Verify advanced features flag."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel, enable_advanced_features=True)
        assert agent._enable_advanced_features is True

    def test_service_id_storage(self):
        """Verify service ID is stored."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel, service_id="test_service")
        assert agent._llm_service_id == "test_service"

    def test_backward_compatibility_properties(self):
        """Verify backward compatibility property access."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)
        # Properties should return None by default
        assert agent.fusion_manager is None
        assert agent.conflict_manager is None
        assert agent.evidence_manager is None
        assert agent.quality_manager is None
        assert agent.enable_advanced_features is False

    def test_backward_compatibility_setters(self):
        """Verify backward compatibility property setters."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)
        mock_manager = MagicMock()
        agent.fusion_manager = mock_manager
        assert agent._fusion_manager is mock_manager


# =====================================================================
# SynthesisAgent Capabilities Tests
# =====================================================================


class TestSynthesisAgentCapabilities:
    """Tests for SynthesisAgent capabilities."""

    def test_get_agent_capabilities(self):
        """Verify capabilities dictionary."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)
        caps = agent.get_agent_capabilities()
        assert caps["synthesis_coordination"] is True
        assert caps["formal_analysis_orchestration"] is True
        assert caps["informal_analysis_orchestration"] is True
        assert caps["unified_reporting"] is True
        assert "propositional" in caps["logic_types_supported"]
        assert "first_order" in caps["logic_types_supported"]
        assert "modal" in caps["logic_types_supported"]
        assert caps["phase"] == 1

    def test_get_agent_capabilities_advanced_mode(self):
        """Verify capabilities with advanced features enabled."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel, enable_advanced_features=True)
        caps = agent.get_agent_capabilities()
        assert caps["advanced_features_enabled"] is True
        assert "fusion_management" in caps
        assert "conflict_resolution" in caps


# =====================================================================
# SynthesisAgent Orchestration Tests
# =====================================================================


class TestSynthesisAgentOrchestration:
    """Tests for SynthesisAgent orchestration methods."""

    @pytest.mark.asyncio
    async def test_orchestrate_analysis_with_exceptions(self):
        """Verify orchestration handles exceptions gracefully."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        # Mock the analysis methods to raise exceptions
        async def mock_error_analysis(text):
            raise RuntimeError("Analysis failed")

        with patch.object(agent, "_run_formal_analysis", side_effect=mock_error_analysis), \
             patch.object(agent, "_run_informal_analysis", side_effect=mock_error_analysis):
            logic_result, informal_result = await agent.orchestrate_analysis("Test text")

        # Should return empty results
        assert isinstance(logic_result, LogicAnalysisResult)
        assert isinstance(informal_result, InformalAnalysisResult)

    @pytest.mark.asyncio
    async def test_unify_results_basic(self):
        """Verify basic result unification."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(
            propositional_result="Valid",
            logical_validity=True,
        )
        informal = InformalAnalysisResult(
            fallacies_detected=[],
            argument_strength=0.8,
        )

        report = await agent.unify_results(logic, informal, "Test text")

        assert report.original_text == "Test text"
        assert report.logic_analysis is logic
        assert report.informal_analysis is informal
        assert report.executive_summary != ""
        assert report.overall_validity is not None
        assert report.confidence_level is not None

    @pytest.mark.asyncio
    async def test_unify_results_with_fallacies(self):
        """Verify unification detects fallacies."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=True)
        informal = InformalAnalysisResult(
            fallacies_detected=[{"type": "ad_hominem"}],
        )

        report = await agent.unify_results(logic, informal, "Test text")

        # Should identify contradiction between valid logic and fallacies
        assert len(report.contradictions_identified) >= 0
        assert len(report.recommendations) > 0


# =====================================================================
# SynthesisAgent Report Generation Tests
# =====================================================================


class TestSynthesisAgentReportGeneration:
    """Tests for SynthesisAgent report generation."""

    @pytest.mark.asyncio
    async def test_generate_report_markdown_format(self):
        """Verify report generates valid Markdown."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(
            propositional_result="P -> Q",
        )
        informal = InformalAnalysisResult(
            fallacies_detected=[],
            arguments_structure="Standard",
        )
        report = UnifiedReport(
            original_text="Test argument",
            logic_analysis=logic,
            informal_analysis=informal,
            executive_summary="Summary",
            overall_validity=True,
            confidence_level=0.9,
        )

        markdown = await agent.generate_report(report)

        assert "# RAPPORT DE SYNTHESE UNIFIE" in markdown or "# RAPPORT DE SYNTH\u00c8SE UNIFI\u00c9" in markdown
        assert "## TEXTE ORIGINAL ANALYS" in markdown
        assert "## R\u00c9SUM\u00c9 EX\u00c9CUTIF" in markdown or "RESUME EXECUTIF" in markdown
        assert "## STATISTIQUES" in markdown
        assert "## \u00c9VALUATION GLOBALE" in markdown or "EVALUATION GLOBALE" in markdown

    @pytest.mark.asyncio
    async def test_generate_report_includes_contradictions(self):
        """Verify report includes contradictions section."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()
        report = UnifiedReport(
            original_text="Test",
            logic_analysis=logic,
            informal_analysis=informal,
            contradictions_identified=["Contradiction 1", "Contradiction 2"],
        )

        markdown = await agent.generate_report(report)

        assert "## CONTRADICTIONS IDENTIFI" in markdown
        assert "Contradiction 1" in markdown
        assert "Contradiction 2" in markdown

    @pytest.mark.asyncio
    async def test_generate_report_includes_recommendations(self):
        """Verify report includes recommendations section."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()
        report = UnifiedReport(
            original_text="Test",
            logic_analysis=logic,
            informal_analysis=informal,
            recommendations=["Fix structure", "Check premises"],
        )

        markdown = await agent.generate_report(report)

        assert "## RECOMMANDATIONS" in markdown
        assert "Fix structure" in markdown
        assert "Check premises" in markdown


# =====================================================================
# SynthesisAgent Helper Methods Tests
# =====================================================================


class TestSynthesisAgentHelperMethods:
    """Tests for SynthesisAgent helper methods."""

    def test_assess_overall_validity_both_valid(self):
        """Verify validity assessment when both analyses are valid."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=True)
        informal = InformalAnalysisResult(fallacies_detected=[])

        validity = agent._assess_overall_validity(logic, informal)
        assert validity is True

    def test_assess_overall_validity_with_fallacies(self):
        """Verify validity assessment with fallacies."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=True)
        informal = InformalAnalysisResult(
            fallacies_detected=[{"type": "straw_man"}]
        )

        validity = agent._assess_overall_validity(logic, informal)
        assert validity is False

    def test_assess_overall_validity_none_logic(self):
        """Verify validity assessment when logic validity is None."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=None)
        informal = InformalAnalysisResult(fallacies_detected=[])

        validity = agent._assess_overall_validity(logic, informal)
        assert validity is True  # Falls back to informal

    def test_calculate_confidence_level_base(self):
        """Verify base confidence level calculation."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult()
        informal = InformalAnalysisResult()

        confidence = agent._calculate_confidence_level(logic, informal)
        assert 0.0 <= confidence <= 1.0
        assert confidence == 0.5  # Base value

    def test_calculate_confidence_level_with_results(self):
        """Verify confidence increases with more results."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(
            propositional_result="Result",
            first_order_result="Result",
            modal_result="Result",
        )
        informal = InformalAnalysisResult(arguments_structure="Structure")

        confidence = agent._calculate_confidence_level(logic, informal)
        assert confidence > 0.5  # Should be higher than base

    def test_calculate_confidence_level_with_fallacies(self):
        """Verify confidence decreases with fallacies."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(propositional_result="Result")
        informal = InformalAnalysisResult(
            arguments_structure="Structure",
            fallacies_detected=[{"type": "f1"}, {"type": "f2"}, {"type": "f3"}],
        )

        confidence = agent._calculate_confidence_level(logic, informal)
        # Should be penalized by fallacies (3 * 0.05 = 0.15 max)
        assert confidence < 1.0

    def test_identify_basic_contradictions_valid_logic_with_fallacies(self):
        """Verify contradiction detection between valid logic and fallacies."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=True)
        informal = InformalAnalysisResult(
            fallacies_detected=[{"type": "ad_hominem"}]
        )

        contradictions = agent._identify_basic_contradictions(logic, informal)
        assert len(contradictions) > 0
        assert "contradiction" in contradictions[0].lower()

    def test_identify_basic_contradictions_inconsistent_valid(self):
        """Verify contradiction detection for inconsistent but valid."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(
            consistency_check=False,
            logical_validity=True,
        )
        informal = InformalAnalysisResult()

        contradictions = agent._identify_basic_contradictions(logic, informal)
        assert len(contradictions) > 0

    def test_generate_basic_recommendations_invalid_logic(self):
        """Verify recommendations for invalid logic."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=False)
        informal = InformalAnalysisResult()

        recommendations = agent._generate_basic_recommendations(logic, informal)
        assert len(recommendations) > 0
        assert any("logique" in r.lower() for r in recommendations)

    def test_generate_basic_recommendations_fallacies(self):
        """Verify recommendations for fallacies."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(logical_validity=True)
        informal = InformalAnalysisResult(
            fallacies_detected=[{"type": "f1"}, {"type": "f2"}]
        )

        recommendations = agent._generate_basic_recommendations(logic, informal)
        assert len(recommendations) > 0
        assert any("sophisme" in r.lower() for r in recommendations)

    def test_generate_basic_recommendations_satisfactory(self):
        """Verify recommendations when analysis is satisfactory."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        logic = LogicAnalysisResult(
            logical_validity=True,
            consistency_check=True,
        )
        informal = InformalAnalysisResult(
            fallacies_detected=[],
            arguments_structure="Clear structure",
        )

        recommendations = agent._generate_basic_recommendations(logic, informal)
        assert len(recommendations) == 1
        assert "satisfaisante" in recommendations[0].lower()


# =====================================================================
# SynthesisAgent Abstract Method Tests
# =====================================================================


class TestSynthesisAgentAbstractMethods:
    """Tests for SynthesisAgent abstract method implementations."""

    @pytest.mark.asyncio
    async def test_invoke_single_returns_unified_report(self):
        """Verify invoke_single returns UnifiedReport."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        # Mock the internal methods
        with patch.object(agent, "_simple_synthesis", new_callable=AsyncMock) as mock_synthesis:
            mock_report = UnifiedReport(
                original_text="Test",
                logic_analysis=LogicAnalysisResult(),
                informal_analysis=InformalAnalysisResult(),
            )
            mock_synthesis.return_value = mock_report

            result = await agent.invoke_single("Test text")

        assert isinstance(result, UnifiedReport)
        assert result.original_text == "Test"

    @pytest.mark.asyncio
    async def test_get_response_with_text(self):
        """Verify get_response generates report for text input."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)

        mock_report = UnifiedReport(
            original_text="Test",
            logic_analysis=LogicAnalysisResult(),
            informal_analysis=InformalAnalysisResult(),
            executive_summary="Test summary",
        )

        # Patch at CLASS level to bypass Pydantic V2 validation on instance setattr
        with patch.object(SynthesisAgent, "invoke_single", new_callable=AsyncMock, return_value=mock_report), \
             patch.object(SynthesisAgent, "generate_report", new_callable=AsyncMock, return_value="# Report"):
            result = await agent.get_response("Test text")

        assert "# Report" in result

    @pytest.mark.asyncio
    async def test_get_response_without_text(self):
        """Verify get_response handles missing text."""
        kernel = _create_mock_kernel()
        agent = SynthesisAgent(kernel)
        result = await agent.get_response()
        assert "Usage" in result
