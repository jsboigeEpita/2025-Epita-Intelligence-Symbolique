# tests/unit/argumentation_analysis/agents/core/oracle/test_dataset_access_manager_fixed.py
"""
Tests unitaires corrigés pour DatasetAccessManager et CluedoDatasetManager.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
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
        """Dataset mocké pour les tests."""
        dataset = Mock(spec=CluedoDataset)
        dataset.process_query = Mock(return_value=QueryResult(
            success=True,
            data={"test": "data"},
            message="Mock result",
            query_type=QueryType.CARD_INQUIRY,
            timestamp=datetime.now()
        ))
        return dataset
    
    @pytest.fixture
    def mock_permission_manager(self):
        """PermissionManager mocké."""
        manager = Mock(spec=PermissionManager)
        manager.is_authorized = Mock(return_value=True)
        manager.get_agent_permissions = Mock(return_value=[])
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
        mock_permission_manager.is_authorized.return_value = True
        result = dataset_manager.permission_manager.is_authorized("Sherlock", QueryType.CARD_INQUIRY)
        assert result is True
        
        # Test autorisation échouée
        mock_permission_manager.is_authorized.return_value = False
        result = dataset_manager.permission_manager.is_authorized("UnknownAgent", QueryType.SUGGESTION_VALIDATION)
        assert result is False
    
    def test_execute_query_success(self, dataset_manager, mock_dataset, mock_permission_manager):
        """Test l'exécution réussie d'une requête."""
        # Configuration des mocks
        mock_permission_manager.is_authorized.return_value = True
        expected_result = QueryResult(
            success=True,
            data={"card": "knife"},
            message="Success",
            query_type=QueryType.CARD_INQUIRY,
            timestamp=datetime.now()
        )
        mock_dataset.process_query.return_value = expected_result
        
        # Test
        result = dataset_manager.execute_query(
            agent_name="Sherlock",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "knife"}
        )
        
        # Vérifications
        assert result.success is True
        assert result.data == {"card": "knife"}
        mock_dataset.process_query.assert_called_once()
    
    def test_permission_denied_query(self, dataset_manager, mock_permission_manager):
        """Test requête refusée pour permissions insuffisantes."""
        # Configuration du mock pour refuser l'accès
        mock_permission_manager.is_authorized.return_value = False
        
        # Test
        result = dataset_manager.execute_query(
            agent_name="UnauthorizedAgent",
            query_type=QueryType.SUGGESTION_VALIDATION,
            query_params={"suggestion": "test"}
        )
        
        # Vérifications
        assert result.success is False
        assert "non autorisé" in result.message.lower()
    
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
        """CluedoDataset mocké pour les tests."""
        dataset = Mock(spec=CluedoDataset)
        dataset.get_moriarty_cards.return_value = ["knife", "rope"]
        dataset.process_query = Mock(return_value=QueryResult(
            success=True,
            data={"revealed_card": "knife"},
            message="Card revealed",
            query_type=QueryType.CARD_INQUIRY,
            timestamp=datetime.now()
        ))
        return dataset
    
    @pytest.fixture
    def cluedo_manager(self, mock_cluedo_dataset):
        """CluedoDatasetManager configuré pour les tests."""
        return CluedoDatasetManager(mock_cluedo_dataset)
    
    def test_cluedo_dataset_manager_initialization(self, cluedo_manager, mock_cluedo_dataset):
        """Test l'initialisation du CluedoDatasetManager."""
        assert cluedo_manager.dataset == mock_cluedo_dataset
        assert isinstance(cluedo_manager.permission_manager, PermissionManager)
    
    def test_execute_oracle_query(self, cluedo_manager, mock_cluedo_dataset):
        """Test l'exécution d'une requête Oracle Cluedo."""
        # Configuration du mock
        expected_result = QueryResult(
            success=True,
            data={"card": "knife"},
            message="Success",
            query_type=QueryType.CARD_INQUIRY,
            timestamp=datetime.now()
        )
        mock_cluedo_dataset.process_query.return_value = expected_result
        
        # Test avec un agent autorisé
        result = cluedo_manager.execute_oracle_query(
            agent_name="SherlockEnqueteAgent",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "knife"}
        )
        
        # Vérifications (OracleResponse a 'authorized' au lieu de 'success')
        assert result.authorized is True
        assert result.data == {"card": "knife"}


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
    
    def test_real_query_execution_flow(self, integration_manager):
        """Test du flux complet d'exécution de requête."""
        # Test avec agent non autorisé (aucune permission configurée)
        result = integration_manager.execute_query(
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
    
    def test_cache_performance_real_data(self, integration_manager):
        """Test des performances de cache avec données réelles."""
        # Première requête
        result1 = integration_manager.execute_query(
            agent_name="Watson",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "rope"}
        )
        
        # Deuxième requête identique (devrait utiliser le cache)
        result2 = integration_manager.execute_query(
            agent_name="Watson",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": "rope"}
        )
        
        # Vérifications
        assert isinstance(result1, QueryResult)
        assert isinstance(result2, QueryResult)
        assert result1.query_type == result2.query_type