"""
Tests unitaires complets pour le système JTMS intégré avec Semantic Kernel
Couvre tous les composants : services, sessions, plugin SK, API REST et intégrations.
"""

import pytest
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Ajouter le chemin du projet
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import des services JTMS
from argumentation_analysis.services.jtms_service import JTMSService
from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager
from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import create_jtms_plugin, JTMSSemanticKernelPlugin
from argumentation_analysis.integrations.semantic_kernel_integration import create_minimal_jtms_integration

class TestJTMSService:
    """Tests pour le service JTMS centralisé."""
    
    @pytest.fixture
    async def jtms_service(self):
        """Fixture pour créer un service JTMS."""
        return JTMSService()
    
    @pytest.fixture
    async def session_manager(self, jtms_service):
        """Fixture pour créer un gestionnaire de sessions."""
        return JTMSSessionManager(jtms_service)
    
    @pytest.fixture
    async def test_session(self, session_manager):
        """Fixture pour créer une session de test."""
        session_id = await session_manager.create_session(
            agent_id="test_agent",
            session_name="Test_Session",
            metadata={"test": True}
        )
        return session_id
    
    @pytest.fixture
    async def test_instance(self, jtms_service, test_session):
        """Fixture pour créer une instance JTMS de test."""
        instance_id = await jtms_service.create_jtms_instance(
            session_id=test_session,
            strict_mode=False
        )
        return instance_id
    
    async def test_create_jtms_instance(self, jtms_service, test_session):
        """Test création d'instance JTMS."""
        instance_id = await jtms_service.create_jtms_instance(
            session_id=test_session,
            strict_mode=False
        )
        
        assert instance_id is not None
        assert instance_id.startswith("jtms_")
        assert instance_id in jtms_service.instances
        assert instance_id in jtms_service.metadata
        
        metadata = jtms_service.metadata[instance_id]
        assert metadata["session_id"] == test_session
        assert metadata["strict_mode"] is False
        assert metadata["beliefs_count"] == 0
    
    async def test_create_belief(self, jtms_service, test_instance):
        """Test création de croyances."""
        # Test création basique
        result = await jtms_service.create_belief(
            instance_id=test_instance,
            belief_name="test_belief",
            initial_value=None
        )
        
        assert result["name"] == "test_belief"
        assert result["valid"] is None
        assert result["non_monotonic"] is False
        assert result["justifications_count"] == 0
        
        # Test création avec valeur initiale
        result2 = await jtms_service.create_belief(
            instance_id=test_instance,
            belief_name="true_belief",
            initial_value=True
        )
        
        assert result2["name"] == "true_belief"
        assert result2["valid"] is True
    
    async def test_add_justification(self, jtms_service, test_instance):
        """Test ajout de justifications."""
        # Créer des croyances préalables
        await jtms_service.create_belief(test_instance, "A", None)
        await jtms_service.create_belief(test_instance, "B", None)
        await jtms_service.create_belief(test_instance, "C", None)
        
        # Ajouter une justification: A ∧ ¬B → C
        result = await jtms_service.add_justification(
            instance_id=test_instance,
            in_beliefs=["A"],
            out_beliefs=["B"],
            conclusion="C"
        )
        
        assert result["in_beliefs"] == ["A"]
        assert result["out_beliefs"] == ["B"]
        assert result["conclusion"] == "C"
        assert result["conclusion_status"] is None  # C devrait être None car A et B ne sont pas définis
    
    async def test_explain_belief(self, jtms_service, test_instance):
        """Test explication de croyances."""
        # Créer une croyance avec justification
        await jtms_service.create_belief(test_instance, "premise", True)
        await jtms_service.create_belief(test_instance, "conclusion", None)
        await jtms_service.add_justification(
            test_instance, ["premise"], [], "conclusion"
        )
        
        # Expliquer la conclusion
        explanation = await jtms_service.explain_belief(test_instance, "conclusion")
        
        assert explanation["belief_name"] == "conclusion"
        assert explanation["current_status"] is True  # Devrait être vraie grâce à la prémisse
        assert len(explanation["justifications"]) == 1
        assert explanation["justifications"][0]["is_valid"] is True
    
    async def test_query_beliefs(self, jtms_service, test_instance):
        """Test interrogation de croyances."""
        # Créer diverses croyances
        await jtms_service.create_belief(test_instance, "true_belief", True)
        await jtms_service.create_belief(test_instance, "false_belief", False)
        await jtms_service.create_belief(test_instance, "unknown_belief", None)
        
        # Tester query sans filtre
        all_beliefs = await jtms_service.query_beliefs(test_instance, None)
        assert all_beliefs["total_beliefs"] == 3
        assert all_beliefs["filtered_count"] == 3
        
        # Tester query avec filtre "valid"
        valid_beliefs = await jtms_service.query_beliefs(test_instance, "valid")
        assert valid_beliefs["filtered_count"] == 1
        assert valid_beliefs["beliefs"][0]["name"] == "true_belief"
        
        # Tester query avec filtre "invalid"
        invalid_beliefs = await jtms_service.query_beliefs(test_instance, "invalid")
        assert invalid_beliefs["filtered_count"] == 1
        assert invalid_beliefs["beliefs"][0]["name"] == "false_belief"
    
    async def test_get_jtms_state(self, jtms_service, test_instance):
        """Test récupération d'état complet."""
        # Créer un système simple
        await jtms_service.create_belief(test_instance, "A", True)
        await jtms_service.create_belief(test_instance, "B", None)
        await jtms_service.add_justification(test_instance, ["A"], [], "B")
        
        # Récupérer l'état
        state = await jtms_service.get_jtms_state(test_instance)
        
        assert state["instance_id"] == test_instance
        assert "beliefs" in state
        assert "justifications_graph" in state
        assert "statistics" in state
        
        stats = state["statistics"]
        assert stats["total_beliefs"] == 2
        assert stats["valid_beliefs"] == 2  # A et B devraient être vraies
        assert stats["total_justifications"] == 1
    
    async def test_set_belief_validity(self, jtms_service, test_instance):
        """Test modification de validité."""
        await jtms_service.create_belief(test_instance, "changeable", None)
        
        # Changer à True
        result = await jtms_service.set_belief_validity(test_instance, "changeable", True)
        assert result["old_value"] is None
        assert result["new_value"] is True
        
        # Changer à False
        result2 = await jtms_service.set_belief_validity(test_instance, "changeable", False)
        assert result2["old_value"] is True
        assert result2["new_value"] is False
    
    async def test_export_import_jtms_state(self, jtms_service, test_session):
        """Test export/import d'état."""
        # Créer une instance avec un état complexe
        instance1 = await jtms_service.create_jtms_instance(test_session, False)
        await jtms_service.create_belief(instance1, "exported_belief", True)
        await jtms_service.create_belief(instance1, "derived_belief", None)
        await jtms_service.add_justification(
            instance1, ["exported_belief"], [], "derived_belief"
        )
        
        # Exporter
        exported_data = await jtms_service.export_jtms_state(instance1, "json")
        assert isinstance(exported_data, str)
        
        # Importer dans une nouvelle instance
        instance2 = await jtms_service.import_jtms_state(test_session, exported_data, "json")
        
        # Vérifier que l'état est identique
        state1 = await jtms_service.get_jtms_state(instance1)
        state2 = await jtms_service.get_jtms_state(instance2)
        
        assert state1["statistics"]["total_beliefs"] == state2["statistics"]["total_beliefs"]
        assert state1["statistics"]["total_justifications"] == state2["statistics"]["total_justifications"]


