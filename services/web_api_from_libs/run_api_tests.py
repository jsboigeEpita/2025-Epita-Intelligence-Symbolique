#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test simple pour l'API d'analyse argumentative.
"""

import requests
import json
import time
import sys
import os

# Ajout du répertoire racine du projet au PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configuration
API_BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test du health check."""
    print("🔍 Test du health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check OK - Status: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur health check: {e}")
        return False

def test_analyze_endpoint():
    """Test de l'endpoint d'analyse."""
    print("\n📊 Test de l'analyse complète...")
    
    payload = {
        "text": "Tous les politiciens sont corrompus. Jean est politicien. Donc Jean est corrompu.",
        "options": {
            "detect_fallacies": True,
            "analyze_structure": True,
            "evaluate_coherence": True,
            "severity_threshold": 0.3
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/analyze",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analyse OK - Sophismes détectés: {data['fallacy_count']}")
            print(f"   Qualité globale: {data['overall_quality']:.2f}")
            if data['fallacies']:
                print(f"   Premier sophisme: {data['fallacies'][0]['name']}")
            return True
        else:
            print(f"❌ Analyse failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur analyse: {e}")
        return False

def test_validate_endpoint():
    """Test de l'endpoint de validation."""
    print("\n✅ Test de la validation d'argument...")
    
    payload = {
        "premises": [
            "Tous les hommes sont mortels",
            "Socrate est un homme"
        ],
        "conclusion": "Socrate est mortel",
        "argument_type": "deductive"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/validate",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data['result']
            print(f"✅ Validation OK - Valide: {result['is_valid']}")
            print(f"   Score de validité: {result['validity_score']:.2f}")
            print(f"   Score de solidité: {result['soundness_score']:.2f}")
            return True
        else:
            print(f"❌ Validation failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur validation: {e}")
        return False

def test_fallacies_endpoint():
    """Test de l'endpoint de détection de sophismes."""
    print("\n🚫 Test de la détection de sophismes...")
    
    payload = {
        "text": "Vous ne pouvez pas critiquer ce projet car vous n'êtes pas expert en la matière.",
        "options": {
            "severity_threshold": 0.3,
            "include_context": True,
            "max_fallacies": 5
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/fallacies",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Détection OK - Sophismes trouvés: {data['fallacy_count']}")
            if data['fallacies']:
                print(f"   Premier sophisme: {data['fallacies'][0]['name']}")
            return True
        else:
            print(f"❌ Détection failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur détection: {e}")
        return False

def test_framework_endpoint():
    """Test de l'endpoint de framework."""
    print("\n🕸️ Test du framework de Dung...")
    
    payload = {
        "arguments": [
            {
                "id": "arg1",
                "content": "Il faut réduire les impôts pour stimuler l'économie",
                "attacks": ["arg2"]
            },
            {
                "id": "arg2",
                "content": "Réduire les impôts diminue les services publics",
                "attacks": ["arg1"]
            },
            {
                "id": "arg3",
                "content": "Les services publics sont essentiels",
                "supports": ["arg2"]
            }
        ],
        "options": {
            "compute_extensions": True,
            "semantics": "preferred",
            "include_visualization": True
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/framework",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Framework OK - Arguments: {data['argument_count']}")
            print(f"   Attaques: {data['attack_count']}")
            print(f"   Extensions: {data['extension_count']}")
            return True
        else:
            print(f"❌ Framework failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur framework: {e}")
        return False

def test_endpoints_list():
    """Test de la liste des endpoints."""
    print("\n📋 Test de la liste des endpoints...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/endpoints")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Liste OK - API: {data['api_name']}")
            print(f"   Version: {data['version']}")
            print(f"   Endpoints disponibles: {len(data['endpoints'])}")
            return True
        else:
            print(f"❌ Liste failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur liste: {e}")
        return False

def run_all_tests():
    """Lance tous les tests."""
    print("🚀 Démarrage des tests de l'API d'analyse argumentative")
    print("=" * 60)
    
    tests = [
        test_health_check,
        test_analyze_endpoint,
        test_validate_endpoint,
        test_fallacies_endpoint,
        test_framework_endpoint,
        test_endpoints_list
    ]
    
    results = []
    start_time = time.time()
    
    for test in tests:
        result = test()
        results.append(result)
        time.sleep(0.5)  # Pause entre les tests
    
    end_time = time.time()
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests réussis: {passed}/{total}")
    print(f"Temps total: {end_time - start_time:.2f}s")
    
    if passed == total:
        print("🎉 Tous les tests sont passés avec succès!")
        return True
    else:
        print(f"⚠️  {total - passed} test(s) ont échoué")
        return False

def test_error_handling():
    """Test de la gestion d'erreurs."""
    print("\n🔧 Test de la gestion d'erreurs...")
    
    # Test avec données invalides
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/analyze",
            headers={"Content-Type": "application/json"},
            json={"text": ""}  # Texte vide
        )
        
        if response.status_code == 400:
            print("✅ Gestion d'erreur OK - Texte vide rejeté")
            return True
        else:
            print(f"❌ Gestion d'erreur failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur test erreur: {e}")
        return False

if __name__ == "__main__":
    print("Assurez-vous que l'API est démarrée sur http://localhost:5000")
    print("Pour démarrer l'API: python libs/web_api/app.py")
    print()
    
    # Vérification de la disponibilité de l'API
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ L'API ne semble pas être disponible")
            exit(1)
    except Exception:
        print("❌ Impossible de se connecter à l'API")
        print("   Vérifiez que l'API est démarrée sur http://localhost:5000")
        exit(1)
    
    # Lancement des tests
    success = run_all_tests()
    
    # Test de gestion d'erreurs
    test_error_handling()
    
    if success:
        print("\n🎯 L'API est prête pour l'utilisation!")
    else:
        print("\n⚠️  Certains tests ont échoué, vérifiez les logs")