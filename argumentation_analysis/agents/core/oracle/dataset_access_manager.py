# argumentation_analysis/agents/core/oracle/dataset_access_manager.py
"""
Fournit un gestionnaire d'accès centralisé et sécurisé aux jeux de données.

Ce module définit `DatasetAccessManager`, une classe qui agit comme un point
d'entrée unique pour toute interaction avec un jeu de données. Il orchestre
la validation des permissions via un `PermissionManager`, la mise en cache
des requêtes, et l'exécution effective des requêtes sur le jeu de données
sous-jacent.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .permissions import (
    PermissionManager,
    QueryType,
    QueryResult,
    OracleResponse,
    PermissionRule,
)
from .cluedo_dataset import CluedoDataset


class QueryCache:
    """
    Implémente un cache pour les résultats de requêtes avec une politique
    d'éviction basée sur la taille et une durée de vie (TTL).

    Attributes:
        max_size (int): Nombre maximum d'entrées dans le cache.
        ttl_seconds (int): Durée de vie d'une entrée de cache en secondes.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Initialise le cache de requêtes.

        Args:
            max_size (int): Taille maximale du cache.
            ttl_seconds (int): Durée de vie (TTL) en secondes pour chaque entrée.
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def _generate_key(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> str:
        """Génère une clé de cache unique et déterministe pour une requête."""
        import hashlib
        import json

        content = f"{agent_name}:{query_type.value}:{json.dumps(query_params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> Optional[QueryResult]:
        """
        Tente de récupérer le résultat d'une requête depuis le cache.

        La récupération échoue si l'entrée n'existe pas ou si sa durée de
        vie (TTL) a expiré.

        Args:
            agent_name (str): Nom de l'agent demandeur.
            query_type (QueryType): Type de la requête.
            query_params (Dict[str, Any]): Paramètres de la requête.

        Returns:
            Optional[QueryResult]: Le résultat en cache s'il est trouvé et
            valide, sinon `None`.
        """
        key = self._generate_key(agent_name, query_type, query_params)

        if key not in self._cache:
            return None

        # Vérification TTL
        if datetime.now() - self._access_times[key] > timedelta(
            seconds=self.ttl_seconds
        ):
            self._remove_entry(key)
            return None

        # Mise à jour du temps d'accès
        self._access_times[key] = datetime.now()

        cached_data = self._cache[key]
        self._logger.debug(f"Cache HIT pour {agent_name}:{query_type.value}")

        return QueryResult(
            success=cached_data["success"],
            data=cached_data["data"],
            message=cached_data["message"],
            query_type=query_type,
            timestamp=cached_data["timestamp"],
            metadata=cached_data.get("metadata", {}),
        )

    def put(
        self,
        agent_name: str,
        query_type: QueryType,
        query_params: Dict[str, Any],
        result: QueryResult,
    ) -> None:
        """
        Ajoute un résultat de requête au cache.

        Si le cache est plein, l'entrée la plus anciennement utilisée est supprimée.

        Args:
            agent_name (str): Nom de l'agent demandeur.
            query_type (QueryType): Type de la requête.
            query_params (Dict[str, Any]): Paramètres de la requête.
            result (QueryResult): L'objet résultat à mettre en cache.
        """
        key = self._generate_key(agent_name, query_type, query_params)

        # Nettoyage si cache plein
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        self._cache[key] = {
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "timestamp": result.timestamp,
            "metadata": result.metadata,
        }
        self._access_times[key] = datetime.now()

        self._logger.debug(f"Cache STORE pour {agent_name}:{query_type.value}")

    def _remove_entry(self, key: str) -> None:
        """Supprime une entrée du cache."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)

    def _evict_oldest(self) -> None:
        """Supprime l'entrée la plus ancienne."""
        if not self._access_times:
            return

        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self._remove_entry(oldest_key)
        self._logger.debug(f"Cache EVICTION: {oldest_key}")

    def clear(self) -> None:
        """Vide le cache."""
        self._cache.clear()
        self._access_times.clear()
        self._logger.info("Cache vidé")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache."""
        now = datetime.now()
        expired_count = sum(
            1
            for access_time in self._access_times.values()
            if now - access_time > timedelta(seconds=self.ttl_seconds)
        )

        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "cache_size_limit": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "utilization": len(self._cache) / self.max_size
            if self.max_size > 0
            else 0.0,
        }


class DatasetAccessManager:
    """
    Orchestre l'accès sécurisé et contrôlé à un jeu de données.

    Cette classe est le point central pour toute interaction avec un jeu de données.
    Elle intègre un `PermissionManager` pour le contrôle d'accès basé sur des
    règles, et un `QueryCache` pour optimiser les performances. Elle est
    également responsable de l'audit de toutes les tentatives d'accès.

    Attributes:
        dataset (Any): L'instance du jeu de données à protéger (ex: `CluedoDataset`).
        permission_manager (PermissionManager): Le gestionnaire qui applique les
            règles de permission.
        query_cache (QueryCache): Le cache pour les résultats de requêtes.
    """

    def __init__(
        self, dataset: Any, permission_manager: Optional[PermissionManager] = None
    ):
        """
        Initialise le gestionnaire d'accès.

        Args:
            dataset (Any): L'instance du jeu de données à gérer.
            permission_manager (Optional[PermissionManager]): Une instance du
                gestionnaire de permissions. Si non fournie, une nouvelle sera
                créée.
        """
        self.dataset = dataset
        self.permission_manager = permission_manager or PermissionManager()
        self.query_cache = QueryCache()
        self._logger = logging.getLogger(self.__class__.__name__)

        # Métriques et monitoring
        self.total_queries = 0
        self.successful_queries = 0
        self.denied_queries = 0
        self.cached_queries = 0
        self.start_time = datetime.now()

        self._logger.info(
            f"DatasetAccessManager initialisé avec dataset: {type(dataset).__name__}"
        )

    async def execute_query(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> QueryResult:
        """
        Exécute une requête en suivant un pipeline de validation et d'exécution sécurisé.

        Le pipeline est le suivant :
        1.  Vérification des permissions via `PermissionManager`.
        2.  Tentative de récupération depuis le `QueryCache`.
        3.  Validation des paramètres de la requête.
        4.  Exécution de la requête sur le jeu de données.
        5.  Filtrage des champs du résultat selon les permissions.
        6.  Mise en cache du résultat final.
        7.  Enregistrement de l'accès pour l'audit.

        Args:
            agent_name (str): Le nom de l'agent qui fait la requête.
            query_type (QueryType): Le type de requête à exécuter.
            query_params (Dict[str, Any]): Les paramètres de la requête.

        Returns:
            QueryResult: Un objet contenant le résultat de l'opération, qu'elle
            ait réussi ou échoué.
        """
        self.total_queries += 1
        start_time = datetime.now()

        try:
            # VALIDATION D'INTÉGRITÉ CLUEDO : sera vérifiée lors de l'exécution réelle si nécessaire
            # Les méthodes interdites sont définies mais vérifiées uniquement lors d'accès effectifs

            # Validation des permissions
            if not self.permission_manager.is_authorized(agent_name, query_type):
                self.denied_queries += 1
                self.permission_manager.log_access(
                    agent_name, query_type, False, "Permission refusée"
                )

                error_msg = f"Agent {agent_name} non autorisé pour {query_type.value}"
                self._logger.warning(error_msg)

                return QueryResult(
                    success=False,
                    message=error_msg,
                    query_type=query_type,
                    metadata={"error_type": "permission_denied"},
                )

            # Vérification du cache
            cached_result = self.query_cache.get(agent_name, query_type, query_params)
            if cached_result:
                self.cached_queries += 1
                self.permission_manager.log_access(
                    agent_name, query_type, True, "Résultat depuis cache"
                )
                return cached_result

            # Validation des paramètres
            validation_error = self._validate_query_params(query_type, query_params)
            if validation_error:
                self.denied_queries += 1
                self.permission_manager.log_access(
                    agent_name,
                    query_type,
                    False,
                    f"Paramètres invalides: {validation_error}",
                )

                return QueryResult(
                    success=False,
                    message=f"Paramètres invalides: {validation_error}",
                    query_type=query_type,
                    metadata={"error_type": "invalid_params"},
                )

            # Exécution de la requête sur le dataset
            result = await self._execute_dataset_query(
                agent_name, query_type, query_params
            )

            # Filtrage selon permissions
            filtered_result = self._apply_permission_filters(agent_name, result)

            # Mise en cache du résultat (seulement si succès)
            if filtered_result.success:
                self.query_cache.put(
                    agent_name, query_type, query_params, filtered_result
                )
                self.successful_queries += 1
            else:
                self.denied_queries += 1

            # Logging de l'accès
            execution_time = (datetime.now() - start_time).total_seconds()
            self.permission_manager.log_access(
                agent_name,
                query_type,
                filtered_result.success,
                f"Exécutée en {execution_time:.3f}s",
            )

            return filtered_result

        except Exception as e:
            self.denied_queries += 1
            error_msg = f"Erreur lors de l'exécution de la requête: {str(e)}"
            self._logger.error(error_msg, exc_info=True)

            self.permission_manager.log_access(agent_name, query_type, False, error_msg)

            return QueryResult(
                success=False,
                message=error_msg,
                query_type=query_type,
                metadata={"error_type": "execution_error", "exception": str(e)},
            )

    def _validate_query_params(
        self, query_type: QueryType, query_params: Dict[str, Any]
    ) -> Optional[str]:
        """Valide les paramètres d'une requête."""
        if query_type == QueryType.SUGGESTION_VALIDATION:
            suggestion = query_params.get("suggestion", {})
            if not all(key in suggestion for key in ["suspect", "arme", "lieu"]):
                return "Suggestion incomplète: suspect, arme et lieu requis"

            if not all(
                isinstance(suggestion[key], str) and suggestion[key].strip()
                for key in ["suspect", "arme", "lieu"]
            ):
                return "Tous les éléments de la suggestion doivent être des chaînes non vides"

        elif query_type == QueryType.CARD_INQUIRY:
            card = query_params.get("card", "")
            if not isinstance(card, str) or not card.strip():
                return "Nom de carte requis pour l'enquête"

        elif query_type == QueryType.CLUE_REQUEST:
            # Pas de paramètres spécifiques requis
            pass

        # Validation générale des paramètres
        if not isinstance(query_params, dict):
            return "Les paramètres doivent être un dictionnaire"

        return None

    def _generate_cache_key(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> str:
        """
        Génère une clé de cache unique pour une requête.

        Args:
            agent_name: Nom de l'agent
            query_type: Type de requête
            query_params: Paramètres de la requête

        Returns:
            Clé de cache unique
        """
        import hashlib
        import json

        # Créer une représentation sérialisable des paramètres
        params_str = json.dumps(query_params, sort_keys=True)
        cache_data = f"{agent_name}:{query_type.value}:{params_str}"

        # Générer un hash pour éviter les clés trop longues
        return hashlib.md5(cache_data.encode()).hexdigest()

    async def _execute_dataset_query(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> QueryResult:
        """Exécute la requête sur le dataset approprié."""
        if isinstance(self.dataset, CluedoDataset):
            return await self.dataset.process_query(
                agent_name, query_type, query_params
            )
        else:
            # Support pour d'autres types de datasets à l'avenir
            return QueryResult(
                success=False,
                message=f"Type de dataset non supporté: {type(self.dataset).__name__}",
                query_type=query_type,
            )

    def _apply_permission_filters(
        self, agent_name: str, result: QueryResult
    ) -> QueryResult:
        """Applique les filtres de permission sur le résultat."""
        permission_rule = self.permission_manager.get_permission_rule(agent_name)
        if not permission_rule:
            return result

        # Vérification des champs interdits
        forbidden_fields = permission_rule.forbidden_fields
        if forbidden_fields and result.data:
            filtered_data = self._filter_forbidden_fields(result.data, forbidden_fields)
            result.data = filtered_data

            if forbidden_fields:
                result.metadata["filtered_fields"] = forbidden_fields

        return result

    def _filter_forbidden_fields(self, data: Any, forbidden_fields: List[str]) -> Any:
        """Filtre les champs interdits des données."""
        # Vérification de sécurité pour éviter les erreurs de données
        if not forbidden_fields or not hasattr(forbidden_fields, "__iter__"):
            return data

        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if key not in forbidden_fields:
                    filtered[key] = self._filter_forbidden_fields(
                        value, forbidden_fields
                    )
            return filtered
        elif isinstance(data, list):
            return [
                self._filter_forbidden_fields(item, forbidden_fields) for item in data
            ]
        else:
            return data

    async def execute_oracle_query(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> OracleResponse:
        """
        Interface haut niveau qui exécute une requête et la formate en `OracleResponse`.

        Cette méthode sert de façade sur `execute_query` pour retourner le type
        `OracleResponse` attendu par les agents.

        Args:
            agent_name (str): Le nom de l'agent demandeur.
            query_type (QueryType): Le type de requête.
            query_params (Dict[str, Any]): Les paramètres de la requête.

        Returns:
            OracleResponse: La réponse standardisée pour le système Oracle.
        """
        try:
            query_result = await self.execute_query(
                agent_name, query_type, query_params
            )

            return OracleResponse(
                authorized=query_result.success,
                data=query_result.data,
                message=query_result.message,
                query_type=query_type,
                revealed_information=self._extract_revealed_info(query_result),
                agent_name=agent_name,
                metadata=query_result.metadata,
            )

        except Exception as e:
            self._logger.error(f"Erreur dans execute_oracle_query: {e}", exc_info=True)
            return OracleResponse(
                authorized=False,
                message=f"Erreur Oracle: {str(e)}",
                query_type=query_type,
                agent_name=agent_name,
                metadata={"error": str(e)},
            )

    def _extract_revealed_info(self, query_result: QueryResult) -> List[str]:
        """Extrait les informations révélées du résultat de requête."""
        revealed_info = []

        if query_result.data and isinstance(query_result.data, dict):
            # Pour les validations de suggestions
            if "revealed_cards" in query_result.data:
                revealed_cards = query_result.data["revealed_cards"]
                if isinstance(revealed_cards, list):
                    for card_info in revealed_cards:
                        if isinstance(card_info, dict) and "value" in card_info:
                            revealed_info.append(card_info["value"])

            # Pour les révélations directes
            if "revelation" in query_result.data:
                revelation = query_result.data["revelation"]
                if hasattr(revelation, "card_revealed"):
                    revealed_info.append(revelation.card_revealed)

        return revealed_info

    def get_agent_permissions(self, agent_name: str) -> Optional[PermissionRule]:
        """Récupère les permissions d'un agent."""
        return self.permission_manager.get_permission_rule(agent_name)

    def add_permission_rule(self, rule: PermissionRule) -> None:
        """Ajoute une règle de permission."""
        self.permission_manager.add_permission_rule(rule)

    def add_permission(self, agent_name: str, query_type: QueryType):
        """Ajoute une permission pour un agent via le gestionnaire de permissions."""
        self.permission_manager.add_permission(agent_name, query_type)
        self._logger.info(
            f"Permission {query_type.value} ajoutée pour l'agent {agent_name}."
        )

    async def check_permission(self, agent_name: str, query_type: QueryType) -> bool:
        """
        Vérifie si un agent a les permissions pour un type de requête.

        Args:
            agent_name: Nom de l'agent à vérifier
            query_type: Type de requête à autoriser

        Returns:
            True si l'agent est autorisé, False sinon
        """
        return self.permission_manager.is_authorized(agent_name, query_type)

    def get_access_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'accès complètes."""
        uptime = (datetime.now() - self.start_time).total_seconds()

        stats = {
            "manager_stats": {
                "total_queries": self.total_queries,
                "successful_queries": self.successful_queries,
                "denied_queries": self.denied_queries,
                "cached_queries": self.cached_queries,
                "success_rate": self.successful_queries / self.total_queries
                if self.total_queries > 0
                else 0.0,
                "cache_hit_rate": self.cached_queries / self.total_queries
                if self.total_queries > 0
                else 0.0,
                "uptime_seconds": uptime,
                "queries_per_second": self.total_queries / uptime
                if uptime > 0
                else 0.0,
            },
            "cache_stats": self.query_cache.get_stats(),
            "dataset_stats": getattr(self.dataset, "get_statistics", lambda: {})(),
        }

        return stats

    def reset_statistics(self) -> None:
        """Remet à zéro les statistiques."""
        self.total_queries = 0
        self.successful_queries = 0
        self.denied_queries = 0
        self.cached_queries = 0
        self.start_time = datetime.now()
        self.query_cache.clear()
        self.permission_manager.reset_daily_counts()
        self._logger.info("Statistiques remises à zéro")


# Classes d'assistance pour l'intégration


class CluedoDatasetManager(DatasetAccessManager):
    """Gestionnaire spécialisé pour les datasets Cluedo."""

    def __init__(self, cluedo_dataset: CluedoDataset):
        from .permissions import get_default_cluedo_permissions

        # Initialisation avec permissions par défaut Cluedo
        permission_manager = PermissionManager()
        for rule in get_default_cluedo_permissions().values():
            permission_manager.add_permission_rule(rule)

        super().__init__(cluedo_dataset, permission_manager)
        self._logger.info("CluedoDatasetManager initialisé avec permissions par défaut")

    async def validate_cluedo_suggestion(
        self, agent_name: str, suspect: str, arme: str, lieu: str
    ) -> OracleResponse:
        """Interface simplifiée pour valider une suggestion Cluedo."""
        return await self.execute_oracle_query(
            agent_name=agent_name,
            query_type=QueryType.SUGGESTION_VALIDATION,
            query_params={
                "suggestion": {"suspect": suspect, "arme": arme, "lieu": lieu}
            },
        )

    async def request_clue(self, agent_name: str) -> OracleResponse:
        """Interface simplifiée pour demander un indice."""
        return await self.execute_oracle_query(
            agent_name=agent_name, query_type=QueryType.CLUE_REQUEST, query_params={}
        )

    async def inquire_about_card(self, agent_name: str, card: str) -> OracleResponse:
        """Interface simplifiée pour enquêter sur une carte."""
        return await self.execute_oracle_query(
            agent_name=agent_name,
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": card},
        )
