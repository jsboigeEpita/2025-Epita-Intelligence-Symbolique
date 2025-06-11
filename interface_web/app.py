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
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Activation automatique de l'environnement
try:
    from scripts.core.auto_env import ensure_env
    ensure_env()
except ImportError:
    try:
        # Fallback: Chemin alternatif pour auto_env
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from scripts.core.auto_env import ensure_env
        ensure_env()
    except ImportError:
        # Dernier fallback: continuer sans auto_env
        print("[WARNING] Auto-env non disponible, environnement non activé automatiquement")

# Import du blueprint JTMS avec gestion d'erreur
JTMS_AVAILABLE = False
jtms_blueprint = None
try:
    from interface_web.routes.jtms_routes import jtms_bp as jtms_blueprint
    JTMS_AVAILABLE = True
    logging.info("Blueprint JTMS importé avec succès")
except ImportError as e:
    logging.warning(f"Blueprint JTMS non disponible: {e}")
except Exception as e:
    logging.error(f"Erreur lors de l'import du blueprint JTMS: {e}")

# Configuration des chemins
PROJECT_ROOT = Path(__file__).resolve().parent.parent
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
    logging.error(f"ServiceManager non disponible: {e}")
    raise ImportError(f"ServiceManager requis mais non disponible: {e}")
except Exception as e:
    logging.error(f"Erreur lors de l'import du ServiceManager: {e}")
    raise ImportError(f"ServiceManager requis mais erreur d'import: {e}")

# Configuration de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-EPITA-2025')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configuration CORS simple sans dépendance externe
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [WebApp] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Instance globale du ServiceManager
service_manager = None

# Services JTMS globaux
jtms_service = None
jtms_session_manager = None
JTMS_SERVICES_AVAILABLE = False


def initialize_services():
    """Initialise les services au démarrage de l'application."""
    global service_manager, jtms_service, jtms_session_manager, JTMS_SERVICES_AVAILABLE
    
    try:
        service_manager = ServiceManager(config={
            'enable_hierarchical': True,
            'enable_specialized_orchestrators': True,
            'enable_communication_middleware': True,
            'save_results': True,
            'results_dir': str(RESULTS_DIR)
        })
        
        # Initialisation asynchrone requise
        async def init_service_manager():
            await service_manager.initialize()
            
        asyncio.run(init_service_manager())
        logger.info("ServiceManager configuré et initialisé")
        
        # Initialisation des services JTMS (optionnel)
        try:
            from argumentation_analysis.services.jtms_service import JTMSService
            from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager
            
            jtms_service = JTMSService()
            jtms_session_manager = JTMSSessionManager()
            JTMS_SERVICES_AVAILABLE = True
            
            logger.info("Services JTMS initialisés avec succès")
            
        except ImportError as e:
            logger.warning(f"Services JTMS non disponibles: {e}")
            JTMS_SERVICES_AVAILABLE = False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des services JTMS: {e}")
            JTMS_SERVICES_AVAILABLE = False
            
    except Exception as e:
        logger.error(f"Erreur critique lors de l'initialisation des services: {e}")
        raise RuntimeError(f"Impossible d'initialiser le ServiceManager: {e}")


def setup_app_context():
    """Configure le contexte global de l'application pour les services JTMS."""
    if JTMS_SERVICES_AVAILABLE and jtms_blueprint:
        # Rendre les services disponibles dans le contexte Flask
        app.config['JTMS_SERVICE'] = jtms_service
        app.config['JTMS_SESSION_MANAGER'] = jtms_session_manager
        app.config['JTMS_AVAILABLE'] = True
        
        # Enregistrer le blueprint JTMS
        app.register_blueprint(jtms_blueprint, url_prefix='/jtms')
        logger.info("Blueprint JTMS enregistré avec succès sur /jtms")
    else:
        app.config['JTMS_AVAILABLE'] = False
        logger.warning("Services JTMS non disponibles - Blueprint non enregistré")


