import asyncio
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP

@asynccontextmanager
async def app_lifespan(app: "FastMCP"):
    """Lifespan minimal pour le serveur."""
    print("Minimal server starting...")
    yield

# Création directe de l'instance du serveur avec le lifespan
mcp_server = FastMCP(lifespan=app_lifespan)

@mcp_server.tool(name="ping", description="A simple tool that returns 'pong'")
async def ping():
    """A simple tool that returns 'pong'."""
    return "pong"

if __name__ == "__main__":
    # La méthode .run() gère la boucle d'événements asyncio.
    mcp_server.run()