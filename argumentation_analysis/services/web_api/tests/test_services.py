#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour les services de l'API web.
"""

import os
import sys

# Ajouter le répertoire racine du projet au PYTHONPATH
# Cela permet aux tests d'importer les modules du projet correctement
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import pytest
from unittest.mock import Mock, patch, MagicMock
from libs.web_api.models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest,
    AnalysisOptions, FallacyOptions, FrameworkOptions, Argument
)


class TestAnalysisService:
    """Tests pour le service d'analyse."""
    
    @pytest.fixture
    def analysis_service(self):
        """Instance du service d'analyse avec mocks."""
        with patch.dict('sys.modules', {
            'argumentation_analysis.agents.core.informal.informal_agent': Mock(),
            'argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator': Mock(),
            'argumentation_analysis.orchestration.hierarchical.operational.manager': Mock(),
        }):
            from libs.web_api.services.analysis_service import AnalysisService
            return AnalysisService()
    
    def test_service_initialization(self, analysis_service):
        """Test de l'initialisation du service."""
        assert analysis_service is not None
        # Le service peut être initialisé même sans les modules d'analyse
        assert hasattr(analysis_service, 'is_initialized')
    
    def test_is_healthy(self, analysis_service):
        """Test de la vérification de santé du service."""
        health_status = analysis_service.is_healthy()
        assert isinstance(health_status, bool)
    
    def test_analyze_text_basic(self, analysis_service):
        """Test d'analyse de texte basique."""
        request = AnalysisRequest(
            text="Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        )
        
        response = analysis_service.analyze_text(request)
        
        assert response is not None
        assert hasattr(response, 'success')
        assert hasattr(response, 'text_analyzed')
        assert hasattr(response, 'processing_time')
        assert response.text_analyzed == request.text
    
    def test_analyze_text_with_options(self, analysis_service):
        """Test d'analyse avec options spécifiques."""
        options = AnalysisOptions(
            detect_fallacies=True,
            analyze_structure=True,
            evaluate_coherence=True,
            severity_threshold=0.7
        )
        request = AnalysisRequest(
            text="Argument avec sophisme potentiel",
            options=options
        )
        
        response = analysis_service.analyze_text(request)
        
        assert response is not None
        assert response.analysis_options == options.dict()
    
    def test_analyze_empty_text_handling(self, analysis_service):
        """Test de gestion du texte vide (devrait être géré par la validation Pydantic)."""
        with pytest.raises(ValueError):
            AnalysisRequest(text="")
    
    def test_fallback_response(self, analysis_service):
        """Test de la réponse de fallback."""
        # Simuler un service non sain
        analysis_service.is_initialized = False
        
        request = AnalysisRequest(text="Texte de test")
        response = analysis_service.analyze_text(request)
        
        assert response is not None
        assert response.success is False
        assert response.overall_quality == 0.0


class TestValidationService:
    """Tests pour le service de validation."""
    
    @pytest.fixture
    def validation_service(self):
        """Instance du service de validation."""
        from libs.web_api.services.validation_service import ValidationService
        return ValidationService()
    
    def test_service_initialization(self, validation_service):
        """Test de l'initialisation du service."""
        assert validation_service is not None
        assert hasattr(validation_service, 'is_healthy')
    
    def test_is_healthy(self, validation_service):
        """Test de la vérification de santé."""
        health_status = validation_service.is_healthy()
        assert isinstance(health_status, bool)
    
    def test_validate_deductive_argument(self, validation_service):
        """Test de validation d'un argument déductif."""
        request = ValidationRequest(
            premises=["Tous les hommes sont mortels", "Socrate est un homme"],
            conclusion="Socrate est mortel",
            argument_type="deductive"
        )
        
        response = validation_service.validate_argument(request)
        
        assert response is not None
        assert hasattr(response, 'success')
        assert hasattr(response, 'result')
        assert response.premises == request.premises
        assert response.conclusion == request.conclusion
        assert response.argument_type == request.argument_type
    
    def test_validate_inductive_argument(self, validation_service):
        """Test de validation d'un argument inductif."""
        request = ValidationRequest(
            premises=["Le soleil s'est levé tous les jours jusqu'à présent"],
            conclusion="Le soleil se lèvera demain",
            argument_type="inductive"
        )
        
        response = validation_service.validate_argument(request)
        
        assert response is not None
        assert response.argument_type == "inductive"
    
    def test_validate_invalid_premises(self):
        """Test de validation avec prémisses invalides."""
        with pytest.raises(ValueError):
            ValidationRequest(
                premises=[],  # Liste vide
                conclusion="Conclusion",
                argument_type="deductive"
            )
    
    def test_validate_invalid_argument_type(self):
        """Test avec type d'argument invalide."""
        with pytest.raises(ValueError):
            ValidationRequest(
                premises=["Prémisse"],
                conclusion="Conclusion",
                argument_type="invalid_type"
            )


class TestFallacyService:
    """Tests pour le service de détection de sophismes."""
    
    @pytest.fixture
    def fallacy_service(self):
        """Instance du service de détection de sophismes."""
        with patch.dict('sys.modules', {
            'argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator': Mock(),
        }):
            from libs.web_api.services.fallacy_service import FallacyService
            return FallacyService()
    
    def test_service_initialization(self, fallacy_service):
        """Test de l'initialisation du service."""
        assert fallacy_service is not None
        assert hasattr(fallacy_service, 'is_healthy')
    
    def test_is_healthy(self, fallacy_service):
        """Test de la vérification de santé."""
        health_status = fallacy_service.is_healthy()
        assert isinstance(health_status, bool)
    
    def test_detect_fallacies_basic(self, fallacy_service):
        """Test de détection de sophismes basique."""
        request = FallacyRequest(
            text="Tu ne peux pas avoir raison car tu es stupide."
        )
        
        response = fallacy_service.detect_fallacies(request)
        
        assert response is not None
        assert hasattr(response, 'success')
        assert hasattr(response, 'fallacies')
        assert hasattr(response, 'fallacy_count')
        assert response.text_analyzed == request.text
    
    def test_detect_fallacies_with_options(self, fallacy_service):
        """Test de détection avec options."""
        options = FallacyOptions(
            severity_threshold=0.8,
            include_context=True,
            max_fallacies=5
        )
        request = FallacyRequest(
            text="Texte avec sophismes potentiels",
            options=options
        )
        
        response = fallacy_service.detect_fallacies(request)
        
        assert response is not None
        assert response.detection_options == options.dict()
    
    def test_fallacy_options_validation(self):
        """Test de validation des options de détection."""
        # Test avec seuil invalide
        with pytest.raises(ValueError):
            FallacyOptions(severity_threshold=2.0)  # > 1.0
        
        with pytest.raises(ValueError):
            FallacyOptions(severity_threshold=-0.5)  # < 0.0
        
        # Test avec nombre maximum invalide
        with pytest.raises(ValueError):
            FallacyOptions(max_fallacies=0)  # < 1
        
        with pytest.raises(ValueError):
            FallacyOptions(max_fallacies=100)  # > 50


class TestFrameworkService:
    """Tests pour le service de framework."""
    
    @pytest.fixture
    def framework_service(self):
        """Instance du service de framework."""
        from libs.web_api.services.framework_service import FrameworkService
        return FrameworkService()
    
    def test_service_initialization(self, framework_service):
        """Test de l'initialisation du service."""
        assert framework_service is not None
        assert hasattr(framework_service, 'is_healthy')
    
    def test_is_healthy(self, framework_service):
        """Test de la vérification de santé."""
        health_status = framework_service.is_healthy()
        assert isinstance(health_status, bool)
    
    def test_build_simple_framework(self, framework_service):
        """Test de construction d'un framework simple."""
        arguments = [
            Argument(id="arg1", content="Argument 1"),
            Argument(id="arg2", content="Argument 2", attacks=["arg1"])
        ]
        request = FrameworkRequest(arguments=arguments)
        
        response = framework_service.build_framework(request)
        
        assert response is not None
        assert hasattr(response, 'success')
        assert hasattr(response, 'arguments')
        assert hasattr(response, 'extensions')
        assert response.argument_count == len(arguments)
    
    def test_build_framework_with_options(self, framework_service):
        """Test de construction avec options."""
        arguments = [Argument(id="arg1", content="Argument 1")]
        options = FrameworkOptions(
            compute_extensions=True,
            semantics="preferred",
            include_visualization=True
        )
        request = FrameworkRequest(arguments=arguments, options=options)
        
        response = framework_service.build_framework(request)
        
        assert response is not None
        assert response.framework_options == options.dict()
        assert response.semantics_used == "preferred"
    
    def test_framework_argument_validation(self):
        """Test de validation des arguments du framework."""
        # Test avec ID dupliqué
        with pytest.raises(ValueError):
            arguments = [
                Argument(id="arg1", content="Argument 1"),
                Argument(id="arg1", content="Argument 2")  # ID dupliqué
            ]
            FrameworkRequest(arguments=arguments)
        
        # Test avec référence d'attaque invalide
        with pytest.raises(ValueError):
            arguments = [
                Argument(id="arg1", content="Argument 1", attacks=["nonexistent"])
            ]
            FrameworkRequest(arguments=arguments)
    
    def test_framework_options_validation(self):
        """Test de validation des options du framework."""
        # Test avec sémantique invalide
        with pytest.raises(ValueError):
            FrameworkOptions(semantics="invalid_semantics")
        
        # Test avec nombre maximum d'arguments invalide
        with pytest.raises(ValueError):
            FrameworkOptions(max_arguments=0)  # < 1
        
        with pytest.raises(ValueError):
            FrameworkOptions(max_arguments=2000)  # > 1000


class TestServiceIntegration:
    """Tests d'intégration entre services."""
    
    def test_all_services_health_check(self):
        """Test de vérification de santé de tous les services."""
        with patch.dict('sys.modules', {
            'argumentation_analysis.agents.core.informal.informal_agent': Mock(),
            'argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator': Mock(),
            'argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer': Mock(),
            'argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator': Mock(),
        }):
            from ..services.analysis_service import AnalysisService
            from ..services.validation_service import ValidationService
            from ..services.fallacy_service import FallacyService
            from ..services.framework_service import FrameworkService
            
            services = [
                AnalysisService(),
                ValidationService(),
                FallacyService(),
                FrameworkService()
            ]
            
            for service in services:
                health_status = service.is_healthy()
                assert isinstance(health_status, bool)
    
    def test_service_error_handling(self):
        """Test de gestion d'erreurs dans les services."""
        with patch.dict('sys.modules', {
            'argumentation_analysis.agents.core.informal.informal_agent': Mock(),
        }):
            from ..services.analysis_service import AnalysisService
            
            service = AnalysisService()
            
            # Simuler une erreur lors de l'analyse
            with patch.object(service, '_detect_fallacies', side_effect=Exception("Erreur test")):
                request = AnalysisRequest(text="Texte de test")
                response = service.analyze_text(request)
                
                # Le service devrait gérer l'erreur gracieusement
                assert response is not None
                assert response.success is False


class TestModelValidation:
    """Tests de validation des modèles de données."""
    
    def test_analysis_request_validation(self):
        """Test de validation des requêtes d'analyse."""
        # Requête valide
        request = AnalysisRequest(text="Texte valide")
        assert request.text == "Texte valide"
        
        # Texte vide
        with pytest.raises(ValueError):
            AnalysisRequest(text="")
        
        # Texte avec espaces seulement
        with pytest.raises(ValueError):
            AnalysisRequest(text="   ")
    
    def test_validation_request_validation(self):
        """Test de validation des requêtes de validation."""
        # Requête valide
        request = ValidationRequest(
            premises=["Prémisse 1", "Prémisse 2"],
            conclusion="Conclusion"
        )
        assert len(request.premises) == 2
        
        # Prémisses vides
        with pytest.raises(ValueError):
            ValidationRequest(premises=[], conclusion="Conclusion")
        
        # Conclusion vide
        with pytest.raises(ValueError):
            ValidationRequest(premises=["Prémisse"], conclusion="")
    
    def test_argument_validation(self):
        """Test de validation des arguments."""
        # Argument valide
        arg = Argument(id="arg1", content="Contenu de l'argument")
        assert arg.id == "arg1"
        assert arg.content == "Contenu de l'argument"
        
        # ID vide
        with pytest.raises(ValueError):
            Argument(id="", content="Contenu")
        
        # Contenu vide
        with pytest.raises(ValueError):
            Argument(id="arg1", content="")