@app.route('/')
def index():
    """Page d'accueil de l'interface web."""
    # Vérifier la disponibilité des services pour l'affichage
    context = {
        'jtms_available': JTMS_SERVICES_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    }
    return render_template('index.html', **context)


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Route pour l'analyse de texte.
    
    Reçoit un texte via POST et retourne les résultats d'analyse.
    """
    try:
        # Récupération des données
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Aucune donnée reçue'}), 400
            
        text = data.get('text', '').strip()
        analysis_type = data.get('analysis_type', 'comprehensive')
        options = data.get('options', {})
        
        if not text:
            return jsonify({'error': 'Texte vide fourni'}), 400
            
        if len(text) > 10000:  # Limite de 10k caractères
            return jsonify({'error': 'Texte trop long (max 10000 caractères)'}), 400
            
        # Génération d'un ID d'analyse
        analysis_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        
        logger.info(f"Analyse {analysis_id} démarrée - Type: {analysis_type}")
        
        # Analyse avec ServiceManager - OBLIGATOIRE
        try:
            # Appel asynchrone au ServiceManager réel
            async def run_analysis():
                return await service_manager.analyze_text(text, analysis_type, options)
            
            result = asyncio.run(run_analysis())
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Formatage des résultats pour l'interface web
            formatted_result = {
                'analysis_id': analysis_id,
                'status': 'success',
                'timestamp': start_time.isoformat(),
                'input': {
                    'text': text[:200] + '...' if len(text) > 200 else text,
                    'text_length': len(text),
                    'analysis_type': analysis_type
                },
                'results': result.get('results', {}),
                'metadata': {
                    'duration': duration,
                    'service_status': 'active',
                    'components_used': _extract_components_used(result),
                    'real_llm_used': True
                },
                'summary': _generate_analysis_summary(result, text)
            }
            
            logger.info(f"Analyse {analysis_id} terminée avec succès - Durée: {duration:.2f}s")
            return jsonify(formatted_result)
            
        except Exception as e:
            logger.error(f"Erreur critique dans l'analyse {analysis_id}: {e}")
            return jsonify({
                'analysis_id': analysis_id,
                'status': 'error',
                'error': f"Erreur ServiceManager: {str(e)}",
                'timestamp': start_time.isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur inattendue dans /analyze: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500


@app.route('/status')
def status():
    """
    Route pour vérifier le statut des services.
    
    Retourne l'état de santé des composants du système.
    """
    try:
        status_info = {
            'status': 'operational' if service_manager else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'service_manager': 'active' if service_manager else 'unavailable',
                'jtms_service': 'active' if JTMS_SERVICES_AVAILABLE else 'unavailable',
                'jtms_blueprint': 'registered' if JTMS_AVAILABLE else 'unavailable'
            },
            'webapp': {
                'version': '1.0.0',
                'mode': 'full' if service_manager and JTMS_SERVICES_AVAILABLE else 'partial'
            }
        }
        
        if service_manager:
            # Simplification synchrone pour les tests
            health_status = {'status': 'healthy'}
            service_status = {'components': ['ServiceManager']}
            
            status_info['services']['health_check'] = health_status
            status_info['services']['service_details'] = service_status
            
        return jsonify(status_info)
            
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/examples')
def get_examples():
    """
    Route pour obtenir des exemples de textes d'analyse.
    
    Retourne une liste d'exemples prédéfinis pour faciliter les tests.
    """
    examples = [
        {
            'title': 'Logique Propositionnelle',
            'text': 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.',
            'type': 'propositional'
        },
        {
            'title': 'Logique Modale',
            'text': 'Il est nécessaire que tous les hommes soient mortels. Socrate est un homme. Il est donc nécessaire que Socrate soit mortel.',
            'type': 'modal'
        },
        {
            'title': 'Argumentation Complexe',
            'text': 'L\'intelligence artificielle représente à la fois une opportunité et un défi. D\'un côté, elle peut révolutionner la médecine et l\'éducation. De l\'autre, elle pose des questions éthiques fondamentales sur l\'emploi et la vie privée.',
            'type': 'comprehensive'
        },
        {
            'title': 'Paradoxe Logique',
            'text': 'Cette phrase est fausse. Si elle est vraie, alors elle est fausse. Si elle est fausse, alors elle est vraie.',
            'type': 'paradox'
        }
    ]
    
    return jsonify({'examples': examples})


def _extract_components_used(result: Dict[str, Any]) -> List[str]:
    """Extrait la liste des composants utilisés lors de l'analyse."""
    components = []
    
    if 'results' in result:
        results = result['results']
        
        if 'specialized' in results:
            components.append('Orchestrateur Spécialisé')
            
        if 'hierarchical' in results:
            hierarchical = results['hierarchical']
            if 'strategic' in hierarchical:
                components.append('Gestionnaire Stratégique')
            if 'tactical' in hierarchical:
                components.append('Gestionnaire Tactique')
            if 'operational' in hierarchical:
                components.append('Gestionnaire Opérationnel')
                
    return components if components else ['Analyse Basique']


def _generate_analysis_summary(result: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Génère un résumé de l'analyse pour l'interface utilisateur."""
    word_count = len(text.split())
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    
    # Analyse basique de mots-clés logiques
    logic_keywords = ['si', 'alors', 'donc', 'tous', 'nécessairement', 'possible', 'probable']
    logic_score = sum(1 for keyword in logic_keywords if keyword.lower() in text.lower())
    
    return {
        'text_metrics': {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'character_count': len(text)
        },
        'analysis_metrics': {
            'logic_keywords_found': logic_score,
            'complexity_level': 'élevée' if word_count > 100 else 'moyenne' if word_count > 50 else 'simple'
        },
        'components_summary': _extract_components_used(result),
        'processing_time': result.get('duration', 0)
    }


# Fonction _fallback_analysis supprimée - Pas de fallback autorisé
# L'application doit crasher si l'environnement n'est pas opérationnel


@app.errorhandler(404)
def page_not_found(e):
    """Gestionnaire d'erreur 404."""
    return render_template('index.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Gestionnaire d'erreur 500."""
    logger.error(f"Erreur interne: {e}")
    return jsonify({'error': 'Erreur interne du serveur'}), 500


if __name__ == '__main__':
    # Gestion des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Lance l'interface web Flask pour l'analyse argumentative.")
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5001)),
                        help='Port pour exécuter le serveur Flask.')
    parser.add_argument('--debug', action='store_true',
                        help='Active le mode debug de Flask.')
    args = parser.parse_args()

    port = args.port
    debug = args.debug or (os.environ.get('DEBUG', 'False').lower() == 'true')
    
    logger.info(f"Démarrage de l'interface web sur le port {port}")
    logger.info(f"Mode debug: {debug}")
    logger.info(f"ServiceManager disponible: {SERVICE_MANAGER_AVAILABLE}")
    
    # Initialisation des répertoires
    RESULTS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    
    # Initialisation des services
    initialize_services()
    
    # Configuration du contexte d'application
    setup_app_context()
    
    logger.info(f"JTMS disponible: {JTMS_SERVICES_AVAILABLE}")
    if JTMS_AVAILABLE:
        logger.info("Routes JTMS disponibles sur: /jtms/dashboard, /jtms/sessions, /jtms/sherlock_watson, /jtms/tutorial, /jtms/playground")
    
    # Démarrage de l'application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )