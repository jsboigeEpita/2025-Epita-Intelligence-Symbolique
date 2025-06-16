#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
REST API for Fallacy Detection
Clean API endpoints for frontend integration
"""

import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any

# Add project paths
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from speech_to_text.services.fallacy_detector import get_fallacy_detection_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Get the fallacy detection service
fallacy_service = get_fallacy_detection_service()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        service_health = fallacy_service.check_health()
        return jsonify({
            "status": "healthy",
            "message": "Fallacy Detection API is running",
            "version": "1.0.0",
            "service_health": service_health,
            "endpoints": {
                "health": "/api/health",
                "detect_fallacies": "/api/fallacies",
                "analyze_text": "/api/analyze"
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "message": "Service unavailable",
            "error": str(e)
        }), 500

@app.route('/api/fallacies', methods=['POST'])
def detect_fallacies():
    """
    Detect fallacies in text
    
    Expected JSON payload:
    {
        "text": "Text to analyze",
        "options": {
            "severity_threshold": 0.5,
            "include_context": true,
            "max_fallacies": 10
        }
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                "status": "error",
                "error_message": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data or 'text' not in data:
            return jsonify({
                "status": "error",
                "error_message": "Field 'text' is required"
            }), 400
        
        text = data['text']
        if not text or not text.strip():
            return jsonify({
                "status": "error",
                "error_message": "Text cannot be empty"
            }), 400
        
        # Get options (optional)
        options = data.get('options', {})
        
        # Detect fallacies
        result = fallacy_service.detect_fallacies(text, options)
        
        # Return result
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Fallacy detection failed: {e}")
        return jsonify({
            "status": "error",
            "error_message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    """
    Comprehensive text analysis (alias for fallacy detection)
    Same as /api/fallacies but with more descriptive name
    """
    return detect_fallacies()

@app.route('/api/service-info', methods=['GET'])
def service_info():
    """Get information about the fallacy detection service"""
    try:
        service_health = fallacy_service.check_health()
        
        return jsonify({
            "service_name": "Fallacy Detection API",
            "version": "1.0.0",
            "description": "Multi-tier fallacy detection with advanced services, web API, and pattern matching",
            "capabilities": {
                "advanced_services": service_health.get("advanced_services", False),
                "web_api_fallback": service_health.get("web_api", False),
                "pattern_matching": service_health.get("pattern_matching", True)
            },
            "supported_fallacies": [
                "Ad Hominem",
                "False Dilemma", 
                "Hasty Generalization",
                "Appeal to Authority"
            ],
            "languages": ["French", "English"],
            "response_format": {
                "status": "success|error",
                "fallacies_detected": "List of detected fallacies",
                "summary": "Analysis summary with metrics",
                "recommendations": "List of improvement suggestions"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Service info failed: {e}")
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "status": "error",
        "error_message": "Endpoint not found",
        "available_endpoints": [
            "GET /api/health",
            "POST /api/fallacies", 
            "POST /api/analyze",
            "GET /api/service-info"
        ]
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "status": "error",
        "error_message": "Method not allowed for this endpoint"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "status": "error",
        "error_message": "Internal server error"
    }), 500

if __name__ == '__main__':
    print("🚀 Starting Fallacy Detection API Server...")
    print("📋 Available endpoints:")
    print("   • GET  /api/health      - Service health check")
    print("   • POST /api/fallacies   - Detect fallacies in text")
    print("   • POST /api/analyze     - Analyze text (alias)")
    print("   • GET  /api/service-info - Service information")
    print("\n📖 API Documentation:")
    print("   • POST /api/fallacies expects JSON: {'text': 'your text', 'options': {...}}")
    print("   • Returns structured analysis with fallacies, summary, and recommendations")
    print("\n✅ Ready for frontend integration!")
    
    # Run the server
    app.run(host='127.0.0.1', port=5001, debug=True) 