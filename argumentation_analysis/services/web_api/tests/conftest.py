#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration pytest pour les tests de l'API web.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Import de l'application Flask
from argumentation_analysis.services.web_api.app import app # MODIFIÉ


@pytest.fixture
def client():
    """Client de test Flask."""
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def mock_analysis_service():
    """Mock du service d'analyse."""
    with patch('services.web_api.app.analysis_service') as mock:
        # Configuration du mock pour is_healthy
        mock.is_healthy.return_value = True
        
        # Configuration du mock pour analyze_text
        from ..models.response_models import AnalysisResponse, ArgumentStructure
        mock_response = AnalysisResponse(
            success=True,
            text_analyzed="Texte de test",
            fallacies=[],
            argument_structure=ArgumentStructure(
                premises=["Prémisse 1"],
                conclusion="Conclusion",
                argument_type="deductive",
                strength=0.8,
                coherence=0.7
            ),
            overall_quality=0.8,
            coherence_score=0.7,
            fallacy_count=0,
            processing_time=0.1,
            analysis_options={}
        )
        mock.analyze_text.return_value = mock_response
        yield mock


@pytest.fixture
def mock_validation_service():
    """Mock du service de validation."""
    with patch('services.web_api.app.validation_service') as mock:
        mock.is_healthy.return_value = True
        
        from ..models.response_models import ValidationResponse, ValidationResult
        mock_response = ValidationResponse(
            success=True,
            premises=["Prémisse 1"],
            conclusion="Conclusion",
            argument_type="deductive",
            result=ValidationResult(
                is_valid=True,
                validity_score=0.9,
                soundness_score=0.8,
                premise_analysis=[],
                conclusion_analysis={},
                logical_structure={},
                issues=[],
                suggestions=[]
            ),
            processing_time=0.1
        )
        mock.validate_argument.return_value = mock_response
        yield mock


@pytest.fixture
def mock_fallacy_service():
    """Mock du service de détection de sophismes."""
    with patch('services.web_api.app.fallacy_service') as mock:
        mock.is_healthy.return_value = True
        
        from ..models.response_models import FallacyResponse, FallacyDetection
        mock_response = FallacyResponse(
            success=True,
            text_analyzed="Texte de test",
            fallacies=[
                FallacyDetection(
                    type="ad_hominem",
                    name="Attaque personnelle",
                    description="Attaque contre la personne plutôt que l'argument",
                    severity=0.7,
                    confidence=0.8,
                    context="Contexte du sophisme"
                )
            ],
            fallacy_count=1,
            severity_distribution={"high": 1},
            category_distribution={"personal_attack": 1},
            processing_time=0.1,
            detection_options={}
        )
        mock.detect_fallacies.return_value = mock_response
        yield mock


@pytest.fixture
def mock_framework_service():
    """Mock du service de framework."""
    with patch('services.web_api.app.framework_service') as mock:
        mock.is_healthy.return_value = True
        
        from ..models.response_models import FrameworkResponse, ArgumentNode, Extension
        mock_response = FrameworkResponse(
            success=True,
            arguments=[
                ArgumentNode(
                    id="arg1",
                    content="Argument 1",
                    status="accepted",
                    attacks=[],
                    attacked_by=[],
                    supports=[],
                    supported_by=[]
                )
            ],
            attack_relations=[],
            support_relations=[],
            extensions=[
                Extension(
                    type="preferred",
                    arguments=["arg1"],
                    is_complete=True,
                    is_preferred=True
                )
            ],
            semantics_used="preferred",
            argument_count=1,
            attack_count=0,
            support_count=0,
            extension_count=1,
            processing_time=0.1,
            framework_options={}
        )
        mock.build_framework.return_value = mock_response
        yield mock


@pytest.fixture
def sample_analysis_request():
    """Requête d'analyse d'exemple."""
    return {
        "text": "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
        "options": {
            "detect_fallacies": True,
            "analyze_structure": True,
            "evaluate_coherence": True
        }
    }


@pytest.fixture
def sample_validation_request():
    """Requête de validation d'exemple."""
    return {
        "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
        "conclusion": "Socrate est mortel",
        "argument_type": "deductive"
    }


@pytest.fixture
def sample_fallacy_request():
    """Requête de détection de sophismes d'exemple."""
    return {
        "text": "Tu ne peux pas avoir raison car tu es stupide.",
        "options": {
            "severity_threshold": 0.5,
            "include_context": True
        }
    }


@pytest.fixture
def sample_framework_request():
    """Requête de framework d'exemple."""
    return {
        "arguments": [
            {
                "id": "arg1",
                "content": "Il faut protéger l'environnement",
                "attacks": ["arg2"]
            },
            {
                "id": "arg2",
                "content": "Le développement économique est prioritaire",
                "attacks": ["arg1"]
            }
        ],
        "options": {
            "compute_extensions": True,
            "semantics": "preferred"
        }
    }


@pytest.fixture
def invalid_json_data():
    """Données JSON invalides pour les tests d'erreur."""
    return {
        "text": "",  # Texte vide
        "options": {
            "severity_threshold": 2.0  # Valeur invalide
        }
    }


# Configuration des mocks globaux pour éviter les erreurs d'import
@pytest.fixture(autouse=True)
def mock_analysis_imports():
    """Mock automatique des imports d'analyse pour éviter les erreurs."""
    with patch.dict('sys.modules', {
        'argumentation_analysis.agents.core.informal.informal_agent': Mock(),
        'argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer': Mock(),
        'argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer': Mock(),
        'argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator': Mock(),
        'argumentation_analysis.orchestration.hierarchical.operational.manager': Mock(),
    }):
        yield