#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests d'integration pour l'API d'analyse argumentative via Flask TestClient.
=============================================================================

DEPRECATED: Flask app archived in #242. Use FastAPI tests via api/main.py instead.
Archive: docs/archives/flask_tests_249/test_argument_analyzer_client.py

Equivalent in-process des tests Playwright API de test_argument_analyzer.py.
Ne necessite PAS de serveur backend en cours d'execution.
"""

import pytest
import json
import logging

logger = logging.getLogger(__name__)

# Flask app has been archived - skip all tests in this module
pytestmark = pytest.mark.skip(
    reason="Flask app archived (#242). Use FastAPI: uvicorn api.main:app --port 8000",
)
