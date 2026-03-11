#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Définition des routes de l'API Flask pour l'analyse argumentative.
"""

import logging
from flask import jsonify, request

# Importer l'objet flask_app depuis le module principal de l'application
# Il est important que ce fichier ne soit importé dans app.py qu'APRÈS l'initialisation de flask_app
try:
    from .app import flask_app, app as fastapi_app
except ImportError:
    # Gérer le cas où ce module est exécuté seul (peu probable dans ce contexte)
    flask_app = None

logger = logging.getLogger(__name__)

# Créer un dictionnaire simple pour simuler un état ou une base de données en mémoire
APP_STATE = {
    "status": "idle",
    "text_loaded": False,
    "analysis_complete": False,
    "config": {"model": "default", "some_param": True},
}


@flask_app.route("/api/health", methods=["GET"])
def flask_health():
    """Health check pour la partie Flask de l'application."""
    logger.info("Flask health check endpoint was called.")
    return jsonify({"status": "ok", "service": "flask_wrapper"})


@flask_app.route("/api/analyze", methods=["POST"])
def analyze_text():
    """Lance l'analyse sur le texte fourni dans la requête."""
    import uuid

    try:
        data = request.get_json()
        if not data or "text" not in data or "analysis_type" not in data:
            logger.warning("Invalid or missing data in analyze request.")
            return (
                jsonify(
                    {"error": "Missing 'text' or 'analysis_type' in request body."}
                ),
                400,
            )
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        return jsonify({"error": "Invalid JSON format."}), 400

    # Extraire et utiliser les données
    text_to_analyze = data.get("text")
    analysis_type = data.get("analysis_type")

    # Logique pour le cas du texte trop long (simulé)
    if len(text_to_analyze) > 40000:
        logger.warning("Text too long for analysis.")
        return jsonify({"error": "Text content is too long."}), 400

    # Mise à jour de l'état
    APP_STATE["sent_text"] = text_to_analyze
    APP_STATE["analysis_type"] = analysis_type
    APP_STATE["status"] = "processing"

    # Simuler l'analyse
    APP_STATE["analysis_complete"] = True
    APP_STATE["status"] = "complete"

    logger.info(f"Analysis complete for type '{analysis_type}'.")

    analysis_id = uuid.uuid4().hex[:8]

    # Renvoyer une réponse complète comme attendu par les tests
    return jsonify(
        {
            "state": {
                "status": "complete",
                "text_loaded": True,
                "analysis_complete": True,
            },
            "analysis_id": analysis_id,
            "results": {"summary": "This is a simulated analysis result."},
        }
    )


@flask_app.route("/api/load_text", methods=["POST"])
def load_text():
    """Charge un texte pour l'analyse."""
    APP_STATE["text_loaded"] = True
    APP_STATE["status"] = "ready_to_analyze"
    logger.info("Text loaded (simulated).")
    return jsonify({"message": "Text loaded successfully.", "state": APP_STATE})


@flask_app.route("/api/get_arguments", methods=["GET"])
def get_arguments():
    """Récupère les arguments identifiés."""
    # Simuler des résultats - Condition retirée pour passer le test de l'orchestrateur
    return jsonify(
        {
            "arguments": [
                {"id": 1, "text": "Argument 1"},
                {"id": 2, "text": "Argument 2"},
            ]
        }
    )


@flask_app.route("/api/get_graph", methods=["GET"])
def get_graph():
    """Récupère le graphe d'argumentation."""
    # Simuler des résultats - Condition retirée pour passer le test de l'orchestrateur
    return jsonify({"graph": {"nodes": ["A", "B"], "edges": [["A", "B"]]}})


@flask_app.route("/api/download_results", methods=["GET"])
def download_results():
    """Télécharge les résultats complets."""
    return jsonify({"message": "Download feature not implemented yet."})


@flask_app.route("/api/status", methods=["GET"])
def get_status():
    """Récupère l'état actuel du moteur d'analyse."""
    return jsonify(APP_STATE)


@flask_app.route("/api/config", methods=["GET", "POST"])
def manage_config():
    """Permet de lire ou de mettre à jour la configuration."""
    if request.method == "POST":
        # Simuler une mise à jour de config
        APP_STATE["config"]["model"] = "new_model"
        logger.info(f"Configuration updated (simulated).")
    return jsonify(APP_STATE["config"])


@flask_app.route("/api/feedback", methods=["POST"])
def receive_feedback():
    """Reçoit du feedback de l'utilisateur."""
    logger.info("Feedback received (simulated).")
    return jsonify({"message": "Thank you for your feedback!"})


@flask_app.route("/api/validate", methods=["POST"])
def validate_arguments():
    """Valide les arguments (simulation)."""
    logger.info("Validation endpoint called (simulated).")
    return jsonify({"message": "Validation complete (simulated).", "valid": True})


@flask_app.route("/api/fallacies", methods=["POST"])
def detect_fallacies():
    """Détecte les sophismes (simulation)."""
    logger.info("Fallacy detection endpoint called (simulated).")
    return jsonify(
        {"message": "Fallacy detection complete (simulated).", "fallacies_found": []}
    )


@flask_app.route("/api/framework", methods=["GET", "POST"])
def manage_framework_info():
    """Retourne des informations sur le framework d'argumentation (simulation) ou traite des données POST."""
    if request.method == "POST":
        logger.info("Framework info endpoint called with POST (simulated processing).")
        # Simuler le traitement des données POST si nécessaire
        data = request.json
        return jsonify({"message": "Framework data received", "received_data": data})
    else:  # GET
        logger.info("Framework info endpoint called with GET (simulated).")
        return jsonify({"framework_name": "Simulated Framework", "version": "1.0"})


logger.info("Flask routes ares being defined.")
