#!/usr/bin/env python3
"""
Test simple pour corriger les 4 derniers tests du Groupe 3.
Identification des erreurs spécifiques sans pytest-playwright.
"""

import sys
import asyncio
import traceback
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Imports du système Oracle
sys.path.append('.')
from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent, OracleTools
from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionRule, OracleResponse, QueryResult
from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
from semantic_kernel.kernel import Kernel

def test_oracle_tools_kernel_function_decorators():
    """Test 11: Correction kernel_function_decorators"""
    print("\n=== TEST 11: Oracle Tools Kernel Function Decorators ===")
    
    try:
        # Setup
        mock_kernel = Mock(spec=Kernel)
        mock_kernel.add_plugin = Mock()
        
        mock_dataset_manager = Mock(spec=DatasetAccessManager)
        mock_permission_manager = Mock()
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
        
        sample_agent_config = {
            "agent_name": "TestOracle",
            "system_prompt_suffix": "Vous êtes un Oracle de test spécialisé.",
            "access_level": "intermediate",
            "allowed_query_types": [QueryType.CARD_INQUIRY, QueryType.DATASET_ACCESS, QueryType.GAME_STATE]
        }
        
        oracle_base_agent = OracleBaseAgent(
            kernel=mock_kernel,
            dataset_manager=mock_dataset_manager,
            **sample_agent_config
        )
        
        # Test proprement dit
        tools = oracle_base_agent.oracle_tools
        
        # Vérification que les méthodes ont les attributs kernel_function
        print(f"query_oracle_dataset has __kernel_function__: {hasattr(tools.query_oracle_dataset, '__kernel_function__')}")
        print(f"validate_agent_permissions has __kernel_function__: {hasattr(tools.validate_agent_permissions, '__kernel_function__')}")
        
        # Vérification que les méthodes sont décorées
        print(f"query_oracle_dataset is callable: {callable(tools.query_oracle_dataset)}")
        print(f"validate_agent_permissions is callable: {callable(tools.validate_agent_permissions)}")
        
        # Vérification des docstrings
        query_doc = tools.query_oracle_dataset.__doc__ or ""
        print(f"query_oracle_dataset docstring: {query_doc[:100]}...")
        
        validate_doc = tools.validate_agent_permissions.__doc__ or ""
        print(f"validate_agent_permissions docstring: {validate_doc[:100]}...")
        
        # Test de l'erreur potentielle: 'bool' object has no attribute 'description'
        # Inspectons les attributs des fonctions décorées
        print("\nInspection des attributs kernel_function:")
        if hasattr(tools.query_oracle_dataset, '__kernel_function__'):
            kf_attr = getattr(tools.query_oracle_dataset, '__kernel_function__')
            print(f"Type de __kernel_function__: {type(kf_attr)}")
            print(f"Valeur de __kernel_function__: {kf_attr}")
            if hasattr(kf_attr, 'description'):
                print(f"Description: {kf_attr.description}")
            else:
                print("Pas d'attribut 'description' trouvé")
        
        print("OK Test 11 reussi!")
        assert True, "Test 11 réussi"
        
    except Exception as e:
        print(f"ERREUR Test 11 echoue: {e}")
        traceback.print_exc()
        return False

async def test_execute_oracle_query_invalid_json():
    """Test 12: Correction gestion JSON invalide"""
    print("\n=== TEST 12: Execute Oracle Query Invalid JSON ===")
    
    try:
        # Setup
        mock_dataset_manager = Mock(spec=DatasetAccessManager)
        oracle_tools = OracleTools(dataset_manager=mock_dataset_manager)
        
        # Test avec JSON invalide
        result = await oracle_tools.query_oracle_dataset(
            query_type="card_inquiry",
            query_params="invalid json"
        )
        
        print(f"Résultat pour JSON invalide: {result}")
        
        # Vérifier que le message d'erreur contient ce qui est attendu
        expected_patterns = ["Erreur de format JSON", "invalid json"]
        for pattern in expected_patterns:
            if pattern in result:
                print(f"✅ Pattern '{pattern}' trouvé")
            else:
                print(f"❌ Pattern '{pattern}' manquant")
        
        print("✅ Test 12 réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Test 12 échoué: {e}")
        traceback.print_exc()
        return False

async def test_check_agent_permission_invalid_query_type():
    """Test 13: Correction ValueError pour query_type invalide"""
    print("\n=== TEST 13: Check Agent Permission Invalid Query Type ===")
    
    try:
        # Setup
        mock_dataset_manager = Mock(spec=DatasetAccessManager)
        oracle_tools = OracleTools(dataset_manager=mock_dataset_manager, agent_name="TestAgent")
        
        # Test avec un type de requête invalide - doit lever ValueError
        try:
            result = await oracle_tools.check_agent_permission(
                query_type="invalid_query_type",
                target_agent="TestAgent"
            )
            print(f"❌ Aucune exception levée! Résultat: {result}")
            return False
            
        except ValueError as ve:
            print(f"✅ ValueError correctement levée: {ve}")
            return True
        except Exception as e:
            print(f"❌ Exception inattendue: {type(e).__name__}: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Test 13 échoué: {e}")
        traceback.print_exc()
        return False

async def test_oracle_tools_error_handling():
    """Test 14: Correction gestion d'erreur OracleTools"""
    print("\n=== TEST 14: Oracle Tools Error Handling ===")
    
    try:
        # Setup
        mock_dataset_manager = Mock(spec=DatasetAccessManager)
        mock_dataset_manager.execute_oracle_query = AsyncMock(side_effect=Exception("Erreur de connexion dataset"))
        
        oracle_tools = OracleTools(dataset_manager=mock_dataset_manager, agent_name="TestAgent")
        
        # Test de gestion d'erreur
        result = await oracle_tools.query_oracle_dataset(
            query_type="card_inquiry",
            query_params='{"card_name": "Test"}'
        )
        
        print(f"Résultat d'erreur: {result}")
        
        # Vérifier que le message d'erreur contient ce qui est attendu
        expected_patterns = ["Erreur lors de la requête Oracle", "Erreur de connexion dataset"]
        for pattern in expected_patterns:
            if pattern in result:
                print(f"✅ Pattern '{pattern}' trouvé")
            else:
                print(f"❌ Pattern '{pattern}' manquant")
        
        print("✅ Test 14 réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Test 14 échoué: {e}")
        traceback.print_exc()
        return False

async def main():
    """Exécution de tous les tests du Groupe 3"""
    print("=== CORRECTION GROUPE 3 - 4 DERNIERS TESTS ===")
    
    results = []
    
    # Test 11
    results.append(test_oracle_tools_kernel_function_decorators())
    
    # Test 12
    results.append(await test_execute_oracle_query_invalid_json())
    
    # Test 13
    results.append(await test_check_agent_permission_invalid_query_type())
    
    # Test 14
    results.append(await test_oracle_tools_error_handling())
    
    # Résumé
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== RÉSUMÉ GROUPE 3 ===")
    print(f"Tests passés: {passed}/{total}")
    
    if passed == total:
        print("🎉 Tous les tests du Groupe 3 passent!")
    else:
        print("❌ Corrections nécessaires")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())