#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.
"""
import os
import sys
import logging
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request, g
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi

# --- Configuration du Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


# --- Imports des Blueprints et des modèles de données ---
from .routes.main_routes import main_bp
from .routes.logic_routes import logic_bp
from .models.response_models import ErrorResponse
# Import des classes de service
from .services.analysis_service import AnalysisService
from .services.validation_service import ValidationService
from .services.fallacy_service import FallacyService
from .services.framework_service import FrameworkService
from .services.logic_service import LogicService
from argumentation_analysis.core.bootstrap import initialize_project_environment

class AppServices:
    """Conteneur pour les instances de service."""
    def __init__(self):
        logger.info("Initializing app services container...")
        self.analysis_service = AnalysisService()
        self.validation_service = ValidationService()
        self.fallacy_service = FallacyService()
        self.framework_service = FrameworkService()
        self.logic_service = LogicService()
        logger.info("App services container initialized.")

def initialize_heavy_dependencies():
    """
    Initialise les dépendances lourdes comme la JVM.
    Cette fonction est destinée à être appelée une seule fois au démarrage du serveur.
    """
    logger.info("Starting heavy dependencies initialization (JVM, etc.)...")
    # S'assure que la racine du projet est dans le path pour les imports
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parent.parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    try:
        initialize_project_environment(root_path_str=str(root_dir))
        logger.info("Project environment (including JVM) initialized successfully.")
    except Exception as e:
        logger.critical(f"Critical failure during project environment initialization: {e}", exc_info=True)
        # Ne pas faire de sys.exit(1) ici, l'erreur doit remonter au serveur ASGI
        raise

def create_app():
    """
    Factory function pour créer et configurer l'application Flask.
    """
    logger.info("Creating Flask app instance...")

    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parent.parent.parent
    react_build_dir = root_dir / "services" / "web_api" / "interface-web-argumentative" / "build"
    
    if not react_build_dir.exists() or not react_build_dir.is_dir():
        logger.warning(f"React build directory not found at: {react_build_dir}")
        static_folder_path = root_dir / "services" / "web_api" / "_temp_static"
        static_folder_path.mkdir(exist_ok=True)
        (static_folder_path / "placeholder.txt").touch()
        app_static_folder = str(static_folder_path)
    else:
        app_static_folder = str(react_build_dir)

    flask_app_instance = Flask(__name__, static_folder=app_static_folder)
    CORS(flask_app_instance, resources={r"/api/*": {"origins": "*"}})
    
    flask_app_instance.config['JSON_AS_ASCII'] = False
    flask_app_instance.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    # Initialisation et stockage des services dans le contexte de l'application
    flask_app_instance.services = AppServices()

    # Enregistrement des Blueprints
    flask_app_instance.register_blueprint(main_bp, url_prefix='/api')
    flask_app_instance.register_blueprint(logic_bp, url_prefix='/api/logic')
    logger.info("Blueprints registered.")

    # --- Gestionnaires d'erreurs et routes statiques ---
    @flask_app_instance.errorhandler(404)
    def handle_404_error(error):
        if request.path.startswith('/api/'):
            logger.warning(f"API endpoint not found: {request.path}")
            return jsonify(ErrorResponse(
                error="Not Found",
                message=f"The API endpoint '{request.path}' does not exist.",
                status_code=404
            ).dict()), 404
        return serve_react_app(error)

    @flask_app_instance.errorhandler(Exception)
    def handle_global_error(error):
        if request.path.startswith('/api/'):
            logger.error(f"Internal API error on {request.path}: {error}", exc_info=True)
            return jsonify(ErrorResponse(
                error="Internal Server Error",
                message="An unexpected internal error occurred.",
                status_code=500
            ).dict()), 500
        logger.error(f"Unhandled server error on route {request.path}: {error}", exc_info=True)
        return serve_react_app(error)

    @flask_app_instance.route('/', defaults={'path': ''})
    @flask_app_instance.route('/<path:path>')
    def serve_react_app(path):
        build_dir = Path(flask_app_instance.static_folder)
        if path != "" and (build_dir / path).exists():
            return send_from_directory(str(build_dir), path)
        
        index_path = build_dir / 'index.html'
        if index_path.exists():
            return send_from_directory(str(build_dir), 'index.html')
        
        logger.critical("React build or index.html missing.")
        return jsonify(ErrorResponse(
            error="Frontend Not Found",
            message="The frontend application files are missing.",
            status_code=404
        ).dict()), 404

    @flask_app_instance.before_request
    def before_request():
        """Rend les services accessibles via g."""
        g.services = flask_app_instance.services

    logger.info("Flask app instance created and configured.")
    return flask_app_instance

# --- Point d'entrée pour le développement local (non recommandé pour la production) ---
if __name__ == '__main__':
    initialize_heavy_dependencies()
    flask_app_dev = create_app()
    port = int(os.environ.get("PORT", 5004))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    logger.info(f"Starting Flask development server on http://0.0.0.0:{port} (Debug: {debug})")
    flask_app_dev.run(host='0.0.0.0', port=port, debug=debug)

# --- Point d'entrée pour Uvicorn/Gunicorn ---
# Initialise les dépendances lourdes une seule fois au démarrage
initialize_heavy_dependencies()
# Crée l'application Flask en utilisant la factory
flask_app = create_app()
# Applique le wrapper ASGI pour la compatibilité avec Uvicorn
# C'est cette variable 'app' que `launch_webapp_background.py` attend.
app = WsgiToAsgi(flask_app)