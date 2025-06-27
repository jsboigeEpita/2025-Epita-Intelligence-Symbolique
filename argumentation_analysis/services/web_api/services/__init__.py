#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Services pour l'API Web d'analyse argumentative.
"""

# Import conditionnel pour éviter les erreurs de dépendances
# Les services sont importés directement par app.py selon disponibilité

__all__ = [
    'AnalysisService',
    'ValidationService',
    'FallacyService',
    'FrameworkService'
]

# Note: Les imports sont maintenant gérés directement dans app.py
# avec fallback vers fallback_services.py si nécessaire