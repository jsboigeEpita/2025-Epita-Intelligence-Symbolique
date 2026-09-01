from typing import Any, Dict, List, Literal, Optional, Union
import logging
import asyncio

try:
    import jpype
except ImportError:
    # #1677: jpype is a hard dep of environment.yml and CI installs it, but the
    # honest-absent contract ("JVM unavailable ⇒ boot degraded, health reports
    # unhealthy") must hold when it is absent. The bare ``import jpype`` made the
    # ``jpype.isJVMStarted() if jpype else False`` defenses below (l.73, l.169)
    # unreachable: the module never loaded in a jpype-less env. Binding to None
    # lets those defenses fire — degraded boot instead of crash. Mirror of the
    # _invoke_bipolar guard (#1682).
    jpype = None  # type: ignore[assignment]
from datetime import datetime
from pathlib import Path
import sys

print("Importation des modules...")

from fastapi import Response
from mcp.server import MCPServer
from pydantic import ValidationError

# Import des services Web API
from argumentation_analysis.services.web_api.services.analysis_service import (
    AnalysisService,
)
from argumentation_analysis.services.web_api.services.validation_service import (
    ValidationService,
)
from argumentation_analysis.services.web_api.services.fallacy_service import (
    FallacyService,
)
from argumentation_analysis.services.web_api.services.framework_service import (
    FrameworkService,
)
from argumentation_analysis.services.web_api.services.logic_service import LogicService

# Import des modèles de requête et réponse
from argumentation_analysis.services.web_api.models.request_models import (
    AnalysisRequest,
    ValidationRequest,
    FallacyRequest,
    LogicBeliefSetRequest,
    LogicQueryRequest,
    LogicGenerateQueriesRequest,
    AnalysisOptions,
    FallacyOptions,
    LogicOptions,
)
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse,
    ValidationResponse,
    FallacyResponse,
    FrameworkResponse,
    ErrorResponse,
)

# Bootstrap pour initialiser l'environnement
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.core.llm_service import create_llm_service


class AppServices:
    """Conteneur pour les instances de service - identique à l'API Web."""

    def __init__(self):
        self.logger = logging.getLogger("AppServices")
        self.logger.info("Initializing app services container...")
        # #1864: LogicService et AnalysisService exigent un llm_service — les
        # constructeurs nus levaient TypeError au boot (serveur inconstructible).
        # Câblage en miroir du conteneur de l'API Web
        # (docs/archives/services_web_api_flask/app.py) : un service LLM par
        # consommateur, via la fabrique canonique. Pas de défaut ``= None``
        # sur les constructeurs : ça déplacerait la panne du démarrage vers
        # le premier appel réel.
        logic_llm = create_llm_service(service_id="logic_service")
        analysis_llm = create_llm_service(service_id="analysis_service")
        self.logic_service = LogicService(llm_service=logic_llm)
        self.analysis_service = AnalysisService(llm_service=analysis_llm)
        self.validation_service = ValidationService(self.logic_service)
        self.fallacy_service = FallacyService()
        self.framework_service = FrameworkService()
        self.logger.info("App services container initialized.")

    def is_healthy(self) -> Dict[str, Any]:
        """Vérification de l'état de santé de tous les services."""
        return {
            "jvm": {
                "running": jpype.isJVMStarted() if jpype else False,
                # #1677: guard the status too — jpype may be None (absent), in
                # which case ``jpype.isJVMStarted()`` would raise AttributeError.
                # The ``running`` line above is already guarded; this one wasn't,
                # a latent crash the import-guard fix (l.4) exposes.
                "status": "OK" if (jpype and jpype.isJVMStarted()) else "Not Running",
            },
            "analysis": self.analysis_service.is_healthy(),
            "validation": self.validation_service.is_healthy(),
            "fallacy": self.fallacy_service.is_healthy(),
            "framework": self.framework_service.is_healthy(),
            "logic": self.logic_service.is_healthy(),
        }


