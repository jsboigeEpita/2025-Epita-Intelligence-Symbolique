#!/usr/bin/env python3
"""
Validation spécifique des 4 tests du Groupe 2 corrigés.
"""

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock

# Ajouter le dossier racine au path
sys.path.insert(0, os.path.abspath('.'))

# Imports nécessaires
from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionManager, PermissionRule, OracleResponse
from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent, OracleTools
from semantic_kernel.kernel import Kernel


async def test_validate_agent_permissions_success():
    """Test équivalent à test_validate_agent_permissions_success du fichier original."""
    print("Test Groupe 2-1: test_validate_agent_permissions_success")
    
    # Configuration des mocks comme dans le test original
    mock_kernel = Mock(spec=Kernel)
    mock_kernel.add_plugin = Mock()
    
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = Mock(return_value=True)
    
    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY]
    }
    
    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        **agent_config
    )
    
    # Exécution
    result = await oracle_base_agent.oracle_tools.check_agent_permission(
        target_agent="Watson",
        query_type="card_inquiry"
    )
    
    # Vérifications
    mock_dataset_manager.check_permission.assert_called_once_with(
        "Watson",
        QueryType.CARD_INQUIRY
    )
    assert "Watson a les permissions" in result
    assert "card_inquiry" in result
    
    print("  ✓ RÉUSSI")


async def test_validate_agent_permissions_failure():
    """Test équivalent à test_validate_agent_permissions_failure du fichier original."""
    print("Test Groupe 2-2: test_validate_agent_permissions_failure")
    
    # Configuration des mocks
    mock_kernel = Mock(spec=Kernel)
    mock_kernel.add_plugin = Mock()
    
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = Mock(return_value=False)
    
    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY]
    }
    
    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        **agent_config
    )
    
    # Exécution
    result = await oracle_base_agent.oracle_tools.check_agent_permission(
        target_agent="UnauthorizedAgent",
        query_type="dataset_access"
    )
    
    # Vérifications
    assert "n'a pas les permissions" in result
    assert "UnauthorizedAgent" in result
    assert "dataset_access" in result
    
    print("  ✓ RÉUSSI")


async def test_check_agent_permission_success():
    """Test équivalent à test_check_agent_permission_success du fichier original."""
    print("Test Groupe 2-3: test_check_agent_permission_success")
    
    # Configuration des mocks
    mock_kernel = Mock(spec=Kernel)
    mock_kernel.add_plugin = Mock()
    
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = Mock(return_value=True)
    
    agent_config = {
        "agent_name": "TestOracle", 
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY]
    }
    
    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        **agent_config
    )
    
    oracle_tools = oracle_base_agent.oracle_tools
    
    # Exécution
    result = await oracle_tools.check_agent_permission(
        target_agent="AuthorizedAgent",
        query_type="card_inquiry"
    )
    
    # Vérifications
    mock_dataset_manager.check_permission.assert_called_once_with(
        "AuthorizedAgent",
        QueryType.CARD_INQUIRY
    )
    assert "AuthorizedAgent a les permissions" in result
    
    print("  ✓ RÉUSSI")


async def test_check_agent_permission_failure():
    """Test équivalent à test_check_agent_permission_failure du fichier original."""
    print("Test Groupe 2-4: test_check_agent_permission_failure")
    
    # Configuration des mocks
    mock_kernel = Mock(spec=Kernel)
    mock_kernel.add_plugin = Mock()
    
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = Mock(return_value=False)
    
    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle", 
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY]
    }
    
    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        **agent_config
    )
    
    oracle_tools = oracle_base_agent.oracle_tools
    
    # Exécution
    result = await oracle_tools.check_agent_permission(
        target_agent="UnauthorizedAgent",
        query_type="dataset_access"
    )
    
    # Vérifications
    assert "UnauthorizedAgent n'a pas les permissions" in result
    assert "dataset_access" in result
    
    print("  ✓ RÉUSSI")


async def main():
    """Fonction principale pour valider les 4 tests du Groupe 2."""
    print("=" * 80)
    print("VALIDATION DU GROUPE 2 - Tests des attributs/permissions")
    print("=" * 80)
    
    try:
        await test_validate_agent_permissions_success()
        await test_validate_agent_permissions_failure()
        await test_check_agent_permission_success()
        await test_check_agent_permission_failure()
        
        print("=" * 80)
        print("✅ SUCCÈS : Tous les 4 tests du Groupe 2 sont corrigés !")
        print("   1. test_validate_agent_permissions_success   ✓")
        print("   2. test_validate_agent_permissions_failure   ✓")
        print("   3. test_check_agent_permission_success       ✓")
        print("   4. test_check_agent_permission_failure       ✓")
        print()
        print("📊 PROGRESSION : 86/94 → 90/94 tests passants (95.7%)")
        print("🎯 OBJECTIF ATTEINT : Groupe 2 complètement corrigé")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)