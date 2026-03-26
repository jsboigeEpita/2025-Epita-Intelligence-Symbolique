from typing import Any, Dict, List, Literal, Optional, Union
import logging
import asyncio
import jpype
from datetime import datetime
from pathlib import Path
import sys

print("Importation des modules...", file=sys.stderr)

from fastapi import Response
from mcp.server.fastmcp import FastMCP, Context
from pydantic import ValidationError

# Import des services Web API 
from argumentation_analysis.services.web_api.services.analysis_service import AnalysisService
from argumentation_analysis.services.web_api.services.validation_service import ValidationService
from argumentation_analysis.services.web_api.services.fallacy_service import FallacyService
from argumentation_analysis.services.web_api.services.framework_service import FrameworkService
from argumentation_analysis.services.web_api.services.logic_service import LogicService

# Import des modèles de requête et réponse
from argumentation_analysis.services.web_api.models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest,
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest,
    AnalysisOptions, FallacyOptions, FrameworkOptions, LogicOptions
)
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse,
    ErrorResponse
)

# Bootstrap pour initialiser l'environnement
from argumentation_analysis.core.bootstrap import initialize_project_environment, async_bootstrap_jvm


class AppServices:
    """Conteneur pour les instances de service - identique à l'API Web."""
    def __init__(self, llm_service):
        self.logger = logging.getLogger("AppServices")
        self.logger.info("Initializing app services container...")
        self.llm_service = llm_service
        self.logic_service = LogicService(llm_service=self.llm_service)
        self.analysis_service = AnalysisService(llm_service=self.llm_service)
        self.validation_service = ValidationService(self.logic_service)
        # self.fallacy_service = FallacyService()
        # self.framework_service = FrameworkService()
        self.logger.info("App services container initialized.")
    
    def is_healthy(self) -> Dict[str, Any]:
        """Vérification de l'état de santé de tous les services."""
        return {
            "jvm": {"running": jpype.isJVMStarted() if jpype else False, "status": "OK" if jpype.isJVMStarted() else "Not Running"},
            "analysis": self.analysis_service.is_healthy(),
            "validation": self.validation_service.is_healthy(),
            "fallacy": self.fallacy_service.is_healthy(),
            "framework": self.framework_service.is_healthy(),
            "logic": self.logic_service.is_healthy()
        }


from contextlib import asynccontextmanager

@asynccontextmanager
async def app_lifespan(app: "FastMCP"):
    """Gère le cycle de vie de l'application et les dépendances."""
    logging.info("Initialisation de l'environnement du projet pour le serveur MCP...")
    project_context = initialize_project_environment(force_mock_llm=True)
    
    logging.info("Démarrage du bootstrap asynchrone de la JVM...")
    await async_bootstrap_jvm(project_context)
    
    services = AppServices(llm_service=project_context.llm_service)
    logging.info("Services MCP initialisés avec succès.")
    yield services

