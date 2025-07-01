#!/usr/bin/env python3
"""
API FastAPI Simplifiée - GPT-4o-mini Authentique
=================================================

Version simplifiée de l'API FastAPI qui évite les dépendances complexes
et utilise directement GPT-4o-mini via OpenAI.
"""
import logging
from .factory import create_app
from .endpoints_simple import router as api_router

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Gestion du cycle de vie ---

async def startup_event():
    """Actions au démarrage de l'API."""
    logger.info("🚀 Démarrage API FastAPI Simplifiée")
    logger.info("🤖 GPT-4o-mini activé")
    logger.info("✅ API prête pour les analyses")

async def shutdown_event():
    """Actions à l'arrêt de l'API."""
    logger.info("🛑 Arrêt API FastAPI Simplifiée")

# --- Création de l'application via la factory ---
app = create_app(
    title="Argumentation Analysis API - Simple",
    description="API simplifiée d'analyse argumentative utilisant GPT-4o-mini",
    version="1.0.0",
    on_startup=[startup_event],
    on_shutdown=[shutdown_event]
)

# --- Routes ---

# Inclusion du routeur pour les endpoints d'analyse (/api/...)
app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Monitoring"])
def root():
    """Point d'entrée racine de l'API simplifiée."""
    return {
        "message": "Welcome to the Simplified Argumentation Analysis API",
        "version": "1.0.0",
        "status": "Running",
        "docs": "/docs"
    }

@app.get("/health", tags=["Monitoring"])
def health_check():
    """Vérifie l'état de santé de l'API simplifiée."""
    return {
        "status": "healthy",
        "message": "Simplified API is running and ready to serve requests."
    }

# --- Point d'entrée pour exécution directe ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)