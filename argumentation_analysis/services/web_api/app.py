#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.
"""
import os
import sys
import logging
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

# --- Initialisation de l'environnement ---
# S'assure que la racine du projet est dans le path pour les imports
current_dir = Path(__file__).resolve().parent
# argumentation_analysis/services/web_api -> project_root
root_dir = current_dir.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# --- Configuration du Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# --- Bootstrap de l'application (JVM, services, etc.) ---
try:
    from argumentation_analysis.core.bootstrap import initialize_project_environment
    logger.info("Démarrage de l'initialisation de l'environnement du projet...")
    initialize_project_environment(root_path_str=str(root_dir))
    logger.info("Initialisation de l'environnement du projet terminée.")
except Exception as e:
    logger.critical(f"Échec critique lors de l'initialisation du projet: {e}", exc_info=True)
    sys.exit(1)


# --- Imports des Blueprints et des modèles de données ---
# NOTE: Ces imports doivent venir APRÈS l'initialisation du path
from .routes.main_routes import main_bp
from .routes.logic_routes import logic_bp
from .models.response_models import ErrorResponse
# Import des services pour instanciation
from .services.analysis_service import AnalysisService
from .services.validation_service import ValidationService
from .services.fallacy_service import FallacyService
from .services.framework_service import FrameworkService
from .services.logic_service import LogicService


# --- Configuration de l'application Flask ---
logger.info("Configuration de l'application Flask...")
react_build_dir = root_dir / "argumentation_analysis" / "services" / "web_api" / "interface-web-argumentative" / "build"
if not react_build_dir.exists() or not react_build_dir.is_dir():
     logger.warning(f"Le répertoire de build de React n'a pas été trouvé à l'emplacement attendu : {react_build_dir}")
     # Créer un répertoire statique factice pour éviter que Flask ne lève une erreur au démarrage.
     static_folder_path = root_dir / "services" / "web_api" / "_temp_static"
     static_folder_path.mkdir(exist_ok=True)
     (static_folder_path / "placeholder.txt").touch()
     app_static_folder = str(static_folder_path)
else:
    app_static_folder = str(react_build_dir)


# Création de l'instance de l'application Flask
app = Flask(__name__, static_folder=app_static_folder)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# --- Initialisation des services ---
logger.info("Initialisation des services...")
analysis_service = AnalysisService()
validation_service = ValidationService()
fallacy_service = FallacyService()
framework_service = FrameworkService()
logic_service = LogicService()
logger.info("Services initialisés.")

# --- Enregistrement des Blueprints ---
logger.info("Enregistrement des blueprints...")
app.register_blueprint(main_bp, url_prefix='/api')
app.register_blueprint(logic_bp, url_prefix='/api/logic')
logger.info("Blueprints enregistrés.")

# --- Gestionnaires d'erreurs spécifiques à l'API ---
@app.errorhandler(404)
def handle_404_error(error):
    """Gestionnaire d'erreurs 404. Spécifique pour l'API."""
    if request.path.startswith('/api/'):
        logger.warning(f"Endpoint API non trouvé: {request.path}")
        return jsonify(ErrorResponse(
            error="Not Found",
            message=f"L'endpoint API '{request.path}' n'existe pas.",
            status_code=404
        ).dict()), 404
    # Pour les autres routes, la route catch-all `serve_react_app` prendra le relais.
    return serve_react_app(error)

@app.errorhandler(Exception)
def handle_global_error(error):
    """Gestionnaire d'erreurs pour toutes les exceptions non capturées."""
    if request.path.startswith('/api/'):
        logger.error(f"Erreur interne de l'API sur {request.path}: {error}", exc_info=True)
        return jsonify(ErrorResponse(
            error="Internal Server Error",
            message="Une erreur interne inattendue est survenue.",
            status_code=500
        ).dict()), 500
    logger.error(f"Erreur serveur non gérée sur la route {request.path}: {error}", exc_info=True)
    # Pour les erreurs hors API, on peut soit afficher une page d'erreur standard,
    # soit rediriger vers la page d'accueil React.
    return serve_react_app(error)

# --- Route "Catch-all" pour servir l'application React ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """
    Sert les fichiers statiques de l'application React, y compris les assets,
    et sert 'index.html' pour toutes les routes non-statiques pour permettre
    le routage côté client.
    """
    build_dir = Path(app.static_folder)

    # Si le chemin correspond à un fichier statique existant (comme CSS, JS, image)
    if path != "" and (build_dir / path).exists():
        return send_from_directory(str(build_dir), path)

    # Sinon, on sert le index.html pour le routage côté client
    index_path = build_dir / 'index.html'
    if index_path.exists():
        return send_from_directory(str(build_dir), 'index.html')
    
    # Si même l'index.html est manquant, on renvoie une erreur JSON.
    logger.critical("Build React ou index.html manquant.")
    return jsonify(ErrorResponse(
        error="Frontend Not Found",
        message="Les fichiers de l'application frontend sont manquants.",
        status_code=404
    ).dict()), 404

logger.info("Configuration de l'application Flask terminée.")

# --- Factory function pour l'app Flask ---
def create_app():
    """
    Factory function pour créer l'application Flask.
    Retourne l'instance de l'application configurée.
    """
    return app

# --- Point d'entrée pour le développement local ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5004))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    logger.info(f"Démarrage du serveur de développement Flask sur http://0.0.0.0:{port} (Debug: {debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)