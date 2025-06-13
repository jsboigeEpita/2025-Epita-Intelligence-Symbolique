
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# tests/unit/argumentation_analysis/agents/core/oracle/test_dataset_access_manager_fixed.py
"""
Tests unitaires corrigés pour DatasetAccessManager et CluedoDatasetManager.
"""

import pytest
import asyncio
import time

from typing import Dict, Any, List
from datetime import datetime, timedelta

# Imports du système Oracle
from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    DatasetAccessManager, 
    CluedoDatasetManager,
    QueryCache
)
from argumentation_analysis.agents.core.oracle.permissions import (
    QueryType, 
    PermissionRule, 
    OracleResponse, 
    QueryResult,
    PermissionManager
)
from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset, RevealPolicy


class TestQueryCache:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour le système de cache des requêtes."""
    
    @pytest.fixture
    def query_cache(self):
        """Cache avec configuration de test."""
        return QueryCache(max_size=3, ttl_seconds=2)
    
    def test_cache_initialization(self, query_cache):
        """Test l'initialisation du cache."""
        assert query_cache.max_size == 3
        assert query_cache.ttl_seconds == 2
        assert len(query_cache._cache) == 0
        assert len(query_cache._access_times) == 0
    
    def test_cache_operations(self, query_cache):
        """Test les opérations du cache."""
        result = QueryResult(
            success=True,
            data={"test": "value1"},
            message="Test result",
            query_type=QueryType.CARD_INQUIRY,
            timestamp=datetime.now()
        )
        
        # Test put/get
        query_cache.put("TestAgent", QueryType.CARD_INQUIRY, {"card": "knife"}, result)
        cached_result = query_cache.get("TestAgent", QueryType.CARD_INQUIRY, {"card": "knife"})
        assert cached_result is not None
        assert cached_result.data == {"test": "value1"}
        assert len(query_cache._cache) == 1
    
    def test_cache_clear(self, query_cache):
        """Test le vidage du cache."""
        result = QueryResult(
            success=True,
            data={},
            message="Test",
            query_type=QueryType.CARD_INQUIRY,
            timestamp=datetime.now()
        )
        
        query_cache.put("Agent1", QueryType.CARD_INQUIRY, {"card": "knife"}, result)
        query_cache.clear()
        
        assert len(query_cache._cache) == 0
        assert len(query_cache._access_times) == 0


