#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Mock API Server for Testing Web API Fallacy Detection
This provides a basic API that mimics the argumentation analysis web API
"""

import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Mock API server running",
        "version": "1.0.0-mock"
    })

@app.route('/api/fallacies', methods=['POST'])
def detect_fallacies():
    """Mock fallacy detection endpoint"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Text is required"}), 400
        
        text = data['text']
        options = data.get('options', {})
        
        # Mock fallacy detection logic
        fallacies = []
        text_lower = text.lower()
        
        # Basic pattern matching (similar to simple analysis)
        patterns = {
            "Ad Hominem": ["idiot", "stupide", "imbécile"],
            "False Dilemma": ["soit", "ou bien", "seulement deux"],
            "Hasty Generalization": ["tous", "toujours", "jamais"],
            "Appeal to Authority": ["expert dit", "scientifique affirme"]
        }
        
        for fallacy_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    position = text_lower.find(keyword)
                    fallacies.append({
                        "type": fallacy_type,
                        "confidence": 0.75,
                        "text_span": text[position:position + len(keyword) + 10],
                        "position": {"start": position, "end": position + len(keyword)},
                        "description": f"Detected by mock API using keyword: {keyword}",
                        "severity": "medium",
                        "context": text[max(0, position-30):position+50]
                    })
                    break  # Only one instance per fallacy type
        
        # Generate mock response
        response = {
            "status": "success",
            "text": text,
            "fallacies": fallacies,
            "processing_time": 0.1,
            "analysis_method": "mock_web_api"
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

if __name__ == '__main__':
    print("🚀 Starting Mock API Server...")
    print("📍 Health check: http://localhost:5000/api/health")
    print("📍 Fallacy detection: POST http://localhost:5000/api/fallacies")
    app.run(host='127.0.0.1', port=5000, debug=True) 