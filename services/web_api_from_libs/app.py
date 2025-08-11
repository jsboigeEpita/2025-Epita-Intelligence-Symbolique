#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.

Cette API expose les fonctionnalités du moteur d'analyse argumentative
pour permettre aux étudiants de créer des interfaces web facilement.
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from typing import Dict, Any, Optional
import atexit

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Import des services et dépendances
# Import des services et dépendances
from argumentation_analysis.core.llm_service import create_llm_service
from .services.analysis_service import AnalysisService
from .services.validation_service import ValidationService
from .services.fallacy_service import FallacyService
from .services.framework_service import FrameworkService
from .services.logic_service import LogicService
from argumentation_analysis.core.jvm_setup import shutdown_jvm, is_jvm_started
 
 # Import des modèles locaux
from .models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest
)
from .models.response_models import (
    AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse, ErrorResponse
)

# Import du Blueprint pour les routes
from .routes.logic_routes import logic_bp
from .routes.main_routes import main_bp

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("WebAPI")

# Chemin vers le build du frontend React
react_build_dir = root_dir / "services" / "web_api" / "interface-web-argumentative" / "build"

# --- Factory Function pour l'Application Flask ---

def create_app(config_overrides: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Crée et configure une instance de l'application Flask.
    Cette factory permet de s'assurer que les initialisations (comme les services)
    ne sont exécutées qu'au moment de la création de l'app, évitant les problèmes
    d'imports circulaires et de contexte, notamment avec pytest.
    """
    # On configure le service des fichiers statiques pour qu'il pointe vers le build de React
    app = Flask(__name__, static_folder=str(react_build_dir / "static"), static_url_path='/static')
    
    # --- Configuration ---
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    if config_overrides:
        app.config.update(config_overrides)

    # --- Initialisation des Services ---
    # Les services sont attachés à l'application via app.extensions pour un accès
    # global et sécurisé via le contexte de l'application (current_app).
    force_mock = os.environ.get('FORCE_MOCK_LLM', 'false').lower() == 'true'
    llm_service = create_llm_service(service_id="default", force_mock=force_mock)
    
    app.extensions['racine_services'] = {
        'analysis': AnalysisService(),
        'validation': ValidationService(),
        'fallacy': FallacyService(),
        'framework': FrameworkService(),
        'logic': LogicService(),
        'llm': llm_service
    }

    # --- Enregistrement des Blueprints ---
    app.register_blueprint(main_bp, url_prefix='/api')
    app.register_blueprint(logic_bp, url_prefix='/api/logic')

    # --- Gestionnaires d'Erreurs ---
    @app.errorhandler(Exception)
    def handle_error(error: Exception) -> tuple[str, int]:
        """Gestionnaire d'erreurs global."""
        logger.error(f"Erreur non gérée: {str(error)}", exc_info=True)
        error_response = ErrorResponse(
            error="Erreur interne du serveur",
            message=str(error),
            status_code=500
        )
        return jsonify(error_response.dict()), 500

    # --- Route de Fallback pour l'Application React ---
    # Doit être enregistré après les blueprints API pour ne pas les intercepter.
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path: str) -> Any:
        # Si le chemin correspond à un fichier existant dans le build React, on le sert.
        if path != "" and os.path.exists(os.path.join(str(react_build_dir), path)):
            return send_from_directory(str(react_build_dir), path)
        # Sinon, on sert l'index.html, en laissant React gérer le routage côté client.
        return send_from_directory(str(react_build_dir), 'index.html')

    return app

# --- Point d'entrée pour l'exécution directe et les serveurs WSGI ---
app = create_app()

# --- Routine de Nettoyage ---
@atexit.register
def cleanup_on_exit():
    """
    Fonction de nettoyage appelée à la sortie de l'application.
    Assure l'arrêt propre de la JVM si elle était active.
    """
    logger.info("Déclenchement du nettoyage 'atexit' de l'application.")
    if is_jvm_started():
        logger.info("La JVM est active, tentative d'arrêt propre...")
        shutdown_jvm()
        logger.info("Arrêt propre de la JVM demandé.")
    else:
        logger.info("La JVM n'était pas active, aucun arrêt nécessaire.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Démarrage de l'API Flask en mode {'Debug' if debug else 'Production'} sur le port {port}")
    
    # Utilise l'application créée par la factory
    app.run(host='0.0.0.0', port=port, debug=debug)