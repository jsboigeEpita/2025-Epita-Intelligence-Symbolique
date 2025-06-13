#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Direct API FastAPI - Point d'Entrée 2
==========================================

Test unitaire simplifié pour valider l'API FastAPI avec GPT-4o-mini authentique
"""

import os
import sys
import time
import requests
import subprocess
import threading
from pathlib import Path
from dotenv import load_dotenv

# Charger l'environnement
load_dotenv()

def test_environment_setup():
    """Test 1: Vérification environnement."""
    print("\n=== Test 1: Vérification environnement ===")
    
    # Vérifier clé OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    assert api_key is not None, "OPENAI_API_KEY manquante"
    assert len(api_key) > 20, "OPENAI_API_KEY invalide"
    print(f"✓ OPENAI_API_KEY configurée ({len(api_key)} chars)")
    
    # Vérifier fichiers API
    api_files = ['api/main_simple.py', 'api/endpoints_simple.py', 'api/dependencies_simple.py']
    for file_path in api_files:
        assert Path(file_path).exists(), f"Fichier manquant: {file_path}"
    print(f"✓ Fichiers API présents: {len(api_files)}")
    
    print("✓ Test environnement RÉUSSI")

def test_api_startup_and_basic_functionality():
    """Test 2: Démarrage API et fonctionnalité de base."""
    print("\n=== Test 2: Démarrage API et fonctionnalités ===")
    
    # Configuration
    api_url = "http://localhost:8001"
    api_process = None
    
    try:
        # Démarrer l'API
        print("Démarrage de l'API FastAPI...")
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "api.main_simple:app",
            "--host", "127.0.0.1",
            "--port", "8001",
            "--log-level", "error"  # Réduire les logs
        ]
        
        api_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
            env=dict(os.environ, PYTHONPATH=os.getcwd())
        )
        
        print(f"API process démarré (PID: {api_process.pid})")
        
        # Attendre que l'API soit prête
        api_ready = False
        max_wait = 30
        wait_time = 0
        
        while wait_time < max_wait:
            try:
                response = requests.get(f"{api_url}/health", timeout=3)
                if response.status_code == 200:
                    api_ready = True
                    print(f"✓ API prête après {wait_time}s")
                    break
            except (requests.ConnectionError, requests.Timeout):
                pass
            
            time.sleep(2)
            wait_time += 2
            print(f"  Attente API... {wait_time}s/{max_wait}s")
        
        assert api_ready, f"API non prête après {max_wait}s"
        
        # Test health endpoint
        print("\nTest endpoint /health...")
        response = requests.get(f"{api_url}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check: {data}")
        
        # Test examples endpoint
        print("\nTest endpoint /api/examples...")
        response = requests.get(f"{api_url}/api/examples", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        print(f"✓ Exemples trouvés: {len(data['examples'])}")
        
        # Test analyse simple
        print("\nTest endpoint /analyze avec GPT-4o-mini...")
        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."
        
        start_time = time.time()
        response = requests.post(
            f"{api_url}/api/analyze",
            json={"text": test_text},
            timeout=60
        )
        processing_time = time.time() - start_time
        
        assert response.status_code == 200, f"Erreur API: {response.text}"
        data = response.json()
        
        # Vérifications
        assert "analysis_id" in data
        assert "status" in data
        assert data["status"] == "success"
        assert "fallacies" in data

        analysis_summary = data.get("summary", "")
        service_metadata = data.get("metadata", {})
        
        print(f"✓ Analyse reçue ({analysis_summary[:50]}...) en {processing_time:.2f}s")
        print(f"✓ Service utilisé: {service_metadata.get('gpt_model')}")

        # Vérifier authenticité
        assert service_metadata.get("authentic_analysis") is True, "L'analyse ne semble pas authentique"
        assert len(analysis_summary) > 10, f"Résumé d'analyse trop court: {len(analysis_summary)} chars"
        assert processing_time > 1.0, f"Temps trop rapide ({processing_time:.2f}s), possible mock"
        
        print(f"✓ Analyse authentique GPT-4o-mini confirmée")
        print(f"  - Temps: {processing_time:.2f}s (> 1.0s)")
        print(f"  - Longueur: {len(analysis_summary)} chars")
        print(f"  - Service: {service_metadata.get('gpt_model')}")
        
        # Test détection sophisme
        print("\nTest détection sophisme...")
        sophisme_text = "Cette théorie est fausse car son auteur est un idiot."
        
        response = requests.post(
            f"{api_url}/api/analyze",
            json={"text": sophisme_text},
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        analysis_summary = data.get("summary", "").lower()
        
        # Chercher des indicateurs de détection logique
        indicators = ["sophisme", "fallacy", "ad hominem", "argument", "logique", "erreur", "raisonnement"]
        found = [ind for ind in indicators if ind in analysis_summary]
        
        print(f"✓ Indicateurs trouvés: {found}")
        assert len(found) > 0, f"Aucun indicateur logique dans: {analysis_summary[:100]}"
        
        print("✓ Test API et fonctionnalités RÉUSSI")
        
    except Exception as e:
        print(f"✗ ERREUR: {e}")
        raise
        
    finally:
        # Nettoyer
        if api_process:
            print("\nArrêt de l'API...")
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
                print("✓ API arrêtée proprement")
            except subprocess.TimeoutExpired:
                api_process.kill()
                print("✓ API tuée forcément")

def run_all_tests():
    """Exécuter tous les tests."""
    print("=== TESTS VALIDATION POINT D'ENTRÉE 2 - API FASTAPI GPT-4O-MINI ===")
    
    try:
        test_environment_setup()
        test_api_startup_and_basic_functionality()
        
        print("\n" + "="*60)
        print("🎉 TOUS LES TESTS RÉUSSIS - VALIDATION CONFIRMÉE")
        print("✓ API FastAPI utilise authentiquement GPT-4o-mini")
        print("✓ Endpoints fonctionnels et temps de réponse réalistes")
        print("✓ Détection de sophismes opérationnelle")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ÉCHEC DE VALIDATION: {e}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)