#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.
"""
import os
import sys

# Assurer que la racine du projet est dans le sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import logging
import traceback
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
from argumentation_analysis.services.web_api.routes.main_routes import main_bp
from argumentation_analysis.services.web_api.routes.logic_routes import logic_bp
from argumentation_analysis.services.web_api.routes.health_routes import health_bp
from argumentation_analysis.services.web_api.routes.framework_routes import framework_bp
from argumentation_analysis.services.web_api.models.response_models import ErrorResponse
# Import des classes de service
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.services.web_api.services.analysis_service import AnalysisService
from argumentation_analysis.services.web_api.services.validation_service import ValidationService
from argumentation_analysis.services.web_api.services.fallacy_service import FallacyService
from argumentation_analysis.services.web_api.services.framework_service import FrameworkService
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.config.settings import settings

class AppServices:
    """Conteneur pour les instances de service."""
    def __init__(self):
        logger.info("Initializing app services container...")
        # Création centralisée des services LLM
        # En environnement de test, la factory retournera des mocks.
        logic_llm_service = create_llm_service(service_id="logic_service", model_id="gpt-4o-mini", force_mock=True)
        analysis_llm_service = create_llm_service(service_id="analysis_service", model_id="gpt-4o-mini", force_mock=True)

        # Injection des dépendances dans les services
        self.logic_service = LogicService(llm_service=logic_llm_service)
        self.analysis_service = AnalysisService(llm_service=analysis_llm_service)
        self.validation_service = ValidationService(self.logic_service)
        self.fallacy_service = FallacyService()
        self.framework_service = FrameworkService()
        logger.info("App services container initialized.")

def initialize_heavy_dependencies():
    """
    Initialise les dépendances lourdes comme la JVM.
    Cette fonction est désactivée si le test est exécuté par un worker pytest-xdist
    pour éviter les initialisations concurrentes de la JVM.
    """
    if "PYTEST_XDIST_WORKER" in os.environ:
        logger.warning("Skipping heavy dependencies initialization for xdist worker.")
        return
        
    logger.info("Starting heavy dependencies initialization (JVM, etc.)...")
    # S'assure que la racine du projet est dans le path pour les imports
    current_dir = Path(__file__).resolve().parent
    # Remonter de 3 niveaux: web_api -> services -> argumentation_analysis -> project_root
    root_dir = current_dir.parent.parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    try:
        # Initialiser l'environnement du projet (ce qui peut inclure le démarrage de la JVM)
        initialize_project_environment(root_path_str=str(root_dir))
        logger.info("Project environment (including JVM) initialized successfully.")
    except Exception as e:
        logger.critical(f"Critical failure during project environment initialization: {e}", exc_info=True)
        # L'erreur doit remonter pour empêcher le serveur de démarrer dans un état instable
        raise

def create_app():
    """
    Factory function pour créer et configurer l'application Flask.
    """
    logger.info("Creating Flask app instance...")

    # --- Initialisation des dépendances lourdes ---
    # L'initialisation est maintenant gérée par le point d'entrée du serveur
    # (ex: conftest.py pour les tests, ou le script de démarrage principal)
    # pour éviter les initialisations multiples.
    # initialize_heavy_dependencies() # Appel supprimé

    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parent.parent.parent
    react_build_dir = root_dir / "services" / "web_api" / "interface-web-argumentative" / "build"
    
    # Gestion du dossier statique pour le build React
    if not react_build_dir.exists() or not react_build_dir.is_dir():
        logger.warning(f"React build directory not found at: {react_build_dir}")
        # Créer un dossier statique temporaire pour éviter une erreur Flask
        static_folder_path = root_dir / "services" / "web_api" / "_temp_static"
        static_folder_path.mkdir(exist_ok=True)
        (static_folder_path / "placeholder.txt").touch()
        app_static_folder = str(static_folder_path)
    else:
        app_static_folder = str(react_build_dir)

    flask_app_instance = Flask(__name__, static_folder=app_static_folder)
    # Configuration CORS plus flexible pour le développement et les tests E2E
    # autorisant localhost et 127.0.0.1 sur n'importe quel port.
    CORS(flask_app_instance,
         resources={r"/api/*": {"origins": "*"}},  # Autorise toutes les origines pour les routes API
         supports_credentials=True)
    
    flask_app_instance.config['JSON_AS_ASCII'] = False
    flask_app_instance.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    # Initialisation et stockage des services
    services_container = AppServices()
    flask_app_instance.services = services_container

    # Attacher les services individuels à l'instance de l'application
    # pour les rendre accessibles via `current_app` dans les blueprints.
    flask_app_instance.logic_service = services_container.logic_service
    flask_app_instance.analysis_service = services_container.analysis_service
    flask_app_instance.validation_service = services_container.validation_service
    flask_app_instance.fallacy_service = services_container.fallacy_service
    flask_app_instance.framework_service = services_container.framework_service

    # Enregistrement des Blueprints
    flask_app_instance.register_blueprint(health_bp, url_prefix='/api')
    flask_app_instance.register_blueprint(main_bp, url_prefix='/api')
    flask_app_instance.register_blueprint(logic_bp, url_prefix='/api/logic')
    flask_app_instance.register_blueprint(framework_bp, url_prefix='/api/v1')
    logger.info("Blueprints registered.")

    # --- Gestionnaires d'erreurs et routes statiques ---
    @flask_app_instance.errorhandler(404)
    def handle_404_error(error):
        """Gestionnaire d'erreurs 404 intelligent."""
        if request.path.startswith('/api/'):
            logger.warning(f"API endpoint not found: {request.path}")
            return jsonify(ErrorResponse(
                error="Not Found",
                message=f"The API endpoint '{request.path}' does not exist.",
                status_code=404
            ).dict()), 404
        # Pour toute autre route, on sert l'app React (Single Page Application)
        return serve_react_app(error)

    @flask_app_instance.errorhandler(Exception)
    def handle_global_error(error):
        """
        Gestionnaire d'erreurs global pour les exceptions non capturées.
        En mode débogage/test, il renvoie des détails sur l'erreur.
        """
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        
        if request.path.startswith('/api/'):
            logger.error(f"Internal API error on {request.path}: {error}\n{tb_str}")
            
            # Renvoyer des détails d'erreur plus explicites pour le débogage E2E
            error_details = {
                "error": "Internal Server Error",
                "message": str(error),
                "traceback": tb_str,
                "status_code": 500
            }
            return jsonify(error_details), 500
            
        logger.error(f"Unhandled server error on route {request.path}: {error}\n{tb_str}")
        return serve_react_app(error)

    @flask_app_instance.route('/', defaults={'path': ''})
    @flask_app_instance.route('/<path:path>')
    def serve_react_app(path):
        build_dir = Path(flask_app_instance.static_folder)
        if path != "" and (build_dir / path).exists():
            return send_from_directory(str(build_dir), path)
        
        # Sinon, servir index.html pour que React puisse gérer la route
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
    # Initialise les dépendances lourdes avant de démarrer le serveur
    initialize_heavy_dependencies()
    flask_app_dev = create_app()
    port = int(os.environ.get("PORT", 5004))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    logger.info(f"Starting Flask development server on http://0.0.0.0:{port} (Debug: {debug})")
    flask_app_dev.run(host='0.0.0.0', port=port, debug=debug)

# --- Point d'entrée pour Uvicorn/Gunicorn ---
# Initialise les dépendances lourdes une seule fois au démarrage,
# sauf si on est en train de lancer les tests, car pytest gérera la JVM.
# L'initialisation est maintenant dans create_app, donc cette section est supprimée.

# Crée l'application Flask en utilisant la factory
# Crée l'application Flask en utilisant la factory
flask_app = create_app()
# Applique le wrapper ASGI pour la compatibilité avec Uvicorn
# C'est cette variable 'app' que `launch_webapp_background.py` attend.
app = WsgiToAsgi(flask_app)
