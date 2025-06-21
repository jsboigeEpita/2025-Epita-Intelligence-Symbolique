#!/usr/bin/env python3
"""
Interface Web pour l'Analyse Argumentative EPITA (Version Starlette)
=====================================================================

Application Starlette pure pour l'interface web du système d'analyse argumentative.
Fournit une interface utilisateur pour soumettre des textes et visualiser les résultats d'analyse.
Cette version élimine Flask pour une pile ASGI native plus simple et robuste.

Version: 2.0.0
Auteur: Intelligence Symbolique EPITA
Date: 16/06/2025
"""

import asyncio
import json
import logging
import os
import uuid
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# --- Imports ASGI/Starlette ---
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# --- Activation de l'environnement et imports du projet ---
try:
    from scripts.core.auto_env import ensure_env
    ensure_env()
except ImportError:
    try:
        import sys
        project_root = Path(__file__).resolve().parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from scripts.core.auto_env import ensure_env
        ensure_env()
    except ImportError:
        print("[WARNING] Auto-env non disponible, environnement non activé automatiquement")

# --- Imports des services de l'application ---
ServiceManager = None
SERVICE_MANAGER_AVAILABLE = False
try:
    from argumentation_analysis.orchestration.service_manager import ServiceManager
    SERVICE_MANAGER_AVAILABLE = True
    logging.info("ServiceManager importé avec succès")
except ImportError as e:
    logging.error(f"ServiceManager non disponible: {e}")
    # Cette dépendance est critique, on lève une exception si elle manque.
    raise ImportError(f"ServiceManager requis mais non disponible: {e}")

# Importation du gestionnaire de modèles NLP
try:
    from argumentation_analysis.agents.tools.analysis.enhanced.nlp_model_manager import nlp_model_manager
    NLP_MODELS_AVAILABLE = True
    logging.info("NLPModelManager importé avec succès.")
except ImportError as e:
    logging.warning(f"NLPModelManager non disponible: {e}")
    nlp_model_manager = None
    NLP_MODELS_AVAILABLE = False


# --- Configuration du Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [StarletteApp] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Configuration des chemins ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_FILES_DIR = PROJECT_ROOT / "services" / "web_api" / "interface-web-argumentative" / "build"
RESULTS_DIR = PROJECT_ROOT / "results"

# ==============================================================================
# CYCLE DE VIE DE L'APPLICATION (LIFESPAN)
# ==============================================================================

