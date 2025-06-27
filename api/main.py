import sys
from pathlib import Path
import os
import glob
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import router as api_router, framework_router
from argumentation_analysis.core.bootstrap import initialize_project_environment

# --- Ajout dynamique de abs_arg_dung au PYTHONPATH ---
# Cela garantit que le service d'analyse peut importer l'agent de l'étudiant.
current_dir = Path(__file__).parent.resolve()
abs_arg_dung_path = current_dir.parent / 'abs_arg_dung'
if str(abs_arg_dung_path) not in sys.path:
    # On l'insère au début pour prioriser ce chemin si nécessaire
    sys.path.insert(0, str(abs_arg_dung_path))
# --- Fin de l'ajout ---

# --- Gestion du cycle de vie de la JVM et des services ---

def startup_event():
    """
    Événement de démarrage de FastAPI.
    Initialise l'environnement complet du projet (JVM, services, etc.)
    et l'attache à l'état de l'application.
    """
    logging.info("Événement de démarrage de FastAPI: initialisation de l'environnement du projet...")
    project_context = initialize_project_environment()
    app.state.project_context = project_context
    logging.info("Environnement du projet initialisé et attaché à l'état de l'application.")

# --- Application FastAPI ---

app = FastAPI(
    title="Argumentation Analysis API",
    on_startup=[startup_event]
    # on_shutdown n'est plus nécessaire car la JVM est gérée par le processus principal
)


# --- Configuration CORS ---
# Le frontend est servi sur le port 3001 (ou une autre URL en production),
# le backend sur 5003. Le navigateur bloque les requêtes cross-origin
# par défaut. On autorise explicitement l'origine du frontend.
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


# Inclure les routeurs
app.include_router(api_router, prefix="/api")
app.include_router(framework_router)

@app.get("/")
async def root():
    import jpype
    return {"message": "Welcome to the Argumentation Analysis API. JVM status: " + ("Running" if jpype.isJVMStarted() else "Stopped")}