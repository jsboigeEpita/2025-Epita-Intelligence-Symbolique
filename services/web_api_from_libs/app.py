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
from flask import Flask, request, jsonify
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
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest
)
# Les modèles de réponse pour la logique sont dans un chemin différent, comme corrigé précédemment
from services.web_api.models.response_models import (
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse
)

from libs.web_api.models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest
)
from libs.web_api.models.response_models import (
    AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse, ErrorResponse
)

# Import du Blueprint pour les routes logiques
from libs.web_api.routes.logic_routes import logic_bp # initialize_logic_blueprint n'est plus nécessaire

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("WebAPI")

# Création de l'application Flask
app = Flask(__name__)
CORS(app)  # Activer CORS pour les appels depuis React

# Configuration
app.config['JSON_AS_ASCII'] = False  # Support des caractères UTF-8
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Initialisation des services
analysis_service = AnalysisService()
validation_service = ValidationService()
fallacy_service = FallacyService()
framework_service = FrameworkService()
logic_service = LogicService()

# Initialiser et enregistrer les blueprints
# initialize_logic_blueprint(logic_service) # N'est plus nécessaire
app.register_blueprint(logic_bp)


@app.errorhandler(Exception)
def handle_error(error):
    """Gestionnaire d'erreurs global."""
    logger.error(f"Erreur non gérée: {str(error)}", exc_info=True)
    return jsonify(ErrorResponse(
        error="Erreur interne du serveur",
        message=str(error),
        status_code=500
    ).dict()), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérification de l'état de l'API."""
    try:
        return jsonify({
            "status": "healthy",
            "message": "API d'analyse argumentative opérationnelle",
            "version": "1.0.0",
            "services": {
                "analysis": analysis_service.is_healthy(),
                "validation": validation_service.is_healthy(),
                "fallacy": fallacy_service.is_healthy(),
                "framework": framework_service.is_healthy(),
                "logic": logic_service.is_healthy() # Ajout du health check pour LogicService
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de health check",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/analyze', methods=['POST'])
async def analyze_text():
    """
    Analyse complète d'un texte argumentatif.
    
    Body JSON:
    {
        "text": "Texte à analyser",
        "options": {
            "detect_fallacies": true,
            "analyze_structure": true,
            "evaluate_coherence": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            analysis_request = AnalysisRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Analyse du texte
        result = await analysis_service.analyze_text(analysis_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur d'analyse",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/validate', methods=['POST'])
def validate_argument():
    """
    Validation logique d'un argument.
    
    Body JSON:
    {
        "premises": ["Prémisse 1", "Prémisse 2"],
        "conclusion": "Conclusion",
        "argument_type": "deductive"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            validation_request = ValidationRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Validation de l'argument
        result = validation_service.validate_argument(validation_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de validation",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/fallacies', methods=['POST'])
def detect_fallacies():
    """
    Détection de sophismes dans un texte.
    
    Body JSON:
    {
        "text": "Texte à analyser",
        "options": {
            "severity_threshold": 0.5,
            "include_context": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            fallacy_request = FallacyRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Détection des sophismes
        result = fallacy_service.detect_fallacies(fallacy_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de sophismes: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de détection",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/framework', methods=['POST'])
def build_framework():
    """
    Construction d'un framework de Dung.
    
    Body JSON:
    {
        "arguments": [
            {
                "id": "arg1",
                "content": "Contenu de l'argument",
                "attacks": ["arg2"]
            }
        ],
        "options": {
            "compute_extensions": true,
            "semantics": "preferred"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            framework_request = FrameworkRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Construction du framework
        result = framework_service.build_framework(framework_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la construction du framework: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de framework",
            message=str(e),
            status_code=500
        ).dict()), 500
    
@app.route('/api/logic_graph', methods=['POST'])
async def logic_graph():
    """
    Analyse un texte et retourne une représentation de graphe logique.
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le champ 'text' est requis dans le body JSON",
                status_code=400
            ).dict()), 400

        # Pour l'instant, nous utilisons une logique de mock simple.
        # Le service `logic_service` devrait être étendu pour gérer cela.
        # On simule une réussite si le texte n'est pas vide.
        if data['text']:
            # Simule une réponse de graphe SVG simple
            mock_graph_data = {
                "graph": "<svg width=\"100\" height=\"100\"><circle cx=\"50\" cy=\"50\" r=\"40\" stroke=\"green\" stroke-width=\"4\" fill=\"yellow\" /></svg>"
            }
            return jsonify(mock_graph_data)
        else:
            return jsonify(ErrorResponse(
                error="Texte vide",
                message="L'analyse d'un texte vide n'est pas supportée.",
                status_code=400
            ).dict()), 400

    except Exception as e:
        logger.error(f"Erreur lors de la génération du graphe logique: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de génération de graphe",
            message=str(e),
            status_code=500
        ).dict()), 500
    
@app.route('/api/endpoints', methods=['GET'])
def list_endpoints():
    """Liste tous les endpoints disponibles avec leur documentation."""
    endpoints = {
        "GET /api/health": {
            "description": "Vérification de l'état de l'API",
            "parameters": None,
            "response": "Status de l'API et des services"
        },
        "POST /api/analyze": {
            "description": "Analyse complète d'un texte argumentatif",
            "parameters": {
                "text": "string (requis) - Texte à analyser",
                "options": "object (optionnel) - Options d'analyse"
            },
            "response": "Résultat complet de l'analyse"
        },
        "POST /api/validate": {
            "description": "Validation logique d'un argument",
            "parameters": {
                "premises": "array[string] (requis) - Liste des prémisses",
                "conclusion": "string (requis) - Conclusion",
                "argument_type": "string (optionnel) - Type d'argument"
            },
            "response": "Résultat de la validation"
        },
        "POST /api/fallacies": {
            "description": "Détection de sophismes",
            "parameters": {
                "text": "string (requis) - Texte à analyser",
                "options": "object (optionnel) - Options de détection"
            },
            "response": "Liste des sophismes détectés"
        },
        "POST /api/framework": {
            "description": "Construction d'un framework de Dung",
            "parameters": {
                "arguments": "array (requis) - Liste des arguments",
                "options": "object (optionnel) - Options du framework"
            },
            "response": "Framework construit avec extensions"
        }
    }
    
    return jsonify({
        "api_name": "API d'Analyse Argumentative",
        "version": "1.0.0",
        "endpoints": endpoints
    })

if __name__ == '__main__':
    # Configuration pour le développement
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Démarrage de l'API sur le port {port}")
    logger.info(f"Mode debug: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )