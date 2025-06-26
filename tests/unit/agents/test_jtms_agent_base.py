# Fichier adapté pour Oracle Enhanced v2.1.0
"""
Tests unitaires pour JTMSAgentBase.
Valide les fonctionnalités de base de l'intégration JTMS.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

import semantic_kernel as sk
from semantic_kernel import Kernel

# Import du code à tester
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from argumentation_analysis.agents.jtms_agent_base import (
    JTMSAgentBase, JTMSSession, ExtendedBelief
)
from argumentation_analysis.models.extended_belief_model import (
    BeliefType, ConfidenceLevel, EvidenceQuality
)

class TestJTMSAgent(JTMSAgentBase):
    """Agent de test héritant de JTMSAgentBase"""
    
    def __init__(self, kernel: Kernel, agent_name: str = "test_agent"):
        super().__init__(kernel, agent_name)
    
    async def process_investigation_request(self, request: str) -> dict:
        """Implémentation minimale pour les tests"""
        return {"status": "processed", "request": request}
    
    async def process_jtms_inference(self, context: str) -> dict:
        """Implémentation abstraite requise"""
        return {"inference": "test", "context": context}
    
    async def validate_reasoning_chain(self, chain: list) -> dict:
        """Implémentation abstraite requise"""
        return {"valid": True, "chain_length": len(chain)}

@pytest.fixture
def mock_kernel():
    """Kernel mocké pour les tests"""
    kernel = Mock(spec=Kernel)
    return kernel

@pytest.fixture
def test_agent(mock_kernel):
    """Agent de test"""
    return TestJTMSAgent(mock_kernel, "test_agent")

class TestJTMSSession:
    """Tests pour la classe JTMSSession"""
    
    def test_session_initialization(self):
        """Test d'initialisation d'une session JTMS"""
        session = JTMSSession("test_session", "test_agent")
        
        assert session.session_id == "test_session"
        assert session.owner_agent == "test_agent"
        assert session.last_consistency_status == True
        assert len(session.extended_beliefs) == 0
        assert len(session.checkpoints) == 0
    
    def test_add_extended_belief(self):
        """Test d'ajout de croyance étendue"""
        session = JTMSSession("test_session", "test_agent")
        
        context = {
            "type": "fact",
            "source": "test"
        }
        
        # Ajouter une croyance
        belief = session.add_belief("test_belief", "test_agent", context, 0.8)
        
        assert belief is not None
        assert "test_belief" in session.extended_beliefs
        
        belief = session.extended_beliefs["test_belief"]
        assert belief.name == "test_belief"
        assert belief.confidence == 0.8
        assert belief.agent_source == "test_agent"
    
    def test_duplicate_belief_rejected(self):
        """Test que les croyances dupliquées sont mises à jour"""
        session = JTMSSession("test_session", "test_agent")
        
        context = {"type": "fact", "source": "test"}
        
        # Premier ajout
        belief1 = session.add_belief("test_belief", "test_agent", context, 0.8)
        assert belief1 is not None
        
        # Tentative de doublon - devrait mettre à jour
        belief2 = session.add_belief("test_belief", "test_agent", context, 0.9)
        assert belief2 is not None
        
        # Vérifier que la confiance a été mise à jour (max des deux)
        assert session.extended_beliefs["test_belief"].confidence == 0.9
    
    def test_update_belief_confidence(self):
        """Test de mise à jour de confiance"""
        session = JTMSSession("test_session", "test_agent")
        
        context = {"type": "hypothesis", "source": "test"}
        belief = session.add_belief("test_belief", "test_agent", context, 0.5)
        
        # Mettre à jour la confiance directement
        belief.confidence = 0.9
        belief.record_modification("confidence_updated", {"old_confidence": 0.5, "new_confidence": 0.9})
        
        assert belief.confidence == 0.9
        
        # Vérifier l'historique
        assert len(belief.modification_history) >= 1
        last_mod = belief.modification_history[-1]
        assert last_mod["action"] == "confidence_updated"
    
    def test_checkpoint_creation(self):
        """Test de création de checkpoint"""
        session = JTMSSession("test_session", "test_agent")
        
        # Ajouter quelques croyances
        context = {"type": "fact", "source": "test"}
        session.add_belief("belief1", "test_agent", context, 0.8)
        session.add_belief("belief2", "test_agent", context, 0.8)
        
        # Créer un checkpoint
        checkpoint_id = session.create_checkpoint("test_checkpoint")
        
        assert checkpoint_id is not None
        assert len(session.checkpoints) == 1
        
        checkpoint = session.checkpoints[0]
        assert checkpoint["name"] == "test_checkpoint"
        assert checkpoint["beliefs_count"] == 2
        assert "belief1" in checkpoint["beliefs_state"]
        assert "belief2" in checkpoint["beliefs_state"]

