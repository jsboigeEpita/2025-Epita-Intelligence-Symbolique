#!/usr/bin/env python3
"""
Interface Web pour l'Analyse Argumentative EPITA
===============================================

Application Flask pour l'interface web du système d'analyse argumentative.
Fournit une interface utilisateur pour soumettre des textes et visualiser les résultats d'analyse.

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime

# AUTO_ENV: Activation automatique environnement
try:
    import scripts.core.auto_env  # Auto-activation environnement intelligent
except ImportError:
    print("[WARNING] auto_env non disponible - environnement non activé")
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configuration des chemins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"

# Import du ServiceManager avec gestion d'erreur améliorée
ServiceManager = None
SERVICE_MANAGER_AVAILABLE = False
try:
    from argumentation_analysis.orchestration.service_manager import ServiceManager

    SERVICE_MANAGER_AVAILABLE = True
    logging.info("ServiceManager importé avec succès")
except ImportError as e:
    logging.warning(f"ServiceManager non disponible: {e}")
    SERVICE_MANAGER_AVAILABLE = False
except Exception as e:
    logging.warning(f"Erreur lors de l'import du ServiceManager: {e}")
    SERVICE_MANAGER_AVAILABLE = False

# Import des analyseurs de sophismes pour intégration complète
try:
    from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
        ComplexFallacyAnalyzer,
    )
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
        ContextualFallacyAnalyzer,
    )

    FALLACY_ANALYZERS_AVAILABLE = True
    logging.info("Analyseurs de sophismes importés avec succès")
except ImportError as e:
    logging.warning(f"Analyseurs de sophismes non disponibles: {e}")
    FALLACY_ANALYZERS_AVAILABLE = False

# Configuration de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-EPITA-2025")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max


# Configuration CORS simple sans dépendance externe
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WebApp] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Instance globale du ServiceManager
service_manager = None


async def initialize_services():
    """Initialise les services au démarrage de l'application."""
    global service_manager

    try:
        if SERVICE_MANAGER_AVAILABLE:
            service_manager = ServiceManager()

            # Initialisation asynchrone du ServiceManager
            initialized = await service_manager.initialize()
            if initialized:
                logger.info("ServiceManager initialisé avec succès")
            else:
                logger.warning("Échec de l'initialisation du ServiceManager")
                service_manager = None
        else:
            logger.warning("ServiceManager non disponible - mode dégradé")

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des services: {e}")
        service_manager = None


