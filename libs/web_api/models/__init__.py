#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modèles de données pour l'API Web d'analyse argumentative.
"""

from .request_models import (
    AnalysisRequest,
    ValidationRequest,
    FallacyRequest,
    FrameworkRequest
)

from .response_models import (
    AnalysisResponse,
    ValidationResponse,
    FallacyResponse,
    FrameworkResponse,
    ErrorResponse
)

__all__ = [
    'AnalysisRequest',
    'ValidationRequest',
    'FallacyRequest',
    'FrameworkRequest',
    'AnalysisResponse',
    'ValidationResponse',
    'FallacyResponse',
    'FrameworkResponse',
    'ErrorResponse'
]