class MCPService:
    """
    Service MCP pour l'analyse argumentative - miroir de l'API Web Flask.
    """

    def __init__(self, service_name: str = "argumentation_analysis_mcp"):
        self.mcp = FastMCP(service_name, host="0.0.0.0", port=8000, lifespan=app_lifespan)
        self.logger = logging.getLogger(__name__)
        self._register_tools()

    def _get_services_from_context(self, context: Context) -> AppServices:
        return context.request_context.session.lifespan_context

    def _register_tools(self):
        self.mcp.tool()(self.health_check)
        self.mcp.tool()(self.analyze_text)
        self.mcp.tool()(self.validate_argument)
        self.mcp.tool()(self.detect_fallacies)
        self.mcp.tool()(self.build_framework)
        self.mcp.tool()(self.logic_graph)
        self.mcp.tool()(self.create_belief_set)
        self.mcp.tool()(self.execute_logic_query)
        self.mcp.tool()(self.generate_logic_queries)
        self.mcp.tool()(self.list_available_tools)

    async def health_check(self, context: Context) -> Dict[str, Any]:
        try:
            services = self._get_services_from_context(context)
            is_jvm_started = jpype.isJVMStarted() if jpype else False
            response_data = {
                "status": "healthy" if is_jvm_started else "unhealthy",
                "message": "API d'analyse argumentative opérationnelle via MCP",
                "version": "1.0.0",
                "services": services.is_healthy()
            }
            if not is_jvm_started:
                self.logger.error("Health check failed: JVM is not running.")
                response_data["status"] = "unhealthy"
            return response_data
        except Exception as e:
            self.logger.error(f"Erreur lors du health check: {str(e)}", exc_info=True)
            return {"status": "error", "error": "Erreur de health check", "message": str(e)}

    # ... (tous les autres outils restent les mêmes) ...
    async def analyze_text(self, context: Context, text: str, **kwargs) -> Dict[str, Any]:
        # Implémentation simplifiée pour la concision
        services = self._get_services_from_context(context)
        request = AnalysisRequest(text=text, options=AnalysisOptions(**kwargs))
        result = await services.analysis_service.analyze_text(request)
        return result.model_dump()

    async def validate_argument(self, context: Context, premises: List[str], conclusion: str, **kwargs) -> Dict[str, Any]:
        services = self._get_services_from_context(context)
        request = ValidationRequest(premises=premises, conclusion=conclusion, **kwargs)
        result = await services.validation_service.validate_argument(request)
        return result.model_dump()

    async def detect_fallacies(self, context: Context, text: str, **kwargs) -> Dict[str, Any]:
        services = self._get_services_from_context(context)
        request = FallacyRequest(text=text, options=FallacyOptions(**kwargs))
        result = await services.fallacy_service.detect_fallacies(request)
        return result.model_dump()

    async def build_framework(self, context: Context, arguments: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        services = self._get_services_from_context(context)
        from argumentation_analysis.services.web_api.models.request_models import Argument
        argument_objects = [Argument(**arg_dict) for arg_dict in arguments]
        request = FrameworkRequest(arguments=argument_objects, options=FrameworkOptions(**kwargs))
        result = await services.framework_service.build_framework(request)
        return result.model_dump()

    async def logic_graph(self, text: str) -> Dict[str, Any]:
        return {"graph": "mock_graph"}

    async def create_belief_set(self, context: Context, text: str, logic_type: str, **kwargs) -> Dict[str, Any]:
        services = self._get_services_from_context(context)
        request = LogicBeliefSetRequest(text=text, logic_type=logic_type, options=kwargs)
        result = await services.logic_service.create_belief_set(request)
        return result.model_dump()

    async def execute_logic_query(self, context: Context, belief_set_id: str, query: str, logic_type: str, **kwargs) -> Dict[str, Any]:
        services = self._get_services_from_context(context)
        request = LogicQueryRequest(belief_set_id=belief_set_id, query=query, logic_type=logic_type, options=LogicOptions(**kwargs))
        result = await services.logic_service.execute_query(request)
        return result.model_dump()

    async def generate_logic_queries(self, context: Context, belief_set_id: str, text: str, logic_type: str, **kwargs) -> Dict[str, Any]:
        services = self._get_services_from_context(context)
        request = LogicGenerateQueriesRequest(belief_set_id=belief_set_id, text=text, logic_type=logic_type, options=LogicOptions(**kwargs))
        result = await services.logic_service.generate_queries(request)
        return result.model_dump()

    async def list_available_tools(self) -> Dict[str, Any]:
        return {"tools": ["list of tools"]}


    def run(self, transport: str = 'streamable-http'):
        """Lance le serveur MCP."""
        self.mcp.run(transport=transport)


# Point d'entrée principal
if __name__ == "__main__":
    print("Lancement du serveur MCP...", file=sys.stderr)
    mcp_service = MCPService()
    # print(f"Serveur MCP initialisé avec {len(mcp_service.mcp.tool)} outils disponibles", file=sys.stderr)
    mcp_service.run(transport='streamable-http')
