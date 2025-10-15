"""
Gestion d'erreurs avancée pour le système Oracle Enhanced
"""

import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime


class OracleError(Exception):
    """Erreur de base du système Oracle"""

    pass


class OraclePermissionError(OracleError):
    """Erreur de permissions Oracle"""

    pass


class OracleDatasetError(OracleError):
    """Erreur de dataset Oracle"""

    pass


class OracleValidationError(OracleError):
    """Erreur de validation Oracle"""

    pass


class CluedoIntegrityError(OracleError):
    """Erreur d'intégrité du jeu Cluedo"""

    pass


class OracleErrorHandler:
    """Gestionnaire d'erreurs centralisé pour Oracle"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_stats = {
            "total_errors": 0,
            "permission_errors": 0,
            "dataset_errors": 0,
            "validation_errors": 0,
            "integrity_errors": 0,
        }

    def handle_oracle_error(
        self, error: Exception, context: str = ""
    ) -> Dict[str, Any]:
        """Gère une erreur Oracle avec logging et statistiques"""
        self.error_stats["total_errors"] += 1

        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }

        if isinstance(error, OraclePermissionError):
            self.error_stats["permission_errors"] += 1
            self.logger.warning(
                f"Erreur permission Oracle: {error} (contexte: {context})"
            )
        elif isinstance(error, OracleDatasetError):
            self.error_stats["dataset_errors"] += 1
            self.logger.error(f"Erreur dataset Oracle: {error} (contexte: {context})")
        elif isinstance(error, OracleValidationError):
            self.error_stats["validation_errors"] += 1
            self.logger.warning(
                f"Erreur validation Oracle: {error} (contexte: {context})"
            )
        elif isinstance(error, CluedoIntegrityError):
            self.error_stats["integrity_errors"] += 1
            self.logger.critical(
                f"Erreur intégrité Cluedo: {error} (contexte: {context})"
            )
        else:
            self.logger.error(f"Erreur Oracle non typée: {error} (contexte: {context})")

        return error_info

    def get_error_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'erreurs"""
        return self.error_stats.copy()


def oracle_error_handler(context: str = ""):
    """Décorateur pour la gestion d'erreurs Oracle"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log l'erreur avec contexte
                logger = logging.getLogger(func.__module__)
                logger.error(f"Erreur dans {func.__name__}: {e} (contexte: {context})")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log l'erreur avec contexte
                logger = logging.getLogger(func.__module__)
                logger.error(f"Erreur dans {func.__name__}: {e} (contexte: {context})")
                raise

        # Retourne le wrapper approprié selon le type de fonction
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
