# libs/web_api/routes/logic_routes.py
from flask import Blueprint, request, jsonify
import logging
from typing import Optional # Ajout de l'import manquant

# Import des services et modèles nécessaires
# Assurez-vous que les chemins d'importation sont corrects par rapport à la structure du projet
# et à l'emplacement de ce fichier blueprint.
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest
)
# Les modèles de réponse pour la logique sont dans un chemin différent
from services.web_api.models.response_models import (
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse
)
from libs.web_api.models.response_models import ErrorResponse # Ajusté pour ErrorResponse
from pydantic import ValidationError # Import manquant pour la gestion d'erreur

logger = logging.getLogger("WebAPI.LogicRoutes")

# Initialiser le service logique.
# Idéalement, l'instance du service devrait être passée ou accessible globalement
# plutôt que d'être recréée ici ou importée directement si elle est déjà instanciée dans app.py.
# Pour l'instant, on suppose qu'on peut l'importer et l'utiliser si elle est un singleton
# ou si on en crée une nouvelle instance ici (ce qui peut être problématique pour l'état partagé).
# Pour simplifier et correspondre à la structure de app.py, nous allons supposer
# que logic_service est accessible d'une manière ou d'une autre.
# Le plus simple serait que app.py passe l'instance de logic_service lors de l'enregistrement du blueprint,
# ou que logic_service soit un singleton accessible.
# Pour l'instant, nous allons ré-importer et instancier, ce qui n'est pas idéal pour les tests avec mocks.
# Une meilleure approche serait d'utiliser current_app.logic_service si enregistré sur l'app.

# Tentative d'importer l'instance de app.py - cela crée une dépendance circulaire si mal géré.
# Mieux : le service est injecté ou le blueprint est configuré avec.
# Pour cette étape, je vais supposer que logic_service est déjà initialisé dans le contexte de l'app
# et que nous pouvons y accéder ou le ré-instancier si nécessaire.
# Le fichier de test patche 'libs.web_api.app.logic_service'.
# Donc, le blueprint doit utiliser CETTE instance.
# Cela signifie que le blueprint doit être configuré AVEC l'instance de logic_service de app.py.

# Ne pas importer logic_service ici pour éviter l'import circulaire.
# Il sera importé dans chaque fonction de route.

logic_bp = Blueprint('logic_api', __name__, url_prefix='/api/logic')

# La fonction initialize_logic_blueprint n'est plus nécessaire.

@logic_bp.route('/belief-set', methods=['POST'])
def logic_text_to_belief_set():
    """Convertit un texte en ensemble de croyances logiques."""
    from libs.web_api.app import logic_service as app_logic_service # Importation au moment de l'exécution
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
            
        result = app_logic_service.text_to_belief_set(req_model) # Utiliser app_logic_service
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion en ensemble de croyances: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de conversion", message=str(e), status_code=500).dict()), 500

@logic_bp.route('/query', methods=['POST'])
def logic_execute_query():
    """Exécute une requête logique sur un ensemble de croyances."""
    from libs.web_api.app import logic_service as app_logic_service # Importation au moment de l'exécution
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
            
        result = app_logic_service.execute_query(req_model) # Utiliser app_logic_service
        return jsonify(result.dict())

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête logique: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur d'exécution de requête", message=str(e), status_code=500).dict()), 500

@logic_bp.route('/generate-queries', methods=['POST'])
def logic_generate_queries():
    """Génère des requêtes logiques pertinentes."""
    from libs.web_api.app import logic_service as app_logic_service # Importation au moment de l'exécution
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
            
        result = app_logic_service.generate_queries(req_model) # Utiliser app_logic_service
        return jsonify(result.dict())

    except Exception as e:
        logger.error(f"Erreur lors de la génération de requêtes logiques: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(error="Erreur de génération de requêtes", message=str(e), status_code=500).dict()), 500