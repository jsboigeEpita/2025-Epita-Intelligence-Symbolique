# argumentation_analysis/services/web_api/routes/logic_routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
from typing import Optional
from pydantic import ValidationError

# Import des modèles nécessaires. Les chemins sont relatifs à ce fichier.
from ..models.request_models import (
    LogicBeliefSetRequest,
    LogicQueryRequest,
    LogicGenerateQueriesRequest,
)
from ..models.response_models import (
    LogicBeliefSetResponse,
    LogicQueryResponse,
    LogicGenerateQueriesResponse,
    ErrorResponse,
)

logger = logging.getLogger("WebAPI.LogicRoutes")

logic_bp = Blueprint("logic_api", __name__)


# Fonction helper pour récupérer le service depuis le contexte de l'application
def get_logic_service_from_app_context():
    return current_app.logic_service


@logic_bp.route("/belief-set", methods=["POST"])
async def logic_text_to_belief_set():
    logger.info("--- ENTERING /api/logic/belief-set ---")
    """Convertit un texte en ensemble de croyances logiques."""
    logic_service = get_logic_service_from_app_context()
    try:
        data = request.get_json()
        logger.debug(f"Received data for belief set conversion: {data}")
        if not data:
            return (
                jsonify(
                    ErrorResponse(
                        error="Données manquantes",
                        message="Le body JSON est requis",
                        status_code=400,
                    ).dict()
                ),
                400,
            )

        try:
            req_model = LogicBeliefSetRequest(**data)
        except ValidationError as ve:
            logger.warning(f"Erreur de validation pour LogicBeliefSetRequest: {ve}")
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()]
            return (
                jsonify(
                    ErrorResponse(
                        error="Données invalides",
                        message="; ".join(error_messages),
                        status_code=400,
                    ).dict()
                ),
                400,
            )

        result = await logic_service.text_to_belief_set(req_model)
        return jsonify(result.dict())

    except Exception as e:
        logger.error(
            f"Erreur lors de la conversion en ensemble de croyances: {str(e)}",
            exc_info=True,
        )
        return (
            jsonify(
                ErrorResponse(
                    error="Erreur de conversion", message=str(e), status_code=500
                ).dict()
            ),
            500,
        )


@logic_bp.route("/query", methods=["POST"])
async def logic_execute_query():
    """Exécute une requête logique sur un ensemble de croyances."""
    logic_service = get_logic_service_from_app_context()
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    ErrorResponse(
                        error="Données manquantes",
                        message="Le body JSON est requis",
                        status_code=400,
                    ).dict()
                ),
                400,
            )

        try:
            req_model = LogicQueryRequest(**data)
        except ValidationError as ve:
            logger.warning(f"Erreur de validation pour LogicQueryRequest: {ve}")
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()]
            return (
                jsonify(
                    ErrorResponse(
                        error="Données invalides",
                        message="; ".join(error_messages),
                        status_code=400,
                    ).dict()
                ),
                400,
            )

        result = await logic_service.execute_query(req_model)
        return jsonify(result.dict())

    except Exception as e:
        logger.error(
            f"Erreur lors de l'exécution de la requête logique: {str(e)}", exc_info=True
        )
        return (
            jsonify(
                ErrorResponse(
                    error="Erreur d'exécution de requête",
                    message=str(e),
                    status_code=500,
                ).dict()
            ),
            500,
        )


@logic_bp.route("/generate-queries", methods=["POST"])
async def logic_generate_queries():
    """Génère des requêtes logiques pertinentes."""
    logic_service = get_logic_service_from_app_context()
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    ErrorResponse(
                        error="Données manquantes",
                        message="Le body JSON est requis",
                        status_code=400,
                    ).dict()
                ),
                400,
            )

        try:
            req_model = LogicGenerateQueriesRequest(**data)
        except ValidationError as ve:
            logger.warning(
                f"Erreur de validation pour LogicGenerateQueriesRequest: {ve}"
            )
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()]
            return (
                jsonify(
                    ErrorResponse(
                        error="Données invalides",
                        message="; ".join(error_messages),
                        status_code=400,
                    ).dict()
                ),
                400,
            )

        result = await logic_service.generate_queries(req_model)
        return jsonify(result.dict())

    except Exception as e:
        logger.error(
            f"Erreur lors de la génération de requêtes logiques: {str(e)}",
            exc_info=True,
        )
        return (
            jsonify(
                ErrorResponse(
                    error="Erreur de génération de requêtes",
                    message=str(e),
                    status_code=500,
                ).dict()
            ),
            500,
        )
