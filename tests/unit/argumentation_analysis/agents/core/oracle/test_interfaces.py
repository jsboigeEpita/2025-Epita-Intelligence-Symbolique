"""
Tests pour le module interfaces.py du système Oracle Enhanced v2.1.0
"""

import pytest
from abc import ABC
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

from argumentation_analysis.agents.core.oracle.interfaces import (
    OracleAgentInterface,
    DatasetManagerInterface,
    StandardOracleResponse,
    OracleResponseStatus,
)


class TestOracleAgentInterface:
    """Tests pour OracleAgentInterface"""

    def test_oracle_agent_interface_is_abstract(self):
        """Test que OracleAgentInterface est une classe abstraite"""
        assert issubclass(OracleAgentInterface, ABC)

        # Tentative d'instanciation directe doit lever TypeError
        with pytest.raises(TypeError):
            OracleAgentInterface()

    def test_oracle_agent_interface_methods(self):
        """Test que l'interface définit les bonnes méthodes abstraites"""

        # Création d'une implémentation concrète
        class ConcreteOracleAgent(OracleAgentInterface):
            async def process_oracle_request(
                self,
                requesting_agent: str,
                query_type: str,
                query_params: Dict[str, Any],
            ) -> Dict[str, Any]:
                return {"success": True, "data": "test_data"}

            def get_oracle_statistics(self) -> Dict[str, Any]:
                return {"total_requests": 5}

            def reset_oracle_state(self) -> None:
                pass

        # L'instanciation doit réussir
        agent = ConcreteOracleAgent()
        assert isinstance(agent, OracleAgentInterface)

    def test_incomplete_oracle_agent_interface(self):
        """Test qu'une implémentation incomplète ne peut pas être instanciée"""

        class IncompleteOracleAgent(OracleAgentInterface):
            async def process_oracle_request(
                self,
                requesting_agent: str,
                query_type: str,
                query_params: Dict[str, Any],
            ) -> Dict[str, Any]:
                return {"success": True}

            # Manque get_oracle_statistics et reset_oracle_state

        with pytest.raises(TypeError):
            IncompleteOracleAgent()


class TestDatasetManagerInterface:
    """Tests pour DatasetManagerInterface"""

    def test_dataset_manager_interface_is_abstract(self):
        """Test que DatasetManagerInterface est une classe abstraite"""
        assert issubclass(DatasetManagerInterface, ABC)

        with pytest.raises(TypeError):
            DatasetManagerInterface()

    def test_dataset_manager_interface_methods(self):
        """Test que l'interface définit les bonnes méthodes abstraites"""

        class ConcreteDatasetManager(DatasetManagerInterface):
            def execute_query(
                self, agent_name: str, query_type: str, query_params: Dict[str, Any]
            ) -> Dict[str, Any]:
                return {"result": "query_executed"}

            def check_permission(self, agent_name: str, query_type: str) -> bool:
                return True

        manager = ConcreteDatasetManager()
        assert isinstance(manager, DatasetManagerInterface)

    def test_incomplete_dataset_manager_interface(self):
        """Test qu'une implémentation incomplète ne peut pas être instanciée"""

        class IncompleteDatasetManager(DatasetManagerInterface):
            def execute_query(
                self, agent_name: str, query_type: str, query_params: Dict[str, Any]
            ) -> Dict[str, Any]:
                return {"result": "query_executed"}

            # Manque check_permission

        with pytest.raises(TypeError):
            IncompleteDatasetManager()


class TestStandardOracleResponse:
    """Tests pour StandardOracleResponse"""

    def test_standard_oracle_response_success(self):
        """Test création StandardOracleResponse avec succès"""
        response = StandardOracleResponse(
            success=True, data={"key": "value"}, message="Operation successful"
        )

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Operation successful"
        assert response.error_code is None
        assert response.metadata is None

    def test_standard_oracle_response_error(self):
        """Test création StandardOracleResponse avec erreur"""
        response = StandardOracleResponse(
            success=False,
            message="Operation failed",
            error_code="VALIDATION_ERROR",
            metadata={"error_details": "Invalid input"},
        )

        assert response.success is False
        assert response.data is None
        assert response.message == "Operation failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.metadata == {"error_details": "Invalid input"}

    def test_standard_oracle_response_to_dict(self):
        """Test conversion to_dict"""
        response = StandardOracleResponse(
            success=True,
            data={"result": 42},
            message="Success",
            error_code=None,
            metadata={"timestamp": "2024-01-01"},
        )

        expected_dict = {
            "success": True,
            "data": {"result": 42},
            "message": "Success",
            "error_code": None,
            "metadata": {"timestamp": "2024-01-01"},
        }

        assert response.to_dict() == expected_dict

    def test_standard_oracle_response_minimal(self):
        """Test création StandardOracleResponse avec paramètres minimaux"""
        response = StandardOracleResponse(success=True)

        assert response.success is True
        assert response.data is None
        assert response.message == ""
        assert response.error_code is None
        assert response.metadata is None

        dict_result = response.to_dict()
        assert dict_result["success"] is True
        assert dict_result["data"] is None


