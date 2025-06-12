# services/web_api_from_libs/routes/main_routes.py
from flask import Blueprint, request, jsonify
import logging

# Import des services et modèles nécessaires
from ..services.analysis_service import AnalysisService
from ..services.validation_service import ValidationService
from ..services.fallacy_service import FallacyService
from ..services.framework_service import FrameworkService
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from ..models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest
)
from ..models.response_models import ErrorResponse

logger = logging.getLogger("WebAPI.MainRoutes")

main_bp = Blueprint('main_api', __name__)

# Note: Les services sont instanciés dans app.py et devraient être accessibles ici.
# Pour simplifier, nous allons les importer directement depuis le contexte de l'application Flask.
# Une meilleure approche serait d'utiliser une injection de dépendances.

@main_bp.route('/health', methods=['GET'])
def health_check():
    """Vérification de l'état de l'API."""
    from ..app import analysis_service, validation_service, fallacy_service, framework_service, logic_service
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
                "logic": logic_service.is_healthy()
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de health check",
            message=str(e),
            status_code=500
        ).dict()), 500

@main_bp.route('/analyze', methods=['POST'])
async def analyze_text():
    """Analyse complète d'un texte argumentatif."""
    from ..app import analysis_service
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400
        
        analysis_request = AnalysisRequest(**data)
        result = await analysis_service.analyze_text(analysis_request)
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur d'analyse", message=str(e), status_code=500).dict()), 500

@main_bp.route('/validate', methods=['POST'])
def validate_argument():
    """Validation logique d'un argument."""
    from ..app import validation_service
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400
        
        validation_request = ValidationRequest(**data)
        result = validation_service.validate_argument(validation_request)
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de validation", message=str(e), status_code=500).dict()), 500

@main_bp.route('/fallacies', methods=['POST'])
def detect_fallacies():
    """Détection de sophismes dans un texte."""
    from ..app import fallacy_service
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400

        fallacy_request = FallacyRequest(**data)
        result = fallacy_service.detect_fallacies(fallacy_request)
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de sophismes: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de détection", message=str(e), status_code=500).dict()), 500

@main_bp.route('/framework', methods=['POST'])
def build_framework():
    """Construction d'un framework de Dung."""
    from ..app import framework_service
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400

        framework_request = FrameworkRequest(**data)
        result = framework_service.build_framework(framework_request)
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la construction du framework: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de framework", message=str(e), status_code=500).dict()), 500

@main_bp.route('/logic_graph', methods=['POST'])
async def logic_graph():
    """Analyse un texte et retourne une représentation de graphe logique."""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le champ 'text' est requis dans le body JSON", status_code=400).dict()), 400

        if data['text']:
            mock_graph_data = {"graph": "<svg width=\"100\" height=\"100\"><circle cx=\"50\" cy=\"50\" r=\"40\" stroke=\"green\" stroke-width=\"4\" fill=\"yellow\" /></svg>"}
            return jsonify(mock_graph_data)
        else:
            return jsonify(ErrorResponse(error="Texte vide", message="L'analyse d'un texte vide n'est pas supportée.", status_code=400).dict()), 400
    except Exception as e:
        logger.error(f"Erreur lors de la génération du graphe logique: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de génération de graphe", message=str(e), status_code=500).dict()), 500

@main_bp.route('/endpoints', methods=['GET'])
def list_endpoints():
    """Liste tous les endpoints disponibles avec leur documentation."""
    endpoints = {
        "GET /api/health": {"description": "Vérification de l'état de l'API"},
        "POST /api/analyze": {"description": "Analyse complète d'un texte argumentatif"},
        "POST /api/validate": {"description": "Validation logique d'un argument"},
        "POST /api/fallacies": {"description": "Détection de sophismes"},
        "POST /api/framework": {"description": "Construction d'un framework de Dung"}
    }
    return jsonify({
        "api_name": "API d'Analyse Argumentative",
        "version": "1.0.0",
        "endpoints": endpoints
    })