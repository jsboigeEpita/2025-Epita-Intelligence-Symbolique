#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Direct API FastAPI - Point d'Entree 2 (sans Unicode)
=========================================================

Test unitaire simplifie pour valider l'API FastAPI avec GPT-4o-mini authentique
"""

import os
import sys
import time
import requests
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Charger l'environnement
load_dotenv()

def test_environment_setup():
    """Test 1: Verification environnement."""
    print("\n=== Test 1: Verification environnement ===")
    
    # Verifier cle OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    assert api_key is not None, "OPENAI_API_KEY manquante"
    assert len(api_key) > 20, "OPENAI_API_KEY invalide"
    print(f"[OK] OPENAI_API_KEY configuree ({len(api_key)} chars)")
    
    # Verifier fichiers API
    api_files = ['api/main_simple.py', 'api/endpoints_simple.py', 'api/dependencies_simple.py']
    for file_path in api_files:
        assert Path(file_path).exists(), f"Fichier manquant: {file_path}"
    print(f"[OK] Fichiers API presents: {len(api_files)}")
    
    print("[OK] Test environnement REUSSI")

def test_api_startup_and_basic_functionality():
    """Test 2: Demarrage API et fonctionnalite de base."""
    print("\n=== Test 2: Demarrage API et fonctionnalites ===")
    
    # Configuration
    api_url = "http://localhost:8001"
    api_process = None
    
    try:
        # Demarrer l'API
        print("Demarrage de l'API FastAPI...")
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "api.main_simple:app",
            "--host", "127.0.0.1",
            "--port", "8001",
            "--log-level", "error"  # Reduire les logs
        ]
        
        api_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
            env=dict(os.environ, PYTHONPATH=os.getcwd())
        )
        
        print(f"API process demarre (PID: {api_process.pid})")
        
        # Attendre que l'API soit prete
        api_ready = False
        max_wait = 30
        wait_time = 0
        
        while wait_time < max_wait:
            try:
                response = requests.get(f"{api_url}/health", timeout=3)
                if response.status_code == 200:
                    api_ready = True
                    print(f"[OK] API prete apres {wait_time}s")
                    break
            except (requests.ConnectionError, requests.Timeout):
                pass
            
            time.sleep(2)
            wait_time += 2
            print(f"  Attente API... {wait_time}s/{max_wait}s")
        
        assert api_ready, f"API non prete apres {max_wait}s"
        
        # Test health endpoint
        print("\nTest endpoint /health...")
        response = requests.get(f"{api_url}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"[OK] Health check: {data}")
        
        # Test examples endpoint  
        print("\nTest endpoint /examples...")
        response = requests.get(f"{api_url}/examples", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        print(f"[OK] Exemples trouves: {len(data['examples'])}")
        
        # Test analyse simple
        print("\nTest endpoint /analyze avec GPT-4o-mini...")
        test_text = "Si il pleut, alors la route est mouillee. Il pleut. Donc la route est mouillee."
        
        start_time = time.time()
        response = requests.post(
            f"{api_url}/analyze",
            json={"text": test_text},
            timeout=60
        )
        processing_time = time.time() - start_time
        
        assert response.status_code == 200, f"Erreur API: {response.text}"
        data = response.json()
        
        # Verifications
        assert "analysis_id" in data
        assert "analysis" in data
        assert "service_used" in data
        
        analysis = data["analysis"]
        service = data["service_used"]
        
        print(f"[OK] Analyse recue ({len(analysis)} chars) en {processing_time:.2f}s")
        print(f"[OK] Service utilise: {service}")
        
        # Verifier authenticite
        assert service == "openai_gpt4o_mini", f"Service incorrect: {service}"
        assert len(analysis) > 20, f"Analyse trop courte: {len(analysis)} chars"
        assert processing_time > 1.0, f"Temps trop rapide ({processing_time:.2f}s), possible mock"
        
        print(f"[OK] Analyse authentique GPT-4o-mini confirmee")
        print(f"  - Temps: {processing_time:.2f}s (> 1.0s)")
        print(f"  - Longueur: {len(analysis)} chars")
        print(f"  - Service: {service}")
        
        # Test detection sophisme
        print("\nTest detection sophisme...")
        sophisme_text = "Cette theorie est fausse car son auteur est un idiot."
        
        response = requests.post(
            f"{api_url}/analyze",
            json={"text": sophisme_text},
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        analysis = data["analysis"].lower()
        
        # Chercher des indicateurs de detection logique
        indicators = ["sophisme", "fallacy", "ad hominem", "argument", "logique", "erreur"]
        found = [ind for ind in indicators if ind in analysis]
        
        print(f"[OK] Indicateurs trouves: {found}")
        assert len(found) > 0, f"Aucun indicateur logique dans: {analysis[:100]}"
        
        print("[OK] Test API et fonctionnalites REUSSI")
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        raise
        
    finally:
        # Nettoyer
        if api_process:
            print("\nArret de l'API...")
            api_process.terminate()
            try:
                api_process.wait(timeout=10)
                print("[OK] API arretee proprement")
            except subprocess.TimeoutExpired:
                api_process.kill()
                print("[OK] API tuee forcement")

def run_all_tests():
    """Executer tous les tests."""
    print("=== TESTS VALIDATION POINT D'ENTREE 2 - API FASTAPI GPT-4O-MINI ===")
    
    try:
        test_environment_setup()
        test_api_startup_and_basic_functionality()
        
        print("\n" + "="*60)
        print("TOUS LES TESTS REUSSIS - VALIDATION CONFIRMEE")
        print("[OK] API FastAPI utilise authentiquement GPT-4o-mini")
        print("[OK] Endpoints fonctionnels et temps de reponse realistes")
        print("[OK] Detection de sophismes operationnelle")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\nECHEC DE VALIDATION: {e}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)