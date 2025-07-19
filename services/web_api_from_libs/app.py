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

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Import des services
from .services.analysis_service import AnalysisService
from .services.validation_service import ValidationService
from .services.fallacy_service import FallacyService
from .services.framework_service import FrameworkService
# Import pour LogicService
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest
)
# Import des modèles locaux
from .models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest
)
from .models.response_models import (
    AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse, ErrorResponse
)
# Les modèles de réponse pour la logique depuis l'autre service
from services.web_api.models.response_models import (
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse
)

# Import du Blueprint pour les routes logiques
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

# Création de l'application Flask
# On configure le service des fichiers statiques pour qu'il pointe vers le build de React
app = Flask(__name__, static_folder=str(react_build_dir / "static"), static_url_path='/static')
CORS(app)  # Activer CORS pour les appels depuis React

# Configuration
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Initialisation des services
analysis_service = AnalysisService()
validation_service = ValidationService()
fallacy_service = FallacyService()
framework_service = FrameworkService()
llm_service = create_llm_service(service_id="default")
logic_service = LogicService(llm_service)

# Enregistrer les blueprints pour les routes API
app.register_blueprint(main_bp, url_prefix='/api')
app.register_blueprint(logic_bp, url_prefix='/api/logic')

@app.errorhandler(404)
def not_found(e):
    # Pour toute route non-API, servir l'application React
    return send_from_directory(str(react_build_dir), 'index.html')

@app.errorhandler(Exception)
def handle_error(error):
    """Gestionnaire d'erreurs global."""
    logger.error(f"Erreur non gérée: {str(error)}", exc_info=True)
    return jsonify(ErrorResponse(
        error="Erreur interne du serveur",
        message=str(error),
        status_code=500
    ).dict()), 500

# Ce fichier est maintenant beaucoup plus propre.
# Les routes sont gérées par les blueprints.
if __name__ == '__main__':
    # Configuration pour le développement
    port = int(os.environ.get('PORT', 5004))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Démarrage de l'API Flask sur le port {port}")
    logger.info(f"Mode debug: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )