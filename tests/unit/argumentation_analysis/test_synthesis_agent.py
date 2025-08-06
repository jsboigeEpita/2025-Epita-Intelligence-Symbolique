"""
Tests unitaires pour SynthesisAgent.

Ce module teste toutes les fonctionnalités de l'agent de synthèse unifié,
y compris l'orchestration d'analyses, l'unification des résultats et
la génération de rapports.
"""
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import asyncio

from typing import List

# Import du module à tester
from argumentation_analysis.agents.core.synthesis.synthesis_agent import (
    SynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.data_models import (
    LogicAnalysisResult,
    InformalAnalysisResult,
    UnifiedReport,
)
from semantic_kernel import Kernel


class MockLogicAgent:
    def __init__(self, logic_type: str):
        self.logic_type = logic_type

    async def analyze_text(self, text: str) -> str:
        if self.logic_type == "first_order":
            return f"Analyse FOL simulée: Prédicats et quantificateurs détectés dans '{text}'"
        if self.logic_type == "modal":
            return f"Analyse ML simulée: Modalités nécessité/possibilité détectées dans '{text}'"
        return f"Analyse {self.logic_type} simulée pour le texte: '{text}'"

class MockInformalAgent:
    async def analyze_text(self, text: str) -> dict:
        fallacies = []
        devices = ["assertion"]
        if "absolument" in text or "évidemment" in text:
            fallacies.append({"type": "assertion_non_fondée", "confidence": 0.8})
        if "tout le monde sait" in text:
            fallacies.append({"type": "appel_au_sens_commun", "confidence": 0.7})
        if len(text) > 50:
            devices.append("argumentation")
        return {"fallacies": fallacies, "structure": "Structure analysée (mock)", "devices": devices}


class TestSynthesisAgent:
    """Classe de tests pour SynthesisAgent."""

    @pytest.fixture
    def mock_kernel(self, mocker):
        """Fixture pour un kernel mocké."""
        kernel = mocker.MagicMock(spec=Kernel)
        kernel.plugins = {}
        kernel.get_prompt_execution_settings_from_service_id = mocker.MagicMock(
            return_value=None
        )
        kernel.add_function = mocker.MagicMock()
        return kernel
    
    @pytest.fixture
    def synthesis_agent(self, mock_kernel):
        """Fixture pour une instance de SynthesisAgent."""
        agent = SynthesisAgent(mock_kernel, "TestSynthesisAgent", enable_advanced_features=False)
        return agent
    
    @pytest.fixture
    def advanced_synthesis_agent(self, mock_kernel):
        """Fixture pour un SynthesisAgent avec fonctionnalités avancées."""
        agent = SynthesisAgent(mock_kernel, "AdvancedSynthesisAgent", enable_advanced_features=True)
        return agent
    
    def test_init_synthesis_agent_basic(self, mock_kernel):
        """Test l'initialisation du SynthesisAgent en mode basique."""
        agent = SynthesisAgent(
            mock_kernel, "TestAgent", enable_advanced_features=False
        )

        assert agent.name == "TestAgent"
        assert not agent.enable_advanced_features
        assert agent.fusion_manager is None
        assert agent.conflict_manager is None
        assert agent.evidence_manager is None
        assert agent.quality_manager is None
        assert agent._logic_agents_cache == {}
        assert agent._informal_agent is None
    
    def test_init_synthesis_agent_advanced(self, mock_kernel):
        """Test l'initialisation du SynthesisAgent en mode avancé."""
        agent = SynthesisAgent(
            mock_kernel, "AdvancedAgent", enable_advanced_features=True
        )

        assert agent.name == "AdvancedAgent"
        assert agent.enable_advanced_features
        assert agent.fusion_manager is None
        assert agent.conflict_manager is None
        assert agent.evidence_manager is None
        assert agent.quality_manager is None
    
    def test_get_agent_capabilities_basic(self, synthesis_agent):
        """Test la récupération des capacités en mode basique."""
        capabilities = synthesis_agent.get_agent_capabilities()
        
        assert capabilities["synthesis_coordination"]
        assert capabilities["formal_analysis_orchestration"]
        assert capabilities["informal_analysis_orchestration"]
        assert capabilities["unified_reporting"]
        assert capabilities["phase"] == 1
        assert not capabilities["advanced_features_enabled"]
        assert "propositional" in capabilities["logic_types_supported"]
        assert "first_order" in capabilities["logic_types_supported"]
        assert "modal" in capabilities["logic_types_supported"]
    
    def test_get_agent_capabilities_advanced(self, advanced_synthesis_agent):
        """Test la récupération des capacités en mode avancé."""
        capabilities = advanced_synthesis_agent.get_agent_capabilities()
        
        assert capabilities["advanced_features_enabled"]
        assert not capabilities["fusion_management"]
        assert not capabilities["conflict_resolution"]
        assert not capabilities["evidence_assessment"]
        assert not capabilities["quality_metrics"]
    
    @pytest.mark.asyncio
    async def test_synthesize_analysis_simple_mode(self, mocker, synthesis_agent):
        """Test la synthèse d'analyse en mode simple."""
        test_text = "Il est urgent d'agir sur le climat car les conséquences seront irréversibles."

        mock_logic_result = LogicAnalysisResult(
            propositional_result="Analyse PL réussie",
            logical_validity=True,
            processing_time_ms=100.0
        )
        mock_informal_result = InformalAnalysisResult(
            arguments_structure="Structure argumentative détectée",
            fallacies_detected=[],
            processing_time_ms=80.0
        )
        
        mocker.patch.object(synthesis_agent, 'orchestrate_analysis', new_callable=AsyncMock, return_value=(mock_logic_result, mock_informal_result))
        expected_report = UnifiedReport(
            original_text=test_text,
            logic_analysis=mock_logic_result,
            informal_analysis=mock_informal_result,
            executive_summary="Synthèse test",
            total_processing_time_ms=180.0,
        )
        mocker.patch.object(synthesis_agent, 'unify_results', new_callable=AsyncMock, return_value=expected_report)

        result = await synthesis_agent.synthesize_analysis(test_text)

        assert isinstance(result, UnifiedReport)
        assert result.original_text == test_text
        assert result.total_processing_time_ms is not None and result.total_processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_synthesize_analysis_advanced_mode_not_implemented(self, mocker, advanced_synthesis_agent):
        """Test que le mode avancé lève NotImplementedError."""
        advanced_synthesis_agent.fusion_manager = mocker.MagicMock()
        with pytest.raises(NotImplementedError):
            await advanced_synthesis_agent.synthesize_analysis("Texte de test")
    
    @pytest.mark.asyncio
    async def test_orchestrate_analysis_success(self, mocker, synthesis_agent):
        """Test l'orchestration réussie des analyses."""
        mock_logic_result = LogicAnalysisResult(propositional_result="Test PL")
        mock_informal_result = InformalAnalysisResult(arguments_structure="Test structure")

        mocker.patch.object(synthesis_agent, '_run_formal_analysis', new_callable=AsyncMock, return_value=mock_logic_result)
        mocker.patch.object(synthesis_agent, '_run_informal_analysis', new_callable=AsyncMock, return_value=mock_informal_result)

        logic_result, informal_result = await synthesis_agent.orchestrate_analysis("Test text")

        assert logic_result.propositional_result == "Test PL"
        assert informal_result.arguments_structure == "Test structure"
    
    @pytest.mark.asyncio
    async def test_orchestrate_analysis_with_exceptions(self, mocker, synthesis_agent):
        """Test l'orchestration avec gestion d'exceptions."""
        mocker.patch.object(synthesis_agent, '_run_formal_analysis', new_callable=AsyncMock, side_effect=Exception("Erreur"))
        mocker.patch.object(synthesis_agent, '_run_informal_analysis', new_callable=AsyncMock, return_value=InformalAnalysisResult())

        logic_result, informal_result = await synthesis_agent.orchestrate_analysis("Texte test")

        assert isinstance(logic_result, LogicAnalysisResult)
        assert isinstance(informal_result, InformalAnalysisResult)
    
    @pytest.mark.asyncio
    async def test_unify_results(self, mocker, synthesis_agent):
        """Test l'unification des résultats d'analyses."""
        logic_result = LogicAnalysisResult(logical_validity=True, consistency_check=True)
        informal_result = InformalAnalysisResult(fallacies_detected=[{"type": "ad_hominem"}])
        mocker.patch.object(synthesis_agent, '_generate_simple_summary', new_callable=AsyncMock, return_value="Résumé")

        report = await synthesis_agent.unify_results(logic_result, informal_result, "Original text")

        assert report.executive_summary == "Résumé"
    
    @pytest.mark.asyncio
    async def test_generate_report(self, synthesis_agent):
        """Test la génération de rapport textuel."""
        report = UnifiedReport(original_text="Texte", logic_analysis=LogicAnalysisResult(),
                               informal_analysis=InformalAnalysisResult(), executive_summary="Résumé",
                               contradictions_identified=["Contradiction"], recommendations=["Recommandation"])
        
        report_text = await synthesis_agent.generate_report(report)
        
        assert "RAPPORT DE SYNTHÈSE UNIFIÉ" in report_text
        assert "STATISTIQUES" in report_text
    
    @pytest.mark.asyncio
    async def test_run_formal_analysis(self, synthesis_agent):
        """Test l'exécution de l'analyse formelle."""
        synthesis_agent._logic_agents_cache = {
            "propositional": MockLogicAgent("propositional"),
            "first_order": MockLogicAgent("first_order"),
            "modal": MockLogicAgent("modal")
        }
        result = await synthesis_agent._run_formal_analysis("Test text")
        assert result.propositional_result is not None
    
    @pytest.mark.asyncio
    async def test_run_informal_analysis(self, synthesis_agent):
        """Test l'exécution de l'analyse informelle."""
        synthesis_agent._informal_agent = MockInformalAgent()
        result = await synthesis_agent._run_informal_analysis("tout le monde sait...")
        assert len(result.fallacies_detected) > 0

    def test_get_logic_agent_creation(self, synthesis_agent):
        with pytest.raises(NotImplementedError):
            synthesis_agent._get_logic_agent("propositional")
    
    def test_get_informal_agent_creation(self, synthesis_agent):
        with pytest.raises(NotImplementedError):
            synthesis_agent._get_informal_agent()
    
    @pytest.mark.asyncio
    async def test_analyze_with_logic_agent(self, mocker, synthesis_agent):
        mock_agent = AsyncMock(analyze_text=AsyncMock(return_value="Résultat"))
        result = await synthesis_agent._analyze_with_logic_agent(mock_agent, "texte", "prop")
        assert result == "Résultat"
        
    @pytest.mark.asyncio
    async def test_analyze_with_logic_agent_exception(self, mocker, synthesis_agent):
        mock_agent = AsyncMock(analyze_text=AsyncMock(side_effect=Exception("Err")))
        result = await synthesis_agent._analyze_with_logic_agent(mock_agent, "texte", "prop")
        assert "Erreur analyse" in result

    @pytest.mark.asyncio
    async def test_analyze_with_informal_agent(self, mocker, synthesis_agent):
        mock_agent = AsyncMock(analyze_text=AsyncMock(return_value={"fallacies":[]}))
        result = await synthesis_agent._analyze_with_informal_agent(mock_agent, "texte")
        assert "fallacies" in result
        
    @pytest.mark.asyncio
    async def test_analyze_with_informal_agent_exception(self, mocker, synthesis_agent):
        mock_agent = AsyncMock(analyze_text=AsyncMock(side_effect=Exception("Err")))
        result = await synthesis_agent._analyze_with_informal_agent(mock_agent, "texte")
        assert "Erreur analyse informelle" in result

    @pytest.mark.asyncio
    async def test_generate_simple_summary(self, synthesis_agent):
        summary = await synthesis_agent._generate_simple_summary(LogicAnalysisResult(), InformalAnalysisResult())
        assert isinstance(summary, str)
        
    def test_assess_overall_validity(self, synthesis_agent):
        assert not synthesis_agent._assess_overall_validity(LogicAnalysisResult(logical_validity=False), InformalAnalysisResult())
        assert synthesis_agent._assess_overall_validity(LogicAnalysisResult(logical_validity=True), InformalAnalysisResult(fallacies_detected=[]))

    def test_calculate_confidence_level(self, synthesis_agent):
        confidence = synthesis_agent._calculate_confidence_level(LogicAnalysisResult(), InformalAnalysisResult())
        assert 0.0 <= confidence <= 1.0

    def test_identify_basic_contradictions(self, synthesis_agent):
        contradictions = synthesis_agent._identify_basic_contradictions(LogicAnalysisResult(logical_validity=True), InformalAnalysisResult(fallacies_detected=[{"type":"test"}]))
        assert len(contradictions) > 0

    def test_generate_basic_recommendations(self, synthesis_agent):
        reco = synthesis_agent._generate_basic_recommendations(LogicAnalysisResult(), InformalAnalysisResult(fallacies_detected=[{"type":"test"}]))
        assert len(reco) > 0

    @pytest.mark.asyncio
    async def test_get_response_with_text(self, mocker, synthesis_agent):
        mocker.patch.object(synthesis_agent, 'synthesize_analysis', new_callable=AsyncMock, return_value=UnifiedReport(original_text="", logic_analysis=LogicAnalysisResult(), informal_analysis=InformalAnalysisResult()))
        mocker.patch.object(synthesis_agent, 'generate_report', new_callable=AsyncMock, return_value="Rapport")
        response = await synthesis_agent.get_response("text")
        assert response == "Rapport"
    
    @pytest.mark.asyncio
    async def test_get_response_without_text(self, synthesis_agent):
        response = await synthesis_agent.get_response()
        assert "Usage" in response
    
    @pytest.mark.asyncio
    async def test_invoke(self, mocker, synthesis_agent):
        mocker.patch.object(synthesis_agent, 'invoke_single', new_callable=AsyncMock, return_value="Report")
        results = [res async for res in synthesis_agent.invoke("text")]
        assert len(results) == 1 and results[0] == "Report"
    
    @pytest.mark.asyncio
    async def test_invoke_stream(self, mocker, synthesis_agent):
        async def gen(): yield "Stream"
        mocker.patch.object(synthesis_agent, 'invoke', return_value=gen())
        results = [res async for res in synthesis_agent.invoke_stream("text")]
        assert len(results) == 1 and results[0] == "Stream"


class TestMockAgents:
    """Tests pour les agents mock utilisés en Phase 1."""
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_logic_agents(self):
        """Test MockLogicAgent pour tous les types."""
        agent_prop = MockLogicAgent("propositional")
        result_prop = await agent_prop.analyze_text("Test")
        assert "Analyse propositional simulée" in result_prop
        
        agent_fol = MockLogicAgent("first_order")
        result_fol = await agent_fol.analyze_text("Test")
        assert "Analyse FOL simulée" in result_fol

    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_informal_agent(self):
        """Test MockInformalAgent avec et sans sophismes."""
        agent = MockInformalAgent()
        result_no_fallacy = await agent.analyze_text("Texte neutre")
        assert len(result_no_fallacy["fallacies"]) == 0
        
        result_with_fallacy = await agent.analyze_text("tout le monde sait...")
        assert len(result_with_fallacy["fallacies"]) > 0


class TestSynthesisAgentIntegration:
    """Tests d'intégration pour SynthesisAgent."""
    
    @pytest.fixture
    def integration_agent(self, mocker):
        """Agent configuré pour tests d'intégration."""
        mock_kernel = mocker.MagicMock(spec=Kernel)
        mock_kernel.plugins = {}
        agent = SynthesisAgent(mock_kernel, "IntegrationAgent", enable_advanced_features=False)
        return agent
    
    @pytest.mark.asyncio
    async def test_full_synthesis_workflow(self, mocker, integration_agent):
        """Test du workflow complet de synthèse."""
        mocker.patch.object(integration_agent, '_get_logic_agent', side_effect=MockLogicAgent)
        mocker.patch.object(integration_agent, '_get_informal_agent', return_value=MockInformalAgent())

        result = await integration_agent.synthesize_analysis("Il est absolument évident que...")
        
        assert isinstance(result, UnifiedReport)
        assert len(result.informal_analysis.fallacies_detected) > 0
    
    @pytest.mark.asyncio
    async def test_report_generation_integration(self, mocker, integration_agent):
        """Test de génération de rapport intégré."""
        test_text = "Argument avec sophisme évident pour tout le monde."
        mock_report = UnifiedReport(
            original_text=test_text,
            logic_analysis=LogicAnalysisResult(),
            informal_analysis=InformalAnalysisResult(fallacies_detected=[{"type": "appel_au_sens_commun"}]),
            executive_summary="Résumé",
            total_processing_time_ms=123.0
        )
        mocker.patch.object(integration_agent, 'synthesize_analysis', new_callable=AsyncMock, return_value=mock_report)

        unified_report = await integration_agent.synthesize_analysis(test_text)
        report_text = await integration_agent.generate_report(unified_report)
        
        assert "RAPPORT DE SYNTHÈSE UNIFIÉ" in report_text
        assert "STATISTIQUES" in report_text # Correction de la typo
        assert "sophisme" in report_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])