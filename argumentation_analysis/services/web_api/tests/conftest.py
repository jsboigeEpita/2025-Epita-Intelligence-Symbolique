#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration pytest simplifiée pour les tests basiques.
"""

import pytest


@pytest.fixture
def sample_text():
    """Texte d'exemple pour les tests."""
    return "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."


@pytest.fixture
def sample_premises():
    """Prémisses d'exemple pour les tests."""
    return ["Tous les hommes sont mortels", "Socrate est un homme"]


@pytest.fixture
def sample_conclusion():
    """Conclusion d'exemple pour les tests."""
    return "Socrate est mortel"


@pytest.fixture
def sample_analysis_data():
    """Données d'analyse d'exemple."""
    return {
        "text": "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
        "options": {
            "detect_fallacies": True,
            "analyze_structure": True,
            "evaluate_coherence": True
        }
    }


@pytest.fixture
def sample_validation_data():
    """Données de validation d'exemple."""
    return {
        "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
        "conclusion": "Socrate est mortel",
        "argument_type": "deductive"
    }


@pytest.fixture
def sample_fallacy_data():
    """Données de détection de sophismes d'exemple."""
    return {
        "text": "Tu ne peux pas avoir raison car tu es stupide.",
        "options": {
            "severity_threshold": 0.5,
            "include_context": True
        }
    }


@pytest.fixture
def sample_framework_data():
    """Données de framework d'exemple."""
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