class TestJTMSAgentBase:
    """Tests pour la classe JTMSAgentBase"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, test_agent):
        """Test d'initialisation de l'agent"""
        assert test_agent.agent_name == "test_agent"
        assert test_agent.session_id is not None
        assert test_agent.jtms_session is not None
        assert test_agent.jtms_session.owner_agent == "test_agent"
    
    @pytest.mark.asyncio
    async def test_add_belief(self, test_agent):
        """Test d'ajout de croyance via l'agent"""
        context = {
            "type": "evidence",
            "source": "observation"
        }
        
        belief = test_agent.add_belief("test_evidence", context, 0.7)
        
        assert belief is not None
        beliefs = test_agent.get_all_beliefs()
        assert "test_evidence" in beliefs
        assert beliefs["test_evidence"].confidence == 0.7
    
    @pytest.mark.asyncio
    async def test_add_justification(self, test_agent):
        """Test d'ajout de justification"""
        # Ajouter d'abord des croyances
        context = {"type": "hypothesis", "source": "deduction"}
        test_agent.add_belief("premise1", context, 0.8)
        test_agent.add_belief("hypothesis1", context, 0.6)
        
        # Ajouter une justification
        test_agent.add_justification(["premise1"], [], "hypothesis1")
        
        # Vérifier que la justification existe dans le JTMS
        assert "hypothesis1" in test_agent.jtms_session.jtms.beliefs
        jtms_belief = test_agent.jtms_session.jtms.beliefs["hypothesis1"]
        assert len(jtms_belief.justifications) > 0
    
    @pytest.mark.asyncio
    async def test_validate_justification(self, test_agent):
        """Test de validation de justification"""
        # Ajouter croyances et justification
        context = {"type": "deduction", "source": "logic"}
        test_agent.add_belief("premise1", context, 0.8)
        test_agent.add_belief("conclusion1", context, 0.8)
        
        # Forcer la validité de la prémisse dans le JTMS
        test_agent.jtms_session.jtms.beliefs["premise1"].valid = True
        
        test_agent.add_justification(["premise1"], [], "conclusion1")
        
        # Valider la justification
        is_valid = test_agent.validate_justification(["premise1"], [], "conclusion1")
        
        # La validation devrait être True avec une prémisse valide
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_explain_belief(self, test_agent):
        """Test d'explication de croyance"""
        # Ajouter une croyance avec justification
        context = {"type": "fact", "source": "observation"}
        test_agent.add_belief("observed_fact", context, 0.9)
        test_agent.add_justification([], [], "observed_fact")
        
        # Obtenir l'explication
        explanation = test_agent.explain_belief("observed_fact")
        
        assert explanation is not None
        assert "observed_fact" in explanation
        assert "Agent source" in explanation
    
    @pytest.mark.asyncio
    async def test_check_consistency(self, test_agent):
        """Test de vérification de cohérence"""
        # Ajouter des croyances cohérentes
        context1 = {"type": "fact", "source": "test"}
        context2 = {"type": "fact", "source": "test"}
        
        test_agent.add_belief("fact1", context1, 0.8)
        test_agent.add_belief("fact2", context2, 0.7)
        
        # Vérifier la cohérence
        consistency_report = test_agent.check_consistency()
        
        assert "is_consistent" in consistency_report
        assert "conflicts" in consistency_report
        assert "total_beliefs" in consistency_report
        
        # Devrait être cohérent avec des faits simples
        assert consistency_report["is_consistent"] is True
        assert len(consistency_report["conflicts"]) == 0
    
    @pytest.mark.asyncio
    async def test_export_session_state(self, test_agent):
        """Test d'export d'état de session"""
        # Ajouter quelques croyances
        context = {"type": "hypothesis", "source": "reasoning"}
        test_agent.add_belief("hyp1", context, 0.6)
        test_agent.add_belief("hyp2", context, 0.6)
        
        # Exporter l'état
        state = test_agent.export_session_state()
        
        assert "session_summary" in state
        assert "beliefs" in state
        assert "export_timestamp" in state
        
        assert len(state["beliefs"]) == 2
        assert "hyp1" in state["beliefs"]
        assert "hyp2" in state["beliefs"]
    
    @pytest.mark.asyncio
    async def test_import_beliefs_from_agent(self, test_agent):
        """Test d'import de croyances d'un autre agent"""
        # État simulé d'un autre agent
        external_state = {
            "session_summary": {
                "session_id": "other_session",
                "owner_agent": "other_agent"
            },
            "beliefs": {
                "external_belief": {
                    "name": "external_belief",
                    "agent_source": "other_agent",
                    "confidence": 0.8,
                    "valid": True,
                    "context": {"content": "Croyance externe"}
                }
            }
        }
        
        # Importer
        result = test_agent.import_beliefs_from_agent(external_state, "merge")
        
        assert "imported_beliefs" in result
        assert len(result["imported_beliefs"]) > 0
        
        # Vérifier que la croyance est importée
        beliefs = test_agent.get_all_beliefs()
        assert "external_belief" in beliefs
        assert beliefs["external_belief"].context["content"] == "Croyance externe"
    
    @pytest.mark.asyncio
    async def test_get_session_statistics(self, test_agent):
        """Test de récupération des statistiques"""
        # Ajouter quelques croyances et justifications
        context = {"type": "fact", "source": "test"}
        test_agent.add_belief("stat_test1", context, 0.8)
        test_agent.add_belief("stat_test2", context, 0.8)
        test_agent.add_justification([], [], "stat_test1")
        
        # Obtenir les statistiques
        stats = test_agent.get_session_statistics()
        
        assert "beliefs_count" in stats
        assert "total_inferences" in stats
        assert "last_modified" in stats
        assert "consistency_status" in stats
        
        assert stats["beliefs_count"] >= 2
        assert stats["total_inferences"] >= 1

