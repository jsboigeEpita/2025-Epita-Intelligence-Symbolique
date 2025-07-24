# argumentation_analysis/services/web_api/routes/main_routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
import asyncio
import jpype
from pydantic import ValidationError

# Import des services et modèles nécessaires
# Les imports relatifs devraient maintenant pointer vers les bons modules.
from ..models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest
)
from ..models.response_models import ErrorResponse

logger = logging.getLogger("WebAPI.MainRoutes")

main_bp = Blueprint('main_api', __name__)

def get_services_from_app_context():
    """Récupère les services depuis le contexte de l'application Flask."""
    services = current_app.services
    return (
        services.analysis_service,
        services.validation_service,
        services.fallacy_service,
        services.framework_service,
        services.logic_service
    )

@main_bp.route('/health', methods=['GET'])
def health_check():
    """Vérification de l'état de l'API, y compris les dépendances critiques comme la JVM."""
    try:
        services = current_app.services
        
        # Vérification de l'état de la JVM
        is_jvm_started = jpype.isJVMStarted()
        
        # Construction de la réponse
        response_data = {
            "status": "healthy" if is_jvm_started else "unhealthy",
            "message": "API d'analyse argumentative opérationnelle",
            "version": "1.0.0",
            "services": {
                "jvm": {"running": is_jvm_started, "status": "OK" if is_jvm_started else "Not Running"},
                "analysis": services.analysis_service.is_healthy(),
                "validation": services.validation_service.is_healthy(),
                "fallacy": services.fallacy_service.is_healthy(),
                "framework": services.framework_service.is_healthy(),
                "logic": services.logic_service.is_healthy()
            }
        }
        
        if not is_jvm_started:
            logger.error("Health check failed: JVM is not running.")
            return jsonify(response_data), 503  # 503 Service Unavailable

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(
            error="Erreur de health check",
            message=str(e),
            status_code=500
        ).dict()), 500

@main_bp.route('/analyze', methods=['POST'])
async def analyze_text():
    """Analyse complète d'un texte argumentatif."""
    logger.info("Entering analyze_text route")
    try:
        analysis_service = current_app.services.analysis_service
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400

        analysis_request = AnalysisRequest(**data)
        result = await analysis_service.analyze_text(analysis_request)

        if not result.success:
            logger.warning(f"Analysis failed (success=False). Request data: {data}")
            return jsonify(ErrorResponse(
                error="Internal Analysis Error",
                message="The service was unable to complete the analysis. Check server logs for details.",
                status_code=500
            ).dict()), 500

        logger.info("Exiting analyze_text route")
        return jsonify(result.dict())

    except ValidationError as e:
        logger.warning(f"Validation des données d'analyse a échoué: {str(e)}")
        return jsonify(ErrorResponse(error="Données invalides", message=str(e), status_code=400).dict()), 400

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur d'analyse", message=str(e), status_code=500).dict()), 500

@main_bp.route('/validate', methods=['POST'])
async def validate_argument():
    """Validation logique d'un argument."""
    try:
        validation_service = current_app.services.validation_service
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400
        
        validation_request = ValidationRequest(**data)
        result = await validation_service.validate_argument(validation_request)
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

@main_bp.route('/v1/framework/analyze', methods=['POST'])
def build_framework():
    """Construction d'un framework de Dung."""
    try:
        framework_service = current_app.services.framework_service
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400

        # Gérer le format de requête alternatif avec 'attack_relations' pour la compatibilité
        if 'arguments' in data and 'attack_relations' in data:
            args_by_id = {arg['id']: arg for arg in data['arguments']}
            for rel in data.get('attack_relations', []):
                attacker_id = rel.get('from')
                target_id = rel.get('to')
                if attacker_id and target_id and attacker_id in args_by_id:
                    if 'attacks' not in args_by_id[attacker_id]:
                        args_by_id[attacker_id]['attacks'] = []
                    if target_id not in args_by_id[attacker_id]['attacks']:
                        args_by_id[attacker_id]['attacks'].append(target_id)
            
            data['arguments'] = list(args_by_id.values())

        framework_request = FrameworkRequest(**data)
        # Extraire les données pour la nouvelle signature de la méthode
        arguments_list = [arg.id for arg in framework_request.arguments]
        attacks_list = [[arg.id, attacked_id] for arg in framework_request.arguments for attacked_id in arg.attacks]
        
        result = framework_service.analyze_dung_framework(
            arguments=arguments_list,
            attacks=attacks_list
        )
        return jsonify(result)
        
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