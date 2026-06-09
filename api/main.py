import argumentation_analysis.core.dll_guard  # noqa: F401 — must load before jpype (#1019)

import glob
import logging
import os
from pathlib import Path
from .factory import create_app
from .endpoints import router as api_router, framework_router, informal_router
from .proposal_endpoints import proposal_router
from .mobile_endpoints import mobile_router
from .shield_endpoints import shield_router
from .websocket_routes import ws_router
from .agent_routes import agent_router
from argumentation_analysis.core.bootstrap import initialize_project_environment

# JTMS endpoints — optional, graceful degradation if import fails (#857).
# The JTMS module depends on JPype/JVM; if unavailable, the API boots
# without JTMS routes rather than crashing entirely.
try:
    from argumentation_analysis.api.jtms_endpoints import (
        jtms_router,
        initialize_jtms_services,
    )

    _JTMS_AVAILABLE = True
except ImportError as exc:
    logging.getLogger(__name__).warning(
        "JTMS endpoints unavailable (import failed: %s). "
        "API will start without JTMS routes.",
        exc,
    )
    jtms_router = None  # type: ignore[assignment,misc]
    initialize_jtms_services = None  # type: ignore[assignment]
    _JTMS_AVAILABLE = False

from fastapi.responses import HTMLResponse, RedirectResponse

# --- Gestion du cycle de vie de la JVM et des services ---


async def startup_event():
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

    # Initialize JTMS services (JTMSService + JTMSSessionManager + SK plugin)
    if _JTMS_AVAILABLE and initialize_jtms_services is not None:
        try:
            await initialize_jtms_services()
            logging.info("Services JTMS initialisés (router monté sur /api/v1/jtms).")
        except Exception as exc:
            logging.warning(
                "JTMS service initialization failed: %s. "
                "JTMS endpoints will return 503.",
                exc,
            )
    else:
        logging.info("JTMS services skipped (module not available).")


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
app.include_router(shield_router, prefix="/api")
app.include_router(ws_router)
app.include_router(agent_router)
if _JTMS_AVAILABLE and jtms_router is not None:
    app.include_router(jtms_router, prefix="/api/v1")


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

_STARLETTE_DASHBOARD_URL = os.environ.get(
    "STARLETTE_DASHBOARD_URL", "http://127.0.0.1:5003/dashboard"
)


@app.get("/dashboard", tags=["Frontend"])
async def unified_dashboard():
    """Redirect to the Starlette frontend dashboard.

    The dashboard is served by the Starlette frontend proxy (:5003),
    which owns the HTML template. This eliminates cross-module coupling
    between api/ and interface_web/templates/ (issue #845).
    """
    return RedirectResponse(url=_STARLETTE_DASHBOARD_URL)
