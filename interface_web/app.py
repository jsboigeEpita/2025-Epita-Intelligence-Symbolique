#!/usr/bin/env python3
"""
Interface Web pour l'Analyse Argumentative EPITA (Version Starlette — Frontend Proxy)
=====================================================================================

Application Starlette servant de **frontend-only proxy** vers le backend FastAPI.
- Sert l'application React (build static) sur `/`
- Proxy les requetes `/api/*` et `/ws/*` vers le backend FastAPI
- Ne contient aucune logique metier (ServiceManager, NLP, JVM)

Architecture (issue #844):
  Navigateur -> Starlette(:5003) -> React SPA (static)
                                -> /api/* -> FastAPI(:8095)
                                -> /ws/*  -> FastAPI(:8095)

Version: 3.0.0
Date: 2026-06-01
"""

import logging
import os
import argparse
from pathlib import Path

# --- Imports ASGI/Starlette ---
from contextlib import asynccontextmanager

import httpx
from starlette.applications import Starlette
from starlette.responses import (
    JSONResponse,
    HTMLResponse,
    StreamingResponse,
    Response,
)
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

# --- Configuration du Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [StarletteProxy] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Configuration des chemins ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_FILES_DIR = (
    PROJECT_ROOT / "services" / "web_api" / "interface-web-argumentative" / "build"
)

# --- Configuration du proxy FastAPI ---
FASTAPI_HOST = os.environ.get("FASTAPI_HOST", "127.0.0.1")
FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", "8095"))
FASTAPI_BASE_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}"


# ==============================================================================
# CYCLE DE VIE DE L'APPLICATION (LIFESPAN)
# ==============================================================================


