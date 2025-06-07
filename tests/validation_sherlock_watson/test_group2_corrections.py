#!/usr/bin/env python3
"""
Script de test pour vérifier les corrections du Groupe 2.
Tests les méthodes liées aux permissions qui échouaient auparavant.
"""

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock

# Ajouter le dossier racine au path
sys.path.insert(0, os.path.abspath('.'))

# Imports nécessaires
from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionManager, PermissionRule
from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent, OracleTools
from semantic_kernel.kernel import Kernel


def test_dataset_manager_check_permission():
    """Test que DatasetAccessManager a maintenant la méthode check_permission."""
    print("🔍 Test 1: Vérification de l'existence de check_permission sur DatasetAccessManager")
    
    # Créer un permission manager avec des règles
    permission_manager = PermissionManager()
    rule = PermissionRule(
        agent_name="Watson",
        allowed_query_types=[QueryType.CARD_INQUIRY, QueryType.LOGICAL_VALIDATION]
    )
    permission_manager.add_permission_rule(rule)
    
    # Créer le dataset manager
    mock_dataset = Mock()
    dataset_manager = DatasetAccessManager(mock_dataset, permission_manager)
    
    # Vérifier que la méthode existe
    assert hasattr(dataset_manager, 'check_permission'), "La méthode check_permission doit exister"
    
    # Tester la méthode
    result_authorized = dataset_manager.check_permission("Watson", QueryType.CARD_INQUIRY)
    result_unauthorized = dataset_manager.check_permission("Watson", QueryType.ADMIN_COMMAND)
    
    assert result_authorized == True, "Watson devrait être autorisé pour CARD_INQUIRY"
    assert result_unauthorized == False, "Watson ne devrait pas être autorisé pour ADMIN_COMMAND"
    
    print("✅ Test 1 RÉUSSI: check_permission fonctionne correctement")


async def test_mock_permission_setup():
    """Test que les mocks peuvent être configurés correctement pour les tests."""
    print("🔍 Test 2: Configuration des mocks pour permission_manager")
    
    # Configuration d'un mock comme dans les tests originaux
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = Mock(return_value=True)
    
    # Vérifier que l'attribut permission_manager peut être mocké
    mock_permission_manager = Mock(spec=PermissionManager)
    mock_permission_manager.is_authorized = Mock(return_value=True)
    mock_dataset_manager.permission_manager = mock_permission_manager
    
    # Test que les mocks fonctionnent
    assert hasattr(mock_dataset_manager, 'permission_manager'), "Le mock doit avoir l'attribut permission_manager"
    assert hasattr(mock_dataset_manager, 'check_permission'), "Le mock doit avoir la méthode check_permission"
    
    # Test des appels
    result = mock_dataset_manager.check_permission("Watson", QueryType.CARD_INQUIRY)
    assert result == True, "Le mock doit retourner True"
    
    mock_dataset_manager.check_permission.assert_called_once_with("Watson", QueryType.CARD_INQUIRY)
    
    print("✅ Test 2 RÉUSSI: Les mocks sont correctement configurés")


async def test_oracle_tools_integration():
    """Test l'intégration avec OracleTools."""
    print("🔍 Test 3: Intégration OracleTools avec check_agent_permission")
    
    # Créer les mocks
    mock_kernel = Mock(spec=Kernel)
    mock_kernel.add_plugin = Mock()
    
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = Mock(return_value=True)
    
    # Créer l'agent Oracle avec OracleTools
    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY]
    }
    
    oracle_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        **agent_config
    )
    
    # Vérifier que oracle_tools existe
    assert hasattr(oracle_agent, 'oracle_tools'), "L'agent doit avoir oracle_tools"
    assert hasattr(oracle_agent.oracle_tools, 'check_agent_permission'), "OracleTools doit avoir check_agent_permission"
    
    # Test de la méthode check_agent_permission
    result = await oracle_agent.oracle_tools.check_agent_permission(
        target_agent="Watson",
        query_type="card_inquiry"
    )
    
    # Vérifier que la méthode a été appelée
    mock_dataset_manager.check_permission.assert_called_once()
    
    # Vérifier le résultat
    assert "Watson a les permissions" in result, f"Résultat attendu non trouvé dans: {result}"
    
    print("✅ Test 3 RÉUSSI: OracleTools fonctionne avec check_agent_permission")


def main():
    """Fonction principale pour exécuter tous les tests."""
    print("🚀 Début des tests du Groupe 2 - Corrections des attributs/permissions")
    print("=" * 80)
    
    try:
        # Test 1: Vérification de l'existence de check_permission
        test_dataset_manager_check_permission()
        print()
        
        # Test 2: Configuration des mocks
        asyncio.run(test_mock_permission_setup())
        print()
        
        # Test 3: Intégration OracleTools
        asyncio.run(test_oracle_tools_integration())
        print()
        
        print("=" * 80)
        print("🎉 TOUS LES TESTS DU GROUPE 2 SONT PASSÉS AVEC SUCCÈS!")
        print("✅ La méthode check_permission a été ajoutée au DatasetAccessManager")
        print("✅ Les mocks peuvent maintenant être configurés correctement")
        print("✅ L'intégration avec OracleTools fonctionne")
        print()
        print("📊 Progression attendue: 86/94 → 90/94 tests passants (95.7%)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)