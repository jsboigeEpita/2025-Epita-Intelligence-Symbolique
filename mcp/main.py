from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("argumentation_analysis_mcp")

WEB_API_URL = "http://localhost:5000/api"

@mcp.tool()
async def analyze(text: str, options: dict = None) -> str:
    """Analyse complète d'un texte argumentatif

    Args:
        text: string (requis) - Texte à analyser
        options: object (optionnel) - Options d'analyse
    """
    url = f"{WEB_API_URL}/analyze"
    response = httpx.post(url, json={"text": text, "options": options})
    return response.json()


@mcp.tool()
async def validate_argument(premises: list[str], conclusion: str, argument_type: str = None) -> dict:
    """Validation logique d'un argument

    Args:
        premises: list[str] (requis) - Liste des prémisses
        conclusion: str (requis) - Conclusion
        argument_type: str (optionnel) - Type d'argument (ex: deductive, inductive)
    """
    url = f"{WEB_API_URL}/validate"
    payload = {"premises": premises, "conclusion": conclusion}
    if argument_type:
        payload["argument_type"] = argument_type
    response = httpx.post(url, json=payload)
    return response.json()


@mcp.tool()
async def detect_fallacies(text: str, options: dict = None) -> dict:
    """Détection de sophismes dans un texte

    Args:
        text: string (requis) - Texte à analyser
        options: object (optionnel) - Options de détection (ex: {"severity_threshold": 0.5})
    """
    url = f"{WEB_API_URL}/fallacies"
    response = httpx.post(url, json={"text": text, "options": options})
    return response.json()


@mcp.tool()
async def build_framework(arguments: list, options: dict = None) -> dict:
    """Construction d'un framework de Dung à partir d'une liste d'arguments et d'attaques.

    Args:
        arguments: list (requis) - Liste des arguments et de leurs attaques.
                   Exemple: [{"id": "arg1", "content": "Contenu", "attacks": ["arg2"]}]
        options: object (optionnel) - Options pour la construction du framework (ex: {"compute_extensions": true})
    """
    url = f"{WEB_API_URL}/framework"
    response = httpx.post(url, json={"arguments": arguments, "options": options})
    return response.json()


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')