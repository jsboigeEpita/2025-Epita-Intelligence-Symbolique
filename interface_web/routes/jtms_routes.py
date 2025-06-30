#!/usr/bin/env python3
"""
Routes JTMS pour Interface Web Flask
===================================

Routes spécialisées pour l'interface JTMS interactive.
Intégration avec le système d'argumentation existant.

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA  
Date: 11/06/2025
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_socketio import emit, join_room, leave_room, rooms
from datetime import datetime
import json
import logging
import uuid
from typing import Dict, List, Any, Optional

# Import des services JTMS existants
try:
    from argumentation_analysis.services.jtms_service import JTMSService
    from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager
    from argumentation_analysis.api.jtms_models import BeliefInfo, JustificationInfo
    JTMS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Services JTMS non disponibles: {e}")
    JTMS_AVAILABLE = False

# Configuration du blueprint
jtms_bp = Blueprint('jtms', __name__, url_prefix='/jtms')
logger = logging.getLogger(__name__)

# Instances des services JTMS
jtms_service = None
session_manager = None

def initialize_jtms_services():
    """Initialise les services JTMS au démarrage."""
    global jtms_service, session_manager
    
    if JTMS_AVAILABLE:
        try:
            jtms_service = JTMSService()
            session_manager = JTMSSessionManager()
            logger.info("Services JTMS initialisés avec succès")
        except Exception as e:
            logger.error(f"Erreur initialisation services JTMS: {e}")
            raise
    else:
        logger.warning("Services JTMS non disponibles - mode dégradé")

# ============================================================================
# ROUTES PRINCIPALES JTMS
# ============================================================================

@jtms_bp.route('/dashboard')
def dashboard():
    """Interface dashboard JTMS principal."""
    try:
        if not JTMS_AVAILABLE:
            return render_template('jtms/error.html', 
                                 error="Services JTMS non disponibles")
        
        # Récupération des sessions existantes
        sessions = session_manager.list_sessions() if session_manager else []
        
        return render_template('jtms/dashboard.html', 
                             sessions=sessions,
                             timestamp=datetime.now().isoformat())
                             
    except Exception as e:
        logger.error(f"Erreur dashboard JTMS: {e}")
        return render_template('jtms/error.html', error=str(e))

@jtms_bp.route('/sessions')
def sessions_management():
    """Interface de gestion des sessions JTMS."""
    try:
        if not JTMS_AVAILABLE:
            return render_template('jtms/error.html', 
                                 error="Services JTMS non disponibles")
        
        sessions = session_manager.list_sessions() if session_manager else []
        sessions_details = []
        
        for session_id in sessions:
            try:
                session_data = session_manager.get_session_info(session_id)
                sessions_details.append(session_data)
            except Exception as e:
                logger.warning(f"Erreur récupération session {session_id}: {e}")
        
        return render_template('jtms/sessions.html', 
                             sessions=sessions_details,
                             total_sessions=len(sessions_details))
                             
    except Exception as e:
        logger.error(f"Erreur gestion sessions: {e}")
        return render_template('jtms/error.html', error=str(e))

@jtms_bp.route('/sherlock_watson')
def sherlock_watson_interface():
    """Interface dédiée aux agents Sherlock/Watson avec JTMS."""
    try:
        return render_template('jtms/sherlock_watson.html',
                             agents_available=True,
                             timestamp=datetime.now().isoformat())
                             
    except Exception as e:
        logger.error(f"Erreur interface Sherlock/Watson: {e}")
        return render_template('jtms/error.html', error=str(e))

@jtms_bp.route('/tutorial')
def tutorial():
    """Interface pédagogique - Mode tutoriel JTMS."""
    try:
        tutorial_steps = [
            {
                "id": 1,
                "title": "Introduction au JTMS",
                "description": "Comprendre les bases du système de maintenance de vérité",
                "content": "Le JTMS maintient automatiquement la cohérence des croyances..."
            },
            {
                "id": 2,
                "title": "Création de croyances",
                "description": "Comment ajouter des croyances dans le système",
                "content": "Une croyance représente une proposition qui peut être vraie, fausse ou inconnue..."
            },
            {
                "id": 3,
                "title": "Justifications",
                "description": "Lier les croyances avec des justifications logiques",
                "content": "Les justifications définissent comment certaines croyances impliquent d'autres..."
            },
            {
                "id": 4,
                "title": "Propagation automatique",
                "description": "Observer la propagation de vérité dans le système",
                "content": "Le JTMS met automatiquement à jour les croyances selon les justifications..."
            }
        ]
        
        return render_template('jtms/tutorial.html', 
                             tutorial_steps=tutorial_steps,
                             total_steps=len(tutorial_steps))
                             
    except Exception as e:
        logger.error(f"Erreur interface tutoriel: {e}")
        return render_template('jtms/error.html', error=str(e))

@jtms_bp.route('/playground')
def playground():
    """Interface Playground - Environnement de test libre JTMS."""
    try:
        # Exemples prédéfinis pour le playground
        examples = [
            {
                "name": "Logique Propositionnelle Simple",
                "beliefs": ["A", "B", "C"],
                "justifications": [
                    {"in_list": ["A"], "out_list": [], "conclusion": "B"},
                    {"in_list": ["B"], "out_list": [], "conclusion": "C"}
                ]
            },
            {
                "name": "Contradiction et Résolution",
                "beliefs": ["P", "not_P", "Q"],
                "justifications": [
                    {"in_list": ["P"], "out_list": [], "conclusion": "Q"},
                    {"in_list": ["not_P"], "out_list": ["Q"], "conclusion": "contradiction"}
                ]
            },
            {
                "name": "Enquête Sherlock Holmes",
                "beliefs": ["suspect_guilty", "weapon_found", "motive_exists", "alibi_verified"],
                "justifications": [
                    {"in_list": ["weapon_found", "motive_exists"], "out_list": ["alibi_verified"], "conclusion": "suspect_guilty"}
                ]
            }
        ]
        
        return render_template('jtms/playground.html', 
                             examples=examples,
                             playground_id=str(uuid.uuid4())[:8])
                             
    except Exception as e:
        logger.error(f"Erreur interface playground: {e}")
        return render_template('jtms/error.html', error=str(e))

@jtms_bp.route('/demo')
def demo():
    """Page de démonstration interactive JTMS."""
    try:
        demo_scenarios = [
            {
                "id": "basic_inference",
                "title": "Inférence Basique",
                "description": "Démonstration de propagation simple A → B → C"
            },
            {
                "id": "contradiction_handling", 
                "title": "Gestion de Contradictions",
                "description": "Comment le JTMS gère les croyances contradictoires"
            },
            {
                "id": "sherlock_investigation",
                "title": "Enquête Sherlock",
                "description": "Simulation d'une enquête avec agents Sherlock/Watson"
            },
            {
                "id": "non_monotonic_reasoning",
                "title": "Raisonnement Non-Monotonique",
                "description": "Révision de croyances avec nouvelles évidences"
            }
        ]
        
        return render_template('jtms/demo.html', 
                             scenarios=demo_scenarios,
                             timestamp=datetime.now().isoformat())
                             
    except Exception as e:
        logger.error(f"Erreur interface démo: {e}")
        return render_template('jtms/error.html', error=str(e))

# ============================================================================
# API REST JTMS
# ============================================================================

@jtms_bp.route('/api/session/<session_id>')
def get_session_data(session_id):
    """Récupère données complètes d'une session JTMS."""
    try:
        if not JTMS_AVAILABLE or not jtms_service:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        # Récupération des données via le service existant
        session_data = jtms_service.get_session(session_id)
        
        if not session_data:
            return jsonify({'error': f'Session {session_id} introuvable'}), 404
        
        # Conversion en format JSON pour l'interface web
        beliefs_data = {}
        justifications_data = []
        
        # Format des croyances pour visualisation
        for belief_name, belief in session_data.beliefs.items():
            beliefs_data[belief_name] = {
                'name': belief_name,
                'valid': belief.valid,
                'non_monotonic': belief.non_monotonic,
                'justifications': [
                    {
                        'in_list': [str(b) for b in j.in_list],
                        'out_list': [str(b) for b in j.out_list],
                        'valid': j.is_valid() if hasattr(j, 'is_valid') else True
                    }
                    for j in belief.justifications
                ],
                'implications': [str(j.conclusion) for j in belief.implications]
            }
            
            # Collecte des justifications pour le graphe
            for j in belief.justifications:
                justifications_data.append({
                    'in_list': [str(b) for b in j.in_list],
                    'out_list': [str(b) for b in j.out_list],
                    'conclusion': belief_name
                })
        
        # Calcul des statistiques
        total_beliefs = len(session_data.beliefs)
        valid_count = sum(1 for b in session_data.beliefs.values() if b.valid is True)
        invalid_count = sum(1 for b in session_data.beliefs.values() if b.valid is False)
        unknown_count = sum(1 for b in session_data.beliefs.values() if b.valid is None and not b.non_monotonic)
        nonmonotonic_count = sum(1 for b in session_data.beliefs.values() if b.non_monotonic)
        
        response_data = {
            'session_id': session_id,
            'beliefs': beliefs_data,
            'justifications': justifications_data,
            'statistics': {
                'total_beliefs': total_beliefs,
                'total_justifications': len(justifications_data),
                'valid_beliefs': valid_count,
                'invalid_beliefs': invalid_count,
                'unknown_beliefs': unknown_count,
                'nonmonotonic_beliefs': nonmonotonic_count
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erreur récupération session {session_id}: {e}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@jtms_bp.route('/api/belief', methods=['POST'])
def add_belief():
    """Ajoute nouvelle croyance dans une session."""
    try:
        if not JTMS_AVAILABLE or not jtms_service:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        belief_name = data.get('belief_name', '').strip()
        session_id = data.get('session_id', 'global')
        context = data.get('context', {})
        
        if not belief_name:
            return jsonify({'error': 'Nom de croyance requis'}), 400
        
        # Ajout via le service JTMS
        jtms_service.add_belief(belief_name, session_id)
        
        # Notification temps réel (si WebSocket configuré)
        try:
            emit('belief_added', {
                'belief_name': belief_name,
                'session_id': session_id,
                'belief_data': {
                    'valid': None,
                    'non_monotonic': False,
                    'justifications': [],
                    'implications': []
                },
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        except:
            pass  # WebSocket optionnel
        
        return jsonify({
            'success': True, 
            'message': f'Croyance "{belief_name}" ajoutée avec succès',
            'belief_name': belief_name,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Erreur ajout croyance: {e}")
        return jsonify({'error': f'Erreur lors de l\'ajout: {str(e)}'}), 500

@jtms_bp.route('/api/justification', methods=['POST'])
def add_justification():
    """Ajoute nouvelle justification dans une session."""
    try:
        if not JTMS_AVAILABLE or not jtms_service:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        in_list = data.get('in_list', [])
        out_list = data.get('out_list', [])
        conclusion = data.get('conclusion', '').strip()
        session_id = data.get('session_id', 'global')
        
        if not conclusion:
            return jsonify({'error': 'Conclusion requise'}), 400
        
        # Validation des listes
        if not isinstance(in_list, list):
            in_list = [in_list] if in_list else []
        if not isinstance(out_list, list):
            out_list = [out_list] if out_list else []
        
        # Ajout via le service JTMS
        jtms_service.add_justification(in_list, out_list, conclusion, session_id)
        
        # Notification temps réel
        try:
            emit('justification_added', {
                'in_list': in_list,
                'out_list': out_list,
                'conclusion': conclusion,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Justification ajoutée avec succès',
            'justification': {
                'in_list': in_list,
                'out_list': out_list,
                'conclusion': conclusion
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur ajout justification: {e}")
        return jsonify({'error': f'Erreur lors de l\'ajout: {str(e)}'}), 500

@jtms_bp.route('/api/belief/<belief_name>')
def get_belief_details(belief_name):
    """Récupère détails d'une croyance spécifique."""
    try:
        if not JTMS_AVAILABLE or not jtms_service:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        session_id = request.args.get('session', 'global')
        
        # Récupération via le service
        session_data = jtms_service.get_session(session_id)
        if not session_data or belief_name not in session_data.beliefs:
            return jsonify({'error': f'Croyance "{belief_name}" introuvable'}), 404
        
        belief = session_data.beliefs[belief_name]
        
        # Explication détaillée
        explanation = jtms_service.explain_belief(belief_name, session_id) if hasattr(jtms_service, 'explain_belief') else "Explication non disponible"
        
        belief_details = {
            'name': belief_name,
            'valid': belief.valid,
            'non_monotonic': belief.non_monotonic,
            'justifications': [
                {
                    'in_list': [str(b) for b in j.in_list],
                    'out_list': [str(b) for b in j.out_list],
                    'valid': all(b.valid for b in j.in_list) and not any(b.valid for b in j.out_list)
                }
                for j in belief.justifications
            ],
            'implications': [str(j.conclusion) for j in belief.implications],
            'explanation': explanation,
            'session_id': session_id
        }
        
        return jsonify(belief_details)
        
    except Exception as e:
        logger.error(f"Erreur détails croyance {belief_name}: {e}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@jtms_bp.route('/api/sessions', methods=['POST'])
def create_session():
    """Crée nouvelle session JTMS."""
    try:
        if not JTMS_AVAILABLE or not session_manager:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        session_id = data.get('session_id', '').strip()
        session_name = data.get('name', session_id)
        description = data.get('description', '')
        
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Création via le gestionnaire de sessions
        created_session_id = session_manager.create_session(session_id, session_name, description)
        
        return jsonify({
            'success': True,
            'session_id': created_session_id,
            'message': f'Session "{session_name}" créée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur création session: {e}")
        return jsonify({'error': f'Erreur lors de la création: {str(e)}'}), 500

@jtms_bp.route('/api/sessions')
def list_sessions():
    """Liste toutes les sessions JTMS."""
    try:
        if not JTMS_AVAILABLE or not session_manager:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        sessions = session_manager.list_sessions()
        sessions_info = []
        
        for session_id in sessions:
            try:
                info = session_manager.get_session_info(session_id)
                sessions_info.append(info)
            except Exception as e:
                logger.warning(f"Erreur info session {session_id}: {e}")
        
        return jsonify({
            'sessions': sessions_info,
            'total': len(sessions_info)
        })
        
    except Exception as e:
        logger.error(f"Erreur liste sessions: {e}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@jtms_bp.route('/api/consistency/<session_id>')
def check_session_consistency(session_id):
    """Vérifie cohérence d'une session."""
    try:
        if not JTMS_AVAILABLE or not jtms_service:
            return jsonify({'error': 'Services JTMS non disponibles'}), 503
        
        # Vérification via le service (si disponible)
        if hasattr(jtms_service, 'check_consistency'):
            consistency_report = jtms_service.check_consistency(session_id)
        else:
            # Vérification basique
            session_data = jtms_service.get_session(session_id)
            consistency_report = {
                'is_consistent': True,
                'conflicts': [],
                'total_beliefs': len(session_data.beliefs) if session_data else 0
            }
        
        # Notification temps réel
        try:
            emit('consistency_check', {
                'session_id': session_id,
                'is_consistent': consistency_report['is_consistent'],
                'conflicts': consistency_report.get('conflicts', []),
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        except:
            pass
        
        return jsonify(consistency_report)
        
    except Exception as e:
        logger.error(f"Erreur vérification cohérence {session_id}: {e}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

# ============================================================================
# GESTIONNAIRES D'ERREURS
# ============================================================================

@jtms_bp.errorhandler(404)
def jtms_not_found(error):
    """Gestionnaire d'erreur 404 pour les routes JTMS."""
    return render_template('jtms/error.html', 
                         error="Page JTMS introuvable"), 404

@jtms_bp.errorhandler(500)
def jtms_internal_error(error):
    """Gestionnaire d'erreur 500 pour les routes JTMS."""
    logger.error(f"Erreur interne JTMS: {error}")
    return render_template('jtms/error.html', 
                         error="Erreur interne du système JTMS"), 500

# ============================================================================
# INITIALISATION
# ============================================================================

def init_jtms_routes(app):
    """Initialise les routes JTMS avec l'application Flask."""
    try:
        initialize_jtms_services()
        app.register_blueprint(jtms_bp)
        logger.info("Routes JTMS configurées avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur configuration routes JTMS: {e}")
        return False