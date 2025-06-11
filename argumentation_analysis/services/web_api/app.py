#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.

Cette API expose les fonctionnalités du moteur d'analyse argumentative
pour permettre aux étudiants de créer des interfaces web facilement.
"""
import logging
import sys

# Configure logging immediately at the very top of the module execution.
# This ensures that any subsequent logging calls, even before full app setup, are captured.
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(name)s [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                    force=True) # force=True allows reconfiguring if it was called before (e.g. by a dependency)
_top_module_logger = logging.getLogger(__name__) # Use __name__ to get 'argumentation_analysis.services.web_api.app'
_top_module_logger.info("--- web_api/app.py module execution START, initial logging configured ---")
sys.stderr.flush() # Ensure this initial log gets out.

logger = _top_module_logger # Make it available globally as 'logger' for existing code

import os
# logging est déjà importé et configuré par basicConfig à la ligne 15
# _top_module_logger est déjà défini à la ligne 18
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional # Optional est déjà importé

# Déclarer les variables avant le bloc try pour qu'elles aient un scope global dans le module
flask_app = None # Sera assigné à flask_app_instance_for_init
app = None # Sera assigné à app_object_for_uvicorn

try:
    _top_module_logger.info("--- Attempting critical imports: Flask, CORS, Werkzeug, a2wsgi ---")
    sys.stderr.flush()
    from flask import Flask, request, jsonify, redirect, url_for
    from flask_cors import CORS
    from werkzeug.exceptions import HTTPException
    from a2wsgi import WSGIMiddleware
    _top_module_logger.info("--- Critical imports SUCCESSFUL ---")
    sys.stderr.flush()

    _top_module_logger.info("--- Initializing Flask app instance ---")
    sys.stderr.flush()
    flask_app_instance_for_init = Flask(__name__) # Variable locale temporaire
    _top_module_logger.info(f"--- Flask app instance CREATED: {type(flask_app_instance_for_init)} ---")
    sys.stderr.flush()

    _top_module_logger.info("--- Applying CORS to Flask app ---")
    sys.stderr.flush()
    CORS(flask_app_instance_for_init)
    _top_module_logger.info("--- CORS applied ---")
    sys.stderr.flush()

    _top_module_logger.info("--- Wrapping Flask app with WSGIMiddleware for Uvicorn ---")
    sys.stderr.flush()
    app_object_for_uvicorn = WSGIMiddleware(flask_app_instance_for_init) # Variable locale temporaire
    _top_module_logger.info(f"--- WSGIMiddleware WRAPPED: {type(app_object_for_uvicorn)} ---")
    sys.stderr.flush()
    
    # Assigner aux variables globales du module si tout a réussi
    flask_app = flask_app_instance_for_init
    app = app_object_for_uvicorn
    _top_module_logger.info(f"--- Global 'flask_app' and 'app' assigned. Type 'app': {type(app)} ---")
    sys.stderr.flush()

except ImportError as e_imports:
    _top_module_logger.critical(f"!!! CRITICAL IMPORT ERROR (Flask/CORS/Werkzeug/a2wsgi): {e_imports} !!!", exc_info=True)
    sys.stderr.flush()
    raise
except Exception as e_init:
    _top_module_logger.critical(f"!!! CRITICAL ERROR during Flask/WSGIMiddleware initialization: {e_init} !!!", exc_info=True)
    sys.stderr.flush()
    raise

if flask_app is None or app is None:
    _critical_error_msg = "!!! flask_app or app object is None after initialization block - THIS SHOULD NOT HAPPEN if no exception was raised. !!!"
    _top_module_logger.critical(_critical_error_msg)
    sys.stderr.flush()
    raise RuntimeError(_critical_error_msg)

_top_module_logger.info("--- Flask app and WSGI wrapper 'app' successfully initialized. Proceeding with module. ---")
sys.stderr.flush()

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
# La structure du projet est c:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis/services/web_api/app.py
# root_dir doit pointer vers c:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis
# donc current_dir.parent.parent
root_dir = current_dir.parent.parent
if str(root_dir) not in sys.path:
    # Ceci ajoute 'c:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis' au path
    sys.path.append(str(root_dir))
    # Pour que les imports comme `from services.web_api...` fonctionnent,
    # il faudrait que `c:/dev/2025-Epita-Intelligence-Symbolique` soit dans le path,
    # ou que les imports soient `from argumentation_analysis.services.web_api...`
    # La version HEAD utilise `from argumentation_analysis.services.web_api...` ce qui est plus propre.
    # Nous allons donc conserver les imports de HEAD et supprimer cette manipulation de sys.path
    # qui est spécifique à pr-student-1 et potentiellement source de confusion.
    pass # On ne modifie plus sys.path ici, on se fie aux imports de HEAD.

# Re-Configuration du logging avec le format désiré (déjà présent dans le code actuel)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s (%(filename)s:%(lineno)d)',
#     datefmt='%H:%M:%S',
#     force=True
# )
# logger = logging.getLogger("WebAPI")
# logger.info("--- Logging reconfiguré avec format complet (après initialisation app) ---")
# sys.stderr.flush()
# Le code existant à partir de la ligne 46 gère déjà la reconfiguration du logging
# et l'initialisation de 'logger'. Les logs d'initialisation de Flask et WSGIMiddleware
# sont également déjà présents (lignes 127-141).

# La modification principale est l'encapsulation des imports critiques et l'appel initial à basicConfig.
# Le reste du fichier à partir de la (nouvelle) ligne ~58 (anciennement ligne 30)
# qui commence par `current_dir = Path(__file__).parent` devrait rester tel quel,
# y compris la création de `flask_app` et `app` qui sont maintenant conditionnées
# par le succès des imports critiques.

# Pour s'assurer que `app` et `flask_app` sont définis globalement si les imports réussissent,
# je vais les assigner après le bloc try-except si `flask_app_instance` et `app_instance_for_uvicorn`
# ont été créés.

# (Le code existant à partir de la ligne 126 pour la création de flask_app et app
#  sera exécuté si les imports ont réussi. Les variables globales `app` et `flask_app`
#  seront donc définies.)

# Import des services (style HEAD, mais avec les try-except de pr-student-1 pour la robustesse)
# Cette section est déjà présente et correcte.
try:
    # Utilisation des imports absolus depuis la racine du module `argumentation_analysis` (style HEAD)
    logger.info("Attempting import: AnalysisService")
    sys.stderr.flush()
    from argumentation_analysis.services.web_api.services.analysis_service import AnalysisService
    logger.info("Imported: AnalysisService")
    sys.stderr.flush()
    logger.info("Attempting import: ValidationService")
    sys.stderr.flush()
    from argumentation_analysis.services.web_api.services.validation_service import ValidationService
    logger.info("Imported: ValidationService")
    sys.stderr.flush()
    logger.info("Attempting import: FallacyService")
    sys.stderr.flush()
    from argumentation_analysis.services.web_api.services.fallacy_service import FallacyService
    logger.info("Imported: FallacyService")
    sys.stderr.flush()
    logger.info("Attempting import: FrameworkService")
    sys.stderr.flush()
    from argumentation_analysis.services.web_api.services.framework_service import FrameworkService
    logger.info("Imported: FrameworkService")
    sys.stderr.flush()
    logger.info("Attempting import: LogicService")
    sys.stderr.flush()
    from argumentation_analysis.services.web_api.services.logic_service import LogicService
    logger.info("Imported: LogicService")
    sys.stderr.flush()
    logger.info("Attempting import: Request Models")
    sys.stderr.flush()
    from argumentation_analysis.services.web_api.models.request_models import (
        AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest,
        LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest, LogicOptions # Ajout de LogicOptions depuis HEAD
    )
    logger.info("Imported: Request Models")
    sys.stderr.flush()
    logger.info("Attempting import: Response Models") # AJOUT
    sys.stderr.flush() # AJOUT
    from argumentation_analysis.services.web_api.models.response_models import (
        AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse, ErrorResponse,
        LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse, LogicInterpretationResponse, LogicQueryResult # Ajout de LogicQueryResult depuis HEAD
    )
    logger.info("Imported: Response Models") # AJOUT
    sys.stderr.flush() # AJOUT
except ImportError as e_abs:
    logger.warning(f"ImportError avec imports absolus ({e_abs}). Tentative d'imports relatifs.")
    try:
        # Fallback pour les imports relatifs (style pr-student-1)
        from .services.analysis_service import AnalysisService
        from .services.validation_service import ValidationService
        from .services.fallacy_service import FallacyService
        from .services.framework_service import FrameworkService
        from .services.logic_service import LogicService
        from .models.request_models import (
            AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest,
            LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest, LogicOptions
        )
        from .models.response_models import (
            AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse, ErrorResponse,
            LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse, LogicInterpretationResponse, LogicQueryResult
        )
        logger.info("Services complets chargés avec imports relatifs")
    except ImportError as e_rel:
        logger.warning(f"ImportError avec imports relatifs ({e_rel}). Utilisation des services de fallback.")
        # Utilisation des services de fallback
        from .services.fallback_services import (
            FallbackAnalysisService as AnalysisService,
            FallbackValidationService as ValidationService,
            FallbackFallacyService as FallacyService,
            FallbackFrameworkService as FrameworkService,
            FallbackLogicService as LogicService
        )
        
        # Classes de modèles simples pour fallback
        class SimpleRequest:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        AnalysisRequest = ValidationRequest = FallacyRequest = FrameworkRequest = SimpleRequest
        LogicBeliefSetRequest = LogicQueryRequest = LogicGenerateQueriesRequest = SimpleRequest
        LogicOptions = SimpleRequest
        
        class SimpleResponse:
            def __init__(self, **kwargs):
                self.data = kwargs
            def dict(self):
                return self.data
        
        AnalysisResponse = ValidationResponse = FallacyResponse = FrameworkResponse = SimpleResponse
        LogicBeliefSetResponse = LogicQueryResponse = LogicGenerateQueriesResponse = SimpleResponse
        LogicInterpretationResponse = LogicQueryResult = SimpleResponse
        ErrorResponse = SimpleResponse
        
        logger.info("Services de fallback chargés")

logger.info("--- Service import block (try-except) in app.py COMPLETED ---")
sys.stderr.flush()

# Configuration (l'initialisation de flask_app et app est faite plus haut)
flask_app.config['JSON_AS_ASCII'] = False  # Support des caractères UTF-8
flask_app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Initialisation lazy des services (à la demande pour éviter de bloquer le démarrage)
_analysis_service = None
_validation_service = None
_fallacy_service = None
_framework_service = None
_logic_service = None

def get_analysis_service():
    global _analysis_service
    if _analysis_service is None:
        logger.info("Initialisation du service d'analyse...")
        _analysis_service = AnalysisService()
    return _analysis_service

def get_validation_service():
    global _validation_service
    if _validation_service is None:
        logger.info("Initialisation du service de validation...")
        _validation_service = ValidationService()
    return _validation_service

def get_fallacy_service():
    global _fallacy_service
    if _fallacy_service is None:
        logger.info("Initialisation du service de détection de sophismes...")
        _fallacy_service = FallacyService()
    return _fallacy_service

def get_framework_service():
    global _framework_service
    if _framework_service is None:
        logger.info("Initialisation du service de framework...")
        _framework_service = FrameworkService()
    return _framework_service

def get_logic_service():
    global _logic_service
    if _logic_service is None:
        logger.info("Initialisation du service logique...")
        _logic_service = LogicService()
    return _logic_service


@flask_app.errorhandler(Exception) # MODIF: Utiliser flask_app
def handle_error(error):
    """Gestionnaire d'erreurs global."""
    logger.error(f"Erreur non gérée: {str(error)}", exc_info=True)
    return jsonify(ErrorResponse(
        error="Erreur interne du serveur",
        message=str(error),
        status_code=500
    ).dict()), 500


@flask_app.route('/api/health', methods=['GET']) # MODIF: Utiliser flask_app
def health_check():
    """Vérification de l'état de l'API."""
    logger.info("[HealthCheck] Endpoint /api/health CALLED") # Log d'entrée
    sys.stderr.flush() # S'assurer que le log est écrit immédiatement
    try:
        # Initialiser les services et vérifier leur état
        services_status = {}
        
        # Test du service d'analyse
        logger.info("[HealthCheck] Test du service d'analyse...")
        try:
            logger.info("[HealthCheck] Appel de get_analysis_service()...")
            analysis_svc = get_analysis_service()
            logger.info("[HealthCheck] get_analysis_service() terminé.")
            logger.info("[HealthCheck] Appel de analysis_svc.is_healthy()...")
            services_status["analysis"] = analysis_svc.is_healthy()
            logger.info(f"[HealthCheck] Service analysis.is_healthy(): {services_status['analysis']}")
        except Exception as e:
            logger.error(f"[HealthCheck] Erreur service analysis: {e}", exc_info=True)
            services_status["analysis"] = False
            
        # Test du service de validation
        logger.info("[HealthCheck] Test du service de validation...")
        try:
            logger.info("[HealthCheck] Appel de get_validation_service()...")
            validation_svc = get_validation_service()
            logger.info("[HealthCheck] get_validation_service() terminé.")
            if hasattr(validation_svc, 'is_healthy'):
                logger.info("[HealthCheck] Appel de validation_svc.is_healthy()...")
                services_status["validation"] = validation_svc.is_healthy()
                logger.info(f"[HealthCheck] Service validation.is_healthy(): {services_status['validation']}")
            else:
                logger.warning("[HealthCheck] Service validation n'a pas d'attribut 'is_healthy'.")
                services_status["validation"] = False # Ou une autre valeur par défaut
        except Exception as e:
            logger.error(f"[HealthCheck] Erreur service validation: {e}", exc_info=True)
            services_status["validation"] = False
            
        # Test du service de détection de sophismes
        logger.info("[HealthCheck] Test du service de détection de sophismes...")
        try:
            logger.info("[HealthCheck] Appel de get_fallacy_service()...")
            fallacy_svc = get_fallacy_service()
            logger.info("[HealthCheck] get_fallacy_service() terminé.")
            if hasattr(fallacy_svc, 'is_healthy'):
                logger.info("[HealthCheck] Appel de fallacy_svc.is_healthy()...")
                services_status["fallacy"] = fallacy_svc.is_healthy()
                logger.info(f"[HealthCheck] Service fallacy.is_healthy(): {services_status['fallacy']}")
            else:
                logger.warning("[HealthCheck] Service fallacy n'a pas d'attribut 'is_healthy'.")
                services_status["fallacy"] = False
        except Exception as e:
            logger.error(f"[HealthCheck] Erreur service fallacy: {e}", exc_info=True)
            services_status["fallacy"] = False
            
        # Test du service de framework
        logger.info("[HealthCheck] Test du service de framework...")
        try:
            logger.info("[HealthCheck] Appel de get_framework_service()...")
            framework_svc = get_framework_service()
            logger.info("[HealthCheck] get_framework_service() terminé.")
            if hasattr(framework_svc, 'is_healthy'):
                logger.info("[HealthCheck] Appel de framework_svc.is_healthy()...")
                services_status["framework"] = framework_svc.is_healthy()
                logger.info(f"[HealthCheck] Service framework.is_healthy(): {services_status['framework']}")
            else:
                logger.warning("[HealthCheck] Service framework n'a pas d'attribut 'is_healthy'.")
                services_status["framework"] = False
        except Exception as e:
            logger.error(f"[HealthCheck] Erreur service framework: {e}", exc_info=True)
            services_status["framework"] = False
            
        # Test du service de logique
        logger.info("[HealthCheck] Test du service de logique...")
        try:
            logger.info("[HealthCheck] Appel de get_logic_service()...")
            logic_svc = get_logic_service()
            logger.info("[HealthCheck] get_logic_service() terminé.")
            if hasattr(logic_svc, 'is_healthy'):
                logger.info("[HealthCheck] Appel de logic_svc.is_healthy()...")
                services_status["logic"] = logic_svc.is_healthy()
                logger.info(f"[HealthCheck] Service logic.is_healthy(): {services_status['logic']}")
            else:
                logger.warning("[HealthCheck] Service logic n'a pas d'attribut 'is_healthy'.")
                services_status["logic"] = False
        except Exception as e:
            logger.error(f"[HealthCheck] Erreur service logic: {e}", exc_info=True)
            services_status["logic"] = False
        
        return jsonify({
            "status": "healthy",
            "message": "API d'analyse argumentative opérationnelle",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "services": services_status
        })
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Erreur de health check: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

logger.info(f"--- Route /api/health defined. Rules: {[str(rule) for rule in flask_app.url_map.iter_rules(endpoint='health_check')]} ---")
sys.stderr.flush()

@flask_app.route('/api/analyze', methods=['POST']) # MODIF: Utiliser flask_app
def analyze_text():
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
        # LOGS ULTRA-VISIBLES ENDPOINT DEBUG V2
        print("[DEBUG] VERSION MODIFIEE - ENDPOINT /api/analyze APPELE V2")
        logger.critical("[DEBUG] ENDPOINT /api/analyze APPELE V2")
        try:
            data = request.get_json()
            logger.critical(f"[DEBUG] JSON recu: {data}")
        except HTTPException as he:
            # Intercepter les erreurs HTTP spécifiques de Werkzeug (ex: 400, 415)
            logger.warning(f"Erreur HTTP lors de la récupération du JSON: {str(he)}")
            return jsonify(ErrorResponse(
                error=he.name, # ex: Bad Request, Unsupported Media Type
                message=he.description,
                status_code=he.code
            ).dict()), he.code

        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            analysis_request = AnalysisRequest(**data)
        except Exception as e: # Pour les erreurs de validation Pydantic
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Analyse du texte
        result = asyncio.run(get_analysis_service().analyze_text(analysis_request))
        
        return jsonify(result.dict())
        
    except Exception as e: # Pour les autres erreurs inattendues
        logger.error(f"Erreur lors de l'analyse: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(
            error="Erreur d'analyse",
            message="Une erreur interne est survenue lors du traitement de votre requête.", # Message plus générique pour l'utilisateur
            status_code=500
        ).dict()), 500


@flask_app.route('/api/validate', methods=['POST']) # MODIF: Utiliser flask_app
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
        result = get_validation_service().validate_argument(validation_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de validation",
            message=str(e),
            status_code=500
        ).dict()), 500


@flask_app.route('/api/fallacies', methods=['POST']) # MODIF: Utiliser flask_app
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
        result = get_fallacy_service().detect_fallacies(fallacy_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de sophismes: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de détection",
            message=str(e),
            status_code=500
        ).dict()), 500


@flask_app.route('/api/framework', methods=['POST']) # MODIF: Utiliser flask_app
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
        result = get_framework_service().build_framework(framework_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la construction du framework: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de framework",
            message=str(e),
            status_code=500
        ).dict()), 500


@flask_app.route('/api/endpoints', methods=['GET']) # MODIF: Utiliser flask_app
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
        },
        "POST /api/logic/belief-set": {
            "description": "Conversion d'un texte en ensemble de croyances logiques",
            "parameters": {
                "text": "string (requis) - Texte à convertir",
                "logic_type": "string (requis) - Type de logique (propositional, first_order, modal)",
                "options": "object (optionnel) - Options de conversion"
            },
            "response": "Ensemble de croyances créé"
        },
        "POST /api/logic/query": {
            "description": "Exécution d'une requête logique",
            "parameters": {
                "belief_set_id": "string (requis) - ID de l'ensemble de croyances",
                "query": "string (requis) - Requête logique à exécuter",
                "logic_type": "string (requis) - Type de logique",
                "options": "object (optionnel) - Options d'exécution"
            },
            "response": "Résultat de la requête"
        },
        "POST /api/logic/generate-queries": {
            "description": "Génération de requêtes logiques pertinentes",
            "parameters": {
                "belief_set_id": "string (requis) - ID de l'ensemble de croyances",
                "text": "string (requis) - Texte source",
                "logic_type": "string (requis) - Type de logique",
                "options": "object (optionnel) - Options de génération"
            },
            "response": "Liste des requêtes générées"
        },
        "POST /api/logic/interpret": {
            "description": "Interprétation des résultats de requêtes logiques",
            "parameters": {
                "belief_set_id": "string (requis) - ID de l'ensemble de croyances",
                "logic_type": "string (requis) - Type de logique",
                "text": "string (requis) - Texte source",
                "queries": "array (requis) - Requêtes exécutées",
                "results": "array (requis) - Résultats des requêtes",
                "options": "object (optionnel) - Options d'interprétation"
            },
            "response": "Interprétation des résultats"
        }
    }
    
    return jsonify({
        "api_name": "API d'Analyse Argumentative",
        "version": "1.0.0",
        "endpoints": endpoints
    })


