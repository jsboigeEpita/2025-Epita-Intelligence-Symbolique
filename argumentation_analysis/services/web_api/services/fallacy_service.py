#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de détection de sophismes.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Imports du moteur d'analyse (style HEAD)
try:
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer as EnhancedContextualAnalyzer
except ImportError as e:
    logging.warning(f"Impossible d'importer les analyseurs de sophismes: {e}")
    ContextualFallacyAnalyzer = None
    FallacySeverityEvaluator = None
    EnhancedContextualAnalyzer = None

# Imports des modèles (style HEAD, avec FallacyOptions)
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
    
    def _initialize_analyzers(self) -> None:
        """Initialise les différents analyseurs de sophismes (contextuel, sévérité, amélioré).

        Met à jour `self.is_initialized` en fonction du succès.

        :return: None
        :rtype: None
        """
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
            
            # Analyseur contextuel amélioré (selon HEAD)
            if EnhancedContextualAnalyzer: 
                self.enhanced_analyzer = EnhancedContextualAnalyzer()
            else:
                self.enhanced_analyzer = None
            
            self.is_initialized = True
            self.logger.info("Analyseurs de sophismes initialisés")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des analyseurs: {e}")
            self.is_initialized = False
    
    def _load_fallacy_database(self) -> None:
        """Charge la base de données des sophismes."""
        # Utilisation des patterns de la branche 0813790 (plus complets)
        self.fallacy_patterns = {
            # Sophismes logiques formels
            'affirming_consequent': {
                'name': 'Affirmation du conséquent',
                'description': 'Erreur logique qui consiste à affirmer le conséquent dans un raisonnement conditionnel',
                'category': 'formal',
                'patterns': ['si.*alors.*donc.*vrai', 'si.*alors.*donc.*correct'], 
                'severity': 0.8
            },
            'denying_antecedent': {
                'name': 'Négation de l\'antécédent',
                'description': 'Erreur logique qui consiste à nier l\'antécédent dans un raisonnement conditionnel',
                'category': 'formal',
                'patterns': ['si.*pas.*alors.*pas', 'si.*pas.*donc.*pas'], 
                'severity': 0.8
            },
            
            # Sophismes informels
            'ad_hominem': {
                'name': 'Attaque personnelle (Ad Hominem)',
                'description': 'Attaquer la personne plutôt que son argument',
                'category': 'informal',
                'patterns': [ 
                    'parce que.*auteur.*condamné',
                    'parce que.*personne.*condamné',
                    'parce que.*il.*condamné',
                    'parce que.*elle.*condamné',
                    'parce que.*son.*condamné',
                    'parce que.*sa.*condamné',
                    'donc.*faux.*parce que.*personne',
                    'donc.*incorrect.*parce que.*personne',
                    'donc.*invalide.*parce que.*personne'
                ],
                'severity': 0.7
            },
            'straw_man': {
                'name': 'Homme de paille',
                'description': 'Déformer l\'argument de l\'adversaire pour le réfuter plus facilement',
                'category': 'informal',
                'patterns': [ 
                    'vous dites que.*mais',
                    'selon vous.*ce qui est',
                    'votre position.*implique',
                    'vous prétendez que',
                    'vous suggérez que',
                    'vous insinuez que'
                ],
                'severity': 0.8
            },
            'false_dilemma': {
                'name': 'Faux dilemme',
                'description': 'Présenter seulement deux options alors qu\'il en existe d\'autres',
                'category': 'informal',
                'patterns': [ 
                    'soit.*soit',
                    'ou.*ou',
                    'seulement deux',
                    'uniquement deux',
                    'vous devez choisir entre',
                    'il n\'y a que deux',
                    'il n\'y a que deux options'
                ],
                'severity': 0.6
            },
            'slippery_slope': {
                'name': 'Pente glissante',
                'description': 'Affirmer qu\'une action mènera inévitablement à des conséquences extrêmes',
                'category': 'informal',
                'patterns': [ 
                    'si.*alors.*et puis',
                    'si.*alors.*ensuite',
                    'mènera à',
                    'conduira à',
                    'finira par',
                    'inévitablement',
                    'cela va',
                    'cela va finir par',
                    'cela va conduire à'
                ],
                'severity': 0.6
            },
            'appeal_to_authority': {
                'name': 'Appel à l\'autorité',
                'description': 'Invoquer une autorité non pertinente ou fallacieuse',
                'category': 'informal',
                'patterns': [ 
                    'expert dit',
                    'selon.*célèbre',
                    'selon.*médecin',
                    'selon.*professeur',
                    'selon.*docteur',
                    'selon.*spécialiste',
                    'parce que.*mécanicien',
                    'parce que.*expert',
                    'parce que.*professionnel'
                ],
                'severity': 0.5
            },
            'appeal_to_emotion': {
                'name': 'Appel à l\'émotion',
                'description': 'Utiliser les émotions plutôt que la logique pour convaincre',
                'category': 'informal',
                'patterns': [ 
                    'pensez aux enfants',
                    'pensez aux familles',
                    'imaginez la souffrance',
                    'imaginez la douleur',
                    'tragique',
                    'terrible',
                    'horrible',
                    'catastrophique',
                    'désastreux'
                ],
                'severity': 0.6
            },
            'bandwagon': {
                'name': 'Appel à la popularité',
                'description': 'Affirmer qu\'une idée est vraie parce qu\'elle est populaire',
                'category': 'informal',
                'patterns': [ 
                    'tout le monde',
                    'la plupart',
                    'populaire',
                    'majorité',
                    'consensus',
                    'commun',
                    'généralement accepté',
                    'largement reconnu'
                ],
                'severity': 0.5
            },
            'circular_reasoning': {
                'name': 'Raisonnement circulaire',
                'description': 'Utiliser la conclusion comme prémisse',
                'category': 'informal',
                'patterns': [ 
                    'parce que.*c\'est',
                    'car.*donc',
                    'puisque.*c\'est',
                    'car.*c\'est',
                    'parce que.*cela',
                    'car.*cela',
                    'puisque.*cela'
                ],
                'severity': 0.8
            },
            'hasty_generalization': {
                'name': 'Généralisation hâtive',
                'description': 'Tirer une conclusion générale à partir d\'exemples insuffisants',
                'category': 'informal',
                'patterns': [ 
                    'tous.*sont',
                    'toujours',
                    'jamais',
                    'aucun',
                    'personne',
                    'tout le monde',
                    'toujours le cas',
                    'jamais le cas'
                ],
                'severity': 0.6
            }
        }
    
    def is_healthy(self) -> bool:
        """Vérifie si le service de détection de sophismes est opérationnel.

        :return: True si les analyseurs sont initialisés ou si la base de données
                 de patterns de sophismes est chargée, False sinon.
        :rtype: bool
        """
        return self.is_initialized or bool(self.fallacy_patterns)
    
    def detect_fallacies(self, request: FallacyRequest) -> FallacyResponse:
        """
        Détecte les sophismes dans un texte donné en utilisant plusieurs stratégies.

        Combine les résultats des analyseurs configurés (contextuel, amélioré) et
        d'une détection basée sur des patterns. Filtre et déduplique ensuite les
        résultats, et calcule des statistiques de distribution.

        :param request: L'objet `FallacyRequest` contenant le texte à analyser
                        et les options de détection.
        :type request: FallacyRequest
        :return: Un objet `FallacyResponse` contenant la liste des sophismes détectés,
                 des statistiques, et le temps de traitement.
        :rtype: FallacyResponse
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
    
    def _detect_with_contextual_analyzer(self, text: str, options: Optional[FallacyOptions]) -> List[FallacyDetection]:
        """Détecte les sophismes en utilisant `ContextualFallacyAnalyzer`.

        :param text: Le texte à analyser.
        :type text: str
        :param options: Les options de détection (non utilisées directement ici mais passées pour cohérence).
        :type options: Optional[FallacyOptions]
        :return: Une liste d'objets `FallacyDetection`.
        :rtype: List[FallacyDetection]
        """
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
    
    def _detect_with_enhanced_analyzer(self, text: str, options: Optional[FallacyOptions]) -> List[FallacyDetection]:
        """Détecte les sophismes en utilisant `EnhancedContextualAnalyzer`.

        :param text: Le texte à analyser.
        :type text: str
        :param options: Les options de détection (non utilisées directement ici).
        :type options: Optional[FallacyOptions]
        :return: Une liste d'objets `FallacyDetection`.
        :rtype: List[FallacyDetection]
        """
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
    
    def _detect_with_patterns(self, text: str, options: Optional[FallacyOptions]) -> List[FallacyDetection]:
        """Détecte les sophismes en utilisant une base de données interne de patterns.

        :param text: Le texte à analyser (converti en minuscules pour la recherche).
        :type text: str
        :param options: Les options de détection (non utilisées directement ici).
        :type options: Optional[FallacyOptions]
        :return: Une liste d'objets `FallacyDetection`.
        :rtype: List[FallacyDetection]
        """
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
        """Vérifie si un pattern (simplifié) correspond à un texte (insensible à la casse).

        Tente une recherche regex après avoir remplacé '.*' par '.*?'.
        En cas d'échec de la regex, effectue une simple recherche de sous-chaîne.

        :param pattern: Le pattern à rechercher (peut contenir '.*').
        :type pattern: str
        :param text: Le texte dans lequel rechercher.
        :type text: str
        :return: True si le pattern est trouvé, False sinon.
        :rtype: bool
        """
        import re
        
        try:
            # Conversion du pattern simple en regex
            regex_pattern = pattern.replace('.*', r'.*?')
            return bool(re.search(regex_pattern, text, re.IGNORECASE))
        except Exception:
            # Fallback: recherche simple
            return pattern.replace('.*', '') in text
    
    def _extract_context(self, text: str, position: int, context_size: int = 50) -> Optional[str]:
        """Extrait une portion de texte (contexte) autour d'une position donnée.

        :param text: Le texte source complet.
        :type text: str
        :param position: La position centrale autour de laquelle extraire le contexte.
        :type position: int
        :param context_size: Le nombre de caractères à inclure avant et après la position.
        :type context_size: int
        :return: La chaîne de caractères du contexte, ou None si la position est invalide.
        :rtype: Optional[str]
        """
        if position < 0:
            return None
        
        start = max(0, position - context_size)
        end = min(len(text), position + context_size)
        
        return text[start:end].strip()
    
    def _filter_and_deduplicate(self, fallacies: List[FallacyDetection], options: Optional[FallacyOptions]) -> List[FallacyDetection]:
        """Filtre les sophismes par sévérité et catégories, puis déduplique les résultats.

        La déduplication est basée sur le type de sophisme et la position de début.
        Limite également le nombre total de sophismes retournés.

        :param fallacies: La liste brute des `FallacyDetection` à traiter.
        :type fallacies: List[FallacyDetection]
        :param options: Les `FallacyOptions` contenant les seuils, catégories et limites.
        :type options: Optional[FallacyOptions]
        :return: Une liste filtrée, dédupliquée et limitée de `FallacyDetection`.
        :rtype: List[FallacyDetection]
        """
        # Filtrage par seuil de sévérité
        threshold = options.severity_threshold if options and options.severity_threshold is not None else 0.5
        filtered = [f for f in fallacies if f.severity >= threshold]
        
        # Filtrage par catégories si spécifié
        if options and options.categories:
            # category_map = {info['name']: key for key, info in self.fallacy_patterns.items()} # Non utilisé
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
        max_fallacies = options.max_fallacies if options and options.max_fallacies is not None else 10
        return deduplicated[:max_fallacies]
    
    def _calculate_severity_distribution(self, fallacies: List[FallacyDetection]) -> Dict[str, int]:
        """Calcule la distribution des sophismes détectés par niveau de sévérité.

        Les niveaux sont "low" (<0.4), "medium" (0.4-0.7), "high" (>=0.7).

        :param fallacies: Liste des objets `FallacyDetection`.
        :type fallacies: List[FallacyDetection]
        :return: Un dictionnaire avec les comptes pour chaque niveau de sévérité.
        :rtype: Dict[str, int]
        """
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
        """Calcule la distribution des sophismes détectés par catégorie.

        Les catégories sont dérivées de `self.fallacy_patterns`.

        :param fallacies: Liste des objets `FallacyDetection`.
        :type fallacies: List[FallacyDetection]
        :return: Un dictionnaire où les clés sont les catégories de sophismes
                 et les valeurs sont le nombre de sophismes détectés dans cette catégorie.
        :rtype: Dict[str, int]
        """
        distribution = {}
        
        for fallacy in fallacies:
            # Déterminer la catégorie
            category = 'unknown'
            if fallacy.type in self.fallacy_patterns:
                category = self.fallacy_patterns[fallacy.type]['category']
            
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution
    
    def get_fallacy_types(self) -> Dict[str, Dict[str, Any]]:
        """Retourne un dictionnaire des types de sophismes supportés et leurs détails.

        Les détails incluent le nom, la description, la catégorie et la sévérité
        tels que définis dans `self.fallacy_patterns`.

        :return: Un dictionnaire où les clés sont les identifiants des types de sophismes
                 et les valeurs sont des dictionnaires de leurs attributs.
        :rtype: Dict[str, Dict[str, Any]]
        """
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
        """Retourne une liste unique des catégories de sophismes définies.

        Les catégories sont extraites de `self.fallacy_patterns`.

        :return: Une liste de chaînes de caractères, chaque chaîne étant une catégorie.
        :rtype: List[str]
        """
        categories = set()
        for info in self.fallacy_patterns.values():
            categories.add(info['category'])
        return list(categories)