#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de logique pour l'analyse argumentative.

Ce module fournit LogicService qui gère les opérations de logique formelle
et informelle pour l'analyse des arguments.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio

# Import du gestionnaire asynchrone
from ..utils.async_manager import (
    AsyncManager,
    run_hybrid_safe,
    ensure_async,
    ensure_sync,
)


class LogicEngineNotWiredError(RuntimeError):
    """Raised by the analysis core when no logic engine is wired (#2344).

    This ``LogicService`` never had an engine behind its analysers: the
    private methods returned hardcoded results, including a fabricated
    ``Tweety Result: ... ACCEPTED`` message impersonating the reasoner. They
    now fail loud; the public methods catch this and name the gap in the
    result state (``success=False`` / ``accepted=None``), so callers keep
    their contract while the fabrication disappears (doctrine #1019: the
    capacity stays, the lie goes).
    """


_ENGINE_NOT_WIRED_MESSAGE = (
    "no logic engine wired — this LogicService never had one; the hardcoded "
    "mock answers were removed (#2344, anti-théâtre #1019). Wire TweetyBridge "
    "or LogicAgentFactory (see web_api/services/logic_service.py for the "
    "engine-backed implementation) to get real answers."
)


class LogicService:
    """
    Service de logique pour l'analyse argumentative.

    Cette classe fournit une interface unifiée pour accéder aux
    différents types d'analyse logique (propositionnelle, premier ordre, modale).
    """

    def __init__(self):
        """Initialise le service de logique."""
        self.logger = logging.getLogger(__name__)
        self.active_sessions = {}
        self.logic_agents = {}
        self.analysis_cache = {}
        self.async_manager = AsyncManager(max_workers=6, default_timeout=30.0)
        self._health_status = {
            "status": "initializing",
            "last_check": datetime.now().isoformat(),
        }
        self._fallback_enabled = True
        self._circuit_breaker = {"failures": 0, "last_failure": None, "max_failures": 5}

    def initialize_logic_agents(
        self, agents_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Initialise les agents de logique.

        Args:
            agents_config: Configuration des agents de logique

        Returns:
            True si l'initialisation réussit
        """
        try:
            self.logger.info("Initialisation des agents de logique...")

            # Configuration par défaut si aucune n'est fournie
            if not agents_config:
                agents_config = {
                    "propositional": {"enabled": True, "priority": 1},
                    "first_order": {"enabled": True, "priority": 2},
                    "modal": {"enabled": False, "priority": 3},
                }

            self.logic_agents = agents_config
            self.logger.info(
                f"Agents de logique configurés: {list(agents_config.keys())}"
            )
            self._health_status = {
                "status": "healthy",
                "last_check": datetime.now().isoformat(),
            }
            return True

        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'initialisation des agents de logique: {e}"
            )
            self._health_status = {
                "status": "error",
                "last_check": datetime.now().isoformat(),
                "error": str(e),
            }
            self._circuit_breaker["failures"] += 1
            self._circuit_breaker["last_failure"] = datetime.now()
            return False

    def analyze_text_logic(
        self,
        text: str,
        logic_type: str = "auto",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyse un texte en utilisant la logique formelle.

        Args:
            text: Texte à analyser
            logic_type: Type de logique ("propositional", "first_order", "modal", "auto")
            context: Contexte optionnel pour l'analyse

        Returns:
            Résultats de l'analyse logique
        """
        self.logger.info(
            f"Analyse logique de {len(text)} caractères (type: {logic_type})"
        )

        analysis_id = self._generate_analysis_id(text, logic_type)

        # Vérifier le cache
        if analysis_id in self.analysis_cache:
            self.logger.info("Résultat trouvé dans le cache")
            return self.analysis_cache[analysis_id]

        # Déterminer le type de logique si auto
        if logic_type == "auto":
            logic_type = self._determine_logic_type(text)

        # Effectuer l'analyse
        analysis_result = {
            "analysis_id": analysis_id,
            "text": text,
            "logic_type": logic_type,
            "timestamp": datetime.now().isoformat(),
            "belief_set": None,
            "queries": [],
            "query_results": [],
            "interpretation": "",
            "success": False,
            "error": None,
        }

        try:
            # Simuler l'analyse logique
            if logic_type == "propositional":
                analysis_result.update(self._analyze_propositional(text, context))
            elif logic_type == "first_order":
                analysis_result.update(self._analyze_first_order(text, context))
            elif logic_type == "modal":
                analysis_result.update(self._analyze_modal(text, context))
            else:
                raise ValueError(f"Type de logique non supporté: {logic_type}")

            analysis_result["success"] = True

        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse logique: {e}")
            analysis_result["error"] = str(e)

        # Mettre en cache
        self.analysis_cache[analysis_id] = analysis_result

        return analysis_result

    def validate_formula(self, formula: str, logic_type: str) -> Tuple[bool, str]:
        """
        Valide une formule logique.

        Args:
            formula: Formule à valider
            logic_type: Type de logique

        Returns:
            Tuple (valide, message)
        """
        self.logger.debug(f"Validation de formule {logic_type}: {formula}")

        try:
            if logic_type == "propositional":
                return self._validate_propositional_formula(formula)
            elif logic_type == "first_order":
                return self._validate_fol_formula(formula)
            elif logic_type == "modal":
                return self._validate_modal_formula(formula)
            else:
                return False, f"Type de logique non supporté: {logic_type}"

        except Exception as e:
            return False, f"Erreur lors de la validation: {e}"

    def execute_query(
        self, belief_set_id: str, query: str, logic_type: str
    ) -> Dict[str, Any]:
        """
        Exécute une requête logique sur un ensemble de croyances.

        Args:
            belief_set_id: Identifiant de l'ensemble de croyances
            query: Requête à exécuter
            logic_type: Type de logique

        Returns:
            Résultats de l'exécution de la requête
        """
        self.logger.info(f"Exécution de requête {logic_type}: {query}")

        result = {
            "belief_set_id": belief_set_id,
            "query": query,
            "logic_type": logic_type,
            "timestamp": datetime.now().isoformat(),
            "accepted": None,
            "message": "",
            "execution_time": 0.0,
            "success": False,
        }

        try:
            start_time = datetime.now()

            # Simuler l'exécution de la requête
            if logic_type == "propositional":
                accepted, message = self._execute_pl_query(query)
            elif logic_type == "first_order":
                accepted, message = self._execute_fol_query(query)
            elif logic_type == "modal":
                accepted, message = self._execute_modal_query(query)
            else:
                raise ValueError(f"Type de logique non supporté: {logic_type}")

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            result.update(
                {
                    "accepted": accepted,
                    "message": message,
                    "execution_time": execution_time,
                    "success": True,
                }
            )

        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la requête: {e}")
            result["message"] = str(e)

        return result

    # Méthodes privées pour l'analyse

    def _generate_analysis_id(self, text: str, logic_type: str) -> str:
        """Génère un ID unique pour l'analyse."""
        import hashlib

        content = f"{text}_{logic_type}_{datetime.now().strftime('%Y%m%d')}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _determine_logic_type(self, text: str) -> str:
        """Détermine automatiquement le type de logique le plus approprié."""
        # Heuristiques simples pour déterminer le type de logique
        if any(keyword in text.lower() for keyword in ["forall", "exists", "∀", "∃"]):
            return "first_order"
        elif any(
            keyword in text.lower() for keyword in ["necessarily", "possibly", "□", "◇"]
        ):
            return "modal"
        else:
            return "propositional"

    def _analyze_propositional(
        self, text: str, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyse en logique propositionnelle — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _analyze_first_order(
        self, text: str, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyse en logique du premier ordre — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _analyze_modal(
        self, text: str, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyse en logique modale — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _validate_propositional_formula(self, formula: str) -> Tuple[bool, str]:
        """Valide une formule propositionnelle — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _validate_fol_formula(self, formula: str) -> Tuple[bool, str]:
        """Valide une formule FOL — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _validate_modal_formula(self, formula: str) -> Tuple[bool, str]:
        """Valide une formule modale — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _execute_pl_query(self, query: str) -> Tuple[bool, str]:
        """Exécute une requête propositionnelle — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _execute_fol_query(self, query: str) -> Tuple[bool, str]:
        """Exécute une requête FOL — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def _execute_modal_query(self, query: str) -> Tuple[bool, str]:
        """Exécute une requête modale — refuse sans moteur (#2344)."""
        raise LogicEngineNotWiredError(_ENGINE_NOT_WIRED_MESSAGE)

    def analyze_text_logic_async(
        self,
        text: str,
        logic_type: str = "auto",
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 25.0,
    ) -> Dict[str, Any]:
        """
        Version asynchrone de l'analyse logique avec gestion robuste.

        Args:
            text: Texte à analyser
            logic_type: Type de logique
            context: Contexte optionnel
            timeout: Timeout en secondes

        Returns:
            Résultats de l'analyse logique asynchrone
        """
        if not self._is_circuit_breaker_open():
            try:
                # Exécuter l'analyse de manière asynchrone
                result = self.async_manager.run_hybrid(
                    self.analyze_text_logic,
                    text,
                    logic_type,
                    context,
                    timeout=timeout,
                    fallback_result=self._get_fallback_analysis_result(
                        text, logic_type
                    ),
                )

                # Réinitialiser le circuit breaker en cas de succès
                self._reset_circuit_breaker()
                return result

            except Exception as e:
                self.logger.error(f"Erreur lors de l'analyse asynchrone: {e}")
                self._record_circuit_breaker_failure()
                return self._get_fallback_analysis_result(text, logic_type, str(e))
        else:
            self.logger.warning("Circuit breaker ouvert, utilisation du fallback")
            return self._get_fallback_analysis_result(
                text, logic_type, "Circuit breaker ouvert"
            )

    def execute_multiple_queries_async(
        self, queries: List[Dict[str, str]], timeout: float = 45.0
    ) -> List[Dict[str, Any]]:
        """
        Exécute plusieurs requêtes logiques en parallèle.

        Args:
            queries: Liste de requêtes (dict avec 'belief_set_id', 'query', 'logic_type')
            timeout: Timeout global en secondes

        Returns:
            Liste des résultats d'exécution
        """
        self.logger.info(f"Exécution asynchrone de {len(queries)} requêtes")

        # Préparer les tâches
        query_tasks = []
        for query_def in queries:
            task_def = {
                "func": self.execute_query,
                "args": (
                    query_def.get("belief_set_id", ""),
                    query_def.get("query", ""),
                    query_def.get("logic_type", "propositional"),
                ),
                "kwargs": {},
                "timeout": timeout / len(queries),
                "fallback_result": {
                    "belief_set_id": query_def.get("belief_set_id", ""),
                    "query": query_def.get("query", ""),
                    "logic_type": query_def.get("logic_type", "propositional"),
                    # #2344 family (a): a timeout measures nothing, so the
                    # verdict is indeterminate — None, not a rejection.
                    "accepted": None,
                    "message": "Timeout ou erreur d'exécution",
                    "success": False,
                },
            }
            query_tasks.append(task_def)

        # Exécuter en parallèle
        results = self.async_manager.run_multiple_hybrid(
            query_tasks, max_concurrent=min(len(queries), 3), global_timeout=timeout
        )

        return results

    def _is_circuit_breaker_open(self) -> bool:
        """
        Vérifie si le circuit breaker est ouvert.

        Returns:
            True si le circuit breaker est ouvert
        """
        if self._circuit_breaker["failures"] >= self._circuit_breaker["max_failures"]:
            last_failure = self._circuit_breaker["last_failure"]
            if (
                last_failure and (datetime.now() - last_failure).total_seconds() < 300
            ):  # 5 minutes
                return True
            else:
                # Réinitialiser après 5 minutes
                self._reset_circuit_breaker()
        return False

    def _record_circuit_breaker_failure(self):
        """Enregistre un échec pour le circuit breaker."""
        self._circuit_breaker["failures"] += 1
        self._circuit_breaker["last_failure"] = datetime.now()

    def _reset_circuit_breaker(self):
        """Réinitialise le circuit breaker."""
        self._circuit_breaker["failures"] = 0
        self._circuit_breaker["last_failure"] = None

    def _get_fallback_analysis_result(
        self, text: str, logic_type: str, error: str = None
    ) -> Dict[str, Any]:
        """
        Génère un résultat d'analyse de fallback.

        Args:
            text: Texte analysé
            logic_type: Type de logique
            error: Message d'erreur optionnel

        Returns:
            Résultat de fallback
        """
        analysis_id = self._generate_analysis_id(text, logic_type)

        # #2344 family (a): this envelope used to fabricate a belief set, a
        # query and ``accepted: True`` under ``success: True`` — a verdict no
        # reasoner computed, only labelled. Unavailability is named in the
        # state (#1019), and what was not measured stays falsy: no belief
        # set, no query, no success.
        interpretation = f"Analyse de fallback pour {logic_type} - service temporairement indisponible"
        if not self._fallback_enabled:
            interpretation = (
                "Service indisponible et fallback désactivé - aucune analyse produite"
            )

        return {
            "analysis_id": analysis_id,
            "text": text,
            "logic_type": logic_type,
            "timestamp": datetime.now().isoformat(),
            "belief_set": None,
            "queries": [],
            "query_results": [],
            "interpretation": interpretation,
            "success": False,
            "fallback_mode": True,
            "error": error,
        }

    def get_service_status(self) -> Dict[str, Any]:
        """
        Version améliorée du statut du service avec monitoring.

        Returns:
            Dictionnaire du statut détaillé du service
        """
        try:
            # Statistiques des performances
            perf_stats = self.async_manager.get_performance_stats()

            # État du circuit breaker
            circuit_breaker_status = {
                "is_open": self._is_circuit_breaker_open(),
                "failures_count": self._circuit_breaker["failures"],
                "last_failure": (
                    self._circuit_breaker["last_failure"].isoformat()
                    if self._circuit_breaker["last_failure"]
                    else None
                ),
                "max_failures_threshold": self._circuit_breaker["max_failures"],
            }

            # Statistiques du cache
            cache_stats = {
                "cached_analyses": len(self.analysis_cache),
                "memory_usage_estimate": sum(
                    len(str(v)) for v in self.analysis_cache.values()
                )
                // 1024,  # KB approximatif
                "cache_hit_potential": len(self.analysis_cache) > 0,
            }

            # Déterminer le statut global
            if circuit_breaker_status["is_open"]:
                overall_status = "degraded"
            elif self._health_status.get("status") == "error":
                overall_status = "unhealthy"
            elif perf_stats["error_tasks"] > perf_stats["completed_tasks"]:
                overall_status = "degraded"
            else:
                overall_status = "healthy"

            return {
                "service_name": "LogicService",
                "status": overall_status,
                "logic_agents": self.logic_agents,
                "active_sessions": len(self.active_sessions),
                "cached_analyses": len(self.analysis_cache),
                "timestamp": datetime.now().isoformat(),
                "performance_stats": perf_stats,
                "circuit_breaker": circuit_breaker_status,
                "cache_stats": cache_stats,
                "fallback_enabled": self._fallback_enabled,
                "health_details": self._health_status,
            }

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du statut: {e}")
            return {
                "service_name": "LogicService",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def enable_fallback_mode(self, enabled: bool = True):
        """
        Choisit la formulation de l'enveloppe d'indisponibilité.

        Elle ne décide pas si une enveloppe de fallback est renvoyée — ce
        choix vit dans ``analyze_text_logic_async`` — et ne change aucun
        verdict : ``success`` est False dans les deux cas depuis #2344
        famille (a). Restent sous ce commutateur la phrase d'interprétation
        de l'enveloppe et le champ ``fallback_enabled`` du statut.

        Args:
            enabled: True pour la formulation standard, False pour celle
                qui nomme un fallback désactivé
        """
        self._fallback_enabled = enabled
        self.logger.info(f"Mode fallback {'activé' if enabled else 'désactivé'}")

    def clear_cache(self) -> bool:
        """
        Version améliorée du vidage du cache.

        Returns:
            True si le nettoyage réussit
        """
        try:
            cache_size_before = len(self.analysis_cache)
            self.analysis_cache.clear()

            # Nettoyer aussi les tâches async terminées
            cleaned_tasks = self.async_manager.cleanup_completed_tasks(max_age_hours=1)

            self.logger.info(
                f"Cache vidé: {cache_size_before} analyses, {cleaned_tasks} tâches async nettoyées"
            )
            return True

        except Exception as e:
            self.logger.error(f"Erreur lors du vidage du cache: {e}")
            return False

    def validate_and_sanitize_input(
        self, text: str, logic_type: str
    ) -> Tuple[bool, str, str]:
        """
        Valide et nettoie les entrées utilisateur.

        Args:
            text: Texte à valider
            logic_type: Type de logique à valider

        Returns:
            Tuple (is_valid, sanitized_text, sanitized_logic_type)
        """
        try:
            # Validation du type de logique (toujours faire cette validation)
            valid_logic_types = ["propositional", "first_order", "modal", "auto"]
            sanitized_logic_type = (
                logic_type if logic_type in valid_logic_types else "auto"
            )

            # Validation du texte
            if not text or not isinstance(text, str):
                return False, "", sanitized_logic_type

            # Nettoyage du texte (limite de taille, caractères spéciaux)
            sanitized_text = text.strip()[:10000]  # Limite à 10k caractères

            return True, sanitized_text, sanitized_logic_type

        except Exception as e:
            self.logger.error(f"Erreur lors de la validation: {e}")
            return False, "", "auto"

    def shutdown(self):
        """Arrête proprement le service logique."""
        self.logger.info("Arrêt du service logique...")

        try:
            # Nettoyer les ressources asynchrones
            self.async_manager.shutdown()

            # Vider les caches
            self.analysis_cache.clear()
            self.active_sessions.clear()

            # Mettre à jour le statut
            self._health_status = {
                "status": "shutdown",
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt: {e}")
