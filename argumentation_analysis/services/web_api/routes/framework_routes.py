#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Routes pour la gestion des frameworks d'argumentation.
"""

from flask import Blueprint, request, jsonify, current_app
from argumentation_analysis.services.web_api.models.request_models import (
    FrameworkAnalysisRequest,
)
from argumentation_analysis.services.web_api.models.response_models import (
    SuccessResponse,
    ErrorResponse,
)

framework_bp = Blueprint("framework_bp", __name__)


@framework_bp.route("/framework/analyze", methods=["POST"])
def analyze_framework_route():
    """
    Endpoint pour analyser un framework d'argumentation de Dung.
    """
    if not request.is_json:
        return (
            jsonify(
                ErrorResponse(
                    error="Invalid input",
                    message="Request must be JSON",
                    status_code=400,
                ).dict()
            ),
            400,
        )

    try:
        data = FrameworkAnalysisRequest(**request.json)
        framework_service = current_app.services.framework_service

        result = framework_service.analyze_dung_framework(data.arguments, data.attacks)

        return jsonify(SuccessResponse(data=result).dict()), 200

    except Exception as e:
        current_app.logger.error(f"Error in framework analysis: {e}", exc_info=True)
        return (
            jsonify(
                ErrorResponse(
                    error="Framework analysis failed", message=str(e), status_code=500
                ).dict()
            ),
            500,
        )