@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Gestionnaire de cycle de vie. S'exécute au démarrage et à l'arrêt de l'application.
    C'est ici qu'on initialise et qu'on nettoie les ressources partagées comme le ServiceManager.
    """
    logger.info("LIFESPAN: Démarrage de l'application...")
    
    # 1. Initialiser les conteneurs d'état
    app.state.service_manager = None
    app.state.nlp_model_manager = None

    # 2. Créer les instances des gestionnaires
    logger.info("Création des instances de ServiceManager et NLPModelManager.")
    service_manager_instance = ServiceManager(config={
        'enable_hierarchical': True,
        'enable_specialized_orchestrators': True,
        'enable_communication_middleware': True,
        'save_results': True,
        'results_dir': str(RESULTS_DIR)
    })
    app.state.service_manager = service_manager_instance

    if NLP_MODELS_AVAILABLE:
        app.state.nlp_model_manager = nlp_model_manager
    else:
        logger.warning("NLPModelManager non initialisé car non disponible.")

    # 3. Lancer les initialisations asynchrones en parallèle
    logger.info("Démarrage des initialisations asynchrones (ServiceManager et NLP Models)...")
    init_tasks = []
    
    # Tâche pour initialiser le ServiceManager
    async def init_service_manager():
        try:
            await service_manager_instance.initialize()
            logger.info("ServiceManager initialisé avec succès.")
        except Exception as e:
            logger.error(f"Erreur critique lors de l'initialisation du ServiceManager: {e}", exc_info=True)
            app.state.service_manager = None # Marquer comme non disponible
            logger.warning("ServiceManager marqué comme indisponible.")
            
    init_tasks.append(init_service_manager())

    # Tâche pour charger les modèles NLP
    if app.state.nlp_model_manager:
        logger.warning("NLP model loading is temporarily disabled for testing.")
        # # Exécuter la méthode de chargement synchrone dans un thread pour ne pas bloquer la boucle asyncio
        # loop = asyncio.get_running_loop()
        # init_tasks.append(loop.run_in_executor(
        #     None, app.state.nlp_model_manager.load_models_sync
        # ))

    # Exécuter les tâches en parallèle
    await asyncio.gather(*init_tasks)

    logger.info("LIFESPAN: Initialisation terminée, l'application est prête.")
    
    yield  # L'application s'exécute ici
    
    logger.info("LIFESPAN: Arrêt de l'application...")
    if hasattr(app.state, 'service_manager') and app.state.service_manager:
        # Logique de nettoyage si nécessaire (ex: await app.state.service_manager.cleanup())
        pass
    logger.info("LIFESPAN: Nettoyage terminé.")

# ==============================================================================
# DÉFINITION DES ROUTES DE L'API
# ==============================================================================

async def status_endpoint(request: Request):
    """Route pour vérifier le statut des services."""
    service_manager = getattr(request.app.state, 'service_manager', None)
    nlp_manager = getattr(request.app.state, 'nlp_model_manager', None)

    sm_status = 'active' if service_manager else 'unavailable'
    
    nlp_status = 'unavailable'
    if nlp_manager:
        nlp_status = 'loaded' if nlp_manager.are_models_loaded() else 'initializing'

    # Le statut global est 'initializing' si un service majeur est en cours de chargement
    app_status = 'operational'
    if sm_status != 'active' or nlp_status == 'initializing':
        app_status = 'initializing'
    if sm_status == 'unavailable' and nlp_status != 'initializing':
        app_status = 'degraded'


    status_info = {
        'status': app_status,
        'timestamp': datetime.now().isoformat(),
        'services': {
            'service_manager': sm_status,
            'nlp_models': nlp_status,
        },
        'webapp': {
            'version': '2.0.0',
            'framework': 'Starlette'
        }
    }
    return JSONResponse(status_info)

async def analyze_endpoint(request: Request):
    """Route pour l'analyse de texte."""
    service_manager = request.app.state.service_manager
    if not service_manager:
        return JSONResponse({'error': 'Le service d\'analyse est indisponible.'}, status_code=503)

    try:
        data = await request.json()
        text = data.get('text', '').strip()
        analysis_type = data.get('analysis_type', 'unified_analysis')
        options = data.get('options', {})

        if not text:
            return JSONResponse({'error': 'Texte vide fourni'}, status_code=400)
        
        if len(text) > 10000:
             return JSONResponse({'error': 'Texte trop long (max 10000 caractères)'}, status_code=400)

        analysis_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        logger.info(f"Analyse {analysis_id} démarrée - Type: {analysis_type}")

        # Ajout d'un timeout pour éviter que le serveur ne gèle indéfiniment
        # si le service d'analyse est bloqué.
        timeout_seconds = 25.0
        try:
            result_data = await asyncio.wait_for(
                service_manager.analyze_text(text, analysis_type, options),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"L'analyse {analysis_id} a dépassé le timeout de {timeout_seconds}s.")
            return JSONResponse({
                'error': f'L\'analyse a dépassé le temps imparti de {timeout_seconds} secondes.'
            }, status_code=504) # 504 Gateway Timeout
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Le formatage des résultats reste le même
        formatted_result = {
            'analysis_id': analysis_id,
            'status': 'success',
            'timestamp': start_time.isoformat(),
            'results': result_data.get('results', {}),
            'metadata': {
                'duration': duration,
            }
        }
        logger.info(f"Analyse {analysis_id} terminée avec succès - Durée: {duration:.2f}s")
        return JSONResponse(formatted_result)

    except json.JSONDecodeError:
        return JSONResponse({'error': 'Corps de la requête JSON invalide'}, status_code=400)
    except Exception as e:
        logger.error(f"Erreur inattendue dans /api/analyze: {e}", exc_info=True)
        return JSONResponse({'error': f'Erreur interne du serveur: {e}'}, status_code=500)