@app.route("/")
def index():
    """Page d'accueil de l'interface web."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
async def analyze():
    """
    Route pour l'analyse de texte avec intégration complète du ServiceManager.

    Reçoit un texte via POST et retourne les résultats d'analyse des sophismes.
    """
    try:
        # Récupération des données
        data = request.get_json()
        if not data:
            return jsonify({"error": "Aucune donnée reçue"}), 400

        text = data.get("text", "").strip()
        analysis_type = data.get("analysis_type", "comprehensive")
        options = data.get("options", {})

        if not text:
            return jsonify({"error": "Texte vide fourni"}), 400

        if len(text) > 10000:  # Limite de 10k caractères
            return jsonify({"error": "Texte trop long (max 10000 caractères)"}), 400

        # Génération d'un ID d'analyse
        analysis_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        logger.info(f"Analyse {analysis_id} démarrée - Type: {analysis_type}")

        # Analyse avec ServiceManager si disponible
        if service_manager:
            try:
                # Appel réel au ServiceManager pour l'analyse de texte
                result = await service_manager.analyze_text(
                    text=text, analysis_type=analysis_type, options=options
                )

                # Formatage des résultats pour l'interface web
                formatted_result = {
                    "analysis_id": analysis_id,
                    "status": "success",
                    "timestamp": start_time.isoformat(),
                    "input": {
                        "text": text[:200] + "..." if len(text) > 200 else text,
                        "text_length": len(text),
                        "analysis_type": analysis_type,
                    },
                    "results": result.get("results", {}),
                    "metadata": {
                        "duration": result.get("duration", 0),
                        "service_status": "active",
                        "components_used": _extract_components_used(result),
                        "analysis_method": "service_manager_real",
                    },
                    "summary": _generate_analysis_summary(result, text),
                    "fallacy_analysis": _extract_fallacy_analysis(result),
                }

                logger.info(
                    f"Analyse {analysis_id} terminée avec succès par ServiceManager"
                )
                return jsonify(formatted_result)

            except Exception as e:
                logger.error(f"Erreur dans l'analyse ServiceManager {analysis_id}: {e}")
                # Fallback vers analyse dégradée si ServiceManager échoue
                fallback_result = _fallback_analysis(text, analysis_type, options)
                fallback_result["analysis_id"] = analysis_id
                fallback_result["timestamp"] = start_time.isoformat()
                fallback_result["metadata"]["service_error"] = str(e)

                logger.warning(f"Analyse {analysis_id} basculée en mode dégradé")
                return jsonify(fallback_result)
        else:
            # Mode dégradé sans ServiceManager
            fallback_result = _fallback_analysis(text, analysis_type, options)
            fallback_result["analysis_id"] = analysis_id
            fallback_result["timestamp"] = start_time.isoformat()

            logger.info(f"Analyse {analysis_id} en mode dégradé")
            return jsonify(fallback_result)

    except Exception as e:
        logger.error(f"Erreur inattendue dans /analyze: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@app.route("/status")
async def status():
    """
    Route pour vérifier le statut des services avec intégration ServiceManager.

    Retourne l'état de santé des composants du système.
    """
    try:
        if service_manager:
            # Vérification de l'état de santé du ServiceManager
            try:
                health_status = (
                    await service_manager.health_check()
                    if hasattr(service_manager, "health_check")
                    else {"status": "healthy"}
                )
                service_details = (
                    await service_manager.get_service_status()
                    if hasattr(service_manager, "get_service_status")
                    else {"components": ["ServiceManager"]}
                )
            except Exception as e:
                logger.warning(f"Erreur lors du health check: {e}")
                health_status = {"status": "degraded", "error": str(e)}
                service_details = {"components": [], "error": str(e)}

            return jsonify(
                {
                    "status": "operational",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "service_manager": "active",
                        "fallacy_analyzers": "available"
                        if FALLACY_ANALYZERS_AVAILABLE
                        else "unavailable",
                        "health_check": health_status,
                        "service_details": service_details,
                    },
                    "webapp": {
                        "version": "1.0.0",
                        "mode": "full_analysis",
                        "features": {
                            "real_fallacy_detection": True,
                            "hierarchical_analysis": True,
                            "specialized_orchestrators": True,
                        },
                    },
                }
            )
        else:
            return jsonify(
                {
                    "status": "degraded",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "service_manager": "unavailable",
                        "fallacy_analyzers": "available"
                        if FALLACY_ANALYZERS_AVAILABLE
                        else "unavailable",
                    },
                    "webapp": {
                        "version": "1.0.0",
                        "mode": "fallback_only",
                        "features": {
                            "real_fallacy_detection": False,
                            "hierarchical_analysis": False,
                            "specialized_orchestrators": False,
                        },
                    },
                }
            )

    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@app.route("/api/examples")
def get_examples():
    """
    Route pour obtenir des exemples de textes d'analyse.

    Retourne une liste d'exemples prédéfinis pour faciliter les tests.
    """
    examples = [
        {
            "title": "Logique Propositionnelle",
            "text": "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.",
            "type": "propositional",
        },
        {
            "title": "Logique Modale",
            "text": "Il est nécessaire que tous les hommes soient mortels. Socrate est un homme. Il est donc nécessaire que Socrate soit mortel.",
            "type": "modal",
        },
        {
            "title": "Argumentation Complexe",
            "text": "L'intelligence artificielle représente à la fois une opportunité et un défi. D'un côté, elle peut révolutionner la médecine et l'éducation. De l'autre, elle pose des questions éthiques fondamentales sur l'emploi et la vie privée.",
            "type": "comprehensive",
        },
        {
            "title": "Paradoxe Logique",
            "text": "Cette phrase est fausse. Si elle est vraie, alors elle est fausse. Si elle est fausse, alors elle est vraie.",
            "type": "paradox",
        },
    ]

    return jsonify({"examples": examples})


def _extract_components_used(result: Dict[str, Any]) -> List[str]:
    """Extrait la liste des composants utilisés lors de l'analyse."""
    components = []

    if "results" in result:
        results = result["results"]

        if "specialized" in results:
            components.append("Orchestrateur Spécialisé")

        if "hierarchical" in results:
            hierarchical = results["hierarchical"]
            if "strategic" in hierarchical:
                components.append("Gestionnaire Stratégique")
            if "tactical" in hierarchical:
                components.append("Gestionnaire Tactique")
            if "operational" in hierarchical:
                components.append("Gestionnaire Opérationnel")

    return components if components else ["Analyse Basique"]