class MCPService:
    """
    Service MCP pour l'analyse argumentative.

    V1 tools (10): mirror the Flask web API (analysis, validation, fallacy,
    framework, logic).
    V2 tools (13): expose the full infrastructure — workflows, capabilities,
    multi-turn conversations, and specialized agents.
    """

    def __init__(self, service_name: str = "argumentation_analysis_mcp"):
        """
        Initialise le service MCP avec les mêmes services que l'API Web.
        """
        # mcp 2.x (#1559): host/port moved out of the constructor into run().
        self.mcp = MCPServer(service_name)
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self.services = None
        self._registry = None
        self._session_manager = None
        self._ensure_initialized()  # Initialisation directe
        self._register_tools()
        self._register_v2_tools()

    def _ensure_initialized(self):
        """S'assure que les services sont initialisés selon le pattern de l'API Web."""
        if not self._initialized:
            try:
                # Initialiser l'environnement du projet (incluant JVM si nécessaire)
                current_dir = Path(__file__).resolve().parent
                root_dir = current_dir.parent.parent

                self.logger.info("Initializing project environment...")
                initialize_project_environment(root_path_str=str(root_dir))

                # Initialiser les services comme dans l'API Web
                self.services = AppServices()

                self._initialized = True
                self.logger.info("MCP services initialized successfully")

            except Exception as e:
                self.logger.error(f"Failed to initialize MCP services: {e}")
                raise RuntimeError(f"MCP service initialization failed: {e}")

    def _register_tools(self):
        """Enregistre les outils MCP - miroir des routes de l'API Web."""
        # Route équivalente: GET /api/health
        self.mcp.tool()(self.health_check)

        # Route équivalente: POST /api/analyze
        self.mcp.tool()(self.analyze_text)

        # Route équivalente: POST /api/validate
        self.mcp.tool()(self.validate_argument)

        # Route équivalente: POST /api/fallacies
        self.mcp.tool()(self.detect_fallacies)

        # Route équivalente: POST /api/framework
        self.mcp.tool()(self.build_framework)

        # Route équivalente: POST /api/logic_graph
        self.mcp.tool()(self.logic_graph)

        # Routes logiques: /api/logic/*
        self.mcp.tool()(self.create_belief_set)
        self.mcp.tool()(self.execute_logic_query)
        self.mcp.tool()(self.generate_logic_queries)

        # Route équivalente: GET /api/endpoints
        self.mcp.tool()(self.list_available_tools)

    # === OUTIL DE SANTÉ ===

    async def health_check(self) -> Dict[str, Any]:
        """
        Vérification de l'état de l'API, y compris les dépendances critiques comme la JVM.
        Équivalent de GET /api/health
        """
        self._ensure_initialized()

        try:
            # Vérification de l'état de la JVM (identique à l'API Web)
            is_jvm_started = jpype.isJVMStarted() if jpype else False

            # Construction de la réponse (identique à l'API Web)
            response_data = {
                "status": "healthy" if is_jvm_started else "unhealthy",
                "message": "API d'analyse argumentative opérationnelle via MCP",
                "version": "1.0.0",
                "services": self.services.is_healthy(),
            }

            if not is_jvm_started:
                self.logger.error("Health check failed: JVM is not running.")
                response_data["status"] = "unhealthy"

            return response_data

        except Exception as e:
            self.logger.error(f"Erreur lors du health check: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": "Erreur de health check",
                "message": str(e),
            }

    # === OUTIL D'ANALYSE PRINCIPALE ===

    async def analyze_text(
        self,
        text: str,
        detect_fallacies: bool = True,
        analyze_structure: bool = True,
        evaluate_coherence: bool = True,
        include_context: bool = True,
        severity_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Analyse complète d'un texte argumentatif.
        Équivalent de POST /api/analyze

        Args:
            text: Texte à analyser
            detect_fallacies: Détecter les sophismes
            analyze_structure: Analyser la structure argumentative
            evaluate_coherence: Évaluer la cohérence
            include_context: Inclure le contexte dans l'analyse
            severity_threshold: Seuil de sévérité (0.0-1.0)
        """
        self._ensure_initialized()

        try:
            # Construire la requête avec validation (identique à l'API Web)
            options = AnalysisOptions(
                detect_fallacies=detect_fallacies,
                analyze_structure=analyze_structure,
                evaluate_coherence=evaluate_coherence,
                include_context=include_context,
                severity_threshold=severity_threshold,
            )

            analysis_request = AnalysisRequest(text=text, options=options)

            # Appeler le service (identique à l'API Web)
            result = await self.services.analysis_service.analyze_text(analysis_request)

            return result.model_dump()

        except ValidationError as e:
            self.logger.warning(f"Validation des données d'analyse a échoué: {str(e)}")
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {str(e)}", exc_info=True)
            return {"error": "Erreur d'analyse", "message": str(e), "status_code": 500}

    # === OUTIL DE VALIDATION ===

    async def validate_argument(
        self, premises: List[str], conclusion: str, argument_type: str = "deductive"
    ) -> Dict[str, Any]:
        """
        Validation logique d'un argument.
        Équivalent de POST /api/validate

        Args:
            premises: Liste des prémisses
            conclusion: Conclusion de l'argument
            argument_type: Type d'argument (deductive, inductive, abductive)
        """
        self._ensure_initialized()

        try:
            # Construire la requête avec validation (identique à l'API Web)
            validation_request = ValidationRequest(
                premises=premises, conclusion=conclusion, argument_type=argument_type
            )

            # Appeler le service (identique à l'API Web)
            result = await self.services.validation_service.validate_argument(
                validation_request
            )

            return result.model_dump()

        except ValidationError as e:
            self.logger.warning(f"Validation des données a échoué: {str(e)}")
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation: {str(e)}", exc_info=True)
            return {
                "error": "Erreur de validation",
                "message": str(e),
                "status_code": 500,
            }

    # === OUTIL DE DÉTECTION DE SOPHISMES ===

    async def detect_fallacies(
        self,
        text: str,
        severity_threshold: float = 0.5,
        include_context: bool = True,
        max_fallacies: int = 10,
        categories: Optional[List[str]] = None,
        use_enhanced: bool = True,
        use_contextual: bool = True,
        use_patterns: bool = True,
    ) -> Dict[str, Any]:
        """
        Détection de sophismes dans un texte.
        Équivalent de POST /api/fallacies

        Args:
            text: Texte à analyser
            severity_threshold: Seuil de sévérité (0.0-1.0)
            include_context: Inclure le contexte
            max_fallacies: Nombre maximum de sophismes à retourner
            categories: Catégories de sophismes à rechercher
            use_enhanced: Utiliser l'analyseur Enhanced Contextual
            use_contextual: Utiliser l'analyseur Contextual
            use_patterns: Utiliser la détection par patterns
        """
        self._ensure_initialized()

        try:
            # Construire la requête avec validation (identique à l'API Web)
            options = FallacyOptions(
                severity_threshold=severity_threshold,
                include_context=include_context,
                max_fallacies=max_fallacies,
                categories=categories,
                use_enhanced=use_enhanced,
                use_contextual=use_contextual,
                use_patterns=use_patterns,
            )

            fallacy_request = FallacyRequest(text=text, options=options)

            # Appeler le service (identique à l'API Web)
            result = await self.services.fallacy_service.detect_fallacies(
                fallacy_request
            )

            return result.model_dump()

        except ValidationError as e:
            self.logger.warning(f"Validation des données a échoué: {str(e)}")
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la détection de sophismes: {str(e)}", exc_info=True
            )
            return {
                "error": "Erreur de détection",
                "message": str(e),
                "status_code": 500,
            }

    # === OUTIL DE CONSTRUCTION DE FRAMEWORK ===

    async def build_framework(
        self,
        arguments: List[Dict[str, Any]],
        max_arguments: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyse d'un framework de Dung.
        Équivalent de POST /api/framework

        Args:
            arguments: Liste des arguments avec id, content, attacks, supports
            max_arguments: Nombre maximum d'arguments
        """
        self._ensure_initialized()

        try:
            # Valider les entrées via le modèle (identique à l'API Web)
            from argumentation_analysis.services.web_api.models.request_models import (
                Argument,
            )

            if len(arguments) > max_arguments:
                return {
                    "error": "Trop d'arguments",
                    "message": (
                        f"{len(arguments)} arguments dépassent la limite "
                        f"de {max_arguments}"
                    ),
                    "status_code": 400,
                }

            # Convertir les dictionnaires en objets Argument
            argument_objects = []
            for arg_dict in arguments:
                argument_objects.append(Argument(**arg_dict))

            # #1864: la surface réelle du service est analyze_dung_framework(
            # arguments, attacks) — synchrone, dict brut (pas de model_dump).
            # L'appel précédent visait build_framework(FrameworkRequest), une
            # méthode qu'aucune version du service n'a jamais exposée ; les
            # paramètres compute_extensions/semantics/include_visualization
            # décrivaient cette interface fantôme (le service calcule les
            # extensions preferred, sans option). Paires d'attaques dérivées
            # des listes `attacks` de chaque argument, miroir de la route
            # /api/v1/framework/analyze archivée.
            argument_ids = [arg.id for arg in argument_objects]
            attack_pairs = [
                [arg.id, target]
                for arg in argument_objects
                for target in (arg.attacks or [])
            ]

            return self.services.framework_service.analyze_dung_framework(
                argument_ids, attack_pairs
            )

        except ValidationError as e:
            self.logger.warning(f"Validation des données a échoué: {str(e)}")
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la construction du framework: {str(e)}", exc_info=True
            )
            return {
                "error": "Erreur de framework",
                "message": str(e),
                "status_code": 500,
            }

    # === OUTIL DE GRAPHE LOGIQUE ===

    async def logic_graph(self, text: str) -> Dict[str, Any]:
        """
        Analyse un texte et retourne une représentation de graphe logique.
        Équivalent de POST /api/logic_graph

        Args:
            text: Texte à analyser pour le graphe logique
        """
        self._ensure_initialized()

        try:
            if not text or not text.strip():
                return {
                    "error": "Texte vide",
                    "message": "L'analyse d'un texte vide n'est pas supportée.",
                    "status_code": 400,
                }

            # Implémentation basique (identique à l'API Web)
            mock_graph_data = {
                "graph": '<svg width="100" height="100"><circle cx="50" cy="50" r="40" stroke="green" stroke-width="4" fill="yellow" /></svg>'
            }
            return mock_graph_data

        except Exception as e:
            self.logger.error(
                f"Erreur lors de la génération du graphe logique: {str(e)}",
                exc_info=True,
            )
            return {
                "error": "Erreur de génération de graphe",
                "message": str(e),
                "status_code": 500,
            }

    # === OUTILS LOGIQUES ===

    async def create_belief_set(
        self,
        text: str,
        logic_type: Literal["propositional", "first_order", "modal"],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Conversion d'un texte en ensemble de croyances logiques.
        Équivalent de POST /api/logic/belief_set

        Args:
            text: Texte à convertir
            logic_type: Type de logique
            options: Options de conversion flexibles
        """
        self._ensure_initialized()

        try:
            request = LogicBeliefSetRequest(
                text=text, logic_type=logic_type, options=options or {}
            )

            result = await self.services.logic_service.create_belief_set(request)
            return result.model_dump()

        except ValidationError as e:
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(f"Erreur création belief set: {str(e)}", exc_info=True)
            return {"error": "Erreur belief set", "message": str(e), "status_code": 500}

    async def execute_logic_query(
        self,
        belief_set_id: str,
        query: str,
        logic_type: Literal["propositional", "first_order", "modal"],
        include_explanation: bool = True,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Exécution d'une requête logique sur un ensemble de croyances.
        Équivalent de POST /api/logic/query

        Args:
            belief_set_id: ID de l'ensemble de croyances
            query: Requête logique à exécuter
            logic_type: Type de logique
            include_explanation: Inclure une explication détaillée
            timeout: Timeout en secondes
        """
        self._ensure_initialized()

        try:
            options = LogicOptions(
                include_explanation=include_explanation, timeout=timeout
            )

            request = LogicQueryRequest(
                belief_set_id=belief_set_id,
                query=query,
                logic_type=logic_type,
                options=options,
            )

            result = await self.services.logic_service.execute_query(request)
            return result.model_dump()

        except ValidationError as e:
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(f"Erreur exécution requête: {str(e)}", exc_info=True)
            return {"error": "Erreur requête", "message": str(e), "status_code": 500}

    async def generate_logic_queries(
        self,
        belief_set_id: str,
        text: str,
        logic_type: Literal["propositional", "first_order", "modal"],
        max_queries: int = 5,
        include_explanation: bool = True,
    ) -> Dict[str, Any]:
        """
        Génération de requêtes logiques pertinentes.
        Équivalent de POST /api/logic/generate_queries

        Args:
            belief_set_id: ID de l'ensemble de croyances
            text: Texte source pour la génération de requêtes
            logic_type: Type de logique
            max_queries: Nombre maximum de requêtes à générer
            include_explanation: Inclure une explication détaillée
        """
        self._ensure_initialized()

        try:
            options = LogicOptions(
                include_explanation=include_explanation, max_queries=max_queries
            )

            request = LogicGenerateQueriesRequest(
                belief_set_id=belief_set_id,
                text=text,
                logic_type=logic_type,
                options=options,
            )

            result = await self.services.logic_service.generate_queries(request)
            return result.model_dump()

        except ValidationError as e:
            return {"error": "Données invalides", "message": str(e), "status_code": 400}
        except Exception as e:
            self.logger.error(f"Erreur génération requêtes: {str(e)}", exc_info=True)
            return {"error": "Erreur génération", "message": str(e), "status_code": 500}

    # === OUTIL D'INFORMATION ===

    async def list_available_tools(self) -> Dict[str, Any]:
        """
        Liste tous les outils disponibles avec leur documentation.
        Équivalent de GET /api/endpoints
        """
        tools = {
            # V1 tools (original)
            "health_check": {
                "description": "Vérification de l'état de l'API et services"
            },
            "analyze_text": {"description": "Analyse complète d'un texte argumentatif"},
            "validate_argument": {"description": "Validation logique d'un argument"},
            "detect_fallacies": {"description": "Détection de sophismes"},
            "build_framework": {"description": "Construction d'un framework de Dung"},
            "logic_graph": {"description": "Génération d'un graphe logique"},
            "create_belief_set": {
                "description": "Création d'un ensemble de croyances logiques"
            },
            "execute_logic_query": {"description": "Exécution d'une requête logique"},
            "generate_logic_queries": {
                "description": "Génération de requêtes logiques"
            },
            "list_available_tools": {"description": "Liste des outils disponibles"},
            # V2 tools (infrastructure)
            "list_workflows": {
                "description": "Liste les workflows d'analyse disponibles"
            },
            "run_workflow": {"description": "Exécute un workflow d'analyse nommé"},
            "get_workflow_details": {"description": "Détails d'un workflow spécifique"},
            "start_conversation": {
                "description": "Démarre une conversation d'analyse multi-tour"
            },
            "continue_conversation": {
                "description": "Continue une conversation existante"
            },
            "get_conversation_status": {
                "description": "Statut d'une session conversationnelle"
            },
            "list_capabilities": {
                "description": "Liste les capacités enregistrées et leurs fournisseurs"
            },
            "invoke_capability": {"description": "Invoque une capacité par nom"},
            "get_registry_summary": {
                "description": "Résumé détaillé du registre de capacités"
            },
            "evaluate_quality": {
                "description": "Évalue la qualité argumentative (9 vertus)"
            },
            "generate_counter_argument": {
                "description": "Génère des contre-arguments (5 stratégies rhétoriques)"
            },
            "run_debate_analysis": {
                "description": "Analyse par débat adversarial multi-personnalités"
            },
            "run_governance_analysis": {
                "description": "Analyse pour prise de décision collective : 5 scrutins (majority, plurality, Borda, Condorcet, quadratic) + 2 protocoles de consensus distribué (Byzantine, Raft) + 8 fonctions de choix social (approval, STV, Copeland, Kemeny-Young + safe, Schulze, Condorcet winner, pairwise matrix). Byzantine et Raft sont des protocoles de tolérance aux pannes, pas des scrutins (#1981)."
            },
        }

        return {
            "api_name": "Service MCP d'Analyse Argumentative",
            "version": "2.0.0",
            "transport": "MCP",
            "tools": tools,
            "total_tools": len(tools),
        }

    # === V2 INFRASTRUCTURE ===

    def _ensure_registry(self):
        """Lazily initialize the CapabilityRegistry."""
        if self._registry is None:
            from argumentation_analysis.orchestration.unified_pipeline import (
                setup_registry,
            )

            self._registry = setup_registry()
            self.logger.info("CapabilityRegistry initialized")
        return self._registry

    def _get_session_manager(self):
        """Lazily initialize the SessionManager."""
        if self._session_manager is None:
            from argumentation_analysis.services.mcp_server.session_manager import (
                SessionManager,
            )

            self._session_manager = SessionManager()
            self.logger.info("SessionManager initialized")
        return self._session_manager

    def _register_v2_tools(self):
        """Register v2 tools (workflow, conversation, capability, specialized).

        Fails silently if dependencies are not available, preserving backward
        compatibility with the original 10 tools.
        """
        try:
            from argumentation_analysis.services.mcp_server.tools.workflow_tools import (
                register_workflow_tools,
            )
            from argumentation_analysis.services.mcp_server.tools.conversation_tools import (
                register_conversation_tools,
            )
            from argumentation_analysis.services.mcp_server.tools.capability_tools import (
                register_capability_tools,
            )
            from argumentation_analysis.services.mcp_server.tools.specialized_tools import (
                register_specialized_tools,
            )

            register_workflow_tools(self.mcp, self._ensure_registry)
            register_conversation_tools(
                self.mcp, self._ensure_registry, self._get_session_manager
            )
            register_capability_tools(self.mcp, self._ensure_registry)
            register_specialized_tools(self.mcp, self._ensure_registry)

            self.logger.info("V2 tools registered successfully (13 additional tools)")
        except Exception as e:
            self.logger.warning(f"V2 tools not registered: {e}")

    def run(
        self,
        transport: str = "streamable-http",
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        """Lance le serveur MCP.

        mcp 2.x (#1559): transport-specific params (host/port) are passed here,
        not to the MCPServer constructor.
        """
        # transport is a runtime str; MCPServer.run's overloads are per-Literal,
        # so mypy cannot narrow — stdio ignores host/port server-side (see #1559).
        self.mcp.run(transport=transport, host=host, port=port)  # type: ignore[call-overload]


# Point d'entrée principal
if __name__ == "__main__":
    print("Lancement du serveur MCP...")
    mcp_service = MCPService()
    print("Serveur MCP initialisé avec 23 outils disponibles")
    mcp_service.run("streamable-http")
