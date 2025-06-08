#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Web d'Analyse Argumentative

Cette API Flask expose les fonctionnalités du moteur d'analyse argumentative
pour permettre aux étudiants de créer facilement des interfaces web.

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Équipe d'Analyse Argumentative EPITA"
__description__ = "API Web pour l'analyse argumentative"

from .app import app
from .models import *
from .services import AnalysisService, ValidationService, FallacyService, FrameworkService # Ne pas importer LogicService ici pour l'instant

__all__ = [
    'app',
    'AnalysisService',
    'ValidationService', 
    'FallacyService',
    'FrameworkService',
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