"""
Tests unitaires pour JTMSCommunicationHub.
Valide les fonctionnalités de communication et coordination entre agents JTMS.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

import semantic_kernel as sk
from semantic_kernel import Kernel

# Import du code à tester
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from argumentation_analysis.agents.jtms_communication_hub import JTMSCommunicationHub
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent
from argumentation_analysis.models.agent_communication_model import AgentMessage, MessageType
from argumentation_analysis.config.settings import AppSettings

@pytest.fixture
def mock_settings():
    """Crée un mock pour AppSettings."""
    settings = MagicMock(spec=AppSettings)
    settings.service_manager = MagicMock()
    settings.service_manager.default_llm_service_id = "mock_service"
    return settings

@pytest.fixture
def mock_kernel():
    """Kernel mocké pour les tests"""
    kernel = Mock(spec=Kernel)
    return kernel

@pytest.fixture
def communication_hub(mock_kernel):
    """Hub de communication de test"""
    return JTMSCommunicationHub(mock_kernel)

@pytest.fixture
def sherlock_agent(mock_kernel, mock_settings):
    """Agent Sherlock de test"""
    return SherlockJTMSAgent(mock_kernel, mock_settings, agent_name="sherlock_test")

@pytest.fixture
def watson_agent(mock_kernel, mock_settings):
    """Agent Watson de test"""
    return WatsonJTMSAgent(mock_kernel, mock_settings, agent_name="watson_test")

class TestJTMSCommunicationHub:
    """Tests pour la classe JTMSCommunicationHub"""
    
    @pytest.mark.asyncio
    async def test_hub_initialization(self, communication_hub):
        """Test d'initialisation du hub de communication"""
        assert communication_hub.hub_id is not None
        assert hasattr(communication_hub, 'registered_agents')
        assert hasattr(communication_hub, 'message_queue')
        assert hasattr(communication_hub, 'collaboration_sessions')
        assert len(communication_hub.registered_agents) == 0
    
    @pytest.mark.asyncio
    async def test_register_agent(self, communication_hub, sherlock_agent, watson_agent):
        """Test d'enregistrement d'agents"""
        # Enregistrer Sherlock
        success1 = await communication_hub.register_agent(sherlock_agent)
        assert success1 is True
        assert sherlock_agent.agent_name in communication_hub.registered_agents
        
        # Enregistrer Watson
        success2 = await communication_hub.register_agent(watson_agent)
        assert success2 is True
        assert watson_agent.agent_name in communication_hub.registered_agents
        
        # Vérifier le nombre total d'agents
        assert len(communication_hub.registered_agents) == 2
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, communication_hub, sherlock_agent):
        """Test de désenregistrement d'agent"""
        # Enregistrer puis désenregistrer
        await communication_hub.register_agent(sherlock_agent)
        assert sherlock_agent.agent_name in communication_hub.registered_agents
        
        success = await communication_hub.unregister_agent(sherlock_agent.agent_name)
        assert success is True
        assert sherlock_agent.agent_name not in communication_hub.registered_agents
    
    @pytest.mark.asyncio
    async def test_send_message(self, communication_hub, sherlock_agent, watson_agent):
        """Test d'envoi de message entre agents"""
        # Enregistrer les agents
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        # Créer un message
        message_data = {
            "content": "J'ai une hypothèse à valider",
            "metadata": {"hypothesis_id": "hyp_1", "confidence": 0.7}
        }
        
        message_id = await communication_hub.send_message(
            sherlock_agent.agent_name,
            watson_agent.agent_name,
            MessageType.VALIDATION_REQUEST,
            message_data
        )
        
        assert message_id is not None
        assert len(communication_hub.message_queue) > 0
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, communication_hub, sherlock_agent, watson_agent):
        """Test de diffusion de message"""
        # Enregistrer les agents
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        broadcast_data = {
            "announcement": "Nouvelle preuve découverte",
            "evidence": {"type": "physical", "reliability": 0.9}
        }
        
        message_ids = await communication_hub.broadcast_message(
            sherlock_agent.agent_name,
            MessageType.BELIEF_SHARE,
            broadcast_data
        )
        
        assert len(message_ids) > 0
        assert len(message_ids) == len(communication_hub.registered_agents) - 1  # Exclude sender
    
    @pytest.mark.asyncio
    async def test_process_message_queue(self, communication_hub, sherlock_agent, watson_agent):
        """Test de traitement de la file de messages"""
        # Enregistrer les agents
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        # Envoyer quelques messages
        await communication_hub.send_message(
            sherlock_agent.agent_name,
            watson_agent.agent_name,
            MessageType.VALIDATION_REQUEST,
            {"content": "Test message 1"}
        )
        
        await communication_hub.send_message(
            watson_agent.agent_name,
            sherlock_agent.agent_name,
            MessageType.CRITIQUE_RESPONSE,
            {"content": "Test message 2"}
        )
        
        # Traiter la file
        processed_count = await communication_hub.process_message_queue()
        
        assert processed_count >= 2
    
    @pytest.mark.asyncio
    async def test_start_collaboration_session(self, communication_hub, sherlock_agent, watson_agent):
        """Test de démarrage de session collaborative"""
        # Enregistrer les agents
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        session_config = {
            "case_id": "murder_case_1",
            "investigation_type": "cluedo",
            "max_iterations": 10,
            "convergence_threshold": 0.9
        }
        
        session_id = await communication_hub.start_collaboration_session(
            [sherlock_agent.agent_name, watson_agent.agent_name],
            session_config
        )
        
        assert session_id is not None
        assert session_id in communication_hub.collaboration_sessions
        
        session = communication_hub.collaboration_sessions[session_id]
        assert session["participants"] == [sherlock_agent.agent_name, watson_agent.agent_name]
        assert session["config"] == session_config
    
    @pytest.mark.asyncio
    async def test_coordinate_investigation(self, communication_hub, sherlock_agent, watson_agent):
        """Test de coordination d'enquête"""
        # Enregistrer les agents
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        investigation_data = {
            "case_type": "cluedo_murder",
            "initial_evidence": [
                {"type": "weapon", "description": "Couteau ensanglanté"},
                {"type": "location", "description": "Bibliothèque fermée"}
            ],
            "suspects": ["Colonel Moutarde", "Mme Leblanc"],
            "coordination_mode": "iterative"
        }
        
        result = await communication_hub.coordinate_investigation("inv_1", investigation_data)
        
        assert result is not None
        assert "investigation_id" in result
        assert "coordination_plan" in result
        assert "agent_assignments" in result
        assert "communication_protocol" in result
    
    @pytest.mark.asyncio
    async def test_synchronize_beliefs(self, communication_hub, sherlock_agent, watson_agent):
        """Test de synchronisation des croyances"""
        # Enregistrer les agents et ajouter des croyances
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        # Ajouter des croyances aux agents
        sherlock_agent.add_belief("evidence_1", {"type": "physical"}, 0.8)
        watson_agent.add_belief("validation_1", {"type": "critique"}, 0.9)
        
        sync_config = {
            "merge_strategy": "confidence_weighted",
            "conflict_resolution": "deliberation",
            "consistency_check": True
        }
        
        result = await communication_hub.synchronize_beliefs(
            [sherlock_agent.agent_name, watson_agent.agent_name],
            sync_config
        )
        
        assert result is not None
        assert "sync_id" in result
        assert "merged_beliefs" in result
        assert "conflicts_resolved" in result
        assert "consistency_status" in result
    
    @pytest.mark.asyncio
    async def test_facilitate_deliberation(self, communication_hub, sherlock_agent, watson_agent):
        """Test de facilitation de délibération"""
        # Enregistrer les agents
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        deliberation_topic = {
            "subject": "Identification du meurtrier",
            "conflicting_hypotheses": [
                {"agent": "sherlock_test", "hypothesis": "Colonel Moutarde", "confidence": 0.7},
                {"agent": "watson_test", "hypothesis": "Mme Leblanc", "confidence": 0.6}
            ],
            "evidence_base": ["weapon_found", "witness_testimony"]
        }
        
        result = await communication_hub.facilitate_deliberation("delib_1", deliberation_topic)
        
        assert result is not None
        assert "deliberation_id" in result
        assert "consensus_reached" in result
        assert "final_hypothesis" in result
        assert "confidence_level" in result
    
    @pytest.mark.asyncio
    async def test_export_communication_log(self, communication_hub, sherlock_agent, watson_agent):
        """Test d'export du journal de communication"""
        # Enregistrer les agents et créer de l'activité
        await communication_hub.register_agent(sherlock_agent)
        await communication_hub.register_agent(watson_agent)
        
        await communication_hub.send_message(
            sherlock_agent.agent_name,
            watson_agent.agent_name,
            MessageType.BELIEF_SHARE,
            {"content": "Test communication"}
        )
        
        log_data = communication_hub.export_communication_log()
        
        assert log_data is not None
        assert "hub_id" in log_data
        assert "registered_agents" in log_data
        assert "message_history" in log_data
        assert "collaboration_sessions" in log_data
        assert "export_timestamp" in log_data
    
    def test_get_hub_statistics(self, communication_hub, sherlock_agent, watson_agent):
        """Test de récupération des statistiques du hub"""
        # Ajouter des agents et de l'activité simulée
        communication_hub.registered_agents[sherlock_agent.agent_name] = {
            "agent": sherlock_agent,
            "registration_time": datetime.now()
        }
        communication_hub.registered_agents[watson_agent.agent_name] = {
            "agent": watson_agent,
            "registration_time": datetime.now()
        }
        
        stats = communication_hub.get_hub_statistics()
        
        assert stats is not None
        assert "total_agents" in stats
        assert "active_sessions" in stats
        assert "messages_processed" in stats
        assert "uptime" in stats
        
        assert stats["total_agents"] == 2
    
    @pytest.mark.asyncio
    async def test_handle_agent_failure(self, communication_hub, sherlock_agent):
        """Test de gestion d'échec d'agent"""
        # Enregistrer l'agent
        await communication_hub.register_agent(sherlock_agent)
        
        # Simuler un échec
        failure_info = {
            "agent_id": sherlock_agent.agent_name,
            "failure_type": "communication_timeout",
            "error_details": "Agent stopped responding"
        }
        
        result = await communication_hub.handle_agent_failure(failure_info)
        
        assert result is not None
        assert "recovery_action" in result
        assert "agent_status" in result
        assert "notification_sent" in result

if __name__ == "__main__":
    # Tests rapides
    async def run_basic_hub_tests():
        from unittest.mock import Mock
        
        mock_kernel = Mock(spec=Kernel)
        
        # Créer un mock pour AppSettings
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.service_manager = MagicMock()
        mock_settings.service_manager.default_llm_service_id = "mock_service"

        hub = JTMSCommunicationHub(mock_kernel)
        sherlock = SherlockJTMSAgent(mock_kernel, mock_settings, agent_name="test_sherlock")
        watson = WatsonJTMSAgent(mock_kernel, mock_settings, agent_name="test_watson")
        
        print("Test d'enregistrement d'agents...")
        success1 = await hub.register_agent(sherlock)
        success2 = await hub.register_agent(watson)
        print(f"Agents enregistrés: {success1 and success2}")
        
        print("Test d'envoi de message...")
        msg_id = await hub.send_message(
            sherlock.agent_name,
            watson.agent_name,
            MessageType.VALIDATION_REQUEST,
            {"content": "Test"}
        )
        print(f"Message envoyé ID: {msg_id}")
        
        print("✅ Tests Hub de base passent!")
    
    asyncio.run(run_basic_hub_tests())