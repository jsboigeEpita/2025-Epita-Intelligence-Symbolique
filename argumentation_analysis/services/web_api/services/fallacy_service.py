#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de détection de sophismes.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Imports du moteur d'analyse
try:
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer as EnhancedContextualAnalyzer
except ImportError as e:
    logging.warning(f"Impossible d'importer les analyseurs de sophismes: {e}")
    ContextualFallacyAnalyzer = None
    FallacySeverityEvaluator = None
    EnhancedContextualAnalyzer = None

from ..models.request_models import FallacyRequest, FallacyOptions
from ..models.response_models import FallacyResponse, FallacyDetection

logger = logging.getLogger("FallacyService")


class FallacyService:
    """
    Service pour la détection de sophismes dans les textes.
    
    Ce service utilise les analyseurs de sophismes existants
    pour identifier et évaluer les erreurs de raisonnement.
    """
    
    def __init__(self):
        """Initialise le service de détection de sophismes."""
        self.logger = logger
        self.is_initialized = False
        self._initialize_analyzers()
        self._load_fallacy_database()
    
    def _initialize_analyzers(self):
        """Initialise les analyseurs de sophismes."""
        try:
            # Analyseur contextuel
            if ContextualFallacyAnalyzer:
                self.contextual_analyzer = ContextualFallacyAnalyzer()
            else:
                self.contextual_analyzer = None
            
            # Évaluateur de sévérité
            if FallacySeverityEvaluator:
                self.severity_evaluator = FallacySeverityEvaluator()
            else:
                self.severity_evaluator = None
            
            # Analyseur contextuel amélioré
            if EnhancedContextualAnalyzer:
                self.enhanced_analyzer = EnhancedContextualAnalyzer()
            else:
                self.enhanced_analyzer = None
            
            self.is_initialized = True
            self.logger.info("Analyseurs de sophismes initialisés")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des analyseurs: {e}")
            self.is_initialized = False
    
    def _load_fallacy_database(self):
        """Charge la base de données des sophismes."""
        self.fallacy_patterns = {
            # Sophismes logiques formels
            'affirming_consequent': {
                'name': 'Affirmation du conséquent',
                'description': 'Erreur logique qui consiste à affirmer le conséquent dans un raisonnement conditionnel',
                'category': 'formal',
                'patterns': ['si.*alors', 'donc.*vrai'],
                'severity': 0.8
            },
            'denying_antecedent': {
                'name': 'Négation de l\'antécédent',
                'description': 'Erreur logique qui consiste à nier l\'antécédent dans un raisonnement conditionnel',
                'category': 'formal',
                'patterns': ['si.*pas', 'donc.*pas'],
                'severity': 0.8
            },
            
            # Sophismes informels
            'ad_hominem': {
                'name': 'Attaque personnelle (Ad Hominem)',
                'description': 'Attaquer la personne plutôt que son argument',
                'category': 'informal',
                'patterns': ['vous êtes', 'tu es', 'il/elle est.*donc'],
                'severity': 0.7
            },
            'straw_man': {
                'name': 'Homme de paille',
                'description': 'Déformer l\'argument de l\'adversaire pour le réfuter plus facilement',
                'category': 'informal',
                'patterns': ['vous dites que', 'selon vous', 'votre position'],
                'severity': 0.8
            },
            'false_dilemma': {
                'name': 'Faux dilemme',
                'description': 'Présenter seulement deux options alors qu\'il en existe d\'autres',
                'category': 'informal',
                'patterns': ['soit.*soit', 'ou.*ou', 'seulement deux'],
                'severity': 0.6
            },
            'slippery_slope': {
                'name': 'Pente glissante',
                'description': 'Affirmer qu\'une action mènera inévitablement à des conséquences extrêmes',
                'category': 'informal',
                'patterns': ['si.*alors.*et puis', 'mènera à', 'conséquences'],
                'severity': 0.6
            },
            'appeal_to_authority': {
                'name': 'Appel à l\'autorité',
                'description': 'Invoquer une autorité non pertinente ou fallacieuse',
                'category': 'informal',
                'patterns': ['expert dit', 'selon.*célèbre', 'autorité'],
                'severity': 0.5
            },
            'appeal_to_emotion': {
                'name': 'Appel à l\'émotion',
                'description': 'Utiliser les émotions plutôt que la logique pour convaincre',
                'category': 'informal',
                'patterns': ['pensez aux enfants', 'tragique', 'terrible'],
                'severity': 0.6
            },
            'bandwagon': {
                'name': 'Appel à la popularité',
                'description': 'Affirmer qu\'une idée est vraie parce qu\'elle est populaire',
                'category': 'informal',
                'patterns': ['tout le monde', 'la plupart', 'populaire'],
                'severity': 0.5
            },
            'circular_reasoning': {
                'name': 'Raisonnement circulaire',
                'description': 'Utiliser la conclusion comme prémisse',
                'category': 'informal',
                'patterns': ['parce que.*c\'est', 'car.*donc'],
                'severity': 0.8
            },
            'hasty_generalization': {
                'name': 'Généralisation hâtive',
                'description': 'Tirer une conclusion générale à partir d\'exemples insuffisants',
                'category': 'informal',
                'patterns': ['tous.*sont', 'toujours', 'jamais'],
                'severity': 0.6
            }
        }
    
    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service."""
        return self.is_initialized or bool(self.fallacy_patterns)
    
    def detect_fallacies(self, request: FallacyRequest) -> FallacyResponse:
        """
        Détecte les sophismes dans un texte.
        
        Args:
            request: Requête de détection
            
        Returns:
            Réponse avec les sophismes détectés
        """
        start_time = time.time()
        
        try:
            fallacies = []
            
            # Détection avec les analyseurs existants
            if self.contextual_analyzer:
                fallacies.extend(self._detect_with_contextual_analyzer(request.text, request.options))
            
            if self.enhanced_analyzer:
                fallacies.extend(self._detect_with_enhanced_analyzer(request.text, request.options))
            
            # Détection avec les patterns intégrés
            fallacies.extend(self._detect_with_patterns(request.text, request.options))
            
            # Filtrage et déduplication
            fallacies = self._filter_and_deduplicate(fallacies, request.options)
            
            # Calcul des statistiques
            severity_distribution = self._calculate_severity_distribution(fallacies)
            category_distribution = self._calculate_category_distribution(fallacies)
            
            processing_time = time.time() - start_time
            
            return FallacyResponse(
                success=True,
                text_analyzed=request.text,
                fallacies=fallacies,
                fallacy_count=len(fallacies),
                severity_distribution=severity_distribution,
                category_distribution=category_distribution,
                processing_time=processing_time,
                detection_options=request.options.dict() if request.options else {}
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection: {e}")
            processing_time = time.time() - start_time
            
            return FallacyResponse(
                success=False,
                text_analyzed=request.text,
                fallacies=[],
                fallacy_count=0,
                severity_distribution={},
                category_distribution={},
                processing_time=processing_time,
                detection_options=request.options.dict() if request.options else {}
            )
    
    def _detect_with_contextual_analyzer(self, text: str, options) -> List[FallacyDetection]:
        """Détection avec l'analyseur contextuel."""
        fallacies = []
        
        try:
            if self.contextual_analyzer:
                results = self.contextual_analyzer.analyze_fallacies(text)
                
                if results:
                    for result in results:
                        fallacy = FallacyDetection(
                            type=result.get('type', 'contextual'),
                            name=result.get('name', 'Sophisme contextuel'),
                            description=result.get('description', ''),
                            severity=result.get('severity', 0.5),
                            confidence=result.get('confidence', 0.7),
                            location=result.get('location'),
                            context=result.get('context'),
                            explanation=result.get('explanation')
                        )
                        fallacies.append(fallacy)
        
        except Exception as e:
            self.logger.error(f"Erreur analyseur contextuel: {e}")
        
        return fallacies
    
    def _detect_with_enhanced_analyzer(self, text: str, options) -> List[FallacyDetection]:
        """Détection avec l'analyseur amélioré."""
        fallacies = []
        
        try:
            if self.enhanced_analyzer:
                results = self.enhanced_analyzer.analyze_fallacies(text)
                
                if results:
                    for result in results:
                        fallacy = FallacyDetection(
                            type=result.get('type', 'enhanced'),
                            name=result.get('name', 'Sophisme détecté'),
                            description=result.get('description', ''),
                            severity=result.get('severity', 0.6),
                            confidence=result.get('confidence', 0.8),
                            location=result.get('location'),
                            context=result.get('context'),
                            explanation=result.get('explanation')
                        )
                        fallacies.append(fallacy)
        
        except Exception as e:
            self.logger.error(f"Erreur analyseur amélioré: {e}")
        
        return fallacies
    
    def _detect_with_patterns(self, text: str, options) -> List[FallacyDetection]:
        """Détection avec les patterns de sophismes intégrés."""
        fallacies = []
        text_lower = text.lower()
        
        try:
            for fallacy_type, fallacy_info in self.fallacy_patterns.items():
                # Vérification des patterns
                for pattern in fallacy_info['patterns']:
                    if self._pattern_matches(pattern, text_lower):
                        # Calcul de la position approximative
                        position = text_lower.find(pattern.split('.*')[0] if '.*' in pattern else pattern)
                        
                        fallacy = FallacyDetection(
                            type=fallacy_type,
                            name=fallacy_info['name'],
                            description=fallacy_info['description'],
                            severity=fallacy_info['severity'],
                            confidence=0.6,  # Confiance modérée pour les patterns
                            location={'start': position, 'end': position + len(pattern)} if position >= 0 else None,
                            context=self._extract_context(text, position) if position >= 0 else None,
                            explanation=f"Pattern détecté: {pattern}"
                        )
                        fallacies.append(fallacy)
                        break  # Un seul match par type de sophisme
        
        except Exception as e:
            self.logger.error(f"Erreur détection patterns: {e}")
        
        return fallacies
    
    def _pattern_matches(self, pattern: str, text: str) -> bool:
        """Vérifie si un pattern correspond au texte."""
        import re
        
        try:
            # Conversion du pattern simple en regex
            regex_pattern = pattern.replace('.*', r'.*?')
            return bool(re.search(regex_pattern, text, re.IGNORECASE))
        except Exception:
            # Fallback: recherche simple
            return pattern.replace('.*', '') in text
    
    def _extract_context(self, text: str, position: int, context_size: int = 50) -> str:
        """Extrait le contexte autour d'une position."""
        if position < 0:
            return None
        
        start = max(0, position - context_size)
        end = min(len(text), position + context_size)
        
        return text[start:end].strip()
    
    def _filter_and_deduplicate(self, fallacies: List[FallacyDetection], options) -> List[FallacyDetection]:
        """Filtre et déduplique les sophismes détectés."""
        # Filtrage par seuil de sévérité
        threshold = options.severity_threshold if options else 0.5
        filtered = [f for f in fallacies if f.severity >= threshold]
        
        # Filtrage par catégories si spécifié
        if options and options.categories:
            category_map = {info['name']: key for key, info in self.fallacy_patterns.items()}
            filtered = [f for f in filtered if f.type in options.categories or f.name in options.categories]
        
        # Déduplication basée sur le type et la position
        seen = set()
        deduplicated = []
        
        for fallacy in filtered:
            key = (fallacy.type, fallacy.location.get('start', 0) if fallacy.location else 0)
            if key not in seen:
                seen.add(key)
                deduplicated.append(fallacy)
        
        # Limitation du nombre de résultats
        max_fallacies = options.max_fallacies if options else 10
        return deduplicated[:max_fallacies]
    
    def _calculate_severity_distribution(self, fallacies: List[FallacyDetection]) -> Dict[str, int]:
        """Calcule la distribution par sévérité."""
        distribution = {'low': 0, 'medium': 0, 'high': 0}
        
        for fallacy in fallacies:
            if fallacy.severity < 0.4:
                distribution['low'] += 1
            elif fallacy.severity < 0.7:
                distribution['medium'] += 1
            else:
                distribution['high'] += 1
        
        return distribution
    
    def _calculate_category_distribution(self, fallacies: List[FallacyDetection]) -> Dict[str, int]:
        """Calcule la distribution par catégorie."""
        distribution = {}
        
        for fallacy in fallacies:
            # Déterminer la catégorie
            category = 'unknown'
            if fallacy.type in self.fallacy_patterns:
                category = self.fallacy_patterns[fallacy.type]['category']
            
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution
    
    def get_fallacy_types(self) -> Dict[str, Any]:
        """Retourne la liste des types de sophismes supportés."""
        return {
            fallacy_type: {
                'name': info['name'],
                'description': info['description'],
                'category': info['category'],
                'severity': info['severity']
            }
            for fallacy_type, info in self.fallacy_patterns.items()
        }
    
    def get_categories(self) -> List[str]:
        """Retourne la liste des catégories de sophismes."""
        categories = set()
        for info in self.fallacy_patterns.values():
            categories.add(info['category'])
        return list(categories)