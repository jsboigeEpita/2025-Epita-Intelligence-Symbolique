import glob
import logging
from pathlib import Path

# Load .env for API keys before any other imports (#208-A)
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:
    pass

from .factory import create_app
from .endpoints import router as api_router, framework_router, informal_router
from .proposal_endpoints import proposal_router
from .mobile_endpoints import mobile_router
from .websocket_routes import ws_router
from .agent_routes import agent_router
from argumentation_analysis.core.bootstrap import initialize_project_environment

from fastapi.responses import HTMLResponse

# --- Gestion du cycle de vie de la JVM et des services ---


def startup_event():
    """
    Configure et exécute les routines de démarrage de l'application.

    Cette fonction est appelée une seule fois au lancement de FastAPI. Elle est
    responsable de l'initialisation de l'environnement global du projet,
    ce qui inclut le démarrage et la configuration de la JVM via JPype.
    Le contexte initialisé (contenant les classes Java, etc.) est ensuite
    stocké dans l'état de l'application (`app.state`) pour être accessible
    depuis les endpoints.
    """
    logging.info(
        "Événement de démarrage de FastAPI: initialisation de l'environnement du projet..."
    )
    project_context = initialize_project_environment()
    app.state.project_context = project_context
    logging.info(
        "Environnement du projet initialisé et attaché à l'état de l'application."
    )


# --- Application FastAPI ---

app = create_app(
    title="Argumentation Analysis API",
    description="API principale d'analyse argumentative avec intégration Java/Tweety.",
    version="2.0.0",
    on_startup=[startup_event],
)

# Inclure les routeurs
app.include_router(api_router, prefix="/api")
app.include_router(framework_router)
app.include_router(informal_router)
app.include_router(proposal_router, prefix="/api")
app.include_router(mobile_router, prefix="/api")
app.include_router(ws_router)
app.include_router(agent_router)


@app.get("/")
async def root():
    import jpype

    return {
        "message": "Welcome to the Argumentation Analysis API. JVM status: "
        + ("Running" if jpype.isJVMStarted() else "Stopped")
    }


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Vérifie l'état de santé de l'API.

    Retourne le statut de l'API et de la JVM.
    """
    import jpype

    jvm_status = "Running" if jpype.isJVMStarted() else "Stopped"
    return {"status": "healthy", "details": {"api": "Operational", "jvm": jvm_status}}


# --- Unified Dashboard ---

_DASHBOARD_TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "interface_web"
    / "templates"
    / "dashboard.html"
)


@app.get("/dashboard", response_class=HTMLResponse, tags=["Frontend"])
async def unified_dashboard():
    """Serve the unified analysis dashboard consolidating all capabilities."""
    if _DASHBOARD_TEMPLATE.exists():
        return HTMLResponse(_DASHBOARD_TEMPLATE.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>Dashboard template not found</h1>"
        f"<p>Expected at: {_DASHBOARD_TEMPLATE}</p>",
        status_code=404,
    )
