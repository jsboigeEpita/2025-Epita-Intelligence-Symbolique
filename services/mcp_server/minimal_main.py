import asyncio
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP

@asynccontextmanager
async def app_lifespan(app: "FastMCP"):
    """Lifespan minimal pour le serveur."""
    print("Minimal server starting...")
    yield

# Création directe de l'instance du serveur avec le lifespan
mcp_server = FastMCP(
    service_name="minimal_server",
    host="127.0.0.1",
    port=8000,
    lifespan=app_lifespan
)

@mcp_server.tool()
async def ping():
    """A simple tool that returns 'pong'."""
    return "pong"

if __name__ == "__main__":
    # On force le transport stdio pour les tests
    mcp_server.run(transport='streamable-http')