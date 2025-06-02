#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Services pour l'API Web d'analyse argumentative.
"""

from .analysis_service import AnalysisService
from .validation_service import ValidationService
from .fallacy_service import FallacyService
from .framework_service import FrameworkService

__all__ = [
    'AnalysisService',
    'ValidationService',
    'FallacyService',
    'FrameworkService'
]