class TestOracleResponseStatus:
    """Tests pour OracleResponseStatus"""

    def test_oracle_response_status_values(self):
        """Test que les valeurs de l'enum sont correctes"""
        assert OracleResponseStatus.SUCCESS.value == "success"
        assert OracleResponseStatus.ERROR.value == "error"
        assert OracleResponseStatus.PERMISSION_DENIED.value == "permission_denied"
        assert OracleResponseStatus.INVALID_QUERY.value == "invalid_query"
        assert OracleResponseStatus.DATASET_ERROR.value == "dataset_error"

    def test_oracle_response_status_enum_members(self):
        """Test que l'enum contient les bons membres"""
        expected_members = {
            "SUCCESS",
            "ERROR",
            "PERMISSION_DENIED",
            "INVALID_QUERY",
            "DATASET_ERROR",
        }
        actual_members = {member.name for member in OracleResponseStatus}
        assert actual_members == expected_members

    def test_oracle_response_status_comparison(self):
        """Test comparaison des valeurs d'enum"""
        assert OracleResponseStatus.SUCCESS == OracleResponseStatus.SUCCESS
        assert OracleResponseStatus.ERROR != OracleResponseStatus.SUCCESS

    def test_oracle_response_status_iteration(self):
        """Test itération sur l'enum"""
        statuses = list(OracleResponseStatus)
        assert len(statuses) == 5
        assert OracleResponseStatus.SUCCESS in statuses
        assert OracleResponseStatus.ERROR in statuses


class TestInterfacesIntegration:
    """Tests d'intégration des interfaces"""

    def test_oracle_agent_implementation_with_standard_response(self):
        """Test implémentation Oracle Agent utilisant StandardOracleResponse"""

        class TestOracleAgent(OracleAgentInterface):
            async def process_oracle_request(
                self,
                requesting_agent: str,
                query_type: str,
                query_params: Dict[str, Any],
            ) -> Dict[str, Any]:
                response = StandardOracleResponse(
                    success=True,
                    data={"agent": requesting_agent, "query": query_type},
                    message="Request processed successfully",
                )
                return response.to_dict()

            def get_oracle_statistics(self) -> Dict[str, Any]:
                return {"requests_processed": 1}

            def reset_oracle_state(self) -> None:
                pass

        agent = TestOracleAgent()

        # Test utilisation
        import asyncio

        async def test_async():
            result = await agent.process_oracle_request(
                "Sherlock", "validate", {"data": "test"}
            )
            assert result["success"] is True
            assert result["data"]["agent"] == "Sherlock"
            assert result["data"]["query"] == "validate"

        asyncio.run(test_async())

    def test_dataset_manager_with_response_status(self):
        """Test Dataset Manager utilisant OracleResponseStatus"""

        class TestDatasetManager(DatasetManagerInterface):
            def execute_query(
                self, agent_name: str, query_type: str, query_params: Dict[str, Any]
            ) -> Dict[str, Any]:
                if agent_name == "unauthorized":
                    return {
                        "status": OracleResponseStatus.PERMISSION_DENIED.value,
                        "message": "Access denied",
                    }
                return {
                    "status": OracleResponseStatus.SUCCESS.value,
                    "result": "Query executed",
                }

            def check_permission(self, agent_name: str, query_type: str) -> bool:
                return agent_name != "unauthorized"

        manager = TestDatasetManager()

        # Test avec agent autorisé
        result = manager.execute_query("Sherlock", "validate", {})
        assert result["status"] == "success"

        # Test avec agent non autorisé
        result = manager.execute_query("unauthorized", "validate", {})
        assert result["status"] == "permission_denied"
