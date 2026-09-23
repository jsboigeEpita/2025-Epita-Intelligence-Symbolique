import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Tests d'intégration pour les nouveaux modules Oracle Enhanced v2.1.0
"""

import pytest
import asyncio


from argumentation_analysis.agents.core.oracle.error_handling import (
    OracleErrorHandler,
    OraclePermissionError,
    oracle_error_handler,
)
from argumentation_analysis.agents.core.oracle.interfaces import OracleAgentInterface
from argumentation_analysis.agents.core.oracle.permissions import (
    OracleResponse,
    QueryType,
)


class TestNewModulesIntegration:
    """Tests d'intégration entre les nouveaux modules"""

    def setup_method(self):
        """Setup pour chaque test"""
        self.error_handler = OracleErrorHandler()

    def test_oracle_agent_with_error_handling(self):
        """Test agent Oracle utilisant le gestionnaire d'erreurs"""

        class TestOracleAgentWithErrorHandling(OracleAgentInterface):
            def __init__(self, error_handler: OracleErrorHandler):
                self.error_handler = error_handler

            @oracle_error_handler("process_request")
            async def process_oracle_request(
                self, requesting_agent: str, query_type: QueryType, query_params: dict
            ) -> OracleResponse:
                if requesting_agent == "error_agent":
                    raise OraclePermissionError("Access denied for error_agent")

                return OracleResponse(
                    authorized=True,
                    data={"processed": True},
                    query_type=query_type,
                    message="Request processed successfully",
                )

            def get_oracle_statistics(self) -> dict:
                stats = self.error_handler.get_error_statistics()
                return {"error_stats": stats}

            def reset_oracle_state(self) -> None:
                self.error_handler.error_stats = {
                    "total_errors": 0,
                    "permission_errors": 0,
                    "dataset_errors": 0,
                    "validation_errors": 0,
                    "integrity_errors": 0,
                }

        agent = TestOracleAgentWithErrorHandling(self.error_handler)

        # Test requête normale
        async def test_normal_request():
            result = await agent.process_oracle_request(
                "Sherlock", QueryType.LOGICAL_VALIDATION, {}
            )
            assert result.authorized is True
            assert result.data["processed"] is True

        asyncio.run(test_normal_request())

        # Test requête avec erreur
        async def test_error_request():
            with pytest.raises(OraclePermissionError):
                await agent.process_oracle_request(
                    "error_agent", QueryType.LOGICAL_VALIDATION, {}
                )

        asyncio.run(test_error_request())

    @pytest.mark.asyncio
    async def test_complete_integration_scenario(self):
        """Test scenario d'intégration complet"""

        class CompleteOracleAgent(OracleAgentInterface):
            def __init__(self):
                self.error_handler = OracleErrorHandler()
                self.request_count = 0

            @oracle_error_handler("oracle_processing")
            async def process_oracle_request(
                self, requesting_agent: str, query_type: QueryType, query_params: dict
            ) -> OracleResponse:
                self.request_count += 1

                try:
                    # Simulation de traitement
                    if query_type == QueryType.ADMIN_COMMAND:
                        raise OraclePermissionError(
                            f"Query type {query_type.value} not allowed for {requesting_agent}"
                        )

                    # Succès
                    return OracleResponse(
                        authorized=True,
                        data={
                            "query_result": "processed",
                            "request_id": self.request_count,
                        },
                        query_type=query_type,
                        message=f"Query {query_type.value} processed for {requesting_agent}",
                    )

                except Exception as e:
                    # Conversion d'erreur en réponse
                    error_info = self.error_handler.handle_oracle_error(
                        e, f"agent={requesting_agent}, query={query_type.value}"
                    )

                    return OracleResponse(
                        authorized=False,
                        query_type=query_type,
                        message=error_info["message"],
                        error_code=error_info["type"],
                    )

            def get_oracle_statistics(self) -> dict:
                return {
                    "total_requests": self.request_count,
                    "error_stats": self.error_handler.get_error_statistics(),
                }

            def reset_oracle_state(self) -> None:
                self.request_count = 0
                self.error_handler.error_stats = {
                    "total_errors": 0,
                    "permission_errors": 0,
                    "dataset_errors": 0,
                    "validation_errors": 0,
                    "integrity_errors": 0,
                }

        agent = CompleteOracleAgent()

        # Requête réussie
        result = await agent.process_oracle_request(
            "Sherlock", QueryType.LOGICAL_VALIDATION, {"data": "test"}
        )
        assert result.authorized is True
        assert result.data["request_id"] == 1

        # Requête interdite
        result = await agent.process_oracle_request(
            "Watson", QueryType.ADMIN_COMMAND, {}
        )
        assert result.authorized is False
        assert result.error_code == "OraclePermissionError"

        # Vérifier statistiques
        stats = agent.get_oracle_statistics()
        assert stats["total_requests"] == 2
        assert stats["error_stats"]["total_errors"] == 1
        assert stats["error_stats"]["permission_errors"] == 1