def _extract_fallacy_analysis(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extrait l'analyse des sophismes depuis les résultats du ServiceManager."""
    fallacy_analysis = {
        "fallacies_detected": [],
        "total_fallacies": 0,
        "severity_distribution": {},
        "categories_found": [],
    }

    if "results" not in result:
        return fallacy_analysis

    results = result["results"]

    # Extraction depuis les résultats hiérarchiques
    if "hierarchical" in results:
        hierarchical = results["hierarchical"]

        # Analyse stratégique
        if "strategic" in hierarchical:
            strategic = hierarchical["strategic"]
            if "fallacy_analysis" in strategic:
                fallacy_data = strategic["fallacy_analysis"]
                fallacy_analysis["fallacies_detected"].extend(
                    fallacy_data.get("detected", [])
                )

        # Analyse tactique
        if "tactical" in hierarchical:
            tactical = hierarchical["tactical"]
            if "fallacy_detection" in tactical:
                fallacy_data = tactical["fallacy_detection"]
                fallacy_analysis["fallacies_detected"].extend(
                    fallacy_data.get("detected", [])
                )

        # Analyse opérationnelle
        if "operational" in hierarchical:
            operational = hierarchical["operational"]
            if "fallacy_results" in operational:
                fallacy_data = operational["fallacy_results"]
                fallacy_analysis["fallacies_detected"].extend(
                    fallacy_data.get("detected", [])
                )

    # Extraction depuis les orchestrateurs spécialisés
    if "specialized" in results:
        specialized = results["specialized"]
        if "fallacies" in specialized:
            fallacy_analysis["fallacies_detected"].extend(specialized["fallacies"])

    # Calcul des statistiques
    fallacy_analysis["total_fallacies"] = len(fallacy_analysis["fallacies_detected"])

    # Distribution de sévérité
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    categories = set()

    for fallacy in fallacy_analysis["fallacies_detected"]:
        # Sévérité
        severity = fallacy.get("severity", 0.5)
        if severity < 0.4:
            severity_counts["low"] += 1
        elif severity < 0.7:
            severity_counts["medium"] += 1
        else:
            severity_counts["high"] += 1

        # Catégories
        category = fallacy.get("category", fallacy.get("type", "unknown"))
        categories.add(category)

    fallacy_analysis["severity_distribution"] = severity_counts
    fallacy_analysis["categories_found"] = sorted(list(categories))

    return fallacy_analysis


def _generate_analysis_summary(result: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Génère un résumé de l'analyse pour l'interface utilisateur."""
    word_count = len(text.split())
    sentence_count = text.count(".") + text.count("!") + text.count("?")

    # Analyse basique de mots-clés logiques
    logic_keywords = [
        "si",
        "alors",
        "donc",
        "tous",
        "nécessairement",
        "possible",
        "probable",
    ]
    logic_score = sum(
        1 for keyword in logic_keywords if keyword.lower() in text.lower()
    )

    return {
        "text_metrics": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "character_count": len(text),
        },
        "analysis_metrics": {
            "logic_keywords_found": logic_score,
            "complexity_level": "élevée"
            if word_count > 100
            else "moyenne"
            if word_count > 50
            else "simple",
        },
        "components_summary": _extract_components_used(result),
        "processing_time": result.get("duration", 0),
    }


def _fallback_analysis(
    text: str, analysis_type: str, options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mode d'analyse de secours quand le ServiceManager n'est pas disponible.

    Fournit une analyse basique du texte.
    """
    start_time = datetime.now()

    # Analyse textuelle basique
    word_count = len(text.split())
    sentence_count = text.count(".") + text.count("!") + text.count("?")
    character_count = len(text)

    # Détection de mots-clés logiques
    logic_keywords = ["si", "alors", "donc", "tous", "nécessairement", "possible"]
    logic_score = sum(
        1 for keyword in logic_keywords if keyword.lower() in text.lower()
    )

    # Simulation d'un délai de traitement
    import time

    time.sleep(0.1)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    return {
        "status": "success",
        "mode": "fallback",
        "input": {
            "text": text[:200] + "..." if len(text) > 200 else text,
            "text_length": len(text),
            "analysis_type": analysis_type,
        },
        "results": {
            "fallback": {
                "text_analysis": {
                    "word_count": word_count,
                    "sentence_count": sentence_count,
                    "character_count": character_count,
                    "logic_keywords_detected": logic_score,
                },
                "assessment": {
                    "complexity": "élevée"
                    if word_count > 100
                    else "moyenne"
                    if word_count > 50
                    else "simple",
                    "logical_structure": "présente" if logic_score > 0 else "limitée",
                    "analysis_confidence": 0.7,
                },
            }
        },
        "metadata": {
            "duration": duration,
            "service_status": "fallback",
            "components_used": ["Analyseur Basique"],
        },
        "summary": {
            "text_metrics": {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "character_count": character_count,
            },
            "analysis_metrics": {
                "logic_keywords_found": logic_score,
                "complexity_level": "élevée"
                if word_count > 100
                else "moyenne"
                if word_count > 50
                else "simple",
            },
            "components_summary": ["Analyseur Basique"],
            "processing_time": duration,
        },
    }


@app.errorhandler(404)
def page_not_found(e):
    """Gestionnaire d'erreur 404."""
    return render_template("index.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Gestionnaire d'erreur 500."""
    logger.error(f"Erreur interne: {e}")
    return jsonify({"error": "Erreur interne du serveur"}), 500


if __name__ == "__main__":
    import asyncio

    # Configuration pour le développement
    port = int(os.environ.get("PORT", 3000))
    debug = os.environ.get("DEBUG", "False").lower() == "true"

    logger.info(f"Démarrage de l'interface web sur le port {port}")
    logger.info(f"Mode debug: {debug}")
    logger.info(f"ServiceManager disponible: {SERVICE_MANAGER_AVAILABLE}")
    logger.info(f"Analyseurs de sophismes disponibles: {FALLACY_ANALYZERS_AVAILABLE}")

    # Initialisation des répertoires
    RESULTS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    # Initialisation asynchrone des services
    async def startup():
        """Initialisation asynchrone des services au démarrage."""
        await initialize_services()
        logger.info("Initialisation des services terminée")

    # Exécuter l'initialisation asynchrone
    asyncio.run(startup())

    # Configuration Flask pour supporter async
    app.config["TESTING"] = debug

    # Démarrage de l'application
    logger.info("Démarrage du serveur Flask...")
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
