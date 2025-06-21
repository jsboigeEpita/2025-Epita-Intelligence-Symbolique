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

    app = Flask(__name__, static_folder=app_static_folder)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Configuration de Flask
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    # Initialisation et stockage des services dans le contexte de l'application
    # pour un accès centralisé et une seule instance par service.
    app.services = AppServices()

    # Enregistrement des Blueprints pour organiser les routes
    app.register_blueprint(main_bp, url_prefix='/api')
    app.register_blueprint(logic_bp, url_prefix='/api/logic')
    logger.info("Blueprints registered.")

    # --- Gestionnaires d'erreurs et routes statiques ---

    @app.errorhandler(404)
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

    @app.errorhandler(Exception)
    def handle_global_error(error):
        """Gestionnaire d'erreurs global pour les exceptions non capturées."""
        if request.path.startswith('/api/'):
            logger.error(f"Internal API error on {request.path}: {error}", exc_info=True)
            return jsonify(ErrorResponse(
                error="Internal Server Error",
                message="An unexpected internal error occurred.",
                status_code=500
            ).dict()), 500
        logger.error(f"Unhandled server error on route {request.path}: {error}", exc_info=True)
        return serve_react_app(error)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        """Sert l'application React et gère le routage côté client."""
        build_dir = Path(app.static_folder)
        # Si le chemin correspond à un fichier existant dans le build (ex: CSS, JS), le servir
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

    @app.before_request
    def before_request():
        """
        Avant chaque requête, rend le conteneur de services accessible
        via l'objet `g` de Flask, spécifique à la requête.
        """
        g.services = app.services

    logger.info("Flask app instance created and configured.")
    return app

# --- Point d'entrée pour le développement local (non recommandé pour la production) ---
if __name__ == '__main__':
    # Initialise les dépendances lourdes avant de démarrer le serveur
    initialize_heavy_dependencies()
    # Crée l'application en utilisant la factory
    flask_app = create_app()
    port = int(os.environ.get("PORT", 5004))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    logger.info(f"Starting Flask development server on http://0.0.0.0:{port} (Debug: {debug})")
    # Utilise le serveur de développement de Flask (ne pas utiliser en production)
    flask_app.run(host='0.0.0.0', port=port, debug=debug)