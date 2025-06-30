import pytest
#!/usr/bin/env python3
"""
Test de validation finale pour les 4 corrections du Groupe 3.
"""

import sys
import asyncio
import traceback


# Imports du système Oracle
sys.path.append('.')
from tests.utils.common_test_helpers import create_authentic_gpt4o_mini_instance
from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent, OracleTools
from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
from argumentation_analysis.agents.core.oracle.permissions import QueryType, OracleResponse, PermissionManager
from semantic_kernel.kernel import Kernel

@pytest.mark.asyncio
async def test_all_group3_fixes():
    """Test complet des 4 corrections appliquées"""
    print("=== VALIDATION FINALE GROUPE 3 ===")
    
    results = []
    
    # Setup de base
    mock_kernel = Mock(spec=Kernel)
    mock_kernel.add_plugin = Mock()
    
    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_permission_manager = Mock(spec=PermissionManager)
    mock_permission_manager.is_authorized = Mock(return_value=True)
    mock_dataset_manager.permission_manager = mock_permission_manager
    
    success_response = OracleResponse(
        authorized=True,
        message="Information révélée avec succès",
        data={"revealed_card": "Colonel Moutarde"},
        query_type=QueryType.CARD_INQUIRY
    )
    mock_dataset_manager.execute_oracle_query = AsyncMock(return_value=success_response)
    mock_dataset_manager.validate_agent_access = Mock(return_value=True)
    mock_dataset_manager.check_permission = Mock(return_value=True)
    
    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        agent_name="TestOracle",
        system_prompt_suffix="Test Oracle.",
        access_level="intermediate",
        allowed_query_types=[QueryType.CARD_INQUIRY, QueryType.DATASET_ACCESS, QueryType.GAME_STATE]
    )
    
    # TEST 11: kernel_function_decorators - maintenant devrait passer
    print("\n--- TEST 11: kernel_function_decorators (FIXED) ---")
    try:
        tools = oracle_base_agent.oracle_tools
        
        # Tests basiques qui ne devraient plus échouer
        assert hasattr(tools.query_oracle_dataset, "__kernel_function__")
        assert hasattr(tools.validate_agent_permissions, "__kernel_function__")
        assert callable(tools.query_oracle_dataset)
        assert callable(tools.validate_agent_permissions)
        
        # Tests des docstrings
        query_doc = tools.query_oracle_dataset.__doc__ or ""
        assert "Oracle" in query_doc or "dataset" in query_doc.lower()
        
        validate_doc = tools.validate_agent_permissions.__doc__ or ""
        assert "permission" in validate_doc.lower()
        
        print("OK Test 11 reussi!")
        results.append(True)
    except Exception as e:
        print(f"ERREUR Test 11: {e}")
        results.append(False)
    
    # TEST 12: invalid_json - maintenant devrait passer
    print("\n--- TEST 12: invalid_json (FIXED) ---")
    try:
        result = await tools.query_oracle_dataset(
            query_type="card_inquiry",
            query_params="invalid json"
        )
        
        if "Erreur de format JSON" in result:
            print("OK Test 12 reussi!")
            results.append(True)
        else:
            print(f"ERREUR Test 12: Message incorrect: {result}")
            results.append(False)
    except Exception as e:
        print(f"ERREUR Test 12: {e}")
        results.append(False)
    
    # TEST 13: invalid_query_type - devrait déjà passer
    print("\n--- TEST 13: invalid_query_type (SHOULD PASS) ---")
    try:
        try:
            result = await tools.check_agent_permission(
                query_type="invalid_query_type",
                target_agent="TestAgent"
            )
            print(f"ERREUR Test 13: Aucune ValueError levée! Résultat: {result}")
            results.append(False)
        except ValueError as ve:
            print(f"OK Test 13 reussi: ValueError levée: {ve}")
            results.append(True)
        except Exception as e:
            print(f"ERREUR Test 13: Exception inattendue: {type(e).__name__}: {e}")
            results.append(False)
    except Exception as e:
        print(f"ERREUR Test 13: {e}")
        results.append(False)
    
    # TEST 14: error_handling - maintenant devrait passer
    print("\n--- TEST 14: error_handling (FIXED) ---")
    try:
        mock_dataset_manager.execute_oracle_query = AsyncMock(side_effect=Exception("Erreur de connexion dataset"))
        
        result = await tools.query_oracle_dataset(
            query_type="card_inquiry",
            query_params='{"card_name": "Test"}'
        )
        
        if "Erreur lors de la requête Oracle" in result and "Erreur de connexion dataset" in result:
            print("OK Test 14 reussi!")
            results.append(True)
        else:
            print(f"ERREUR Test 14: Message incorrect: {result}")
            results.append(False)
    except Exception as e:
        print(f"ERREUR Test 14: {e}")
        results.append(False)
    
    # Résumé final
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== RÉSUMÉ VALIDATION GROUPE 3 ===")
    print(f"Tests passés: {passed}/{total}")
    
    if passed == total:
        print("🎉 TOUS LES TESTS DU GROUPE 3 PASSENT!")
        print("🎯 OBJECTIF 100% ATTEINT!")
        return True
    else:
        print("❌ Des corrections supplémentaires sont nécessaires")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_all_group3_fixes())
    if success:
        print("\n[OK] VALIDATION FINALE RÉUSSIE - GROUPE 3 CORRIGÉ À 100%")
    else:
        print("\n❌ VALIDATION FINALE ÉCHOUÉE - CORRECTIONS SUPPLÉMENTAIRES NÉCESSAIRES")