async def examples_endpoint(request: Request):
    """Route pour obtenir des exemples de textes d'analyse."""
    examples = [
        {'title': 'Logique Propositionnelle', 'text': 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.', 'type': 'propositional'},
        {'title': 'Argumentation Complexe', 'text': 'L\'IA est une opportunité et un défi. Elle peut révolutionner la médecine, mais pose des questions éthiques.', 'type': 'unified_analysis'},
    ]
    return JSONResponse({'examples': examples})

async def framework_analyze_endpoint(request: Request):
    """Route pour l'analyse d'un A.F. de Dung."""
    service_manager = request.app.state.service_manager
    if not service_manager:
        return JSONResponse({'error': 'Le service d\'analyse est indisponible.'}, status_code=503)

    try:
        data = await request.json()
        arguments = data.get("arguments")
        attacks = data.get("attacks")
        options = data.get("options", {})

        if not arguments or not isinstance(arguments, list) or not isinstance(attacks, list):
            return JSONResponse({'error': 'Les arguments et les attaques sont requis et doivent être des listes.'}, status_code=400)

        # Appel direct de la méthode du service manager.
        # Si la méthode n'existe pas, une AttributeError sera levée, ce qui est correct.
        result_data = await service_manager.analyze_dung_framework(arguments=arguments, attacks=attacks, options=options)
        
        return JSONResponse(result_data)

    except json.JSONDecodeError:
        return JSONResponse({'error': 'Corps de la requête JSON invalide'}, status_code=400)
    except AttributeError as e:
        logger.error(f"La méthode requise est manquante dans le ServiceManager: {e}", exc_info=True)
        return JSONResponse({'error': f'Fonctionnalité non implémentée sur le serveur: {e}'}, status_code=501)
    except Exception as e:
        logger.error(f"Erreur inattendue dans /api/v1/framework/analyze: {e}", exc_info=True)
        return JSONResponse({'error': f'Erreur interne du serveur: {e}'}, status_code=500)

# ==============================================================================
# CONFIGURATION DE L'APPLICATION STARLETTE
# ==============================================================================

# --- Définition des Routes ---
# On combine les routes de l'API et le service des fichiers statiques.
routes = [
    Route('/api/status', endpoint=status_endpoint, methods=['GET']),
    Route('/api/analyze', endpoint=analyze_endpoint, methods=['POST']),
    Route('/api/examples', endpoint=examples_endpoint, methods=['GET']),
    Route('/api/v1/framework/analyze', endpoint=framework_analyze_endpoint, methods=['POST']),
    # Le Mount pour les fichiers statiques doit gérer le service de l'application React,
    # y compris la route index.html pour le chemin racine.
    Mount('/', app=StaticFiles(directory=str(STATIC_FILES_DIR), html=True), name="static_assets")
]

# --- Middlewares ---
# Configuration de CORS pour autoriser les requêtes cross-origin (utile pour les tests et le dev local)
middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
]

# --- Création de l'Application ---
app = Starlette(
    debug=True, 
    routes=routes,
    middleware=middleware,
    lifespan=lifespan
)

# ==============================================================================
# POINT D'ENTRÉE POUR LE DÉMARRAGE DIRECT
# ==============================================================================

if __name__ == '__main__':
    import uvicorn
    
    parser = argparse.ArgumentParser(description="Lance le serveur web Starlette.")
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5003)), help='Port pour exécuter le serveur.')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Hôte sur lequel écouter.')
    args = parser.parse_args()

    logger.info(f"Démarrage du serveur Uvicorn sur http://{args.host}:{args.port}")
    
    uvicorn.run(
        "interface_web.app:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=True
    )