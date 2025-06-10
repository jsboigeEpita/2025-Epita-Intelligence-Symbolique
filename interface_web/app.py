#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface Web Simple pour Tests Playwright avec auto_env
========================================================
"""

# AUTO_ENV: Activation automatique environnement
try:
    import scripts.core.auto_env  # Auto-activation environnement intelligent
except ImportError:
    print("[WARNING] auto_env non disponible - environnement non activé")

from flask import Flask, render_template, request, jsonify
import os
import time
import uuid

app = Flask(__name__)

@app.route('/')
def index():
    """Page d'accueil de l'interface web."""
    return render_template('index.html')

@app.route('/status')
def status():
    """Status du système."""
    return jsonify({
        'status': 'Opérationnel',
        'timestamp': time.time()
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    """Endpoint d'analyse."""
    data = request.get_json() or {}
    text = data.get('text', '')
    
    analysis = {
        'id': f'analysis_{int(time.time())}',
        'status': 'completed',
        'text': text,
        'summary': f'Analyse simulée pour: {text[:50]}...' if len(text) > 50 else f'Analyse pour: {text}',
        'word_count': len(text.split()),
        'char_count': len(text)
    }
    
    return jsonify(analysis)

@app.route('/api/examples')
def api_examples():
    """Exemples prédéfinis."""
    return jsonify({
        'examples': [
            {
                'name': 'Logique Simple',
                'text': 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.',
                'type': 'propositional'
            },
            {
                'name': 'Modal',
                'text': 'Il est nécessaire que tous les hommes soient mortels.',
                'type': 'modal'
            }
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"Demarrage Flask avec auto_env sur port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)