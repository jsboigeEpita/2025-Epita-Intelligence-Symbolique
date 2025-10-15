from unittest.mock import Mock, AsyncMock

# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python3
"""
from unittest.mock import Mock, AsyncMock
Test simple pour identifier les problèmes des 4 derniers tests du Groupe 3.
"""

import sys
import asyncio
import traceback


# Imports du système Oracle
sys.path.append(".")
from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
    OracleBaseAgent,
    OracleTools,
)
from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    DatasetAccessManager,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    QueryType,
    OracleResponse,
)
from semantic_kernel.kernel import Kernel


def main():
    """Test simplifié des 4 problèmes identifiés"""
    print("=== DIAGNOSTIC GROUPE 3 ===")

    # Setup de base
    mock_kernel = Mock(spec=Kernel)
    # mock_kernel.add_plugin = await self._create_authentic_gpt4o_mini_instance() # Cannot await in sync function

    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    # mock_permission_manager = await self._create_authentic_gpt4o_mini_instance() # Cannot await in sync function
    mock_permission_manager = Mock()
    mock_permission_manager.is_authorized = Mock(return_value=True)
    mock_dataset_manager.permission_manager = mock_permission_manager

    success_response = OracleResponse(
        authorized=True,
        message="Information révélée avec succès",
        data={"revealed_card": "Colonel Moutarde"},
        query_type=QueryType.CARD_INQUIRY,
    )
    mock_dataset_manager.execute_oracle_query = AsyncMock(return_value=success_response)
    mock_dataset_manager.validate_agent_access = Mock(return_value=True)

    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel,
        dataset_manager=mock_dataset_manager,
        agent_name="TestOracle",
        system_prompt_suffix="Test Oracle.",
        access_level="intermediate",
        allowed_query_types=[
            QueryType.CARD_INQUIRY,
            QueryType.DATASET_ACCESS,
            QueryType.GAME_STATE,
        ],
    )

    # TEST 11: kernel_function_decorators
    print("\n--- TEST 11: kernel_function_decorators ---")
    tools = oracle_base_agent.oracle_tools

    # Problème identifié: __kernel_function__ est un bool, pas un objet avec description
    if hasattr(tools.query_oracle_dataset, "__kernel_function__"):
        kf_attr = getattr(tools.query_oracle_dataset, "__kernel_function__")
        print(f"Type __kernel_function__: {type(kf_attr)}")
        print(f"Valeur: {kf_attr}")
        if hasattr(kf_attr, "description"):
            print(f"Description: {kf_attr.description}")
        else:
            print(
                "PROBLEME: Pas d'attribut 'description' - c'est un bool pas un objet!"
            )

    # TEST 12: invalid_json
    print("\n--- TEST 12: invalid_json ---")
    result = asyncio.run(
        tools.query_oracle_dataset(
            query_type="card_inquiry", query_params="invalid json"
        )
    )
    print(f"Résultat JSON invalide: {result}")

    # TEST 13: invalid_query_type
    print("\n--- TEST 13: invalid_query_type ---")
    try:
        result = asyncio.run(
            tools.check_agent_permission(
                query_type="invalid_query_type", target_agent="TestAgent"
            )
        )
        print(f"PROBLEME: Aucune ValueError levée! Résultat: {result}")
    except ValueError as ve:
        print(f"OK: ValueError levée: {ve}")
    except Exception as e:
        print(f"PROBLEME: Exception inattendue: {type(e).__name__}: {e}")

    # TEST 14: error_handling
    print("\n--- TEST 14: error_handling ---")
    mock_dataset_manager.execute_oracle_query = AsyncMock(
        side_effect=Exception("Erreur de connexion dataset")
    )

    result = asyncio.run(
        tools.query_oracle_dataset(
            query_type="card_inquiry", query_params='{"card_name": "Test"}'
        )
    )
    print(f"Résultat erreur: {result}")

    print("\n=== FIN DIAGNOSTIC ===")


if __name__ == "__main__":
    main()
