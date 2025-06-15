"""
Tests unitaires pour WatsonJTMSAgent.
Valide les fonctionnalités spécialisées de l'agent critique/validateur.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

import semantic_kernel as sk
from semantic_kernel import Kernel

# Import du code à tester
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent
from argumentation_analysis.models.extended_belief_model import BeliefType, ConfidenceLevel
from argumentation_analysis.models.agent_communication_model import AgentMessage

@pytest.fixture
def mock_kernel():
    """Kernel mocké pour les tests"""
    kernel = Mock(spec=Kernel)
    return kernel

@pytest.fixture
def watson_agent(mock_kernel):
    """Agent Watson de test"""
    return WatsonJTMSAgent(mock_kernel, "watson_test")

class TestWatsonJTMSAgent:
    """Tests pour la classe WatsonJTMSAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, watson_agent):
        """Test d'initialisation de l'agent Watson"""
        assert watson_agent.agent_name == "watson_test"
        assert watson_agent.specialization == "critical_analysis"
        assert hasattr(watson_agent.validator, 'validation_history')
        assert hasattr(watson_agent.critique_engine, 'critique_patterns')
    
    @pytest.mark.asyncio
    async def test_validate_hypothesis(self, watson_agent):
        """Test de validation d'hypothèse"""
        # Ajouter d'abord une hypothèse à valider
        hypothesis_data = {
            "content": "Colonel Moutarde a tué avec le couteau dans la bibliothèque",
            "supporting_evidence": ["couteau_trouve", "empreintes"],
            "confidence": 0.7
        }
        
        watson_agent.add_belief("hyp_test", {"type": "hypothesis"}, 0.7)
        
        result = await watson_agent.validate_hypothesis("hyp_test", hypothesis_data)
        
        assert result is not None
        assert "validation_result" in result
        assert "critique_points" in result
        assert "adjusted_confidence" in result
        assert "validation_reasoning" in result
        assert isinstance(result["validation_result"], bool)
    
    @pytest.mark.asyncio
    async def test_critique_reasoning_chain(self, watson_agent):
        """Test de critique de chaîne de raisonnement"""
        reasoning_chain = [
            {"step": "Couteau trouvé dans bibliothèque", "type": "evidence", "confidence": 0.9},
            {"step": "Empreintes de Moutarde sur couteau", "type": "evidence", "confidence": 0.8},
            {"step": "Donc Moutarde est le meurtrier", "type": "conclusion", "confidence": 0.6}
        ]
        
        result = await watson_agent.critique_reasoning_chain("chain_test", reasoning_chain)
        
        assert result is not None
        assert "chain_id" in result
        assert "logical_issues" in result
        assert "missing_evidence" in result
        assert "alternative_explanations" in result
        assert "revised_confidence" in result
    
    @pytest.mark.asyncio
    async def test_cross_validate_evidence(self, watson_agent):
        """Test de validation croisée d'indices"""
        evidence_set = [
            {"id": "ev1", "description": "Couteau ensanglanté", "reliability": 0.9},
            {"id": "ev2", "description": "Empreintes digitales", "reliability": 0.8},
            {"id": "ev3", "description": "Témoignage suspect", "reliability": 0.4}
        ]
        
        result = await watson_agent.cross_validate_evidence(evidence_set)
        
        assert result is not None
        assert "validation_summary" in result
        assert "reliability_scores" in result
        assert "contradictions" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_challenge_assumption(self, watson_agent):
        """Test de remise en question d'hypothèse"""
        assumption_data = {
            "assumption": "Le meurtrier était seul",
            "basis": ["une_seule_arme", "pas_de_temoin_multiple"],
            "confidence": 0.6
        }
        
        result = await watson_agent.challenge_assumption("assump_1", assumption_data)
        
        assert result is not None
        assert "challenge_id" in result
        assert "counter_arguments" in result
        assert "alternative_scenarios" in result
        assert "confidence_impact" in result
    
    @pytest.mark.asyncio
    async def test_process_jtms_inference(self, watson_agent):
        """Test du traitement d'inférence JTMS spécialisé"""
        context = "Validation des déductions de Sherlock sur le meurtre"
        
        result = await watson_agent.process_jtms_inference(context)
        
        assert result is not None
        assert "inference_type" in result
        assert result["inference_type"] == "critical_validation"
        assert "validation_points" in result
        assert "confidence" in result
    
    @pytest.mark.asyncio
    async def test_validate_reasoning_chain(self, watson_agent):
        """Test de validation de chaîne de raisonnement"""
        chain = [
            {"premise": "Arme du crime identifiée", "type": "evidence", "strength": 0.9},
            {"premise": "Suspect présent sur les lieux", "type": "evidence", "strength": 0.7},
            {"conclusion": "Suspect est coupable", "type": "deduction", "strength": 0.5}
        ]
        
        result = await watson_agent.validate_reasoning_chain(chain)
        
        assert result is not None
        assert "valid" in result
        assert "validation_details" in result
        assert "weak_links" in result
        assert "suggested_improvements" in result
    
    @pytest.mark.asyncio
    async def test_analyze_sherlock_conclusions(self, watson_agent):
        """Test d'analyse des conclusions de Sherlock"""
        sherlock_state = {
            "beliefs": {
                "conclusion_1": {
                    "name": "Colonel Moutarde coupable",
                    "confidence": 0.8,
                    "agent_source": "sherlock",
                    "context": {"evidence": ["couteau", "lieu"]}
                }
            },
            "session_summary": {
                "owner_agent": "sherlock"
            }
        }
        
        result = await watson_agent.analyze_sherlock_conclusions(sherlock_state)
        
        assert result is not None
        assert "analysis_id" in result
        assert "validated_conclusions" in result
        assert "challenged_conclusions" in result
        assert "overall_assessment" in result
    
    @pytest.mark.asyncio
    async def test_provide_alternative_theory(self, watson_agent):
        """Test de proposition de théorie alternative"""
        primary_theory = {
            "suspect": "Colonel Moutarde",
            "weapon": "Couteau",
            "location": "Bibliothèque",
            "confidence": 0.7
        }
        
        available_evidence = ["couteau_biblio", "cheveu_salon", "temoin_couloir"]
        
        result = await watson_agent.provide_alternative_theory("alt_theory_1", primary_theory, available_evidence)
        
        assert result is not None
        assert "theory_id" in result
        assert "alternative_suspect" in result or "alternative_weapon" in result or "alternative_location" in result
        assert "supporting_evidence" in result
        assert "plausibility_score" in result
    
    @pytest.mark.asyncio
    async def test_identify_logical_fallacies(self, watson_agent):
        """Test d'identification d'erreurs logiques"""
        reasoning_text = """
        Puisque le couteau était dans la bibliothèque, et que Colonel Moutarde était dans la bibliothèque,
        alors Colonel Moutarde a forcément utilisé le couteau. De plus, tous les militaires sont violents,
        donc Colonel Moutarde est nécessairement le meurtrier.
        """
        
        result = await watson_agent.identify_logical_fallacies("reasoning_1", reasoning_text)
        
        assert result is not None
        assert "fallacies_found" in result
        assert "severity_scores" in result
        assert "corrections_suggested" in result
    
    def test_get_validation_summary(self, watson_agent):
        """Test de résumé de validation"""
        # Simuler quelques validations
        watson_agent.validator.validation_history["val_1"] = {
            "hypothesis": "test_hyp",
            "result": True,
            "confidence": 0.8
        }
        
        summary = watson_agent.validator.get_validation_summary()
        
        assert summary is not None
        assert "total_validations" in summary
        assert "validation_rate" in summary
        assert "average_confidence" in summary
        assert "recent_validations" in summary
    
    def test_export_critique_state(self, watson_agent):
        """Test d'export d'état de critique"""
        # Ajouter quelques éléments de test
        watson_agent.critique_engine.critique_patterns["pattern_1"] = {
            "type": "logical_gap",
            "frequency": 3
        }
        
        state = watson_agent.critique_engine.export_critique_state()
        
        assert state is not None
        assert "agent_type" in state
        assert state["engine_type"] == "critique_engine"
        assert "critique_patterns" in state
        assert "last_critique_timestamp" in state

if __name__ == "__main__":
    # Tests rapides
    async def run_basic_watson_tests():
        from unittest.mock import Mock
        
        mock_kernel = Mock(spec=Kernel)
        agent = WatsonJTMSAgent(mock_kernel, "test_watson")
        
        print("Test de validation d'hypothèse...")
        agent.add_belief("test_hyp", {"type": "hypothesis"}, 0.7)
        result = await agent.validate_hypothesis("test_hyp", {"content": "Test hypothesis"})
        print(f"Résultat: {result}")
        
        print("Test de critique de raisonnement...")
        chain = [{"step": "test", "type": "evidence"}]
        result2 = await agent.critique_reasoning_chain("test_chain", chain)
        print(f"Résultat: {result2}")
        
        print("✅ Tests Watson de base passent!")
    
    asyncio.run(run_basic_watson_tests())