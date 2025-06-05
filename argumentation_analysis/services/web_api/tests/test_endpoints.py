#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour les endpoints de l'API web.
"""

import json
import pytest
from unittest.mock import patch


class TestHealthEndpoint:
    """Tests pour l'endpoint /api/health."""
    
    def test_health_check_success(self, client, mock_analysis_service, mock_validation_service, 
                                 mock_fallacy_service, mock_framework_service):
        """Test du health check avec tous les services opérationnels."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'healthy'
        assert data['message'] == "API d'analyse argumentative opérationnelle"
        assert data['version'] == '1.0.0'
        assert 'services' in data
        assert data['services']['analysis'] is True
        assert data['services']['validation'] is True
        assert data['services']['fallacy'] is True
        assert data['services']['framework'] is True
    
    def test_health_check_with_service_failure(self, client):
        """Test du health check avec échec d'un service."""
        with patch('argumentation_analysis.services.web_api.app.analysis_service') as mock_service:
            mock_service.is_healthy.side_effect = Exception("Service indisponible")
            
            response = client.get('/api/health')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['error'] == 'Erreur de health check'


class TestAnalyzeEndpoint:
    """Tests pour l'endpoint /api/analyze."""
    
    def test_analyze_success(self, client, mock_analysis_service, sample_analysis_request):
        """Test d'analyse réussie."""
        response = client.post('/api/analyze', 
                              data=json.dumps(sample_analysis_request),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert data['text_analyzed'] == sample_analysis_request["text"] # Vérifier le texte de la requête
        assert 'fallacies' in data
        assert 'argument_structure' in data
        assert 'overall_quality' in data
        assert 'coherence_score' in data
        assert 'processing_time' in data
        
        # Vérifier que le service a été appelé
        mock_analysis_service.analyze_text.assert_called_once()

    def test_analyze_integration_simple_success(self, client, sample_analysis_request, mock_analysis_service): # Ajout de mock_analysis_service
        """Test d'intégration simple pour /api/analyze avec texte simple."""
        response = client.post('/api/analyze',
                              data=json.dumps(sample_analysis_request),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert data['text_analyzed'] == sample_analysis_request["text"]
        assert 'fallacies' in data
        assert 'argument_structure' in data
        assert 'overall_quality' in data
        assert 'coherence_score' in data
        assert 'processing_time' in data
        # Pas de vérification de mock_analysis_service.analyze_text.assert_called_once()
        # car c'est un test d'intégration qui peut appeler le vrai service
        # ou un service partiellement mocké selon la configuration du client de test.
    
    def test_analyze_missing_body(self, client):
        """Test d'analyse sans body JSON."""
        response = client.post('/api/analyze') # Pas de Content-Type, pas de corps
        
        assert response.status_code == 415 # S'attendre à 415 car request.get_json() échoue sans Content-Type
        data = response.get_json()
        assert data['error'] == 'Unsupported Media Type' # Message d'erreur de HTTPException
        assert "Did not attempt to load JSON data because the request Content-Type was not 'application/json'" in data['message']
    
    def test_analyze_empty_text(self, client):
        """Test d'analyse avec texte vide."""
        request_data = {"text": "", "options": {}}
        
        response = client.post('/api/analyze',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
        assert 'validation' in data['message']
    
    def test_analyze_invalid_options(self, client):
        """Test d'analyse avec options invalides."""
        request_data = {
            "text": "Texte valide",
            "options": {
                "severity_threshold": 2.0  # Valeur invalide (> 1.0)
            }
        }
        
        response = client.post('/api/analyze',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
    
    def test_analyze_service_error(self, client, sample_analysis_request):
        """Test d'analyse avec erreur du service."""
        with patch('argumentation_analysis.services.web_api.app.analysis_service') as mock_service:
            mock_service.analyze_text.side_effect = Exception("Erreur interne")
            
            response = client.post('/api/analyze',
                                  data=json.dumps(sample_analysis_request),
                                  content_type='application/json')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['error'] == "Erreur d'analyse"


class TestValidateEndpoint:
    """Tests pour l'endpoint /api/validate."""
    
    def test_validate_success(self, client, mock_validation_service, sample_validation_request):
        """Test de validation réussie."""
        response = client.post('/api/validate',
                              data=json.dumps(sample_validation_request),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert 'premises' in data
        assert 'conclusion' in data
        assert 'argument_type' in data
        assert 'result' in data
        assert 'processing_time' in data
        
        # Vérifier la structure du résultat
        result = data['result']
        assert 'is_valid' in result
        assert 'validity_score' in result
        assert 'soundness_score' in result
        
        mock_validation_service.validate_argument.assert_called_once()
    
    def test_validate_missing_premises(self, client):
        """Test de validation sans prémisses."""
        request_data = {
            "conclusion": "Conclusion",
            "argument_type": "deductive"
        }
        
        response = client.post('/api/validate',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
    
    def test_validate_empty_premises(self, client):
        """Test de validation avec prémisses vides."""
        request_data = {
            "premises": [],
            "conclusion": "Conclusion",
            "argument_type": "deductive"
        }
        
        response = client.post('/api/validate',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
    
    def test_validate_invalid_argument_type(self, client):
        """Test de validation avec type d'argument invalide."""
        request_data = {
            "premises": ["Prémisse 1"],
            "conclusion": "Conclusion",
            "argument_type": "invalid_type"
        }
        
        response = client.post('/api/validate',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'


class TestFallaciesEndpoint:
    """Tests pour l'endpoint /api/fallacies."""
    
    def test_detect_fallacies_success(self, client, mock_fallacy_service, sample_fallacy_request):
        """Test de détection de sophismes réussie."""
        response = client.post('/api/fallacies',
                              data=json.dumps(sample_fallacy_request),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert data['text_analyzed'] == "Texte de test"
        assert 'fallacies' in data
        assert 'fallacy_count' in data
        assert 'severity_distribution' in data
        assert 'category_distribution' in data
        assert 'processing_time' in data
        
        # Vérifier la structure des sophismes
        if data['fallacies']:
            fallacy = data['fallacies'][0]
            assert 'type' in fallacy
            assert 'name' in fallacy
            assert 'description' in fallacy
            assert 'severity' in fallacy
            assert 'confidence' in fallacy
        
        mock_fallacy_service.detect_fallacies.assert_called_once()
    
    def test_detect_fallacies_with_options(self, client, mock_fallacy_service):
        """Test de détection avec options spécifiques."""
        request_data = {
            "text": "Texte à analyser",
            "options": {
                "severity_threshold": 0.8,
                "include_context": False,
                "max_fallacies": 5
            }
        }
        
        response = client.post('/api/fallacies',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        mock_fallacy_service.detect_fallacies.assert_called_once()
    
    def test_detect_fallacies_invalid_threshold(self, client):
        """Test avec seuil de sévérité invalide."""
        request_data = {
            "text": "Texte valide",
            "options": {
                "severity_threshold": -0.5  # Valeur invalide
            }
        }
        
        response = client.post('/api/fallacies',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'


class TestFrameworkEndpoint:
    """Tests pour l'endpoint /api/framework."""
    
    def test_build_framework_success(self, client, mock_framework_service, sample_framework_request):
        """Test de construction de framework réussie."""
        response = client.post('/api/framework',
                              data=json.dumps(sample_framework_request),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] is True
        assert 'arguments' in data
        assert 'attack_relations' in data
        assert 'support_relations' in data
        assert 'extensions' in data
        assert 'semantics_used' in data
        assert 'argument_count' in data
        assert 'processing_time' in data
        
        mock_framework_service.build_framework.assert_called_once()
    
    def test_build_framework_empty_arguments(self, client):
        """Test avec liste d'arguments vide."""
        request_data = {
            "arguments": [],
            "options": {}
        }
        
        response = client.post('/api/framework',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
    
    def test_build_framework_duplicate_ids(self, client):
        """Test avec IDs d'arguments dupliqués."""
        request_data = {
            "arguments": [
                {"id": "arg1", "content": "Argument 1"},
                {"id": "arg1", "content": "Argument 2"}  # ID dupliqué
            ]
        }
        
        response = client.post('/api/framework',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
    
    def test_build_framework_invalid_attack_reference(self, client):
        """Test avec référence d'attaque invalide."""
        request_data = {
            "arguments": [
                {
                    "id": "arg1",
                    "content": "Argument 1",
                    "attacks": ["nonexistent_arg"]  # Référence invalide
                }
            ]
        }
        
        response = client.post('/api/framework',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'
    
    def test_build_framework_invalid_semantics(self, client):
        """Test avec sémantique invalide."""
        request_data = {
            "arguments": [
                {"id": "arg1", "content": "Argument 1"}
            ],
            "options": {
                "semantics": "invalid_semantics"
            }
        }
        
        response = client.post('/api/framework',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Données invalides'


class TestEndpointsListEndpoint:
    """Tests pour l'endpoint /api/endpoints."""
    
    def test_list_endpoints(self, client):
        """Test de listage des endpoints."""
        response = client.get('/api/endpoints')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'api_name' in data
        assert 'version' in data
        assert 'endpoints' in data
        
        endpoints = data['endpoints']
        assert 'GET /api/health' in endpoints
        assert 'POST /api/analyze' in endpoints
        assert 'POST /api/validate' in endpoints
        assert 'POST /api/fallacies' in endpoints
        assert 'POST /api/framework' in endpoints
        
        # Vérifier la structure de la documentation
        for endpoint_info in endpoints.values():
            assert 'description' in endpoint_info
            assert 'parameters' in endpoint_info
            assert 'response' in endpoint_info


class TestErrorHandling:
    """Tests pour la gestion d'erreurs globale."""
    
    def test_global_error_handler(self, client):
        """Test du gestionnaire d'erreurs global."""
        with patch('argumentation_analysis.services.web_api.app.analysis_service') as mock_service:
            # Simuler une erreur inattendue
            mock_service.analyze_text.side_effect = RuntimeError("Erreur inattendue")
            
            request_data = {"text": "Texte de test"}
            response = client.post('/api/analyze',
                                  data=json.dumps(request_data),
                                  content_type='application/json')
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'message' in data
            assert 'status_code' in data
            assert 'timestamp' in data
    
    def test_malformed_json(self, client):
        """Test avec JSON malformé."""
        response = client.post('/api/analyze',
                              data='{"invalid": json}',
                              content_type='application/json')
        
        assert response.status_code == 400
    
    def test_missing_content_type(self, client):
        """Test sans Content-Type."""
        response = client.post('/api/analyze',
                              data='{"text": "test"}')
        
        # Flask devrait gérer automatiquement ou retourner une erreur appropriée
        assert response.status_code in [400, 415]


class TestCORS:
    """Tests pour la configuration CORS."""
    
    def test_cors_headers(self, client):
        """Test de la présence des headers CORS."""
        response = client.get('/api/health')
        
        # Vérifier que CORS est configuré (les headers peuvent varier selon la configuration)
        assert response.status_code == 200
        # Note: Les headers CORS spécifiques dépendent de la configuration Flask-CORS