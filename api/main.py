import sys
from pathlib import Path
import os
import glob
import logging
from .factory import create_app
from .endpoints import router as api_router, framework_router, informal_router
from argumentation_analysis.core.bootstrap import initialize_project_environment

# --- Configuration du PYTHONPATH ---
# Ajoute dynamiquement le répertoire 'abs_arg_dung' au PYTHONPATH.
# C'est une solution nécessaire pour assurer que les modules de ce répertoire,
# qui contiennent la logique d'analyse de l'argumentation de Dung,
# soient importables par l'API, car ils ne sont pas installés comme un paquet standard.
current_dir = Path(__file__).parent.resolve()
abs_arg_dung_path = current_dir.parent / "abs_arg_dung"
if str(abs_arg_dung_path) not in sys.path:
    sys.path.insert(0, str(abs_arg_dung_path))
# --- Fin de la configuration du PYTHONPATH ---

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
