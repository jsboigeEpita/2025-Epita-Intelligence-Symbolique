#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Services de fallback simples pour permettre le démarrage de l'API
même quand certaines dépendances sont manquantes
"""

from typing import Dict, Any, List
from datetime import datetime

class FallbackAnalysisService:
    """Service d'analyse de fallback"""
    
    def analyze_text(self, request) -> Any:
        return {
            'analysis_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'message': 'Service d\'analyse en mode fallback',
            'fallacies': [],
            'structure': {'type': 'simple', 'elements': []},
            'coherence': {'score': 0.5, 'details': 'Mode fallback'}
        }

class FallbackValidationService:
    """Service de validation de fallback"""
    
    def validate_argument(self, request) -> Any:
        return {
            'validation_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'is_valid': True,
            'message': 'Validation en mode fallback',
            'details': 'Service de validation non disponible'
        }

class FallbackFallacyService:
    """Service de détection de sophismes de fallback"""
    
    def detect_fallacies(self, request) -> Any:
        return {
            'detection_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'fallacies': [],
            'message': 'Détection de sophismes en mode fallback'
        }

class FallbackFrameworkService:
    """Service de framework de fallback"""
    
    def build_framework(self, request) -> Any:
        return {
            'framework_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'arguments': [],
            'relations': [],
            'extensions': [],
            'message': 'Framework en mode fallback'
        }

class FallbackLogicService:
    """Service de logique de fallback"""
    
    def text_to_belief_set(self, request) -> Any:
        return {
            'belief_set_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'beliefs': [],
            'message': 'Conversion en mode fallback'
        }
    
    def execute_query(self, request) -> Any:
        return {
            'query_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'result': False,
            'explanation': 'Requête en mode fallback',
            'message': 'Service de logique non disponible'
        }
    
    def generate_queries(self, request) -> Any:
        return {
            'generation_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'queries': [],
            'message': 'Génération de requêtes en mode fallback'
        }
    
    def interpret_results(self, request) -> Any:
        return {
            'interpretation_id': f'fallback_{datetime.now().timestamp()}',
            'status': 'completed',
            'interpretation': 'Interprétation en mode fallback',
            'confidence': 0.0,
            'message': 'Service d\'interprétation non disponible'
        }