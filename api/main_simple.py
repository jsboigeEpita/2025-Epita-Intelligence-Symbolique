#!/usr/bin/env python3
"""
API FastAPI Simplifiée - GPT-4o-mini Authentique
=================================================

Version simplifiée de l'API FastAPI qui évite les dépendances complexes
et utilise directement GPT-4o-mini via OpenAI.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import des endpoints simplifiés
from .endpoints_simple import router as api_router

# Configuration de base
app = FastAPI(
    title="Argumentation Analysis API - Simple",
    description="API simplifiée d'analyse argumentative utilisant GPT-4o-mini",
    version="1.0.0"
)

# Configuration CORS pour permettre les appels depuis l'interface web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inclusion du router API
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Simplified Argumentation Analysis API",
        "version": "1.0.0",
        "features": ["GPT-4o-mini analysis", "Fallacy detection", "Simple API"],
        "endpoints": ["/api/analyze", "/api/status", "/api/examples"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Simplified API is running",
        "version": "1.0.0",
        "services": {
            "analysis": True,
            "gpt4o_mini": True,
            "simple_mode": True
        }
    }

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Actions au démarrage de l'API"""
    logger.info("🚀 Démarrage API FastAPI Simplifiée")
    logger.info("🤖 GPT-4o-mini activé")
    logger.info("✅ API prête pour les analyses")

@app.on_event("shutdown")
async def shutdown_event():
    """Actions à l'arrêt de l'API"""
    logger.info("🛑 Arrêt API FastAPI Simplifiée")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)