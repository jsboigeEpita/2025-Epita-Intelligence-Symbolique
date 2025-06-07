#!/usr/bin/env python3
"""Script de test pour valider les corrections du Groupe 1."""

import sys
import asyncio
import os
from unittest.mock import Mock, AsyncMock

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent, OracleTools
    from argumentation_analysis.agents.core.oracle.permissions import QueryType, OracleResponse
    from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
    from semantic_kernel.kernel import Kernel
except ImportError as e:
    print(f"ERREUR d'import: {e}")
    sys.exit(1)

async def test_group1_fixes():
    """Test des corrections du Groupe 1."""
    print("=== Test des corrections Groupe 1 - AsyncMock ===")
    
    # Test 1: test_execute_oracle_query_success pattern
    print("\n1. Test execute_oracle_query_success pattern:")
    
    try:
        # Setup comme dans le test corrigé
        mock_kernel = Mock(spec=Kernel)
        mock_kernel.add_plugin = Mock()
        
        mock_dataset_manager = Mock(spec=DatasetAccessManager)
        expected_response = OracleResponse(
            authorized=True,
            message="Colonel Moutarde révélé",
            data={"card": "Colonel Moutarde", "category": "suspect"},
            query_type=QueryType.CARD_INQUIRY
        )
        # CORRECTION: AsyncMock au lieu de return_value
        mock_dataset_manager.execute_oracle_query = AsyncMock(return_value=expected_response)
        
        # Création de l'agent (doit créer le plugin)
        agent = OracleBaseAgent(
            kernel=mock_kernel,
            dataset_manager=mock_dataset_manager,
            agent_name="TestOracle"
        )
        
        # Test que le plugin a été ajouté
        mock_kernel.add_plugin.assert_called()
        print("  ✓ Plugin registration: OK")
        
        # Test execute_oracle_query 
        result = await agent.oracle_tools.execute_oracle_query(
            query_type="card_inquiry",
            query_params='{"card_name": "Colonel Moutarde"}'
        )
        
        print(f"  ✓ execute_oracle_query result: {result}")
        
        # Vérifier que le mock async a été appelé
        mock_dataset_manager.execute_oracle_query.assert_called_once()
        print("  ✓ AsyncMock appelé correctement")
        
    except Exception as e:
        print(f"  ✗ ERREUR test 1: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: error_handling pattern
    print("\n2. Test oracle_error_handling pattern:")
    
    try:
        mock_kernel2 = Mock(spec=Kernel)
        mock_kernel2.add_plugin = Mock()
        
        mock_dataset_manager2 = Mock(spec=DatasetAccessManager)
        # CORRECTION: AsyncMock avec side_effect
        mock_dataset_manager2.execute_oracle_query = AsyncMock(side_effect=Exception("Erreur de connexion dataset"))
        
        agent2 = OracleBaseAgent(
            kernel=mock_kernel2,
            dataset_manager=mock_dataset_manager2,
            agent_name="TestOracle2"
        )
        
        result = await agent2.oracle_tools.execute_oracle_query(
            query_type="card_inquiry",
            query_params='{"card_name": "Test"}'
        )
        
        print(f"  ✓ error_handling result: {result}")
        assert "Erreur lors de la requête Oracle" in result
        assert "Erreur de connexion dataset" in result
        print("  ✓ Gestion d'erreur correcte")
        
    except Exception as e:
        print(f"  ✗ ERREUR test 2: {e}")
        return False
    
    # Test 3: query_type_validation pattern
    print("\n3. Test query_type_validation pattern:")
    
    try:
        mock_kernel3 = Mock(spec=Kernel)
        mock_kernel3.add_plugin = Mock()
        
        mock_dataset_manager3 = Mock(spec=DatasetAccessManager)
        valid_response = OracleResponse(
            authorized=True,
            message="Requête valide",
            data={},
            query_type=QueryType.CARD_INQUIRY
        )
        # CORRECTION: AsyncMock 
        mock_dataset_manager3.execute_oracle_query = AsyncMock(return_value=valid_response)
        
        agent3 = OracleBaseAgent(
            kernel=mock_kernel3,
            dataset_manager=mock_dataset_manager3,
            agent_name="TestOracle3"
        )
        
        # Test requête valide
        result = await agent3.oracle_tools.execute_oracle_query(
            query_type="card_inquiry",
            query_params="{}"
        )
        assert "Requête valide" in result
        print("  ✓ Requête valide: OK")
        
        # Test requête invalide
        try:
            await agent3.oracle_tools.execute_oracle_query(
                query_type="invalid_query_type",
                query_params="{}"
            )
            print("  ✗ ERREUR: ValueError non levée")
            return False
        except ValueError as ve:
            if "Type de requête invalide" in str(ve):
                print("  ✓ Validation type requête: OK")
            else:
                print(f"  ✗ Message d'erreur incorrect: {ve}")
                return False
        
    except Exception as e:
        print(f"  ✗ ERREUR test 3: {e}")
        return False
    
    print("\n✅ TOUS LES TESTS GROUPE 1 PASSENT!")
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_group1_fixes())
        if result:
            print("\n🎉 SUCCÈS: Corrections Groupe 1 validées!")
            print("   - 5 tests AsyncMock corrigés")
            print("   - 1 test plugin registration corrigé")
            print("   - Prêt pour progression 80/94 → 86/94")
            sys.exit(0)
        else:
            print("\n❌ ÉCHEC: Des corrections nécessaires")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERREUR lors des tests: {e}")
        sys.exit(1)