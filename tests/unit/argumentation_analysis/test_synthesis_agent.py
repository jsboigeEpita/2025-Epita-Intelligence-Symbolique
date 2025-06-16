
"""
Tests unitaires pour SynthesisAgent.

Ce module teste toutes les fonctionnalités de l'agent de synthèse unifié,
y compris l'orchestration d'analyses, l'unification des résultats et
la génération de rapports.
"""
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import time

from typing import Dict, Any, Optional, Tuple, List

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
        assert agent.enable_advanced_features == False
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
        assert agent.enable_advanced_features == True
        # Les modules avancés sont None en Phase 1, mais la configuration est prête
        assert agent.fusion_manager is None
        assert agent.conflict_manager is None
        assert agent.evidence_manager is None
        assert agent.quality_manager is None
    
    def test_get_agent_capabilities_basic(self, synthesis_agent):
        """Test la récupération des capacités en mode basique."""
        capabilities = synthesis_agent.get_agent_capabilities()
        
        assert capabilities["synthesis_coordination"] == True
        assert capabilities["formal_analysis_orchestration"] == True
        assert capabilities["informal_analysis_orchestration"] == True
        assert capabilities["unified_reporting"] == True
        assert capabilities["phase"] == 1
        assert capabilities["advanced_features_enabled"] == False
        assert "propositional" in capabilities["logic_types_supported"]
        assert "first_order" in capabilities["logic_types_supported"]
        assert "modal" in capabilities["logic_types_supported"]
    
    def test_get_agent_capabilities_advanced(self, advanced_synthesis_agent):
        """Test la récupération des capacités en mode avancé."""
        capabilities = advanced_synthesis_agent.get_agent_capabilities()
        
        assert capabilities["advanced_features_enabled"] == True
        assert capabilities["fusion_management"] == False  # Non encore implémenté
        assert capabilities["conflict_resolution"] == False
        assert capabilities["evidence_assessment"] == False
        assert capabilities["quality_metrics"] == False
    
    def test_setup_agent_components(self, synthesis_agent):
        """Test la configuration des composants de l'agent."""
        synthesis_agent.setup_agent_components("test_service")
        
        assert hasattr(synthesis_agent, '_llm_service_id')
        assert synthesis_agent._llm_service_id == "test_service"
    
    @pytest.mark.asyncio
    async def test_synthesize_analysis_simple_mode(self, mocker, synthesis_agent):
        """Test la synthèse d'analyse en mode simple."""
        test_text = "Il est urgent d'agir sur le climat car les conséquences seront irréversibles."

        # Mock des méthodes internes
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
        
        mock_orchestrate = mocker.patch.object(synthesis_agent, 'orchestrate_analysis', new_callable=AsyncMock)
        mock_orchestrate.return_value = (mock_logic_result, mock_informal_result)

        mock_unify = mocker.patch.object(synthesis_agent, 'unify_results', new_callable=AsyncMock)
        expected_report = UnifiedReport(
            original_text=test_text,
            logic_analysis=mock_logic_result,
            informal_analysis=mock_informal_result,
            executive_summary="Synthèse test",
            total_processing_time_ms=180.0,
        )
        mock_unify.return_value = expected_report

        result = await synthesis_agent.synthesize_analysis(test_text)

        assert isinstance(result, UnifiedReport)
        assert result.original_text == test_text
        assert result.total_processing_time_ms is not None
        assert result.total_processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_synthesize_analysis_advanced_mode_not_implemented(self, mocker, advanced_synthesis_agent):
        """Test que le mode avancé lève NotImplementedError."""
        # Activer artificiellement le fusion_manager pour déclencher le mode avancé
        advanced_synthesis_agent.fusion_manager = mocker.MagicMock()

        test_text = "Texte de test"

        with pytest.raises(NotImplementedError):
            await advanced_synthesis_agent.synthesize_analysis(test_text)
    
    @pytest.mark.asyncio
    async def test_orchestrate_analysis_success(self, mocker, synthesis_agent):
        """Test l'orchestration réussie des analyses."""
        test_text = "Argument politique complexe avec potentiels sophismes."

        # Mock des agents
        mock_logic_result = LogicAnalysisResult(propositional_result="Test PL")
        mock_informal_result = InformalAnalysisResult(
            arguments_structure="Test structure"
        )

        mock_formal = mocker.patch.object(synthesis_agent, '_run_formal_analysis', new_callable=AsyncMock)
        mock_formal.return_value = mock_logic_result

        mock_informal = mocker.patch.object(synthesis_agent, '_run_informal_analysis', new_callable=AsyncMock)
        mock_informal.return_value = mock_informal_result

        logic_result, informal_result = await synthesis_agent.orchestrate_analysis(
            test_text
        )

        assert isinstance(logic_result, LogicAnalysisResult)
        assert isinstance(informal_result, InformalAnalysisResult)
        assert logic_result.propositional_result == "Test PL"
        assert informal_result.arguments_structure == "Test structure"
    
    @pytest.mark.asyncio
    async def test_orchestrate_analysis_with_exceptions(self, mocker, synthesis_agent):
        """Test l'orchestration avec gestion d'exceptions."""
        test_text = "Texte test"

        # Mock avec exception pour l'analyse formelle
        mock_formal = mocker.patch.object(synthesis_agent, '_run_formal_analysis', new_callable=AsyncMock)
        mock_formal.side_effect = Exception("Erreur analyse formelle")

        mock_informal = mocker.patch.object(synthesis_agent, '_run_informal_analysis', new_callable=AsyncMock)
        mock_informal.return_value = InformalAnalysisResult()

        logic_result, informal_result = await synthesis_agent.orchestrate_analysis(
            test_text
        )

        # Doit retourner des résultats par défaut même en cas d'erreur
        assert isinstance(logic_result, LogicAnalysisResult)
        assert isinstance(informal_result, InformalAnalysisResult)
    
    @pytest.mark.asyncio
    async def test_unify_results(self, mocker, synthesis_agent):
        """Test l'unification des résultats d'analyses."""
        original_text = "Texte original pour test"

        logic_result = LogicAnalysisResult(
            propositional_result="Logique valide",
            logical_validity=True,
            consistency_check=True,
        )

        informal_result = InformalAnalysisResult(
            arguments_structure="Structure solide",
            fallacies_detected=[{"type": "ad_hominem", "confidence": 0.8}],
        )

        # Mock des méthodes de génération
        mock_summary = mocker.patch.object(synthesis_agent, '_generate_simple_summary', new_callable=AsyncMock)
        mock_summary.return_value = "Résumé de test"

        report = await synthesis_agent.unify_results(
            logic_result, informal_result, original_text
        )

        assert isinstance(report, UnifiedReport)
        assert report.original_text == original_text
        assert report.logic_analysis == logic_result
        assert report.informal_analysis == informal_result
        assert report.executive_summary == "Résumé de test"
        assert report.overall_validity is not None
        assert report.confidence_level is not None
        assert isinstance(report.contradictions_identified, list)
        assert isinstance(report.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_generate_report(self, synthesis_agent):
        """Test la génération de rapport textuel."""
        logic_result = LogicAnalysisResult(propositional_result="Test PL")
        informal_result = InformalAnalysisResult(fallacies_detected=[])
        
        unified_report = UnifiedReport(
            original_text="Texte test",
            logic_analysis=logic_result,
            informal_analysis=informal_result,
            executive_summary="Résumé exécutif test",
            overall_validity=True,
            confidence_level=0.85,
            contradictions_identified=["Contradiction test"],
            recommendations=["Recommandation test"]
        )
        
        report_text = await synthesis_agent.generate_report(unified_report)
        
        assert "RAPPORT DE SYNTHÈSE UNIFIÉ" in report_text
        assert "RÉSUMÉ EXÉCUTIF" in report_text
        assert "STATISTIQUES" in report_text
        assert "ÉVALUATION GLOBALE" in report_text
        assert "CONTRADICTIONS IDENTIFIÉES" in report_text
        assert "RECOMMANDATIONS" in report_text
        assert "DÉTAILS DES ANALYSES" in report_text
        assert "Résumé exécutif test" in report_text
    
    @pytest.mark.asyncio
    async def test_run_formal_analysis(self, synthesis_agent):
        """Test l'exécution de l'analyse formelle."""
        test_text = "Texte à analyser formellement"
        
        # Mock des agents logiques
        mock_agent_prop = MockLogicAgent("propositional")
        mock_agent_fol = MockLogicAgent("first_order")
        mock_agent_modal = MockLogicAgent("modal")
        
        synthesis_agent._logic_agents_cache = {
            "propositional": mock_agent_prop,
            "first_order": mock_agent_fol,
            "modal": mock_agent_modal
        }
        
        result = await synthesis_agent._run_formal_analysis(test_text)
        
        assert isinstance(result, LogicAnalysisResult)
        assert result.propositional_result is not None
        assert result.first_order_result is not None
        assert result.modal_result is not None
        assert result.processing_time_ms is not None
        assert result.processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_run_informal_analysis(self, synthesis_agent):
        """Test l'exécution de l'analyse informelle."""
        test_text = "Texte qui dit que tout le monde sait que les sophismes sont évidents."
        
        # Mock de l'agent informel
        OrchestrationServiceManager = MockInformalAgent()
        synthesis_agent._informal_agent = OrchestrationServiceManager
        
        result = await synthesis_agent._run_informal_analysis(test_text)
        
        assert isinstance(result, InformalAnalysisResult)
        assert result.processing_time_ms is not None
        assert result.processing_time_ms >= 0
        # Le MockInformalAgent devrait détecter des sophismes dans ce texte
        # Le MockInformalAgent doit détecter "tout le monde sait"
        assert len(result.fallacies_detected) > 0
    
    def test_get_logic_agent_creation(self, synthesis_agent):
        """Test que la création d'un agent logique non-mocké lève une exception."""
        with pytest.raises(NotImplementedError, match="implémenter agent authentique propositional"):
            synthesis_agent._get_logic_agent("propositional")
    
    def test_get_informal_agent_creation(self, synthesis_agent):
        """Test que la création d'un agent informel non-mocké lève une exception."""
        with pytest.raises(NotImplementedError, match="implémenter agent authentique"):
            synthesis_agent._get_informal_agent()
    
    @pytest.mark.asyncio
    async def test_analyze_with_logic_agent_analyze_text(self, mocker, synthesis_agent):
        """Test l'analyse avec un agent logique (méthode analyze_text)."""
        mock_agent = mocker.MagicMock()
        mock_agent.analyze_text = AsyncMock(return_value="Résultat analyse")

        result = await synthesis_agent._analyze_with_logic_agent(
            mock_agent, "texte test", "propositional"
        )

        assert result == "Résultat analyse"
        mock_agent.analyze_text.assert_called_once_with("texte test")

    @pytest.mark.asyncio
    async def test_analyze_with_logic_agent_process_text(self, mocker, synthesis_agent):
        """Test l'analyse avec un agent logique (méthode process_text)."""
        mock_agent = mocker.MagicMock()
        mock_agent.process_text = AsyncMock(return_value="Résultat process")
        # S'assurer que hasattr fonctionne correctement
        del mock_agent.analyze_text  # Pour que hasattr(mock_agent, "analyze_text") soit False

        result = await synthesis_agent._analyze_with_logic_agent(
            mock_agent, "texte test", "modal"
        )

        assert result == "Résultat process"
        mock_agent.process_text.assert_called_once_with("texte test")
    
    @pytest.mark.asyncio
    async def test_analyze_with_logic_agent_no_interface(self, mocker, synthesis_agent):
        """Test l'analyse avec un agent sans interface reconnue."""
        mock_agent = mocker.MagicMock(spec=[])  # Mock sans aucune méthode
        # Explicitement supprimer les méthodes si elles existent
        if hasattr(mock_agent, "analyze_text"):
            del mock_agent.analyze_text
        if hasattr(mock_agent, "process_text"):
            del mock_agent.process_text

        result = await synthesis_agent._analyze_with_logic_agent(
            mock_agent, "texte test", "unknown"
        )

        assert "interface non reconnue" in result
    
    @pytest.mark.asyncio
    async def test_analyze_with_logic_agent_exception(self, mocker, synthesis_agent):
        """Test la gestion d'exception lors de l'analyse logique."""
        mock_agent = mocker.MagicMock()
        mock_agent.analyze_text = AsyncMock(side_effect=Exception("Test error"))

        result = await synthesis_agent._analyze_with_logic_agent(
            mock_agent, "texte test", "propositional"
        )

        assert "Erreur analyse propositional" in result
        assert "Test error" in result
    
    @pytest.mark.asyncio
    async def test_analyze_with_informal_agent_success(self, mocker, synthesis_agent):
        """Test l'analyse avec l'agent informel."""
        mock_agent = mocker.MagicMock()
        mock_agent.analyze_text = AsyncMock(
            return_value={"fallacies": ["test"], "structure": "test"}
        )

        result = await synthesis_agent._analyze_with_informal_agent(
            mock_agent, "texte test"
        )

        assert result["fallacies"] == ["test"]
        assert result["structure"] == "test"

    @pytest.mark.asyncio
    async def test_analyze_with_informal_agent_exception(self, mocker, synthesis_agent):
        """Test la gestion d'exception lors de l'analyse informelle."""
        mock_agent = mocker.MagicMock()
        mock_agent.analyze_text = AsyncMock(side_effect=Exception("Informal error"))

        result = await synthesis_agent._analyze_with_informal_agent(
            mock_agent, "texte test"
        )

        assert "Erreur analyse informelle" in result
        assert "Informal error" in result
    
    @pytest.mark.asyncio
    async def test_generate_simple_summary(self, synthesis_agent):
        """Test la génération de résumé simple."""
        logic_result = LogicAnalysisResult(
            propositional_result="PL test",
            first_order_result="FOL test",
            modal_result="Modal test",
            logical_validity=True
        )
        
        informal_result = InformalAnalysisResult(
            fallacies_detected=[
                {"type": "ad_hominem"},
                {"type": "strawman"}
            ]
        )
        
        summary = await synthesis_agent._generate_simple_summary(logic_result, informal_result)
        
        assert "logique propositionnelle" in summary
        assert "logique de premier ordre" in summary
        assert "logique modale" in summary
        assert "2 sophisme(s) détecté(s)" in summary
        assert "valide" in summary
    
    @pytest.mark.asyncio
    async def test_generate_simple_summary_no_fallacies(self, synthesis_agent):
        """Test la génération de résumé sans sophismes."""
        logic_result = LogicAnalysisResult()
        informal_result = InformalAnalysisResult(fallacies_detected=[])
        
        summary = await synthesis_agent._generate_simple_summary(logic_result, informal_result)
        
        assert "aucun sophisme majeur détecté" in summary
    
    def test_assess_overall_validity(self, synthesis_agent):
        """Test l'évaluation de la validité globale."""
        # Cas 1: Logique valide + pas de sophismes
        logic_result = LogicAnalysisResult(logical_validity=True)
        informal_result = InformalAnalysisResult(fallacies_detected=[])
        
        validity = synthesis_agent._assess_overall_validity(logic_result, informal_result)
        assert validity == True
        
        # Cas 2: Logique valide + sophismes présents
        informal_result_with_fallacies = InformalAnalysisResult(
            fallacies_detected=[{"type": "test"}]
        )
        
        validity = synthesis_agent._assess_overall_validity(logic_result, informal_result_with_fallacies)
        assert validity == False
        
        # Cas 3: Logique invalide
        logic_result_invalid = LogicAnalysisResult(logical_validity=False)
        
        validity = synthesis_agent._assess_overall_validity(logic_result_invalid, informal_result)
        assert validity == False
    
    def test_calculate_confidence_level(self, synthesis_agent):
        """Test le calcul du niveau de confiance."""
        logic_result = LogicAnalysisResult(
            propositional_result="Test",
            first_order_result="Test",
            modal_result="Test"
        )
        
        informal_result = InformalAnalysisResult(
            arguments_structure="Test structure",
            fallacies_detected=[{"type": "test"}]  # 1 sophisme = -0.05
        )
        
        confidence = synthesis_agent._calculate_confidence_level(logic_result, informal_result)
        
        # Base: 0.5 + 0.3 (résultats logiques) + 0.15 (structure) - 0.05 (1 sophisme) = 0.9
        assert abs(confidence - 0.9) < 0.001  # Tolérance pour les flottants
        assert 0.0 <= confidence <= 1.0
    
    def test_identify_basic_contradictions(self, synthesis_agent):
        """Test l'identification de contradictions basiques."""
        # Cas 1: Argument logiquement valide mais avec sophismes
        logic_result = LogicAnalysisResult(
            logical_validity=True,
            consistency_check=True
        )
        informal_result = InformalAnalysisResult(
            fallacies_detected=[{"type": "ad_hominem"}]
        )
        
        contradictions = synthesis_agent._identify_basic_contradictions(logic_result, informal_result)
        
        assert len(contradictions) >= 1
        assert any("logiquement valide mais contenant des sophismes" in c for c in contradictions)
        
        # Cas 2: Argument valide mais prémisses incohérentes
        logic_result_inconsistent = LogicAnalysisResult(
            logical_validity=True,
            consistency_check=False
        )
        informal_result_clean = InformalAnalysisResult(fallacies_detected=[])
        
        contradictions = synthesis_agent._identify_basic_contradictions(logic_result_inconsistent, informal_result_clean)
        
        assert any("valide mais ensemble de prémisses incohérent" in c for c in contradictions)
    
    def test_generate_basic_recommendations(self, synthesis_agent):
        """Test la génération de recommandations basiques."""
        # Cas avec problèmes multiples
        logic_result = LogicAnalysisResult(
            logical_validity=False,
            consistency_check=False
        )
        informal_result = InformalAnalysisResult(
            fallacies_detected=[{"type": "test1"}, {"type": "test2"}],
            arguments_structure=""
        )
        
        recommendations = synthesis_agent._generate_basic_recommendations(logic_result, informal_result)
        
        assert len(recommendations) >= 3
        assert any("structure logique" in r for r in recommendations)
        assert any("cohérence des prémisses" in r for r in recommendations)
        assert any("2 sophisme(s)" in r for r in recommendations)
        assert any("structure argumentative" in r for r in recommendations)
    
    def test_generate_basic_recommendations_clean(self, synthesis_agent):
        """Test la génération de recommandations pour analyse propre."""
        logic_result = LogicAnalysisResult(
            logical_validity=True,
            consistency_check=True
        )
        informal_result = InformalAnalysisResult(
            fallacies_detected=[],
            arguments_structure="Structure claire"
        )
        
        recommendations = synthesis_agent._generate_basic_recommendations(logic_result, informal_result)
        
        assert len(recommendations) == 1
        assert "satisfaisante" in recommendations[0]
        assert "aucune correction majeure" in recommendations[0]
    
    @pytest.mark.asyncio
    async def test_get_response_with_text(self, mocker, synthesis_agent):
        """Test get_response avec un texte."""
        test_text = "Argument de test"

        mock_synthesize = mocker.patch.object(synthesis_agent, 'synthesize_analysis', new_callable=AsyncMock)
        mock_report = UnifiedReport(
            original_text=test_text,
            logic_analysis=LogicAnalysisResult(),
            informal_analysis=InformalAnalysisResult(),
        )
        mock_synthesize.return_value = mock_report

        mock_generate = mocker.patch.object(synthesis_agent, 'generate_report', new_callable=AsyncMock)
        mock_generate.return_value = "Rapport généré"

        response = await synthesis_agent.get_response(test_text)

        assert response == "Rapport généré"
        mock_synthesize.assert_called_once_with(test_text)
    
    @pytest.mark.asyncio
    async def test_get_response_without_text(self, synthesis_agent):
        """Test get_response sans texte."""
        response = await synthesis_agent.get_response()
        
        assert "Usage: fournir un texte à analyser" in response
    
    @pytest.mark.asyncio
    async def test_invoke(self, mocker, synthesis_agent):
        """Test invoke (doit appeler get_response)."""
        test_text = "Test invoke"

        mock_get_response = mocker.patch.object(synthesis_agent, 'get_response', new_callable=AsyncMock)
        mock_get_response.return_value = "Réponse invoke"

        response = await synthesis_agent.invoke(test_text)

        assert response == "Réponse invoke"
        mock_get_response.assert_called_once_with(test_text)
    
    @pytest.mark.asyncio
    async def test_invoke_stream(self, mocker, synthesis_agent):
        """Test invoke_stream."""
        test_text = "Test stream"
        
        mock_invoke = mocker.patch.object(synthesis_agent, 'invoke', new_callable=AsyncMock)
        mock_invoke.return_value = "Résultat stream"

        async for result in synthesis_agent.invoke_stream(test_text):
            assert result == "Résultat stream"
            break


class TestMockAgents:
    """Tests pour les agents mock utilisés en Phase 1."""
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_propositional(self):
        """Test MockLogicAgent pour logique propositionnelle."""
        agent = MockLogicAgent("propositional")
        
        assert agent.logic_type == "propositional"
        
        result = await agent.analyze_text("Texte de test avec logique")
        
        assert "Analyse propositional simulée" in result
        assert "Texte de test" in result
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_first_order(self):
        """Test MockLogicAgent pour logique de premier ordre."""
        agent = MockLogicAgent("first_order")
        
        result = await agent.analyze_text("Texte avec prédicats")
        
        assert "Analyse FOL simulée" in result
        assert "Prédicats et quantificateurs" in result
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_modal(self):
        """Test MockLogicAgent pour logique modale."""
        agent = MockLogicAgent("modal")
        
        result = await agent.analyze_text("Il est nécessaire que...")
        
        assert "Analyse ML simulée" in result
        assert "Modalités nécessité/possibilité" in result
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_unknown_type(self):
        """Test MockLogicAgent pour type inconnu."""
        agent = MockLogicAgent("unknown_logic")
        
        result = await agent.analyze_text("Texte quelconque")
        
        assert "Analyse unknown_logic simulée" in result
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_no_fallacies(self):
        """Test MockInformalAgent sans sophismes."""
        agent = MockInformalAgent()
        
        result = await agent.analyze_text("Texte neutre sans mots-clés")
        
        assert isinstance(result, dict)
        assert "fallacies" in result
        assert "structure" in result
        assert "devices" in result
        assert len(result["fallacies"]) == 0
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_with_fallacies(self):
        """Test MockInformalAgent avec détection de sophismes."""
        agent = MockInformalAgent()
        
        # Texte contenant des mots-clés déclencheurs
        text = "C'est absolument évident que tout le monde sait cela"
        result = await agent.analyze_text(text)
        
        assert len(result["fallacies"]) >= 2  # "absolument" et "tout le monde sait"
        
        # Vérifier les types de sophismes détectés
        fallacy_types = [f["type"] for f in result["fallacies"]]
        assert "assertion_non_fondée" in fallacy_types
        assert "appel_au_sens_commun" in fallacy_types
    
    @pytest.mark.asyncio
    async def test_OrchestrationServiceManager_structure_analysis(self):
        """Test l'analyse de structure par MockInformalAgent."""
        agent = MockInformalAgent()
        
        # Texte court
        short_text = "Court"
        result_short = await agent.analyze_text(short_text)
        assert "assertion" in result_short["devices"]
        assert len(result_short["devices"]) == 1
        
        # Texte long
        long_text = "Texte long avec plus de cinquante caractères pour déclencher l'analyse avancée"
        result_long = await agent.analyze_text(long_text)
        assert "assertion" in result_long["devices"]
        assert "argumentation" in result_long["devices"]
        assert len(result_long["devices"]) == 2


class TestSynthesisAgentIntegration:
    """Tests d'intégration pour SynthesisAgent."""
    
    @pytest.fixture
    def integration_agent(self, mocker):
        """Agent configuré pour tests d'intégration."""
        # Créer un mock kernel simple
        mock_kernel = mocker.MagicMock(spec=Kernel)
        mock_kernel.plugins = {}

        agent = SynthesisAgent(
            mock_kernel, "IntegrationAgent", enable_advanced_features=False
        )
        agent.setup_agent_components("test_service")
        return agent
    
    @pytest.mark.asyncio
    async def test_full_synthesis_workflow(self, mocker, integration_agent):
        """Test du workflow complet de synthèse."""
        # Patch des méthodes qui lèvent NotImplementedError
        mocker.patch.object(integration_agent, '_get_logic_agent', side_effect=MockLogicAgent)
        mocker.patch.object(integration_agent, '_get_informal_agent', return_value=MockInformalAgent())

        test_text = "Il est absolument évident que le changement climatique nécessite une action immédiate."
        
        # Ce test utilise les agents mock intégrés via les patchs
        result = await integration_agent.synthesize_analysis(test_text)
        
        assert isinstance(result, UnifiedReport)
        assert result.original_text == test_text
        assert result.logic_analysis is not None
        assert result.informal_analysis is not None
        assert result.executive_summary != ""
        assert result.total_processing_time_ms is not None
        assert result.total_processing_time_ms >= 0 # Assouplissement de l'assertion
        
        # Vérifier que les analyses mock ont fonctionné
        assert result.logic_analysis.propositional_result is not None
        assert result.logic_analysis.first_order_result is not None
        assert result.logic_analysis.modal_result is not None
        
        # Le texte contient "absolument" donc devrait détecter des sophismes
        assert len(result.informal_analysis.fallacies_detected) > 0
    
    @pytest.mark.asyncio
    async def test_report_generation_integration(self, mocker, integration_agent):
        """Test de génération de rapport intégré."""
        test_text = "Argument avec sophisme évident pour tout le monde."
        
        # Mock du rapport de synthèse pour isoler le test de la génération de rapport
        mock_report = UnifiedReport(
            original_text=test_text,
            logic_analysis=LogicAnalysisResult(propositional_result="Test PL"),
            informal_analysis=InformalAnalysisResult(fallacies_detected=[{"type": "appel_au_sens_commun"}]),
            executive_summary="Résumé pour rapport",
            total_processing_time_ms=123.0
        )
        # Patch synthesize_analysis pour ne tester que generate_report
        mocker.patch.object(integration_agent, 'synthesize_analysis', return_value=mock_report)

        # Synthèse complète (mockée)
        unified_report = await integration_agent.synthesize_analysis(test_text)
        
        # Génération du rapport textuel
        report_text = await integration_agent.generate_report(unified_report)
        
        # Vérifications du contenu du rapport
        assert "RAPPORT DE SYNTHÈSE UNIFIÉ" in report_text
        assert test_text in report_text or test_text[:50] in report_text
        assert "STATISTIQUES" in report_text
        assert "ÉVALUATION GLOBALE" in report_text
        
        # Le rapport doit mentionner les sophismes détectés
        stats = unified_report.get_summary_statistics()
        assert stats['fallacies_count'] > 0
        assert "sophisme" in report_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])