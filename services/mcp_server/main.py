from typing import Any, Dict, List, Literal, Optional
print("Importation des modules...")
# L'import de httpx n'est plus nécessaire car nous n'utilisons plus de requêtes HTTP
# import httpx
from fastapi import Response
from mcp.server.fastmcp import FastMCP

# TODO: Importer les véritables modules d'analyse une fois identifiés.
# from argumentation_analysis.main_analyzer import MainAnalyzer
# from argumentation_analysis.validator import ArgumentValidator
# from argumentation_analysis.fallacy_detector import FallacyDetector
# from argumentation_analysis.dung_framework_builder import DungFrameworkBuilder
# from argumentation_analysis.

from argumentation_analysis.orchestration.service_manager import ServiceManager




class MCPService:
    """
    Service MCP pour l'analyse argumentative, intégré à l'écosystème du projet.
    Hérite de BaseService pour être géré par le ServiceManager.
    """

    def __init__(self, service_name: str = "argumentation_analysis_mcp"):
        """
        Initialise le service MCP et enregistre les outils.
        """
        self.mcp = FastMCP(service_name, host="0.0.0.0", port=8000)

        self.service_manager = ServiceManager()
        self._register_tools()

    def _register_tools(self):
        """Enregistre tous les outils MCP."""
        self.mcp.tool()(self.analyze)
        # self.mcp.tool()(self.validate_argument)
        self.mcp.tool()(self.detect_fallacies)
        # self.mcp.tool()(self.build_framework)

    async def raw_tool(self, text: str, analysis_type: Literal["comprehensive", "logical", "rhetorical"] = "comprehensive", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.service_manager.analyze_text(text=text, analysis_type=analysis_type, options=options)

    async def analyze(self, text: str) -> str:
        """Analyse complète d'un texte argumentatif."""
        return self.service_manager.analyze_text(text=text, analysis_type="comprehensive")

    async def detect_fallacies(self, text: str) -> dict:
        """Détection de sophismes dans un texte."""
        return self.service_manager.analyze_text(
            text=text,
            analysis_type="comprehensive",
            options={'detect_fallacies': True}
        )

    def run(self, transport: str = 'streamable-http'):
        """Lance le serveur MCP."""
        self.mcp.run(transport=transport)




# if __name__ == "__main__":
#     # Initialise et lance le service
print("Lancement du serveur MCP...")
mcp_service = MCPService()
print("Serveur MCP initialisé")
mcp_service.run("stdio")