class TestDatasetAccessManager:
    """Tests pour la classe DatasetAccessManager."""
    
    @pytest.fixture
    def mock_dataset(self):
        """Dataset Cluedo réel pour les tests."""
        # Utilise un CluedoDataset réel au lieu d'un mock
        return CluedoDataset(moriarty_cards=["Colonel Moutarde", "Revolver", "Cuisine"])

    @pytest.fixture
    def mock_permission_manager(self):
        """PermissionManager réel pour les tests."""
        # Utilise un PermissionManager réel au lieu d'un mock
        manager = PermissionManager()
        # Configurer des permissions de base pour les tests si nécessaire
        # Exemple : manager.add_permission_rule(PermissionRule("Sherlock", [QueryType.CARD_INQUIRY]))
        return manager
    
    @pytest.fixture
    def dataset_manager(self, mock_dataset, mock_permission_manager):
        """DatasetAccessManager configuré pour les tests."""
        return DatasetAccessManager(
            dataset=mock_dataset,
            permission_manager=mock_permission_manager
        )
    
    def test_dataset_access_manager_initialization(self, dataset_manager, mock_dataset, mock_permission_manager):
        """Test l'initialisation du DatasetAccessManager."""
        assert dataset_manager.dataset == mock_dataset
        assert dataset_manager.permission_manager == mock_permission_manager
        assert isinstance(dataset_manager.query_cache, QueryCache)
    
    def test_permission_validation(self, dataset_manager, mock_permission_manager):
        """Test la validation des permissions."""
        # Test autorisation réussie
        # Configurer une règle pour Sherlock
        dataset_manager.permission_manager.add_permission_rule(PermissionRule("Sherlock", [QueryType.CARD_INQUIRY]))
        
        result_sherlock_authorized = dataset_manager.permission_manager.is_authorized("Sherlock", QueryType.CARD_INQUIRY)
        assert result_sherlock_authorized is True
        
        # Test autorisation échouée pour un agent sans règle ou un type de requête non autorisé
        result_unknown_authorized = dataset_manager.permission_manager.is_authorized("UnknownAgent", QueryType.SUGGESTION_VALIDATION)
        assert result_unknown_authorized is False

        result_sherlock_unauthorized_type = dataset_manager.permission_manager.is_authorized("Sherlock", QueryType.SUGGESTION_VALIDATION)
        assert result_sherlock_unauthorized_type is False
    
    @pytest.mark.asyncio
    async def test_execute_query_success(self, dataset_manager, mock_dataset, mock_permission_manager):
        """Test l'exécution réussie d'une requête."""
        # S'assurer que l'agent a la permission
        mock_permission_manager.add_permission_rule(PermissionRule("Sherlock", [QueryType.CARD_INQUIRY]))
        
        # Test
        result = await dataset_manager.execute_query(
            agent_name="Sherlock",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "Colonel Moutarde"} # Utiliser une carte du dataset réel
        )
        
        # Vérifications
        assert result.success is True
        # Les données retournées par CluedoDataset.process_query pour CARD_INQUIRY
        # peuvent être plus complexes, par exemple:
        # {'card_info': {'name': 'Colonel Moutarde', 'type': 'suspect', 'owned_by': None, 'seen_by': []}}
        # ou {'revealed_card': 'Colonel Moutarde', 'holder': 'Moriarty'} si Moriarty la possède.
        # Pour un test simple, vérifions juste que data n'est pas vide si success.
        assert result.data is not None
        assert result.query_type == QueryType.CARD_INQUIRY
    
    @pytest.mark.asyncio
    async def test_permission_denied_query(self, dataset_manager, mock_permission_manager):
        """Test requête refusée pour permissions insuffisantes."""
        # S'assurer que l'agent n'a PAS la permission pour ce type de requête
        # mock_permission_manager.is_authorized est maintenant une vraie méthode,
        # elle retournera False si aucune règle n'autorise UnauthorizedAgent pour SUGGESTION_VALIDATION.
        
        # Test
        result = await dataset_manager.execute_query(
            agent_name="UnauthorizedAgent", # Cet agent n'a pas de règle de permission définie
            query_type=QueryType.SUGGESTION_VALIDATION,
            query_params={"suggestion": {"suspect": "Plum", "arme": "Poignard", "lieu": "Salon"}}
        )
        
        # Vérifications
        assert result.success is False
        assert "non autorisé" in result.message.lower()
        assert result.query_type == QueryType.SUGGESTION_VALIDATION
    
    def test_generate_cache_key(self, dataset_manager):
        """Test la génération de clés de cache."""
        key1 = dataset_manager._generate_cache_key(
            "Agent1", 
            QueryType.CARD_INQUIRY, 
            {"card": "knife"}
        )
        
        key2 = dataset_manager._generate_cache_key(
            "Agent1", 
            QueryType.CARD_INQUIRY, 
            {"card": "knife"}
        )
        
        key3 = dataset_manager._generate_cache_key(
            "Agent1", 
            QueryType.CARD_INQUIRY, 
            {"card": "rope"}
        )
        
        # Même paramètres = même clé
        assert key1 == key2
        # Paramètres différents = clés différentes
        assert key1 != key3
    
    def test_apply_permission_filters(self, dataset_manager):
        """Test l'application des filtres de permissions."""
        from argumentation_analysis.agents.core.oracle.permissions import QueryResult, QueryType
        
        test_data = {"sensitive": "data", "public": "info"}
        
        # Créer un QueryResult de test
        test_result = QueryResult(
            success=True,
            data=test_data,
            query_type=QueryType.CARD_INQUIRY
        )
        
        # Test avec données filtrées
        filtered_result = dataset_manager._apply_permission_filters(
            "TestAgent",  # agent_name
            test_result   # QueryResult
        )
        
        # Vérification que le résultat a été traité
        assert isinstance(filtered_result, QueryResult)
        assert filtered_result.success is True


