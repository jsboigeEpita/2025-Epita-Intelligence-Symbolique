#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Mock pour Démo Playwright
=================================

Serveur Flask minimaliste pour les démos d'interface
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockAPI")

app = Flask(__name__)
CORS(app)

# Données mockées pour les démos
MOCK_RESPONSES = {
    "analysis": {
        "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
        "conclusion": "Socrate est mortel", 
        "validity": True,
        "confidence": 0.95,
        "structure": "Syllogisme valide"
    },
    "fallacies": {
        "detected": True,
        "fallacy_type": "Ad Hominem",
        "confidence": 0.87,
        "description": "Attaque contre la personne plutôt que l'argument"
    },
    "reconstruction": {
        "reconstructed_argument": "Prémisse 1: P1\nPrémisse 2: P2\nConclusion: C",
        "missing_premises": ["Prémisse implicite trouvée"],
        "structure": "Argument reconstructed"
    }
}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Point de vérification de l'état de l'API"""
    return jsonify({
        "status": "ok",
        "message": "Mock API opérationnelle",
        "version": "demo-1.0"
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_argument():
    """Analyse d'argument mockée"""
    data = request.get_json()
    text = data.get('text', '')
    
    logger.info(f"Analyse demandée pour: {text[:50]}...")
    
    response = MOCK_RESPONSES["analysis"].copy()
    response["input_text"] = text
    response["timestamp"] = "2025-06-08T15:00:00Z"
    
    return jsonify(response)

@app.route('/api/detect-fallacies', methods=['POST'])
def detect_fallacies():
    """Détection de sophismes mockée"""
    data = request.get_json()
    text = data.get('text', '')
    
    logger.info(f"Détection sophismes pour: {text[:50]}...")
    
    response = MOCK_RESPONSES["fallacies"].copy()
    response["input_text"] = text
    response["timestamp"] = "2025-06-08T15:00:00Z"
    
    return jsonify(response)

@app.route('/api/reconstruct', methods=['POST'])
def reconstruct_argument():
    """Reconstruction d'argument mockée"""
    data = request.get_json()
    text = data.get('text', '')
    
    logger.info(f"Reconstruction pour: {text[:50]}...")
    
    response = MOCK_RESPONSES["reconstruction"].copy()
    response["input_text"] = text
    response["timestamp"] = "2025-06-08T15:00:00Z"
    
    return jsonify(response)

@app.route('/api/validate', methods=['POST'])
def validate_argument():
    """Validation d'argument mockée"""
    data = request.get_json()
    
    logger.info("Validation d'argument demandée")
    
    return jsonify({
        "valid": True,
        "confidence": 0.92,
        "explanation": "Argument valide selon les règles logiques",
        "timestamp": "2025-06-08T15:00:00Z"
    })

@app.route('/api/logic-graph', methods=['POST'])
def generate_logic_graph():
    """Génération de graphe logique mockée"""
    data = request.get_json()
    
    logger.info("Génération graphe logique demandée")
    
    return jsonify({
        "nodes": [
            {"id": "p1", "label": "Prémisse 1", "type": "premise"},
            {"id": "p2", "label": "Prémisse 2", "type": "premise"},
            {"id": "c1", "label": "Conclusion", "type": "conclusion"}
        ],
        "edges": [
            {"from": "p1", "to": "c1"},
            {"from": "p2", "to": "c1"}
        ],
        "timestamp": "2025-06-08T15:00:00Z"
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backend Mock pour démo')
    parser.add_argument('--port', type=int, default=5003, help='Port du serveur')
    parser.add_argument('--debug', action='store_true', help='Mode debug')
    
    args = parser.parse_args()
    
    print(f"[MOCK] Démarrage backend mock sur le port {args.port}")
    print(f"[MOCK] Health check: http://localhost:{args.port}/api/health")
    
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)