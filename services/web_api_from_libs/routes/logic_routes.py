# libs/web_api/routes/logic_routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
from typing import Optional # Ajout de l'import manquant

# Import des services et modèles nécessaires
from ..models.logic_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest
)
from ..models.logic_response_models import (
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse
)
from ..models.response_models import ErrorResponse
from pydantic import ValidationError

logger = logging.getLogger("WebAPI.LogicRoutes")

logic_bp = Blueprint('logic_api', __name__)

@logic_bp.route('/belief-set', methods=['POST'])
async def logic_text_to_belief_set():
    """Convertit un texte en ensemble de croyances logiques."""
    logic_service = current_app.extensions['racine_services']['logic']
    logger.info("VALIDATION_CORRECTIF: La route ASYNC logic_text_to_belief_set a été appelée.")
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400
        
        try:
            req_model = LogicBeliefSetRequest(**data)
        except ValidationError as ve: # Attraper ValidationError spécifiquement
            logger.warning(f"Erreur de validation pour LogicBeliefSetRequest: {ve}")
            # Extraire les messages d'erreur de Pydantic pour une meilleure réponse
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()]
            return jsonify(ErrorResponse(error="Données invalides", message="; ".join(error_messages), status_code=400).dict()), 400
            
        result = await logic_service.text_to_belief_set(req_model)
        return jsonify(result.dict())

    except Exception as e:
        logger.error(f"Erreur lors de la conversion en ensemble de croyances: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de conversion", message=str(e), status_code=500).dict()), 500

@logic_bp.route('/query', methods=['POST'])
def logic_execute_query():
    """Exécute une requête logique sur un ensemble de croyances."""
    logic_service = current_app.extensions['racine_services']['logic']
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400

        try:
            req_model = LogicQueryRequest(**data)
        except ValidationError as ve: # Attraper ValidationError spécifiquement
            logger.warning(f"Erreur de validation pour LogicQueryRequest: {ve}")
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()]
            return jsonify(ErrorResponse(error="Données invalides", message="; ".join(error_messages), status_code=400).dict()), 400
            
        result = logic_service.execute_query(req_model)
        return jsonify(result.dict())

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête logique: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur d'exécution de requête", message=str(e), status_code=500).dict()), 500

@logic_bp.route('/generate-queries', methods=['POST'])
def logic_generate_queries():
    """Génère des requêtes logiques pertinentes."""
    logic_service = current_app.extensions['racine_services']['logic']
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Données manquantes", message="Le body JSON est requis", status_code=400).dict()), 400
        
        try:
            req_model = LogicGenerateQueriesRequest(**data)
        except ValidationError as ve: # Attraper ValidationError spécifiquement
            logger.warning(f"Erreur de validation pour LogicGenerateQueriesRequest: {ve}")
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()]
            return jsonify(ErrorResponse(error="Données invalides", message="; ".join(error_messages), status_code=400).dict()), 400
            
        result = logic_service.generate_queries(req_model)
        return jsonify(result.dict())

    except Exception as e:
        logger.error(f"Erreur lors de la génération de requêtes logiques: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de génération de requêtes", message=str(e), status_code=500).dict()), 500