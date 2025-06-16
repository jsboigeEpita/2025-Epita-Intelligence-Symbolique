#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour validation API FastAPI avec GPT-4o-mini authentique
========================================================================

Tests pour Point d'Entrée 2 : Applications Web (API FastAPI + Interface React + Tests Playwright)
"""

# AUTO_ENV: Activation automatique environnement
try:
    import project_core.core_from_scripts.auto_env  # Auto-activation environnement intelligent
except ImportError:
    print("[WARNING] auto_env non disponible - environnement non activé")

import pytest
import time
import requests
import subprocess
import threading
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du test
API_BASE_URL = "http://localhost:8001"
API_PORT = 8001
TEST_TIMEOUT = 30

class TestAPIFastAPIAuthentique:
    """Tests unitaires pour l'API FastAPI avec GPT-4o-mini authentique."""
    
    @classmethod
    def setup_class(cls):
        """Configuration initiale des tests."""
        cls.api_process = None
        cls.api_started = False
        
    @classmethod
    def teardown_class(cls):
        """Nettoyage après tous les tests."""
        if cls.api_process:
            cls.api_process.terminate()
            cls.api_process.wait()
    
    def test_01_environment_setup(self):
        """Test 1: Vérification de la configuration environnement."""
        # Vérifier la clé OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        assert api_key is not None, "OPENAI_API_KEY non trouvée dans l'environnement"
        assert len(api_key) > 20, "OPENAI_API_KEY semble invalide (trop courte)"
        
        # Vérifier que les fichiers API existent
        api_files = [
            'api/main_simple.py',
            'api/endpoints_simple.py', 
            'api/dependencies_simple.py'
        ]
        
        for file_path in api_files:
            assert Path(file_path).exists(), f"Fichier API manquant: {file_path}"
    
    def test_02_start_api_server(self):
        """Test 2: Démarrage du serveur API FastAPI."""
        def start_server():
            """Démarre le serveur API en arrière-plan."""
            try:
                # Import local pour éviter les problèmes de dépendances
                import sys
                sys.path.append('api')
                from main_simple import app
                
                uvicorn.run(app, host="127.0.0.1", port=API_PORT, log_level="info")
            except Exception as e:
                print(f"Erreur démarrage serveur: {e}")
        
        # Démarrer le serveur dans un thread séparé
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        # Attendre que le serveur soit prêt
        start_time = time.time()
        while time.time() - start_time < TEST_TIMEOUT:
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    self.__class__.api_started = True
                    break
            except requests.ConnectionError:
                pass
            time.sleep(1)
        
        assert self.api_started, f"API n'a pas démarré dans les {TEST_TIMEOUT}s"
    
    def test_03_health_endpoint(self):
        """Test 3: Endpoint de santé de l'API."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        response = requests.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"
    
    def test_04_status_endpoint(self):
        """Test 4: Endpoint de statut de l'API."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        response = requests.get(f"{API_BASE_URL}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "service_name" in data
        assert "version" in data
        assert data["service_name"] == "FastAPI Analysis Service"
    
    def test_05_examples_endpoint(self):
        """Test 5: Endpoint des exemples prédéfinis."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        response = requests.get(f"{API_BASE_URL}/examples")
        assert response.status_code == 200
        
        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0
        
        # Vérifier la structure des exemples
        example = data["examples"][0]
        assert "text" in example
        assert "description" in example
    
    def test_06_analyze_endpoint_simple_text(self):
        """Test 6: Analyse d'un texte simple via endpoint /analyze."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        test_text = "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée."
        
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"text": test_text},
            timeout=60  # GPT-4o-mini peut prendre du temps
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier la structure de la réponse
        assert "analysis_id" in data
        assert "text" in data
        assert "analysis" in data
        assert "timestamp" in data
        assert "service_used" in data
        
        # Vérifier que l'analyse contient du contenu
        analysis = data["analysis"]
        assert len(analysis) > 10, "Analyse trop courte, probablement un mock"
        
        # Vérifier que GPT-4o-mini est utilisé
        assert data["service_used"] == "openai_gpt4o_mini", "Service utilisé incorrect"
    
    def test_07_analyze_endpoint_fallacy_detection(self):
        """Test 7: Détection de sophisme avec GPT-4o-mini."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        # Texte contenant un sophisme (ad hominem)
        test_text = "Cette théorie est fausse parce que son auteur est un idiot."
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"text": test_text},
            timeout=60
        )
        end_time = time.time()
        
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier que l'analyse prend un temps réaliste (>2s pour authentique)
        processing_time = end_time - start_time
        assert processing_time > 2.0, f"Temps de traitement trop rapide ({processing_time:.2f}s), probablement un mock"
        
        # Vérifier le contenu de l'analyse
        analysis = data["analysis"].lower()
        sophisme_keywords = ["sophisme", "fallacy", "ad hominem", "attaque personnelle", "argument"]
        
        found_keywords = [kw for kw in sophisme_keywords if kw in analysis]
        assert len(found_keywords) > 0, f"Analyse ne détecte pas le sophisme. Mots trouvés: {found_keywords}"
    
    def test_08_analyze_endpoint_performance_check(self):
        """Test 8: Vérification des performances pour authentifier GPT-4o-mini."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        test_text = "Le modus ponens est une règle d'inférence valide en logique propositionnelle."
        
        # Mesurer plusieurs appels pour vérifier la variabilité
        times = []
        responses = []
        
        for i in range(3):
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/analyze",
                json={"text": f"{test_text} Test {i+1}"},
                timeout=60
            )
            end_time = time.time()
            
            assert response.status_code == 200
            times.append(end_time - start_time)
            responses.append(response.json()["analysis"])
        
        # Vérifier que les temps sont dans une plage réaliste pour GPT-4o-mini
        avg_time = sum(times) / len(times)
        assert avg_time > 1.5, f"Temps moyen trop rapide ({avg_time:.2f}s), probablement un mock"
        assert avg_time < 30, f"Temps moyen trop lent ({avg_time:.2f}s), possible problème"
        
        # Vérifier que les réponses sont différentes (signe d'authenticité)
        unique_responses = set(responses)
        assert len(unique_responses) > 1, "Réponses identiques, probablement un mock"
    
    def test_09_analyze_endpoint_error_handling(self):
        """Test 9: Gestion d'erreurs de l'endpoint d'analyse."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        # Test avec texte vide
        response = requests.post(f"{API_BASE_URL}/analyze", json={"text": ""})
        assert response.status_code == 422, "Devrait rejeter le texte vide"
        
        # Test sans paramètre text
        response = requests.post(f"{API_BASE_URL}/analyze", json={})
        assert response.status_code == 422, "Devrait rejeter l'absence de texte"
        
        # Test avec texte trop long
        long_text = "a" * 10000
        response = requests.post(f"{API_BASE_URL}/analyze", json={"text": long_text})
        # Peut réussir ou échouer selon la configuration, mais ne doit pas crasher
        assert response.status_code in [200, 422, 413]
    
    def test_10_api_documentation(self):
        """Test 10: Documentation API automatique FastAPI."""
        if not self.api_started:
            pytest.skip("API non démarrée")
            
        # Test endpoint docs
        response = requests.get(f"{API_BASE_URL}/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Test OpenAPI schema
        response = requests.get(f"{API_BASE_URL}/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/analyze" in schema["paths"]

def pytest_main():
    """Point d'entrée pour exécuter les tests."""
    return pytest.main([__file__, "-v", "--tb=short"])

if __name__ == "__main__":
    pytest_main()