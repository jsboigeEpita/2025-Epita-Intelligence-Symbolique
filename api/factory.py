import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Callable, Optional

def create_app(
    title: str,
    description: str,
    version: str,
    on_startup: Optional[List[Callable]] = None,
    on_shutdown: Optional[List[Callable]] = None,
) -> FastAPI:
    """
    Crée et configure une instance de l'application FastAPI.

    Cette factory centralise la configuration de base de l'application, y compris :
    - Les métadonnées de l'API (titre, description, version).
    - Les gestionnaires d'événements de cycle de vie (startup, shutdown).
    - Le middleware CORS pour autoriser les requêtes cross-origin de manière sécurisée.

    Args:
        title (str): Le titre de l'application API.
        description (str): Une brève description de l'API.
        version (str): Le numéro de version de l'API.
        on_startup (Optional[List[Callable]]): Liste des fonctions à exécuter au démarrage.
        on_shutdown (Optional[List[Callable]]): Liste des fonctions à exécuter à l'arrêt.

    Returns:
        FastAPI: L'instance de l'application FastAPI configurée.
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )

    # Configuration CORS standardisée, basée sur la version la plus robuste disponible
    origins = [
        os.environ.get("FRONTEND_URL", "http://127.0.0.1:3001"),
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app