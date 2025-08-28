#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service d'analyse complète utilisant le moteur d'analyse argumentative.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Imports du moteur d'analyse
try:
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
    from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
except ImportError as e:
    logging.warning(f"Impossible d'importer les modules d'analyse: {e}")
    # Mode dégradé pour les tests
    InformalAgent = None
    ComplexFallacyAnalyzer = None
    ContextualFallacyAnalyzer = None
    FallacySeverityEvaluator = None
    OperationalManager = None

# Imports des modèles
from ..models.request_models import AnalysisRequest
from ..models.response_models import (
    AnalysisResponse, FallacyDetection, ArgumentStructure
)

logger = logging.getLogger("AnalysisService")


class AnalysisService:
    """
    Service pour l'analyse complète de textes argumentatifs.
    
    Ce service utilise le moteur d'analyse existant pour fournir
    une analyse complète incluant la détection de sophismes,
    l'analyse de structure et l'évaluation de cohérence.
    """
    
    def __init__(self, complex_analyzer=None, contextual_analyzer=None, severity_evaluator=None, informal_agent=None):
        """Initialise le service d'analyse avec injection de dépendances."""
        self.logger = logger
        self.complex_analyzer = complex_analyzer
        self.contextual_analyzer = contextual_analyzer
        self.severity_evaluator = severity_evaluator
        self.informal_agent = informal_agent
        self.is_initialized = True  # L'initialisation est maintenant gérée en amont
        self.logger.info("Service d'analyse initialisé avec les dépendances injectées.")
        self.health_check()

    def health_check(self):
        """Vérifie et logue l'état des composants injectés."""
        self.logger.info("=== DIAGNOSTIC ANALYSIS SERVICE ===")
        self.logger.info(f"✅ ComplexFallacyAnalyzer: {'Présent' if self.complex_analyzer else 'Absent'}")
        self.logger.info(f"✅ ContextualFallacyAnalyzer: {'Présent' if self.contextual_analyzer else 'Absent'}")
        self.logger.info(f"✅ FallacySeverityEvaluator: {'Présent' if self.severity_evaluator else 'Absent'}")
        self.logger.info(f"✅ InformalAgent: {'Présent' if self.informal_agent else 'Absent'}")
    
    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service."""
        has_informal = self.informal_agent is not None
        has_analyzers = any([self.complex_analyzer, self.contextual_analyzer, self.severity_evaluator])
        is_healthy = self.is_initialized and (has_informal or has_analyzers)
        
        self.logger.info(f"=== HEALTH CHECK ===")
        self.logger.info(f"is_initialized: {self.is_initialized}")
        self.logger.info(f"has_informal_agent: {has_informal}")
        self.logger.info(f"has_analyzers: {has_analyzers}")
        self.logger.info(f"overall_health: {is_healthy}")
        
        return is_healthy
    
    async def analyze_text(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Analyse complète d'un texte argumentatif.
        
        Args:
            request: Requête d'analyse
            
        Returns:
            Réponse avec les résultats d'analyse
        """
        start_time = time.time()
        
        try:
            # Vérification de l'état du service
            if not self.is_healthy():
                return self._create_fallback_response(request, start_time)
            
            # Analyse des sophismes
            fallacies = await self._detect_fallacies(request.text, request.options)
            
            # Analyse de la structure argumentative
            structure = await self._analyze_structure(request.text, request.options)
            
            # Calcul des métriques globales
            overall_quality = self._calculate_overall_quality(fallacies, structure)
            coherence_score = self._calculate_coherence_score(structure)
            
            processing_time = time.time() - start_time
            
            return AnalysisResponse(
                success=True,
                text_analyzed=request.text,
                fallacies=fallacies,
                argument_structure=structure,
                overall_quality=overall_quality,
                coherence_score=coherence_score,
                fallacy_count=len(fallacies),
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {}
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {e}")
            processing_time = time.time() - start_time
            
            return AnalysisResponse(
                success=False,
                text_analyzed=request.text,
                fallacies=[],
                argument_structure=None,
                overall_quality=0.0,
                coherence_score=0.0,
                fallacy_count=0,
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {}
            )
    
    async def _detect_fallacies(self, text: str, options) -> List[FallacyDetection]:
        """Détecte les sophismes dans le texte."""
        fallacies = []
        
        try:
            # Utilisation de l'agent informel si disponible
            if self.informal_agent:
                result = await self.informal_agent.analyze_text(text)
                if result and 'fallacies' in result:
                    for fallacy_data in result['fallacies']:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get('type', 'unknown'),
                            name=fallacy_data.get('name', 'Sophisme non identifié'),
                            description=fallacy_data.get('description', ''),
                            severity=fallacy_data.get('severity', 0.5),
                            confidence=fallacy_data.get('confidence', 0.5),
                            location=fallacy_data.get('location'),
                            context=fallacy_data.get('context'),
                            explanation=fallacy_data.get('explanation')
                        )
                        fallacies.append(fallacy)
            
            # Analyse contextuelle si disponible
            elif self.contextual_analyzer:
                # L'appel correct est `identify_contextual_fallacies` avec un contexte vide par défaut
                result = self.contextual_analyzer.identify_contextual_fallacies(text, "")
                if result:
                    for fallacy_data in result:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get('type', 'contextual'),
                            name=fallacy_data.get('name', 'Sophisme contextuel'),
                            description=fallacy_data.get('description', ''),
                            severity=fallacy_data.get('severity', 0.5),
                            confidence=fallacy_data.get('confidence', 0.5),
                            context=fallacy_data.get('context')
                        )
                        fallacies.append(fallacy)
            
            # Filtrage par seuil de sévérité
            if options and hasattr(options, 'severity_threshold'):
                fallacies = [f for f in fallacies if f.severity >= options.severity_threshold]
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection de sophismes: {e}")
        
        return fallacies
    
    async def _analyze_structure(self, text: str, options) -> Optional[ArgumentStructure]:
        """Analyse la structure argumentative du texte."""
        try:
            # Analyse basique de structure
            # TODO: Intégrer avec les outils d'analyse de structure existants
            
            # Détection simple de prémisses et conclusion
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            
            if len(sentences) < 2:
                return ArgumentStructure(
                    premises=[],
                    conclusion=text,
                    argument_type="simple",
                    strength=0.3,
                    coherence=0.3
                )
            
            # Heuristique simple: dernière phrase = conclusion
            conclusion = sentences[-1]
            premises = sentences[:-1]
            
            # Calcul de la force et cohérence (simplifié)
            strength = min(0.8, len(premises) * 0.2 + 0.4)
            coherence = 0.7 if len(premises) > 1 else 0.5
            
            return ArgumentStructure(
                premises=premises,
                conclusion=conclusion,
                argument_type="deductive" if len(premises) > 1 else "simple",
                strength=strength,
                coherence=coherence
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de structure: {e}")
            return None
    
    def _calculate_overall_quality(self, fallacies: List[FallacyDetection], structure: Optional[ArgumentStructure]) -> float:
        """Calcule la qualité globale de l'argument."""
        try:
            # Score basé sur le nombre et la sévérité des sophismes
            fallacy_penalty = sum(f.severity for f in fallacies) * 0.1
            fallacy_score = max(0.0, 1.0 - fallacy_penalty)
            
            # Score basé sur la structure
            structure_score = structure.strength if structure else 0.3
            
            # Score global (moyenne pondérée)
            overall = (fallacy_score * 0.6 + structure_score * 0.4)
            return min(1.0, max(0.0, overall))
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de qualité: {e}")
            return 0.5
    
    def _calculate_coherence_score(self, structure: Optional[ArgumentStructure]) -> float:
        """Calcule le score de cohérence."""
        try:
            if structure:
                return structure.coherence
            return 0.3
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de cohérence: {e}")
            return 0.3
    
    def _create_fallback_response(self, request: AnalysisRequest, start_time: float) -> AnalysisResponse:
        """Crée une réponse de fallback en cas de problème."""
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            success=False,
            text_analyzed=request.text,
            fallacies=[],
            argument_structure=ArgumentStructure(
                premises=[],
                conclusion=request.text,
                argument_type="unknown",
                strength=0.0,
                coherence=0.0
            ),
            overall_quality=0.0,
            coherence_score=0.0,
            fallacy_count=0,
            processing_time=processing_time,
            analysis_options=request.options.dict() if request.options else {}
        )