class TestJTMSSessionManager:
    """Tests pour le gestionnaire de sessions JTMS."""
    
    @pytest.fixture
    async def jtms_service(self):
        return JTMSService()
    
    @pytest.fixture
    async def session_manager(self, jtms_service):
        return JTMSSessionManager(jtms_service)
    
    async def test_create_session(self, session_manager):
        """Test création de session."""
        session_id = await session_manager.create_session(
            agent_id="test_agent",
            session_name="Test Session",
            metadata={"key": "value"}
        )
        
        assert session_id is not None
        assert session_id.startswith("session_")
        assert session_id in session_manager.sessions
        
        session = session_manager.sessions[session_id]
        assert session["agent_id"] == "test_agent"
        assert session["session_name"] == "Test Session"
        assert session["metadata"]["key"] == "value"
        assert session["status"] == "active"
    
    async def test_get_session(self, session_manager):
        """Test récupération de session."""
        session_id = await session_manager.create_session("agent", "Session")
        
        session_info = await session_manager.get_session(session_id)
        
        assert session_info["session_id"] == session_id
        assert session_info["agent_id"] == "agent"
        assert session_info["session_name"] == "Session"
        assert "jtms_instances_info" in session_info
    
    async def test_list_sessions(self, session_manager):
        """Test listage de sessions."""
        # Compter les sessions existantes avant le test
        initial_all = await session_manager.list_sessions()
        initial_agent1 = await session_manager.list_sessions(agent_id="agent1")
        initial_agent2 = await session_manager.list_sessions(agent_id="agent2")
        
        # Créer plusieurs sessions
        await session_manager.create_session("agent1", "Session 1")
        await session_manager.create_session("agent2", "Session 2")
        await session_manager.create_session("agent1", "Session 3")
        
        # Lister toutes les sessions
        all_sessions = await session_manager.list_sessions()
        assert len(all_sessions) >= len(initial_all) + 3
        
        # Lister par agent - vérifier l'augmentation correcte
        final_agent1 = await session_manager.list_sessions(agent_id="agent1")
        final_agent2 = await session_manager.list_sessions(agent_id="agent2")
        
        assert len(final_agent1) == len(initial_agent1) + 2  # 2 nouvelles sessions pour agent1
        assert len(final_agent2) == len(initial_agent2) + 1  # 1 nouvelle session pour agent2
        assert all(s["agent_id"] == "agent1" for s in final_agent1)
        assert all(s["agent_id"] == "agent2" for s in final_agent2)
    
    async def test_create_checkpoint(self, session_manager, jtms_service):
        """Test création de checkpoint."""
        session_id = await session_manager.create_session("agent", "Session")
        instance_id = await jtms_service.create_jtms_instance(session_id, False)
        await session_manager.add_jtms_instance_to_session(session_id, instance_id)
        
        # Ajouter du contenu
        await jtms_service.create_belief(instance_id, "test_belief", True)
        
        # Créer un checkpoint
        checkpoint_id = await session_manager.create_checkpoint(
            session_id, "Test checkpoint"
        )
        
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("cp_")
        assert session_id in session_manager.checkpoints
        assert len(session_manager.checkpoints[session_id]) >= 1
    
    async def test_restore_checkpoint(self, session_manager, jtms_service):
        """Test restauration de checkpoint."""
        session_id = await session_manager.create_session("agent", "Session")
        instance_id = await jtms_service.create_jtms_instance(session_id, False)
        await session_manager.add_jtms_instance_to_session(session_id, instance_id)
        
        # État initial
        await jtms_service.create_belief(instance_id, "initial_belief", True)
        checkpoint_id = await session_manager.create_checkpoint(session_id, "Initial state")
        
        # Modifier l'état
        await jtms_service.create_belief(instance_id, "additional_belief", False)
        state_before_restore = await jtms_service.get_jtms_state(instance_id)
        assert state_before_restore["statistics"]["total_beliefs"] == 2
        
        # Restaurer
        success = await session_manager.restore_checkpoint(session_id, checkpoint_id)
        assert success is True
        
        # Vérifier la restauration (nouvelle instance créée)
        session_info = await session_manager.get_session(session_id)
        restored_instance = session_info["jtms_instances"][-1]  # Dernière instance
        restored_state = await jtms_service.get_jtms_state(restored_instance)
        assert restored_state["statistics"]["total_beliefs"] == 1
    
    async def test_delete_session(self, session_manager, jtms_service):
        """Test suppression de session."""
        session_id = await session_manager.create_session("agent", "Session")
        instance_id = await jtms_service.create_jtms_instance(session_id, False)
        await session_manager.add_jtms_instance_to_session(session_id, instance_id)
        
        # Vérifier existence
        assert session_id in session_manager.sessions
        assert instance_id in jtms_service.instances
        
        # Supprimer
        success = await session_manager.delete_session(session_id)
        assert success is True
        
        # Vérifier suppression
        assert session_id not in session_manager.sessions
        assert instance_id not in jtms_service.instances


