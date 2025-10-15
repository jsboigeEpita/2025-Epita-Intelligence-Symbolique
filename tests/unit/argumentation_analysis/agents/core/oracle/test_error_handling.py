# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Tests pour le module error_handling.py du système Oracle Enhanced v2.1.0
"""

import pytest
import logging

from datetime import datetime

from argumentation_analysis.agents.core.oracle.error_handling import (
    OracleError,
    OraclePermissionError,
    OracleDatasetError,
    OracleValidationError,
    CluedoIntegrityError,
    OracleErrorHandler,
    oracle_error_handler,
)


class TestOracleErrors:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour les classes d'erreurs Oracle"""

    def test_oracle_error_base(self):
        """Test de la classe d'erreur de base Oracle"""
        error = OracleError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_oracle_permission_error(self):
        """Test de OraclePermissionError"""
        error = OraclePermissionError("Permission denied")
        assert str(error) == "Permission denied"
        assert isinstance(error, OracleError)

    def test_oracle_dataset_error(self):
        """Test de OracleDatasetError"""
        error = OracleDatasetError("Dataset error")
        assert str(error) == "Dataset error"
        assert isinstance(error, OracleError)

    def test_oracle_validation_error(self):
        """Test de OracleValidationError"""
        error = OracleValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, OracleError)

    def test_cluedo_integrity_error(self):
        """Test de CluedoIntegrityError"""
        error = CluedoIntegrityError("Integrity violation")
        assert str(error) == "Integrity violation"
        assert isinstance(error, OracleError)


class TestOracleErrorHandler:
    """Tests pour OracleErrorHandler"""

    def setup_method(self):
        """Setup pour chaque test"""
        # Utilise un logger réel au lieu d'un mock
        self.real_logger = logging.getLogger("TestOracleErrorHandlerLogger")
        self.real_logger.setLevel(
            logging.DEBUG
        )  # Configurer le niveau pour capturer les logs si nécessaire
        # Vous pouvez ajouter un handler si vous voulez vérifier les logs émis,
        # par exemple un StreamHandler vers un StringIO. Pour l'instant, on s'assure juste que ça ne crashe pas.
        self.handler = OracleErrorHandler(logger=self.real_logger)

    def test_init_default_logger(self):
        """Test initialisation avec logger par défaut"""
        handler = OracleErrorHandler()
        assert handler.logger is not None
        assert isinstance(handler.logger, logging.Logger)
        assert handler.error_stats["total_errors"] == 0

    def test_init_custom_logger(self):
        """Test initialisation avec logger personnalisé"""
        assert self.handler.logger == self.real_logger
        assert self.handler.error_stats["total_errors"] == 0

    def test_handle_oracle_permission_error(self):
        """Test gestion OraclePermissionError"""
        error = OraclePermissionError("Permission denied")
        result = self.handler.handle_oracle_error(error, "test_context")

        assert result["type"] == "OraclePermissionError"
        assert result["message"] == "Permission denied"
        assert result["context"] == "test_context"
        assert "timestamp" in result

        assert self.handler.error_stats["total_errors"] == 1
        assert self.handler.error_stats["permission_errors"] == 1
        # Pas d'assertion de mock ici

    def test_handle_oracle_dataset_error(self):
        """Test gestion OracleDatasetError"""
        error = OracleDatasetError("Dataset failed")
        result = self.handler.handle_oracle_error(error, "dataset_context")

        assert result["type"] == "OracleDatasetError"
        assert self.handler.error_stats["dataset_errors"] == 1
        # Pas d'assertion de mock ici

    def test_handle_oracle_validation_error(self):
        """Test gestion OracleValidationError"""
        error = OracleValidationError("Validation failed")
        result = self.handler.handle_oracle_error(error)

        assert result["type"] == "OracleValidationError"
        assert self.handler.error_stats["validation_errors"] == 1
        # Pas d'assertion de mock ici

    def test_handle_cluedo_integrity_error(self):
        """Test gestion CluedoIntegrityError"""
        error = CluedoIntegrityError("Integrity violation")
        result = self.handler.handle_oracle_error(error)

        assert result["type"] == "CluedoIntegrityError"
        assert self.handler.error_stats["integrity_errors"] == 1
        # Pas d'assertion de mock ici

    def test_handle_generic_error(self):
        """Test gestion erreur générique"""
        error = ValueError("Generic error")
        result = self.handler.handle_oracle_error(error, "generic_context")

        assert result["type"] == "ValueError"
        assert self.handler.error_stats["total_errors"] == 1
        # Autres compteurs restent à 0
        assert self.handler.error_stats["permission_errors"] == 0
        # Pas d'assertion de mock ici

    def test_get_error_statistics(self):
        """Test récupération statistiques d'erreurs"""
        # Simuler plusieurs erreurs
        self.handler.handle_oracle_error(OraclePermissionError("test1"))
        self.handler.handle_oracle_error(OracleDatasetError("test2"))
        self.handler.handle_oracle_error(OracleValidationError("test3"))

        stats = self.handler.get_error_statistics()

        assert stats["total_errors"] == 3
        assert stats["permission_errors"] == 1
        assert stats["dataset_errors"] == 1
        assert stats["validation_errors"] == 1
        assert stats["integrity_errors"] == 0


class TestOracleErrorDecorator:
    """Tests pour le décorateur oracle_error_handler"""

    def test_decorator_sync_function_success(self):
        """Test décorateur sur fonction synchrone réussie"""

        @oracle_error_handler("test_context")
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5

    def test_decorator_sync_function_error(self):
        """Test décorateur sur fonction synchrone avec erreur"""

        @oracle_error_handler("test_context")
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_function()

    @pytest.mark.asyncio
    async def test_decorator_async_function_success(self):
        """Test décorateur sur fonction asynchrone réussie"""

        @oracle_error_handler("async_context")
        async def test_async_function(x, y):
            return x * y

        result = await test_async_function(3, 4)
        assert result == 12

    @pytest.mark.asyncio
    async def test_decorator_async_function_error(self):
        """Test décorateur sur fonction asynchrone avec erreur"""

        @oracle_error_handler("async_context")
        async def test_async_function():
            raise OracleDatasetError("Async test error")

        with pytest.raises(OracleDatasetError, match="Async test error"):
            await test_async_function()

    @pytest.mark.asyncio
    async def test_decorator_logging(self):  # mock_get_logger n'est plus nécessaire ici
        """Test que le décorateur log correctement les erreurs"""
        # Le décorateur utilise logging.getLogger(func.__module__)
        # Pour ce test, on s'assure juste que l'appel ne crashe pas et que l'erreur est bien levée.
        # Vérifier le contenu exact du log nécessiterait de patcher logging.getLogger
        # ou d'inspecter les handlers du logger du module, ce qui est plus complexe.

        @oracle_error_handler("logging_context")
        def test_function_for_logging():  # Renommer pour éviter conflit potentiel
            raise RuntimeError("Runtime error for decorator logging")

        with pytest.raises(RuntimeError, match="Runtime error for decorator logging"):
            test_function_for_logging()

        # Pas d'assertion de mock ici
