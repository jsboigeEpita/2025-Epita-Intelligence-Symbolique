"""
Tests unitaires refactorisés pour WatsonJTMSAgent.
Ces tests valident que l'agent délègue correctement les appels à ses moteurs internes (critique, validation, etc.)
en utilisant des mocks pour isoler le comportement de l'agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from argumentation_analysis.agents.watson_jtms.agent import WatsonJTMSAgent

# #####################################################################################

# Mocker les dépendances (moteurs) de l'agent
@pytest.fixture(autouse=True)
def mock_engines():
    """
    Patche les classes des moteurs pour s'assurer que toute instance de WatsonJTMSAgent
    sera créée avec des mocks.
    """
    with patch('argumentation_analysis.agents.watson_jtms.agent.ConsistencyChecker', new_callable=Mock) as mock_consistency, \
         patch('argumentation_analysis.agents.watson_jtms.agent.FormalValidator', new_callable=Mock) as mock_validator, \
         patch('argumentation_analysis.agents.watson_jtms.agent.CritiqueEngine', new_callable=Mock) as mock_critique, \
         patch('argumentation_analysis.agents.watson_jtms.agent.SynthesisEngine', new_callable=Mock) as mock_synthesis:
        
        mock_critique.return_value.suggest_alternatives = AsyncMock()
        mock_critique.return_value.analyze_sherlock_conclusions = AsyncMock()
        mock_critique.return_value.critique_reasoning_chain = AsyncMock()
        mock_critique.return_value.challenge_assumption = AsyncMock()
        mock_critique.return_value.identify_logical_fallacies = AsyncMock()
        mock_critique.return_value.export_critique_state = Mock()

        mock_validator.return_value.validate_sherlock_reasoning = AsyncMock()
        mock_validator.return_value.prove_belief = AsyncMock()
        mock_validator.return_value.cross_validate_evidence = AsyncMock()
        mock_validator.return_value.get_validation_summary = Mock()

        mock_synthesis.return_value.provide_alternative_theory = AsyncMock()
        mock_synthesis.return_value.process_jtms_inference = AsyncMock()
        
        mock_consistency.return_value.resolve_conflicts = AsyncMock()

        yield {
            "consistency": mock_consistency,
            "validator": mock_validator,
            "critique": mock_critique,
            "synthesis": mock_synthesis
        }
        
# La fixture stop_module_patcher n'est plus nécessaire car le patcher au niveau du module a été supprimé.

@pytest.fixture
def mock_kernel():
    """Kernel mocké simple pour l'initialisation de l'agent."""
    return Mock(name="MockKernel")

@pytest.fixture
def watson_agent(mock_kernel, mock_engines):
    """
    Fixture pour créer une instance de WatsonJTMSAgent avec des moteurs mockés.
    """
    agent = WatsonJTMSAgent(kernel=mock_kernel, agent_name="WatsonTest")
    return agent

class TestWatsonJTMSAgentRefactored:
    """Suite de tests refactorisés pour WatsonJTMSAgent."""

    def test_agent_initialization(self, watson_agent, mock_engines):
        """Vérifie que l'agent et ses moteurs sont initialisés correctement."""
        assert watson_agent.agent_name == "WatsonTest"
        assert watson_agent.specialization == "critical_analysis"
        
        mock_engines["consistency"].assert_called_once()
        mock_engines["validator"].assert_called_once()
        mock_engines["critique"].assert_called_once()
        mock_engines["synthesis"].assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_sherlock_reasoning(self, watson_agent):
        """Teste la délégation de la validation du raisonnement de Sherlock."""
        expected_result = {"status": "valid"}
        watson_agent.validator.validate_sherlock_reasoning.return_value = expected_result
        
        result = await watson_agent.validate_sherlock_reasoning({"state": "test"})
        
        watson_agent.validator.validate_sherlock_reasoning.assert_awaited_once_with({"state": "test"})
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_suggest_alternatives(self, watson_agent):
        """Teste la délégation de la suggestion d'alternatives."""
        expected_result = ["alt1", "alt2"]
        watson_agent.critique_engine.suggest_alternatives.return_value = expected_result
        
        result = await watson_agent.suggest_alternatives("belief", context={})
        
        watson_agent.critique_engine.suggest_alternatives.assert_awaited_once_with("belief", {})
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_resolve_conflicts(self, watson_agent):
        """Teste la délégation de la résolution de conflits."""
        expected_result = ["resolved_conflict"]
        watson_agent.consistency_checker.resolve_conflicts.return_value = expected_result
        
        result = await watson_agent.resolve_conflicts(["conflict1"])
        
        watson_agent.consistency_checker.resolve_conflicts.assert_awaited_once_with(["conflict1"])
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_process_jtms_inference(self, watson_agent):
        """Teste la délégation du traitement d'inférence JTMS."""
        expected_result = {"processed": True}
        watson_agent.synthesis_engine.process_jtms_inference.return_value = expected_result
        
        result = await watson_agent.process_jtms_inference("context_str")
        
        watson_agent.synthesis_engine.process_jtms_inference.assert_awaited_once_with("context_str")
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_validate_hypothesis(self, watson_agent):
        """Teste la délégation de la validation d'hypothèse."""
        expected_proof = {"provable": True}
        watson_agent.validator.prove_belief.return_value = expected_proof
        hypothesis_data = {"hypothesis": "le colonel est coupable"}

        result = await watson_agent.validate_hypothesis("hyp_1", hypothesis_data)

        watson_agent.validator.prove_belief.assert_awaited_once_with("le colonel est coupable")
        assert result["is_valid"] == True
        assert result["details"] == expected_proof

    @pytest.mark.asyncio
    async def test_cross_validate_evidence(self, watson_agent):
        """Teste la délégation de la validation croisée d'évidences."""
        expected_result = {"summary": "all good"}
        watson_agent.validator.cross_validate_evidence.return_value = expected_result
        evidence_set = [{"id": "e1"}]
        
        result = await watson_agent.cross_validate_evidence(evidence_set)
        
        watson_agent.validator.cross_validate_evidence.assert_awaited_once_with(evidence_set)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_analyze_sherlock_conclusions(self, watson_agent):
        """Teste la délégation de l'analyse des conclusions de Sherlock."""
        expected_result = {"analysis": "looks ok"}
        watson_agent.critique_engine.analyze_sherlock_conclusions.return_value = expected_result
        sherlock_state = {"conclusions": []}

        result = await watson_agent.analyze_sherlock_conclusions(sherlock_state)

        watson_agent.critique_engine.analyze_sherlock_conclusions.assert_awaited_once_with(sherlock_state)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_provide_alternative_theory(self, watson_agent):
        """Teste la délégation de la création de théorie alternative."""
        expected_result = {"theory": "Mme Leblanc a fait le coup"}
        watson_agent.synthesis_engine.provide_alternative_theory.return_value = expected_result
        
        result = await watson_agent.provide_alternative_theory("t1", {}, [])
        
        watson_agent.synthesis_engine.provide_alternative_theory.assert_awaited_once_with("t1", {}, [])
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_critique_reasoning_chain(self, watson_agent):
        """Teste la délégation de la critique de chaîne de raisonnement."""
        expected_result = {"critique": "flawed"}
        watson_agent.critique_engine.critique_reasoning_chain.return_value = expected_result
        
        result = await watson_agent.critique_reasoning_chain("c1", [])
        
        watson_agent.critique_engine.critique_reasoning_chain.assert_awaited_once_with("c1", [])
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_challenge_assumption(self, watson_agent):
        """Teste la délégation du défi d'une supposition."""
        expected_result = {"challenge": "refuted"}
        watson_agent.critique_engine.challenge_assumption.return_value = expected_result
        
        result = await watson_agent.challenge_assumption("a1", {})
        
        watson_agent.critique_engine.challenge_assumption.assert_awaited_once_with("a1", {})
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_identify_logical_fallacies(self, watson_agent):
        """Teste la délégation de l'identification de sophismes."""
        expected_result = {"fallacies": ["hasty generalization"]}
        watson_agent.critique_engine.identify_logical_fallacies.return_value = expected_result
        
        result = await watson_agent.identify_logical_fallacies("r1", "texte...")
        
        watson_agent.critique_engine.identify_logical_fallacies.assert_awaited_once_with("r1", "texte...")
        assert result == expected_result

    def test_export_critique_state(self, watson_agent):
        """Teste la délégation de l'export de l'état de la critique."""
        expected_result = {"state": "exported"}
        watson_agent.critique_engine.export_critique_state.return_value = expected_result
        
        result = watson_agent.export_critique_state()
        
        watson_agent.critique_engine.export_critique_state.assert_called_once()
        assert result == expected_result
        
    def test_get_validation_summary(self, watson_agent):
        """Teste la délégation de l'obtention du résumé de validation."""
        # Test du fallback au cas où le validateur n'a pas la nouvelle méthode
        del watson_agent.validator.get_validation_summary
        watson_agent.validator.validation_cache = {"val1": {}}
        
        summary = watson_agent.get_validation_summary()
        assert summary["total_validations"] > 0
        
        # Test du chemin normal
        watson_agent.validator.get_validation_summary = Mock(return_value={"summary": "ok"})
        result = watson_agent.get_validation_summary()
        
        watson_agent.validator.get_validation_summary.assert_called_once()
        assert result == {"summary": "ok"}