@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Gestionnaire de cycle de vie. Cree le client HTTP pour le proxy FastAPI.
    Pas de ServiceManager, pas de NLP, pas de JVM — juste un proxy.
    """
    logger.info(f"LIFESPAN: Demarrage du frontend proxy -> {FASTAPI_BASE_URL}")

    # Creer un client HTTP persistant pour le proxy
    app.state.http_client = httpx.AsyncClient(
        base_url=FASTAPI_BASE_URL,
        timeout=httpx.Timeout(30.0, connect=5.0),
    )

    logger.info("LIFESPAN: Proxy pret.")

    yield  # L'application s'execute ici

    logger.info("LIFESPAN: Fermeture du client proxy...")
    await app.state.http_client.aclose()
    logger.info("LIFESPAN: Nettoyage termine.")


# ==============================================================================
# PROXY VERS FASTAPI
# ==============================================================================


async def api_proxy(request: Request):
    """
    Proxy generique pour les requetes /api/* vers FastAPI.
    Transfere methode, headers, body, et retourne la reponse intacte.
    """
    client: httpx.AsyncClient = request.app.state.http_client

    # Construire le chemin cible (enlever le prefixe si necessaire)
    path = request.url.path
    query_string = str(request.url.query)

    # Determiner les headers a transferer (exclure host)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Lire le body
    body = await request.body()

    try:
        # Transfere la requete vers FastAPI
        response = await client.request(
            method=request.method,
            url=path,
            params=dict(request.query_params) if query_string else None,
            headers=headers,
            content=body,
        )

        # Construire la reponse
        # Exclure les headers de transfert encoding qui causent des problemes
        response_headers = dict(response.headers)
        for hop_header in ("transfer-encoding", "content-encoding", "connection"):
            response_headers.pop(hop_header, None)

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response_headers.get("content-type"),
        )

    except httpx.ConnectError:
        logger.error(f"Proxy: FastAPI indisponible ({FASTAPI_BASE_URL}{path})")
        return JSONResponse(
            {
                "error": "Backend API indisponible",
                "detail": f"Impossible de joindre {FASTAPI_BASE_URL}",
            },
            status_code=502,
        )
    except httpx.TimeoutException:
        logger.error(f"Proxy: timeout vers FastAPI ({path})")
        return JSONResponse(
            {"error": "Backend API timeout"},
            status_code=504,
        )


async def ws_proxy(websocket: WebSocket):
    """
    Proxy WebSocket vers FastAPI.
    Etablit la connexion avec le client, puis relay bidirectionnel avec FastAPI.
    """
    await websocket.accept()

    # Extraire le path et construire l'URL WebSocket FastAPI
    path = websocket.url.path
    ws_target_url = f"ws://{FASTAPI_HOST}:{FASTAPI_PORT}{path}"

    logger.info(f"WS Proxy: {path} -> {ws_target_url}")

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", ws_target_url) as backend_ws:
                # Relay bidirectionnel
                async def relay_to_backend():
                    try:
                        while True:
                            data = await websocket.receive_text()
                            # Forward to backend
                    except WebSocketDisconnect:
                        logger.info(f"WS Proxy: client deconnecte ({path})")

                # Pour l'instant, les WebSocket FastAPI sont accessibles directement.
                # Ce proxy est un placeholder pour une future implementation complete.
                await websocket.send_json(
                    {
                        "type": "proxy_info",
                        "message": f"Connect FastAPI WebSocket directly at {ws_target_url}",
                    }
                )
                await websocket.close()

    except Exception as e:
        logger.error(f"WS Proxy error ({path}): {e}")
        await websocket.close(code=1011, reason=str(e))


# ==============================================================================
# ROUTES LOCALES (non-proxy)
# ==============================================================================


async def examples_endpoint(request: Request):
    """Route pour obtenir des exemples de textes d'analyse (hardcoded)."""
    examples = [
        {
            "title": "Logique Propositionnelle",
            "text": "Si il pleut, alors la route est mouillee. Il pleut. Donc la route est mouillee.",
            "type": "propositional",
        },
        {
            "title": "Argumentation Complexe",
            "text": "L'IA est une opportunite et un defi. Elle peut revolutionner la medecine, mais pose des questions ethiques.",
            "type": "unified_analysis",
        },
    ]
    return JSONResponse({"examples": examples})


async def dashboard_endpoint(request: Request):
    """Serve the unified analysis dashboard."""
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    if template_path.exists():
        return HTMLResponse(template_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=404)


# ==============================================================================
# CONFIGURATION DE L'APPLICATION STARLETTE
# ==============================================================================

# --- Definition des Routes ---
# Toutes les routes /api/* sont proxyees vers FastAPI.
# Seuls les fichiers statiques (React SPA) et les routes locales restent.
routes = [
    # Dashboard (local — peut aussi etre servi par FastAPI)
    Route("/dashboard", endpoint=dashboard_endpoint, methods=["GET"]),
    # Exemples hardcoded (local)
    Route("/api/examples", endpoint=examples_endpoint, methods=["GET"]),
    # Proxy pour toutes les requetes /api/* vers FastAPI
    Route("/api/{path:path}", endpoint=api_proxy, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
    # Le Mount pour les fichiers statiques doit gerer le service de l'application React,
    # y compris la route index.html pour le chemin racine.
    Mount(
        "/",
        app=StaticFiles(directory=str(STATIC_FILES_DIR), html=True),
        name="static_assets",
    ),
]

# --- Middlewares ---
# Configuration de CORS pour autoriser les requetes cross-origin
middleware = [
    Middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
]

# --- Creation de l'Application ---
app = Starlette(debug=True, routes=routes, middleware=middleware, lifespan=lifespan)

# ==============================================================================
# POINT D'ENTREE POUR LE DEMARRAGE DIRECT
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Lance le serveur web Starlette (frontend proxy).")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 5003)),
        help="Port pour executer le serveur.",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Hote sur lequel ecouter."
    )
    parser.add_argument(
        "--fastapi-port",
        type=int,
        default=FASTAPI_PORT,
        help="Port du backend FastAPI.",
    )
    args = parser.parse_args()

    if args.fastapi_port:
        FASTAPI_PORT = args.fastapi_port

    logger.info(f"Demarrage du frontend proxy sur http://{args.host}:{args.port}")
    logger.info(f"  -> Backend FastAPI: {FASTAPI_BASE_URL}")

    uvicorn.run(
        "interface_web.app:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=True,
    )