class TestJTMSSemanticKernelPlugin:
    """Tests pour le plugin Semantic Kernel."""
    
    @pytest.fixture
    async def sk_plugin(self):
        return create_jtms_plugin()
    
    async def test_create_belief_function(self, sk_plugin):
        """Test fonction SK create_belief."""
        result = await sk_plugin.create_belief(
            belief_name="sk_test_belief",
            initial_value="true",
            agent_id="test_sk_agent"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["operation"] == "create_belief"
        assert result_data["belief"]["name"] == "sk_test_belief"
        assert result_data["belief"]["valid"] is True
    
    async def test_add_justification_function(self, sk_plugin):
        """Test fonction SK add_justification."""
        # Créer d'abord une croyance
        await sk_plugin.create_belief("premise", "true", agent_id="test_agent")
        
        result = await sk_plugin.add_justification(
            in_beliefs="premise",
            out_beliefs="",
            conclusion="conclusion",
            agent_id="test_agent"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["operation"] == "add_justification"
        assert result_data["justification"]["conclusion"] == "conclusion"
    
    async def test_query_beliefs_function(self, sk_plugin):
        """Test fonction SK query_beliefs."""
        # Créer quelques croyances
        await sk_plugin.create_belief("belief1", "true", agent_id="query_agent")
        await sk_plugin.create_belief("belief2", "false", agent_id="query_agent")
        
        result = await sk_plugin.query_beliefs(
            filter_status="all",
            agent_id="query_agent"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["operation"] == "query_beliefs"
        assert result_data["total_beliefs"] >= 2
        assert "natural_language_summary" in result_data
    
    async def test_explain_belief_function(self, sk_plugin):
        """Test fonction SK explain_belief."""
        # Créer une croyance avec justification
        await sk_plugin.create_belief("explainable", "true", agent_id="explain_agent")
        await sk_plugin.add_justification("explainable", "", "derived", agent_id="explain_agent")
        
        result = await sk_plugin.explain_belief(
            belief_name="derived",
            agent_id="explain_agent"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["operation"] == "explain_belief"
        assert result_data["belief_name"] == "derived"
        assert "natural_language_summary" in result_data
    
    async def test_get_jtms_state_function(self, sk_plugin):
        """Test fonction SK get_jtms_state."""
        # Créer un système simple
        await sk_plugin.create_belief("state_test", "true", agent_id="state_agent")
        
        result = await sk_plugin.get_jtms_state(
            include_graph="true",
            include_statistics="true",
            agent_id="state_agent"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["operation"] == "get_jtms_state"
        assert "beliefs" in result_data
        assert "statistics" in result_data
        assert "natural_language_summary" in result_data
    
    async def test_plugin_configuration(self, sk_plugin):
        """Test configuration du plugin."""
        # Tester configuration auto-création
        sk_plugin.configure_auto_creation(auto_session=False, auto_instance=False)
        assert sk_plugin.auto_create_session is False
        assert sk_plugin.auto_create_instance is False
        
        # Tester définition de sessions par défaut
        sk_plugin.set_default_session("test_session")
        assert sk_plugin.default_session_id == "test_session"
        
        # Tester statut du plugin
        status = await sk_plugin.get_plugin_status()
        assert status["plugin_name"] == "JTMSSemanticKernelPlugin"
        assert status["functions_count"] == 5
        assert len(status["functions"]) == 5


class TestJTMSIntegration:
    """Tests pour l'intégration complète."""
    
    @pytest.fixture
    async def integration(self):
        return create_minimal_jtms_integration()
    
    async def test_create_reasoning_session(self, integration):
        """Test création de session de raisonnement."""
        session_id, instance_id = await integration.create_reasoning_session(
            agent_id="reasoning_agent",
            session_name="Reasoning Test"
        )
        
        assert session_id is not None
        assert instance_id is not None
        assert integration.jtms_plugin.default_session_id == session_id
        assert integration.jtms_plugin.default_instance_id == instance_id
    
    async def test_multi_agent_reasoning(self, integration):
        """Test raisonnement multi-agents."""
        agents_info = [
            {
                "agent_id": "agent1",
                "initial_beliefs": [
                    {"name": "belief1", "value": True},
                    {"name": "belief2", "value": False}
                ]
            },
            {
                "agent_id": "agent2",
                "initial_beliefs": [
                    {"name": "belief3", "value": True}
                ]
            }
        ]
        
        result = await integration.multi_agent_reasoning(agents_info)
        
        assert "shared_session_id" in result
        assert "shared_instance_id" in result
        assert len(result["participating_agents"]) == 2
        assert result["final_shared_state"]["statistics"]["total_beliefs"] >= 3
    
    async def test_checkpoint_with_description(self, integration):
        """Test création de checkpoint avec description auto."""
        session_id, instance_id = await integration.create_reasoning_session("checkpoint_agent")
        
        # Ajouter du contenu
        await integration.jtms_service.create_belief(instance_id, "checkpoint_belief", True)
        
        # Créer checkpoint avec description auto
        checkpoint_id = await integration.create_checkpoint_with_description(session_id)
        
        assert checkpoint_id is not None
        # Vérifier que le checkpoint contient des informations sur les croyances
        checkpoints = integration.session_manager.checkpoints[session_id]
        latest_checkpoint = next(cp for cp in checkpoints if cp["checkpoint_id"] == checkpoint_id)
        assert "croyances" in latest_checkpoint["description"]


class TestErrorHandling:
    """Tests pour la gestion d'erreurs."""
    
    @pytest.fixture
    async def jtms_service(self):
        return JTMSService()
    
    async def test_invalid_instance_id(self, jtms_service):
        """Test avec ID d'instance invalide."""
        with pytest.raises(ValueError, match="Instance JTMS non trouvée"):
            await jtms_service.create_belief("invalid_instance", "test", None)
    
    async def test_invalid_belief_name(self, jtms_service):
        """Test avec nom de croyance invalide."""
        session_id = "test_session"
        instance_id = await jtms_service.create_jtms_instance(session_id, False)
        
        with pytest.raises(ValueError, match="Croyance non trouvée"):
            await jtms_service.explain_belief(instance_id, "nonexistent_belief")
    
    async def test_invalid_filter_status(self, jtms_service):
        """Test avec statut de filtre invalide pour le plugin SK."""
        sk_plugin = create_jtms_plugin(jtms_service, None)
        
        result = await sk_plugin.query_beliefs(filter_status="invalid_filter")
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert "Filtre invalide" in result_data["error"]


@pytest.mark.asyncio
class TestPerformance:
    """Tests de performance pour le système JTMS."""
    
    async def test_large_belief_system(self):
        """Test avec un grand nombre de croyances."""
        jtms_service = JTMSService()
        session_id = "perf_session"
        instance_id = await jtms_service.create_jtms_instance(session_id, False)
        
        # Créer 100 croyances
        start_time = asyncio.get_event_loop().time()
        
        for i in range(100):
            await jtms_service.create_belief(instance_id, f"belief_{i}", i % 2 == 0)
        
        creation_time = asyncio.get_event_loop().time() - start_time
        
        # Interroger toutes les croyances
        query_start = asyncio.get_event_loop().time()
        result = await jtms_service.query_beliefs(instance_id, None)
        query_time = asyncio.get_event_loop().time() - query_start
        
        assert result["total_beliefs"] == 100
        assert creation_time < 5.0  # Moins de 5 secondes pour créer 100 croyances
        assert query_time < 1.0     # Moins de 1 seconde pour interroger
    
    async def test_complex_justification_network(self):
        """Test avec un réseau complexe de justifications."""
        jtms_service = JTMSService()
        session_id = "complex_session"
        instance_id = await jtms_service.create_jtms_instance(session_id, False)
        
        # Créer une hiérarchie de croyances
        beliefs = [f"level_{i}_{j}" for i in range(5) for j in range(10)]
        
        for belief in beliefs:
            await jtms_service.create_belief(instance_id, belief, None)
        
        # Créer des justifications entre niveaux
        start_time = asyncio.get_event_loop().time()
        
        for i in range(4):
            for j in range(10):
                current_belief = f"level_{i}_{j}"
                next_belief = f"level_{i+1}_{j}"
                
                await jtms_service.add_justification(
                    instance_id, [current_belief], [], next_belief
                )
        
        justification_time = asyncio.get_event_loop().time() - start_time
        
        # Obtenir l'état final
        state = await jtms_service.get_jtms_state(instance_id)
        
        assert state["statistics"]["total_beliefs"] == 50
        assert state["statistics"]["total_justifications"] == 40
        assert justification_time < 10.0  # Moins de 10 secondes pour un réseau complexe


# Configuration pytest
def pytest_configure(config):
    """Configuration pytest pour les tests JTMS."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as asyncio test"
    )

if __name__ == "__main__":
    # Exécuter les tests directement
    pytest.main([__file__, "-v", "--tb=short"])