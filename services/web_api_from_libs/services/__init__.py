#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Services pour l'API Web d'analyse argumentative.
"""

from .analysis_service import AnalysisService
from .validation_service import ValidationService
from .fallacy_service import FallacyService
from .framework_service import FrameworkService

import sys
import os
# Tentative d'ajout explicite du chemin du projet parent pour résoudre l'import
project_root_for_libs = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root_for_libs not in sys.path:
    sys.path.insert(0, project_root_for_libs)
    # print(f"DEBUG: Added to sys.path from libs/web_api/services: {project_root_for_libs}") # Ligne de débogage commentée

from argumentation_analysis.services.web_api.logic_service import LogicService

__all__ = [
    'LogicService',
    'AnalysisService',
    'ValidationService',
    'FallacyService',
    'FrameworkService'
]