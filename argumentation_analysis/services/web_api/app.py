#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.

Cette API expose les fonctionnalités du moteur d'analyse argumentative
pour permettre aux étudiants de créer des interfaces web facilement.
"""
import logging
import sys
import os # Assurez-vous qu'os est importé si ce n'est pas déjà le cas plus haut
from pathlib import Path # Assurez-vous que Path est importé
from typing import Optional, Dict, Any # AJOUTÉ ICI POUR CORRIGER NameError

# --- Initialisation explicite de l'environnement du projet ---
# Cela doit être fait AVANT toute autre logique d'application ou import de service spécifique au projet.
try:
    # Déterminer la racine du projet pour bootstrap.py
    # argumentation_analysis/services/web_api/app.py -> services/web_api -> services -> argumentation_analysis -> project_root
    _app_file_path = Path(__file__).resolve()
    _project_root_for_bootstrap = _app_file_path.parent.parent.parent.parent
    
    # S'assurer que argumentation_analysis.core est accessible
    # Normalement, si PROJECT_ROOT (d:/2025-Epita-Intelligence-Symbolique-4) est dans PYTHONPATH,
    # argumentation_analysis.core.bootstrap devrait être importable.
    # Si bootstrap.py gère lui-même l'ajout de la racine du projet à sys.path,
    # cet ajout ici pourrait être redondant mais ne devrait pas nuire s'il est idempotent.
    if str(_project_root_for_bootstrap) not in sys.path:
         sys.path.insert(0, str(_project_root_for_bootstrap))

    from argumentation_analysis.core.bootstrap import initialize_project_environment, ProjectContext
    
    # Utiliser le .env à la racine du projet global (d:/2025-Epita-Intelligence-Symbolique-4/.env)
    # et la racine du projet global comme root_path_str.
    _env_file_path_for_bootstrap = _project_root_for_bootstrap / ".env"

    print(f"[BOOTSTRAP CALL from app.py] Initializing project environment with root: {_project_root_for_bootstrap}, env_file: {_env_file_path_for_bootstrap}")
    sys.stdout.flush() # For Uvicorn logs

    project_context: Optional[ProjectContext] = initialize_project_environment(
        env_path_str=str(_env_file_path_for_bootstrap) if _env_file_path_for_bootstrap.exists() else None,
        root_path_str=str(_project_root_for_bootstrap)
    )
    if project_context:
        print(f"[BOOTSTRAP CALL from app.py] Project environment initialized. JVM: {project_context.jvm_initialized}, LLM: {'OK' if project_context.llm_service else 'FAIL'}")
        sys.stdout.flush()
    else:
        print("[BOOTSTRAP CALL from app.py] FAILED to initialize project environment.")
        sys.stdout.flush()
        # Gérer l'échec de l'initialisation si nécessaire, par exemple en levant une exception
        # raise RuntimeError("Échec critique de l'initialisation de l'environnement du projet via bootstrap.")
except ImportError as e_bootstrap_import:
    print(f"[BOOTSTRAP CALL from app.py] CRITICAL ERROR: Failed to import bootstrap components: {e_bootstrap_import}", file=sys.stderr)
    sys.stderr.flush()
    raise
except Exception as e_bootstrap_init:
    print(f"[BOOTSTRAP CALL from app.py] CRITICAL ERROR: Failed during bootstrap initialization: {e_bootstrap_init}", file=sys.stderr)
    sys.stderr.flush()
    raise
# --- Fin de l'initialisation explicite de l'environnement ---


# Configure logging immediately at the very top of the module execution.
# This ensures that any subsequent logging calls, even before full app setup, are captured.
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(name)s [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                    force=True) # force=True allows reconfiguring if it was called before (e.g. by a dependency)
_top_module_logger = logging.getLogger(__name__) # Use __name__ to get 'argumentation_analysis.services.web_api.app'
_top_module_logger.info("--- web_api/app.py module execution START, initial logging configured ---")
sys.stderr.flush() # Ensure this initial log gets out.

logger = _top_module_logger # Make it available globally as 'logger' for existing code

import os
# logging est déjà importé et configuré par basicConfig à la ligne 15
# _top_module_logger est déjà défini à la ligne 18
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI


# Déclarer les variables avant le bloc try pour qu'elles aient un scope global dans le module
flask_app = None # Sera assigné à flask_app_instance_for_init
app = None # Sera assigné à app_object_for_uvicorn

try:
    _top_module_logger.info("--- Initializing Flask app instance ---")
    sys.stderr.flush()
    flask_app_instance_for_init = Flask(__name__) # Variable locale temporaire
    _top_module_logger.info(f"--- Flask app instance CREATED: {type(flask_app_instance_for_init)} ---")
    sys.stderr.flush()

    _top_module_logger.info("--- Applying CORS to Flask app ---")
    sys.stderr.flush()
    CORS(flask_app_instance_for_init)
    _top_module_logger.info("--- CORS applied ---")
    sys.stderr.flush()

    _top_module_logger.info("--- Mounting Flask app within a FastAPI instance ---")
    sys.stderr.flush()

    # Créer une instance de FastAPI comme application principale
    fastapi_app = FastAPI()

    # Monter l'application Flask (WSGI) sur un sous-chemin pour éviter les conflits de routes.
    fastapi_app.mount("/flask", WSGIMiddleware(flask_app_instance_for_init))

    _top_module_logger.info(f"--- Flask app mounted on FastAPI at /flask. Main app type: {type(fastapi_app)} ---")
    sys.stderr.flush()

    # Assigner aux variables globales du module si tout a réussi
    flask_app = flask_app_instance_for_init
    app = fastapi_app

except Exception as e_init:
    _top_module_logger.critical(f"!!! CRITICAL ERROR during Flask/WSGIMiddleware initialization: {e_init} !!!", exc_info=True)
    # Dans un scénario de production, un `raise` ici serait approprié pour arrêter le chargement du module.
    # raise e_init


# Ajout du endpoint de health check pour l'orchestrateur
if app: # S'assurer que 'app' (fastapi_app) a été initialisé
    @app.get("/api/health")
    def health_check():
        """
        Simple health check endpoint for the orchestrator.
        """
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    @app.get("/api/endpoints")
    def get_all_endpoints():
        """
        Renvoie la liste des endpoints disponibles.
        NOTE: Pour l'instant, c'est une implémentation de base pour satisfaire l'orchestrateur.
        """
        # TODO: Rendre cette liste dynamique en inspectant à la fois FastAPI et Flask.
        return {
            "fastapi_endpoints": [{"path": route.path, "name": route.name} for route in app.routes if hasattr(route, 'path')],
            "flask_endpoints_expected": [
                "/flask/api/health", "/flask/api/analyze", "/flask/api/load_text",
                "/flask/api/get_arguments", "/flask/api/get_graph", "/flask/api/download_results",
                "/flask/api/status", "/flask/api/config", "/flask/api/feedback"
            ]
        }

# Importer les routes Flask pour les enregistrer auprès de l'application flask_app
    from . import flask_routes
    _top_module_logger.info("Flask routes module imported.")
    
    # Enregistrer explicitement le blueprint (si flask_routes utilise un Blueprint)
    # Assurez-vous que flask_routes.bp existe ou adaptez à votre structure.
    # Exemple: app.register_blueprint(flask_routes.bp, url_prefix='/api')
    
    _top_module_logger.info("Flask routes registered.")
# Vérification de sécurité: si l'initialisation a échoué, app et flask_app seront None.
# Le serveur Uvicorn échouera au démarrage car il ne trouvera pas de callable 'app'.
if flask_app is None or app is None:
    _top_module_logger.critical("!!! FATAL: App objects (flask_app, app) are None after initialization. Uvicorn will fail. !!!")
    # Pour s'assurer que le processus s'arrête si le log seul ne suffit pas.
    # Dans un contexte de chargement de module, il est préférable que l'exception se propage.
    # sys.exit(1)

_top_module_logger.info(f"--- web_api/app.py module execution END.. App object to be served by Uvicorn: {type(app)} ---")
sys.stderr.flush()