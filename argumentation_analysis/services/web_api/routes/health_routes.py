#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Routes minimalistes pour les health checks, sans dépendances lourdes.
"""

import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

health_bp = Blueprint('health_bp', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Point de terminaison de health check simple.
    Retourne un statut 'ok' si l'application est capable de répondre aux requêtes.
    Ce point de terminaison ne doit avoir aucune dépendance avec les services lourds (JVM, etc.).
    """
    logger.info("Executing simple health check endpoint...")
    return jsonify({"status": "ok", "message": "Server is up and responding."}), 200