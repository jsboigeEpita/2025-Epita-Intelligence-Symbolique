#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration pytest pour les tests de la couche services (web_api).

#1783: the Flask-era fixtures (`client`, `mock_*_service`, `sample_*`)
moved to docs/archives/flask_tests_249/ together with their only
consumer (test_endpoints.py). What remains here serves test_services.py,
which tests the business-logic services preserved by the #217 archive.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))


# Configuration des mocks globaux pour éviter les erreurs d'import
@pytest.fixture(autouse=True)
def mock_analysis_imports():
    """Mock automatique des imports d'analyse pour éviter les erreurs."""
    with patch.dict(
        "sys.modules",
        {
            "argumentation_analysis.agents.core.informal.informal_agent": Mock(),
            "argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer": Mock(),
            "argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer": Mock(),
            "argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator": Mock(),
            "argumentation_analysis.orchestration.hierarchical.operational.manager": Mock(),
        },
    ):
        yield
