#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend minimal pour tests Playwright
=====================================

Backend simple sans dépendances lourdes pour valider l'intégration Playwright.
"""

import sys
import argparse
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_minimal_app():
    """Crée une application Flask minimale pour les tests"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for frontend
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'ok',
            'message': 'Minimal backend pour tests Playwright',
            'timestamp': time.time()
        })
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_text():
        """Endpoint d'analyse minimal"""
        data = request.get_json() or {}
        text = data.get('text', '')
        
        # Simulation d'analyse simple
        analysis = {
            'id': f'analysis_{int(time.time())}',
            'text': text,
            'summary': f'Analyse simulée pour: {text[:50]}...' if len(text) > 50 else f'Analyse simulée pour: {text}',
            'word_count': len(text.split()),
            'char_count': len(text),
            'arguments': [
                {'type': 'premise', 'text': 'Prémisse simulée', 'confidence': 0.8},
                {'type': 'conclusion', 'text': 'Conclusion simulée', 'confidence': 0.9}
            ],
            'status': 'completed',
            'processing_time': 0.5
        }
        
        return jsonify(analysis)
    
    @app.route('/api/status', methods=['GET'])
    def api_status():
        """Status de l'API"""
        return jsonify({
            'api_version': '1.0.0',
            'backend_type': 'minimal_for_tests',
            'endpoints': ['/api/health', '/api/analyze', '/api/status'],
            'ready': True
        })
    
    return app

def run_server(port=5003, debug=False):
    """Lance le serveur minimal"""
    try:
        app = create_minimal_app()
        logger.info(f"🚀 Démarrage backend minimal sur port {port}")
        
        # Lancement en thread séparé pour éviter le blocage
        def run_app():
            app.run(
                host='0.0.0.0',
                port=port,
                debug=debug,
                use_reloader=False,  # Important pour éviter les conflits
                threaded=True
            )
        
        server_thread = threading.Thread(target=run_app, daemon=True)
        server_thread.start()
        
        # Attendre que le serveur soit prêt
        time.sleep(2)
        logger.info(f"✅ Backend minimal prêt sur http://localhost:{port}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur démarrage backend minimal: {e}")
        return False

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description='Backend minimal pour tests Playwright')
    parser.add_argument('--port', type=int, default=5003, help='Port d\'écoute')
    parser.add_argument('--debug', action='store_true', help='Mode debug')
    
    args = parser.parse_args()
    
    logger.info("🎯 Backend minimal pour tests Playwright - DÉMARRAGE")
    
    try:
        # Création et démarrage de l'application
        app = create_minimal_app()
        logger.info(f"🚀 Démarrage sur port {args.port}")
        
        app.run(
            host='0.0.0.0',
            port=args.port,
            debug=args.debug,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur critique: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()