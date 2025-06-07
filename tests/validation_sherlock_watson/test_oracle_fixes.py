#!/usr/bin/env python3
"""Script de test rapide pour vérifier nos corrections Oracle."""

import sys
import asyncio
import os
from unittest.mock import Mock, AsyncMock

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent
from argumentation_analysis.agents.core.oracle.permissions import QueryType

async def test_oracle_fixes():
    """Test rapide des corrections Oracle."""
    print("=== Test des corrections Oracle ===")
    
    # Création des mocks
    mock_kernel = Mock()
    mock_dataset_manager = Mock()
    mock_permission_manager = Mock()
    mock_permission_manager.is_authorized = Mock(return_value=True)
    mock_dataset_manager.permission_manager = mock_permission_manager
    
    # Création de l'agent
    agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        agent_name="TestAgent"
    )
    
    print("✓ Agent créé avec succès")
    
    # Test 1: validate_agent_permissions - success
    try:
        result = await agent.oracle_tools.validate_agent_permissions(
            target_agent="Watson",
            query_type="card_inquiry"
        )
        
        # Vérifier que le mock a été appelé
        mock_permission_manager.is_authorized.assert_called_with(
            "Watson",
            QueryType.CARD_INQUIRY
        )
        
        # Vérifier le message de succès
        assert "Permission accordée" in result
        assert "Watson" in result
        assert "card_inquiry" in result
        print("✓ Test validate_agent_permissions (success) - PASSÉ")
        
    except Exception as e:
        print(f"✗ Test validate_agent_permissions (success) - ÉCHEC: {e}")
        return False
    
    # Test 2: validate_agent_permissions - failure
    try:
        # Reconfigurer le mock pour retourner False
        mock_permission_manager.is_authorized.return_value = False
        mock_permission_manager.is_authorized.reset_mock()
        
        result = await agent.oracle_tools.validate_agent_permissions(
            target_agent="UnauthorizedAgent",
            query_type="admin_command"
        )
        
        # Vérifier que le mock a été appelé
        mock_permission_manager.is_authorized.assert_called_with(
            "UnauthorizedAgent",
            QueryType.ADMIN_COMMAND
        )
        
        # Vérifier le message de refus
        assert "Permission refusée" in result
        assert "UnauthorizedAgent" in result
        assert "admin_command" in result
        print("✓ Test validate_agent_permissions (failure) - PASSÉ")
        
    except Exception as e:
        print(f"✗ Test validate_agent_permissions (failure) - ÉCHEC: {e}")
        return False
    
    # Test 3: query_type_validation 
    try:
        # Test avec type de requête invalide - doit lever ValueError
        try:
            await agent.oracle_tools.query_oracle_dataset(
                query_type="invalid_query_type",
                query_params="{}"
            )
            print("✗ Test query_type_validation - ÉCHEC: ValueError non levée")
            return False
        except ValueError as ve:
            if "Type de requête invalide" in str(ve):
                print("✓ Test query_type_validation - PASSÉ")
            else:
                print(f"✗ Test query_type_validation - ÉCHEC: Message incorrect: {ve}")
                return False
        
    except Exception as e:
        print(f"✗ Test query_type_validation - ÉCHEC: {e}")
        return False
    
    print("\n🎉 Tous les tests sont PASSÉS !")
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_oracle_fixes())
        if result:
            print("\n✅ Corrections Oracle validées avec succès!")
            sys.exit(0)
        else:
            print("\n❌ Des corrections Oracle ont échoué.")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur lors des tests: {e}")
        sys.exit(1)