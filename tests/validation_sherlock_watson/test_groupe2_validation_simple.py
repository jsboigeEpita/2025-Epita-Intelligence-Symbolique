import pytest

#!/usr/bin/env python3
"""
Validation specifique des 4 tests du Groupe 2 corriges.
"""

import sys
import os
import asyncio

from unittest.mock import Mock, MagicMock, AsyncMock

# Ajouter le dossier racine au path
sys.path.insert(0, os.path.abspath("."))

# Imports necessaires
from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    DatasetAccessManager,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    QueryType,
    PermissionManager,
    PermissionRule,
    OracleResponse,
)
from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
    OracleBaseAgent,
    OracleTools,
)
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion


def _create_test_kernel():
    """Create a real Kernel with a mock-compatible service for Pydantic V2 validation."""
    kernel = Kernel()
    service = OpenAIChatCompletion(
        service_id="test_service", api_key="test-key-not-real", ai_model_id="test"
    )
    kernel.add_service(service)
    return kernel


def test_validate_agent_permissions_success():
    """Test equivalent a test_validate_agent_permissions_success du fichier original."""
    mock_kernel = _create_test_kernel()

    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = AsyncMock(return_value=True)

    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY],
    }

    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel, dataset_manager=mock_dataset_manager, **agent_config
    )

    # Execution
    result = asyncio.run(
        oracle_base_agent.oracle_tools.check_agent_permission(
            target_agent="Watson", query_type="card_inquiry"
        )
    )

    # Verifications
    mock_dataset_manager.check_permission.assert_awaited_once_with(
        "Watson", QueryType.CARD_INQUIRY
    )
    assert "Watson a les permissions" in result
    assert "card_inquiry" in result


def test_validate_agent_permissions_failure():
    """Test equivalent a test_validate_agent_permissions_failure du fichier original."""
    mock_kernel = _create_test_kernel()

    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = AsyncMock(return_value=False)

    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY],
    }

    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel, dataset_manager=mock_dataset_manager, **agent_config
    )

    # Execution
    result = asyncio.run(
        oracle_base_agent.oracle_tools.check_agent_permission(
            target_agent="UnauthorizedAgent", query_type="dataset_access"
        )
    )

    # Verifications
    assert "n'a pas les permissions" in result
    assert "UnauthorizedAgent" in result
    assert "dataset_access" in result


def test_check_agent_permission_success():
    """Test equivalent a test_check_agent_permission_success du fichier original."""
    mock_kernel = _create_test_kernel()

    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = AsyncMock(return_value=True)

    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY],
    }

    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel, dataset_manager=mock_dataset_manager, **agent_config
    )

    oracle_tools = oracle_base_agent.oracle_tools

    # Execution
    result = asyncio.run(
        oracle_tools.check_agent_permission(
            target_agent="AuthorizedAgent", query_type="card_inquiry"
        )
    )

    # Verifications
    mock_dataset_manager.check_permission.assert_awaited_once_with(
        "AuthorizedAgent", QueryType.CARD_INQUIRY
    )
    assert "AuthorizedAgent a les permissions" in result


def test_check_agent_permission_failure():
    """Test equivalent a test_check_agent_permission_failure du fichier original."""
    mock_kernel = _create_test_kernel()

    mock_dataset_manager = Mock(spec=DatasetAccessManager)
    mock_dataset_manager.check_permission = AsyncMock(return_value=False)

    agent_config = {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Test Oracle",
        "access_level": "intermediate",
        "allowed_query_types": [QueryType.CARD_INQUIRY],
    }

    oracle_base_agent = OracleBaseAgent(
        kernel=mock_kernel, dataset_manager=mock_dataset_manager, **agent_config
    )

    oracle_tools = oracle_base_agent.oracle_tools

    # Execution
    result = asyncio.run(
        oracle_tools.check_agent_permission(
            target_agent="UnauthorizedAgent", query_type="dataset_access"
        )
    )

    # Verifications
    assert "UnauthorizedAgent n'a pas les permissions" in result
    assert "dataset_access" in result
