import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_fallacy_api(text, test_name):
    """Test l'API de détection de sophismes"""
    url = "http://localhost:5000/api/fallacies"
    
    payload = {
        "text": text,
        "context": "general",
        "severity_threshold": 0.3,
        "include_explanations": True
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        print(f"\n=== Test {test_name} ===")
        print(f"Texte: {text}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Sophismes détectés: {len(result.get('fallacies', []))}")
            for fallacy in result.get('fallacies', []):
                print(f"- {fallacy.get('name', 'N/A')} ({fallacy.get('type', 'N/A')})")
                print(f"  Confiance: {fallacy.get('confidence_level', 'N/A')} ({fallacy.get('confidence', 'N/A')}%)")
                print(f"  Description: {fallacy.get('description', 'N/A')}")
                if 'explanation' in fallacy:
                    print(f"  Explication: {fallacy['explanation']}")
        else:
            print(f"Erreur: {result}")
            
    except Exception as e:
        print(f"Erreur de connexion: {e}")

if __name__ == "__main__":
    # Test 1: Pente glissante
    test_fallacy_api(
        "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h.",
        "#5 - Pente glissante"
    )
    
    # Test 2: Homme de paille
    test_fallacy_api(
        "Les écologistes veulent qu'on retourne à l'âge de pierre.",
        "#6 - Homme de paille"
    )