@flask_app.route('/api/logic/belief-set', methods=['POST']) # MODIF: Utiliser flask_app
def create_belief_set():
    """
    Convertit un texte en ensemble de croyances logiques.
    
    Body JSON:
    {
        "text": "Texte à convertir",
        "logic_type": "propositional",
        "options": {
            "include_explanation": true,
            "max_queries": 5
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
            belief_set_request = LogicBeliefSetRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Conversion du texte en ensemble de croyances
        result = get_logic_service().text_to_belief_set(belief_set_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion en ensemble de croyances: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de conversion",
            message=str(e),
            status_code=500
        ).dict()), 500


@flask_app.route('/api/logic/query', methods=['POST']) # MODIF: Utiliser flask_app
def execute_logic_query():
    """
    Exécute une requête logique sur un ensemble de croyances.
    
    Body JSON:
    {
        "belief_set_id": "id-de-l-ensemble-de-croyances",
        "query": "a => b",
        "logic_type": "propositional",
        "options": {
            "include_explanation": true
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
            query_request = LogicQueryRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Exécution de la requête
        result = get_logic_service().execute_query(query_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête logique: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur d'exécution",
            message=str(e),
            status_code=500
        ).dict()), 500


@flask_app.route('/api/logic/generate-queries', methods=['POST']) # MODIF: Utiliser flask_app
def generate_logic_queries():
    """
    Génère des requêtes logiques pertinentes.
    
    Body JSON:
    {
        "belief_set_id": "id-de-l-ensemble-de-croyances",
        "text": "Texte source",
        "logic_type": "propositional",
        "options": {
            "max_queries": 5
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
            generate_request = LogicGenerateQueriesRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Génération des requêtes
        result = get_logic_service().generate_queries(generate_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de requêtes logiques: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de génération",
            message=str(e),
            status_code=500
        ).dict()), 500


@flask_app.route('/api/logic/interpret', methods=['POST']) # MODIF: Utiliser flask_app
def interpret_logic_results():
    """
    Interprète les résultats de requêtes logiques.
    
    Body JSON:
    {
        "belief_set_id": "id-de-l-ensemble-de-croyances",
        "logic_type": "propositional",
        "text": "Texte source",
        "queries": ["a", "b", "a => b"],
        "results": [
            {
                "query": "a",
                "result": true,
                "formatted_result": "Tweety Result: Query 'a' is ACCEPTED (True)."
            },
            ...
        ],
        "options": {
            "include_explanation": true
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
        
        # Extraction des données
        try:
            belief_set_id = data.get("belief_set_id")
            logic_type = data.get("logic_type")
            text = data.get("text")
            queries = data.get("queries", [])
            results_data = data.get("results", [])
            options_data = data.get("options", {})
            
            if not belief_set_id or not logic_type or not text or not queries or not results_data:
                return jsonify(ErrorResponse(
                    error="Données manquantes",
                    message="Les champs belief_set_id, logic_type, text, queries et results sont requis",
                    status_code=400
                ).dict()), 400
            
            # Conversion des résultats en objets LogicQueryResult
            # Utilisation de l'import global de LogicQueryResult (style HEAD)
            results = [LogicQueryResult(**result) for result in results_data]
            
            # Conversion des options en objet LogicOptions
            # Utilisation de l'import global de LogicOptions (style HEAD)
            options = LogicOptions(**options_data) if options_data else None
            
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Interprétation des résultats
        result = get_logic_service().interpret_results(
            belief_set_id=belief_set_id,
            logic_type=logic_type,
            text=text,
            queries=queries,
            results=results,
            options=options
        )
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'interprétation des résultats logiques: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur d'interprétation",
            message=str(e),
            status_code=500
        ).dict()), 500

# Ajout des routes de pr-student-1
@flask_app.route('/', methods=['GET']) # MODIF: Utiliser flask_app
def index():
    """Redirection vers la documentation de l'API."""
    return redirect('/api/endpoints')

@flask_app.route('/favicon.ico', methods=['GET']) # MODIF: Utiliser flask_app
def favicon():
    """Gestion du favicon."""
    return '', 204  # No content

try:
    # Log des routes enregistrées par Flask pour le débogage
    # Cela doit être fait après que toutes les routes @flask_app.route() ont été déclarées.
    # Et avant que l'application ne soit potentiellement exécutée si __name__ == '__main__'
    # (bien que dans notre cas, Uvicorn lance 'app', donc __main__ n'est pas directement exécuté par Uvicorn)
    
    # Pour obtenir les routes, il faut un contexte d'application ou de test.
    # Le plus simple ici est de le faire avant la section __main__.
    # Cependant, pour être sûr que cela s'exécute lorsque le module est chargé par Uvicorn,
    # nous le plaçons à la fin du scope global du module.
    
    # Créer une chaîne de caractères listant les règles de routage
    rules_string = []
    for rule in flask_app.url_map.iter_rules():
        rules_string.append(f"Endpoint: {rule.endpoint}, Methods: {','.join(rule.methods)}, Path: {str(rule)}")
    logger.info(f"--- Flask App Registered Routes ---\n{os.linesep.join(rules_string)}\n--- End of Flask Routes ---")
    sys.stderr.flush()
except Exception as e_routes:
    logger.error(f"Erreur lors de la tentative de lister les routes Flask: {e_routes}", exc_info=True)
    sys.stderr.flush()


if __name__ == '__main__':
    # Configuration des arguments de ligne de commande
    parser = argparse.ArgumentParser(description='API Flask pour l\'analyse argumentative')
    parser.add_argument('--port', type=int,
                       default=int(os.environ.get('PORT', 5003)),
                       help='Port d\'écoute du serveur (défaut: 5003)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Adresse d\'écoute du serveur (défaut: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true',
                       default=os.environ.get('DEBUG', 'False').lower() == 'true',
                       help='Mode debug (défaut: False)')
    
    args = parser.parse_args()
    
    logger.info(f"Démarrage de l'API sur {args.host}:{args.port}")
    logger.info(f"Mode debug: {args.debug}")
    
    # MODIF: Uvicorn est maintenant responsable du lancement, donc app.run n'est plus nécessaire ici.
    # Si on lance ce script directement, on pourrait utiliser uvicorn.run(app, ...)
    # Mais comme c'est BackendManager qui lance Uvicorn, on commente cette section.
    # import uvicorn
    # uvicorn.run(app, host=args.host, port=args.port, log_level="info" if not args.debug else "debug")
    logger.info("L'application est prête à être servie par Uvicorn via BackendManager.")
    logger.info("Pour lancer directement: uvicorn argumentation_analysis.services.web_api.app:app --host <host> --port <port>")