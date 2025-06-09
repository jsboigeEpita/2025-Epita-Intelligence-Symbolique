#!/usr/bin/env python3
"""
Script de validation complète de l'interface web simple
======================================================

Tests API et validation de performance pour l'interface web EPITA
"""

import requests
import json
import time
from datetime import datetime

def test_api_endpoints():
    """Test des endpoints API principaux."""
    base_url = "http://127.0.0.1:3000"
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    print("=== VALIDATION API ENDPOINTS ===")
    
    # Test 1: Status endpoint
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/status", timeout=10)
        end_time = time.time()
        
        results["tests"]["status"] = {
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None
        }
        print(f"[OK] Status endpoint: {response.status_code} ({end_time - start_time:.3f}s)")
        
    except Exception as e:
        results["tests"]["status"] = {
            "success": False,
            "error": str(e)
        }
        print(f"[ERROR] Status endpoint error: {e}")
    
    # Test 2: Examples endpoint
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/api/examples", timeout=10)
        end_time = time.time()
        
        results["tests"]["examples"] = {
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None
        }
        print(f"[OK] Examples endpoint: {response.status_code} ({end_time - start_time:.3f}s)")
        
    except Exception as e:
        results["tests"]["examples"] = {
            "success": False,
            "error": str(e)
        }
        print(f"[ERROR] Examples endpoint error: {e}")
    
    # Test 3: Analyze endpoint avec données réalistes
    test_data = {
        "text": "L'intelligence artificielle optimise la consommation énergétique mais les centres de données consomment énormément d'énergie. Cette dichotomie soulève des questions fondamentales.",
        "analysis_type": "comprehensive",
        "options": {}
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/analyze",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        end_time = time.time()
        
        results["tests"]["analyze"] = {
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None
        }
        print(f"[OK] Analyze endpoint: {response.status_code} ({end_time - start_time:.3f}s)")
        
    except Exception as e:
        results["tests"]["analyze"] = {
            "success": False,
            "error": str(e)
        }
        print(f"[ERROR] Analyze endpoint error: {e}")
    
    return results

if __name__ == "__main__":
    results = test_api_endpoints()
    
    # Sauvegarder les résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"../../../logs/web_api_calls_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED] Resultats sauvegardes: logs/web_api_calls_{timestamp}.json")