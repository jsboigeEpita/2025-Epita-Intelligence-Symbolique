"""
Tests unitaires pour SherlockJTMSAgent.
Valide les fonctionnalités spécialisées de l'agent détective.
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

from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.models.extended_belief_model import BeliefType, ConfidenceLevel

@pytest.fixture
def mock_kernel():
    """Kernel mocké pour les tests"""
    kernel = Mock(spec=Kernel)
    return kernel

@pytest.fixture
def sherlock_agent(mock_kernel):
    """Agent Sherlock de test"""
    return SherlockJTMSAgent(mock_kernel, "sherlock_test")

class TestSherlockJTMSAgent:
    """Tests pour la classe SherlockJTMSAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, sherlock_agent):
        """Test d'initialisation de l'agent Sherlock"""
        assert sherlock_agent.agent_name == "sherlock_test"
        assert hasattr(sherlock_agent, '_hypothesis_tracker')
        assert hasattr(sherlock_agent, '_evidence_manager')
        assert hasattr(sherlock_agent, '_base_sherlock')
    
    @pytest.mark.asyncio
    async def test_analyze_clue(self, sherlock_agent):
        """Test d'analyse d'indice"""
        clue_data = {
            "description": "Un couteau ensanglanté trouvé dans la bibliothèque",
            "location": "bibliotheque",
            "reliability": 0.9
        }
        
        result = await sherlock_agent.analyze_clues([clue_data])
        
        assert result is not None
        assert "processed_clues" in result
        assert "new_evidence_ids" in result
        assert len(result["new_evidence_ids"]) == 1
        
        # Vérifier qu'une croyance a été ajoutée
        beliefs = sherlock_agent.get_all_beliefs()
        assert any(evidence_id in beliefs for evidence_id in result["new_evidence_ids"])
    
    @pytest.mark.asyncio
    async def test_form_hypothesis(self, sherlock_agent):
        """Test de formation d'hypothèse"""
        # Ajouter quelques indices
        clue1_result = await sherlock_agent.analyze_clues([{"description": "Couteau", "location": "bibliotheque"}])
        clue2_result = await sherlock_agent.analyze_clues([{"description": "Bibliothèque fermée", "location": "bibliotheque"}])
        evidence_ids = clue1_result["new_evidence_ids"] + clue2_result["new_evidence_ids"]

        context = "Suspect: Colonel Moutarde, Arme: Couteau, Lieu: Bibliothèque"
        
        result = await sherlock_agent.formulate_hypothesis(context, evidence_ids)
        
        assert result is not None
        assert "hypothesis_id" in result
        assert "hypothesis" in result
        assert "confidence" in result
        
        # Vérifier que l'hypothèse est dans les croyances
        beliefs = sherlock_agent.get_all_beliefs()
        assert result["hypothesis_id"] in beliefs
    
    @pytest.mark.asyncio
    async def test_build_reasoning_chain(self, sherlock_agent):
        """Test de construction de chaîne de raisonnement"""
        # Ajouter des éléments
        await sherlock_agent.analyze_clue("trace_sang", {"description": "Traces de sang"})
        await sherlock_agent.analyze_clue("empreintes", {"description": "Empreintes de pas"})
        await sherlock_agent.form_hypothesis("suspect_principal", {"suspect": "Mme Leblanc"})
        
        chain_elements = ["trace_sang", "empreintes", "suspect_principal"]
        
        result = await sherlock_agent.build_reasoning_chain("chain_1", chain_elements)
        
        assert result is not None
        assert "chain_id" in result
        assert "logical_links" in result
        assert "overall_validity" in result
        
        # Vérifier que la chaîne est stockée
        assert "chain_1" in sherlock_agent.reasoning_chains
    
    @pytest.mark.asyncio
    async def test_process_jtms_inference(self, sherlock_agent):
        """Test du traitement d'inférence JTMS spécialisé"""
        context = "Analyse du meurtre dans la bibliothèque avec Colonel Moutarde"
        
        result = await sherlock_agent.process_jtms_inference(context)
        
        assert result is not None
        assert "inference_type" in result
        assert result["inference_type"] == "deductive_analysis"
        assert "deductions" in result
        assert "confidence" in result
    
    @pytest.mark.asyncio
    async def test_validate_reasoning_chain(self, sherlock_agent):
        """Test de validation de chaîne de raisonnement"""
        # Créer une chaîne simple
        chain = [
            {"premise": "Couteau trouvé", "type": "evidence"},
            {"premise": "Empreintes sur le couteau", "type": "evidence"},
            {"conclusion": "Le meurtrier a utilisé le couteau", "type": "deduction"}
        ]
        
        result = await sherlock_agent.validate_reasoning_chain(chain)
        
        assert result is not None
        assert "valid" in result
        assert "logical_gaps" in result
        assert "strength_score" in result
        assert isinstance(result["valid"], bool)
    
    @pytest.mark.asyncio
    async def test_cross_reference_evidence(self, sherlock_agent):
        """Test de recoupement d'indices"""
        # Ajouter plusieurs indices
        await sherlock_agent.analyze_clue("indice1", {"description": "Cheveu blond", "location": "salon"})
        await sherlock_agent.analyze_clue("indice2", {"description": "Parfum", "location": "salon"})
        await sherlock_agent.analyze_clue("indice3", {"description": "Cheveu blond", "location": "bibliotheque"})
        
        result = await sherlock_agent.cross_reference_evidence(["indice1", "indice2", "indice3"])
        
        assert result is not None
        assert "correlations" in result
        assert "patterns" in result
        assert "reliability_score" in result
    
    @pytest.mark.asyncio
    async def test_investigate_cluedo_case(self, sherlock_agent):
        """Test d'enquête complète sur un cas Cluedo"""
        case_data = {
            "suspects": ["Colonel Moutarde", "Mme Leblanc", "M. Violet"],
            "weapons": ["Couteau", "Corde", "Chandelier"],
            "locations": ["Bibliothèque", "Salon", "Cuisine"],
            "clues": [
                {"description": "Couteau ensanglanté", "location": "Bibliothèque"},
                {"description": "Cheveu blond", "location": "Bibliothèque"}
            ]
        }
        
        result = await sherlock_agent.investigate_cluedo_case("case_1", case_data)
        
        assert result is not None
        assert "case_id" in result
        assert "primary_hypothesis" in result
        assert "alternative_hypotheses" in result
        assert "evidence_analysis" in result
        assert "confidence_level" in result
    
    def test_get_investigation_summary(self, sherlock_agent):
        """Test de résumé d'enquête"""
        # Ajouter quelques éléments
        sherlock_agent.investigation_memory["case_1"] = {
            "clues": ["indice1", "indice2"],
            "hypotheses": ["hyp1"],
            "reasoning_chains": ["chain1"]
        }
        
        summary = sherlock_agent.get_investigation_summary("case_1")
        
        assert summary is not None
        assert "case_id" in summary
        assert "clues_analyzed" in summary
        assert "hypotheses_formed" in summary
        assert "reasoning_chains" in summary
        assert "session_statistics" in summary
    
    def test_export_investigation_state(self, sherlock_agent):
        """Test d'export d'état d'enquête"""
        # Ajouter quelques éléments de test
        sherlock_agent.reasoning_chains["test_chain"] = {
            "elements": ["a", "b", "c"],
            "validity": 0.8
        }
        
        state = sherlock_agent.export_investigation_state()
        
        assert state is not None
        assert "agent_type" in state
        assert state["agent_type"] == "sherlock_detective"
        assert "investigation_memory" in state
        assert "reasoning_chains" in state
        assert "session_state" in state

if __name__ == "__main__":
    # Tests rapides
    async def run_basic_sherlock_tests():
        from unittest.mock import Mock
        
        mock_kernel = Mock(spec=Kernel)
        agent = SherlockJTMSAgent(mock_kernel, "test_sherlock")
        
        print("Test d'analyse d'indice...")
        result = await agent.analyze_clue("test_clue", {"description": "Test clue"})
        print(f"Résultat: {result}")
        
        print("Test de formation d'hypothèse...")
        result2 = await agent.form_hypothesis("test_hyp", {"suspect": "Test"})
        print(f"Résultat: {result2}")
        
        print("✅ Tests Sherlock de base passent!")
    
    asyncio.run(run_basic_sherlock_tests())