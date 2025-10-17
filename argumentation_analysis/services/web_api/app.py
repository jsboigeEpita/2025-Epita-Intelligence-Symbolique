#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.
"""
import os
import sys

# Assurer que la racine du projet est dans le sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

import logging
import traceback
from pathlib import Path

from flask import Flask, send_from_directory, jsonify, request, g
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi

# --- Configuration du Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Imports des Blueprints et des modèles de données ---
from argumentation_analysis.services.web_api.routes.main_routes import main_bp
from argumentation_analysis.services.web_api.routes.logic_routes import logic_bp
from argumentation_analysis.services.web_api.routes.health_routes import health_bp
from argumentation_analysis.services.web_api.routes.framework_routes import framework_bp
from argumentation_analysis.services.web_api.models.response_models import ErrorResponse

# ATTENTION: Les imports de services et de bootstrap sont déplacés dans les hooks
# pour éviter de charger des bibliothèques natives (ex: PyTorch) avant la JVM.
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.config.settings import settings


# La définition de la classe AppServices est déplacée dans le hook pour la même raison.


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
    react_build_dir = (
        root_dir / "services" / "web_api" / "interface-web-argumentative" / "build"
    )

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
    CORS(
        flask_app_instance,
        resources={
            r"/api/*": {"origins": "*"}
        },  # Autorise toutes les origines pour les routes API
        supports_credentials=True,
    )

    flask_app_instance.config["JSON_AS_ASCII"] = False
    flask_app_instance.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

    # L'initialisation des services est maintenant différée et gérée par le hook before_first_request.
    flask_app_instance.services_initialized = False
    flask_app_instance.project_context = None
    flask_app_instance.services = None

    # Enregistrement des Blueprints
    flask_app_instance.register_blueprint(health_bp, url_prefix="/api")
    flask_app_instance.register_blueprint(main_bp, url_prefix="/api")
    flask_app_instance.register_blueprint(logic_bp, url_prefix="/api/logic")
    flask_app_instance.register_blueprint(framework_bp, url_prefix="/api/v1")
    logger.info("Blueprints registered.")

    # --- Gestionnaires d'erreurs et routes statiques ---
    @flask_app_instance.errorhandler(404)
    def handle_404_error(error):
        """Gestionnaire d'erreurs 404 intelligent."""
        if request.path.startswith("/api/"):
            logger.warning(f"API endpoint not found: {request.path}")
            return (
                jsonify(
                    ErrorResponse(
                        error="Not Found",
                        message=f"The API endpoint '{request.path}' does not exist.",
                        status_code=404,
                    ).dict()
                ),
                404,
            )
        # Pour toute autre route, on sert l'app React (Single Page Application)
        return serve_react_app(error)

    @flask_app_instance.errorhandler(Exception)
    def handle_global_error(error):
        """
        Gestionnaire d'erreurs global pour les exceptions non capturées.
        En mode débogage/test, il renvoie des détails sur l'erreur.
        """
        tb_str = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        if request.path.startswith("/api/"):
            logger.error(f"Internal API error on {request.path}: {error}\n{tb_str}")

            # Renvoyer des détails d'erreur plus explicites pour le débogage E2E
            error_details = {
                "error": "Internal Server Error",
                "message": str(error),
                "traceback": tb_str,
                "status_code": 500,
            }
            return jsonify(error_details), 500

        logger.error(
            f"Unhandled server error on route {request.path}: {error}\n{tb_str}"
        )
        return serve_react_app(error)

    @flask_app_instance.route("/", defaults={"path": ""})
    @flask_app_instance.route("/<path:path>")
    def serve_react_app(path):
        build_dir = Path(flask_app_instance.static_folder)
        if path != "" and (build_dir / path).exists():
            return send_from_directory(str(build_dir), path)

        # Sinon, servir index.html pour que React puisse gérer la route
        index_path = build_dir / "index.html"
        if index_path.exists():
            return send_from_directory(str(build_dir), "index.html")

        logger.critical("React build or index.html missing.")
        return (
            jsonify(
                ErrorResponse(
                    error="Frontend Not Found",
                    message="The frontend application files are missing.",
                    status_code=404,
                ).dict()
            ),
            404,
        )

    @flask_app_instance.before_request
    def before_request_hook():
        """
        Gère l'initialisation des services à la première requête et les attache
        au contexte global de la requête (`g`).
        L'endpoint de health check est explicitement exclu pour garantir une réponse
        rapide sans dépendances lourdes.
        """
        if request.path == "/api/health":
            logger.debug(
                f"Skipping heavy initialization for health check endpoint: {request.path}"
            )
            return

        # Utilise un drapeau sur l'objet `g` pour éviter de refaire l'initialisation
        # plusieurs fois pendant la même requête, bien que `before_first_request`
        # soit la principale protection.
        if not getattr(g, "services_initialized", False):
            if not flask_app_instance.services_initialized:
                logger.info("[DEADLOCK_DEBUG] Entrée dans le hook 'before_request'.")
                try:
                    logger.info(
                        "[DEADLOCK_DEBUG] ÉTAPE 1: Appel de initialize_project_environment..."
                    )
                    project_context = initialize_project_environment()
                    logger.info(
                        "[DEADLOCK_DEBUG] ÉTAPE 1: ... initialize_project_environment TERMINÉ."
                    )
                    flask_app_instance.project_context = project_context

                    logger.info(
                        "[DEADLOCK_DEBUG] ÉTAPE 2: Imports locaux des services..."
                    )
                    from argumentation_analysis.core.llm_service import (
                        create_llm_service,
                    )
                    from argumentation_analysis.services.web_api.services.analysis_service import (
                        AnalysisService,
                    )
                    from argumentation_analysis.services.web_api.services.validation_service import (
                        ValidationService,
                    )
                    from argumentation_analysis.services.web_api.services.fallacy_service import (
                        FallacyService,
                    )
                    from argumentation_analysis.services.web_api.services.framework_service import (
                        FrameworkService,
                    )
                    from argumentation_analysis.services.web_api.services.logic_service import (
                        LogicService,
                    )

                    logger.info(
                        "[DEADLOCK_DEBUG] ÉTAPE 2: ... Imports locaux TERMINÉS."
                    )

                    class AppServices:
                        """Conteneur pour les instances de service, initialisé paresseusement."""

                        def __init__(self, proj_context):
                            logger.info(
                                "[DEADLOCK_DEBUG] Initializing AppServices container..."
                            )
                            self.project_context = proj_context
                            is_integration_test = (
                                os.environ.get("INTEGRATION_TEST_MODE") == "true"
                            )

                            logger.info(
                                "[DEADLOCK_DEBUG] Création du logic_llm_service..."
                            )
                            logic_llm = create_llm_service(
                                service_id="logic_service",
                                model_id="gpt-5-mini",
                                force_mock=is_integration_test,
                            )
                            logger.info("[DEADLOCK_DEBUG] ... logic_llm_service créé.")

                            logger.info(
                                "[DEADLOCK_DEBUG] Création du analysis_llm_service..."
                            )
                            analysis_llm = create_llm_service(
                                service_id="analysis_service",
                                model_id="gpt-5-mini",
                                force_mock=is_integration_test,
                            )
                            logger.info(
                                "[DEADLOCK_DEBUG] ... analysis_llm_service créé."
                            )

                            self.logic_service = LogicService(llm_service=logic_llm)
                            self.analysis_service = AnalysisService(
                                llm_service=analysis_llm
                            )
                            self.validation_service = ValidationService(
                                self.logic_service
                            )
                            self.fallacy_service = FallacyService()
                            self.framework_service = FrameworkService()
                            logger.info(
                                "[DEADLOCK_DEBUG] AppServices container initialized."
                            )

                    logger.info(
                        "[DEADLOCK_DEBUG] ÉTAPE 3: Instanciation de AppServices..."
                    )
                    services_container = AppServices(project_context)
                    logger.info("[DEADLOCK_DEBUG] ÉTAPE 3: ... AppServices instancié.")
                    flask_app_instance.services = services_container

                    flask_app_instance.services_initialized = True
                    logger.info(
                        "[DEADLOCK_DEBUG] Hook 'before_request': Initialisation terminée avec succès."
                    )
                except Exception as e:
                    logger.critical(
                        f"Échec critique de l'initialisation des services: {e}",
                        exc_info=True,
                    )
                    return (
                        jsonify(
                            {
                                "error": "Service Unavailable",
                                "message": "Critical components failed to initialize.",
                            }
                        ),
                        503,
                    )

            # Attache les services initialisés au contexte de la requête `g`
            g.services = flask_app_instance.services
            g.services_initialized = True

    logger.info("Flask app instance created and configured.")
    return flask_app_instance


# --- Point d'entrée pour Uvicorn/Gunicorn ---
# Crée l'application Flask en utilisant la factory.
# L'initialisation des services est maintenant gérée "lazily" par le hook `before_request`
# à l'intérieur de `create_app`.
flask_app = create_app()

# Applique le wrapper ASGI pour la compatibilité avec Uvicorn.
# C'est cette variable 'app' que les scripts de lancement comme `launch_webapp_background.py` attendent.
app = WsgiToAsgi(flask_app)


# --- Point d'entrée pour le développement local (non recommandé pour la production) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5004))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    logger.info(
        f"Starting Flask development server on http://0.0.0.0:{port} (Debug: {debug})"
    )
    # L'application `flask_app` est déjà créée ci-dessus.
    # Le hook `before_request` gérera l'initialisation à la première requête.
    flask_app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
