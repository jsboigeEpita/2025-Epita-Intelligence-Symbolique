# argumentation_analysis/services/web_api/routes/main_routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
import asyncio

# Import des services et modèles nécessaires
# Les imports relatifs devraient maintenant pointer vers les bons modules.
from ..models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest
)
from ..models.response_models import ErrorResponse

logger = logging.getLogger("WebAPI.MainRoutes")

main_bp = Blueprint('main_api', __name__)

# Note: Pour une meilleure architecture, les services devraient être injectés
# plutôt qu'importés de cette manière.
# On importe directement depuis le contexte de l'application.
@main_bp.route('/health', methods=['GET'])
def health_check():
    """Vérification de l'état de l'API."""
    try:
        services = current_app.services
        return jsonify({
            "status": "healthy",
            "message": "API d'analyse argumentative opérationnelle",
            "version": "1.0.0",
            "services": {
                "analysis": services.analysis_service.is_healthy(),
                "validation": services.validation_service.is_healthy(),
                "fallacy": services.fallacy_service.is_healthy(),
                "framework": services.framework_service.is_healthy(),
                "logic": services.logic_service.is_healthy()
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
def analyze_text():
    """Analyse complète d'un texte argumentatif."""
    try:
        analysis_service = current_app.services.analysis_service
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400
        
        analysis_request = AnalysisRequest(**data)
        # Exécute la coroutine dans une boucle d'événements asyncio
        # Note: Cela crée une nouvelle boucle à chaque appel. Pour la production,
        # il serait préférable d'utiliser un framework ASGI comme Hypercorn.
        result = asyncio.run(analysis_service.analyze_text(analysis_request))
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur d'analyse", message=str(e), status_code=500).dict()), 500

@main_bp.route('/validate', methods=['POST'])
def validate_argument():
    """Validation logique d'un argument."""
    try:
        validation_service = current_app.services.validation_service
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
    try:
        fallacy_service = current_app.services.fallacy_service
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
    try:
        framework_service = current_app.services.framework_service
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