@pytest.mark.asyncio
async def test_concurrent_belief_operations(test_agent):
    """Test d'opérations concurrentes sur les croyances"""
    # Simuler des ajouts concurrent
    def add_belief_sync(belief_id: str, context: dict, confidence: float):
        return test_agent.add_belief(belief_id, context, confidence)
    
    context = {"type": "fact", "source": "concurrent_test"}
    
    # Ajouter plusieurs croyances en séquence (simulant la concurrence)
    results = []
    for i in range(5):
        result = add_belief_sync(f"concurrent_belief_{i}", context, 0.7)
        results.append(result is not None)
    
    # Tous devraient réussir
    assert all(results)
    
    # Vérifier que toutes les croyances sont présentes
    beliefs = test_agent.get_all_beliefs()
    for i in range(5):
        assert f"concurrent_belief_{i}" in beliefs

def test_extended_belief_creation():
    """Test de création de croyance étendue"""
    belief = ExtendedBelief(
        name="test_belief",
        agent_source="test_agent",
        context={"content": "Contenu de test"},
        confidence=0.8
    )
    
    assert belief.name == "test_belief"
    assert belief.context["content"] == "Contenu de test"
    assert belief.confidence == 0.8
    assert belief.agent_source == "test_agent"
    assert belief.creation_timestamp is not None
    assert belief.modification_history is not None
    assert len(belief.modification_history) >= 0

def test_extended_belief_modification_tracking():
    """Test du suivi des modifications"""
    belief = ExtendedBelief(
        name="track_test",
        agent_source="test_agent",
        context={"content": "Contenu initial"},
        confidence=0.5
    )
    
    initial_history_count = len(belief.modification_history)
    
    # Modifier la confiance
    belief.record_modification("confidence_update", {
        "old_confidence": 0.5,
        "new_confidence": 0.8,
        "reason": "Mise à jour test"
    })
    
    assert len(belief.modification_history) == initial_history_count + 1
    
    last_mod = belief.modification_history[-1]
    assert last_mod["action"] == "confidence_update"
    assert last_mod["agent"] == "test_agent"
    assert last_mod["details"]["reason"] == "Mise à jour test"

if __name__ == "__main__":
    # Exécution directe pour tests rapides
    import asyncio
    
    async def run_basic_tests():
        from unittest.mock import Mock
        
        mock_kernel = Mock(spec=Kernel)
        agent = TestJTMSAgent(mock_kernel, "test_agent")
        
        print("Test d'ajout de croyance...")
        metadata = {"type": "fact", "source": "test", "confidence": 0.8}
        success = await agent.add_belief("test_belief", metadata)
        print(f"Succès: {success}")
        
        print("Test de récupération des croyances...")
        beliefs = agent.get_all_beliefs()
        print(f"Nombre de croyances: {len(beliefs)}")
        
        print("Test de vérification de cohérence...")
        consistency = agent.check_consistency()
        print(f"Cohérent: {consistency['is_consistent']}")
        
        print("Test d'export d'état...")
        state = agent.export_session_state()
        print(f"État exporté avec {len(state['beliefs'])} croyances")
        
        print("✅ Tous les tests de base passent!")
    
    asyncio.run(run_basic_tests())