class TestCluedoDatasetManager:
    """Tests pour la classe CluedoDatasetManager."""
    
    @pytest.fixture
    def mock_cluedo_dataset(self):
        """CluedoDataset réel pour les tests."""
        # Utilise un CluedoDataset réel au lieu d'un mock
        return CluedoDataset(moriarty_cards=["Professeur Violet", "Chandelier", "Bureau"])
    
    @pytest.fixture
    def cluedo_manager(self, mock_cluedo_dataset):
        """CluedoDatasetManager configuré pour les tests."""
        return CluedoDatasetManager(mock_cluedo_dataset)
    
    def test_cluedo_dataset_manager_initialization(self, cluedo_manager, mock_cluedo_dataset):
        """Test l'initialisation du CluedoDatasetManager."""
        assert cluedo_manager.dataset == mock_cluedo_dataset
        assert isinstance(cluedo_manager.permission_manager, PermissionManager)
    
    @pytest.mark.asyncio
    async def test_execute_oracle_query(self, cluedo_manager, mock_cluedo_dataset):
        """Test l'exécution d'une requête Oracle Cluedo."""
        # CluedoDatasetManager configure des permissions par défaut.
        # SherlockEnqueteAgent devrait avoir la permission CARD_INQUIRY par défaut.
        
        # Test avec un agent autorisé et une carte du dataset réel
        result = await cluedo_manager.execute_oracle_query(
            agent_name="SherlockEnqueteAgent", # Agent défini dans les permissions par défaut
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "Professeur Violet"} # Carte du dataset réel
        )
        
        # Vérifications
        assert result.authorized is True
        # La structure exacte de data dépend de l'implémentation de CluedoDataset.process_query
        # Pour ce test, nous vérifions que data n'est pas None et que le type de requête est correct.
        assert result.data is not None
        assert result.query_type == QueryType.CARD_INQUIRY
        assert result.agent_name == "SherlockEnqueteAgent"


class TestDatasetAccessManagerIntegration:
    """Tests d'intégration pour DatasetAccessManager."""
    
    @pytest.fixture
    def real_cluedo_dataset(self):
        """Dataset Cluedo réel pour tests d'intégration."""
        return CluedoDataset(moriarty_cards=["knife", "rope"])
    
    @pytest.fixture
    def integration_manager(self, real_cluedo_dataset):
        """Manager avec dataset réel."""
        return DatasetAccessManager(dataset=real_cluedo_dataset)
    
    @pytest.mark.asyncio
    async def test_real_query_execution_flow(self, integration_manager):
        """Test du flux complet d'exécution de requête."""
        # Test avec agent non autorisé (aucune permission configurée)
        result = await integration_manager.execute_query(
            agent_name="Sherlock",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "knife"}
        )
        
        # Vérification que le résultat est cohérent
        assert isinstance(result, QueryResult)
        assert result.query_type == QueryType.CARD_INQUIRY
    
    def test_real_permission_validation(self, integration_manager):
        """Test de validation de permissions avec données réelles."""
        # Test de vérification d'autorisation
        result_sherlock = integration_manager.permission_manager.is_authorized("Sherlock", QueryType.CARD_INQUIRY)
        result_watson = integration_manager.permission_manager.is_authorized("Watson", QueryType.SUGGESTION_VALIDATION)
        
        # Les résultats doivent être cohérents
        assert isinstance(result_sherlock, bool)
        assert isinstance(result_watson, bool)
    
    @pytest.mark.asyncio
    async def test_cache_performance_real_data(self, integration_manager):
        """Test des performances de cache avec données réelles."""
        # Première requête
        result1 = await integration_manager.execute_query(
            agent_name="Watson",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "rope"}
        )
        
        # Deuxième requête identique (devrait utiliser le cache)
        result2 = await integration_manager.execute_query(
            agent_name="Watson",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "rope"}
        )
        
        # Vérifications
        assert isinstance(result1, QueryResult)
        assert isinstance(result2, QueryResult)
        assert result1.query_type == result2.query_type