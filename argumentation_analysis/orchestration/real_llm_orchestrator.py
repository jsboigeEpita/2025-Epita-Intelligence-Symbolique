#!/usr/bin/env python3
"""
Orchestrateur LLM réel pour l'analyse d'argumentation
==================================================

Orchestrateur authentique utilisant des LLMs réels pour l'analyse d'argumentation
en intégrant toutes les capacités du système unifié.
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from datetime import datetime

# Import des composants internes
from ..analyzers.syntactic_analyzer import SyntacticAnalyzer
from ..analyzers.semantic_analyzer import SemanticAnalyzer  
from ..analyzers.pragmatic_analyzer import PragmaticAnalyzer
from ..analyzers.logical_analyzer import LogicalAnalyzer
from ..extraction.entity_extractor import EntityExtractor
from ..extraction.relation_extractor import RelationExtractor
from ..validation.consistency_validator import ConsistencyValidator
from ..validation.coherence_validator import CoherenceValidator
from ..utils.error_handler import ErrorHandler
from ..pipelines.unified_text_analysis import UnifiedTextAnalyzer


@dataclass
class LLMAnalysisRequest:
    """Structure pour les requêtes d'analyse LLM."""
    text: str
    analysis_type: str
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    timeout: int = 30


@dataclass
class LLMAnalysisResult:
    """Structure pour les résultats d'analyse LLM."""
    request_id: str
    analysis_type: str
    result: Dict[str, Any]
    confidence: float
    processing_time: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class RealLLMOrchestrator:
    """
    Orchestrateur LLM réel pour coordonner l'analyse d'argumentation.
    
    Cette classe utilise de vrais LLMs pour effectuer des analyses sophistiquées
    d'argumentation en coordonnant tous les composants du système.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'orchestrateur LLM.
        
        Args:
            config: Configuration optionnelle pour l'orchestrateur
        """
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
        # État de l'orchestrateur
        self.is_initialized = False
        self.active_sessions = {}
        self.analysis_cache = {}
        
        # Composants d'analyse
        self.syntactic_analyzer = None
        self.semantic_analyzer = None
        self.pragmatic_analyzer = None
        self.logical_analyzer = None
        self.entity_extractor = None
        self.relation_extractor = None
        self.consistency_validator = None
        self.coherence_validator = None
        self.unified_analyzer = None
        self.error_handler = None
        
        # Métriques et monitoring
        self.metrics = {
            'total_requests': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        self.logger.info("RealLLMOrchestrator initialisé")
    
    def _default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut."""
        return {
            'max_concurrent_analyses': 10,
            'default_timeout': 30,
            'cache_enabled': True,
            'cache_ttl': 3600,  # 1 heure
            'retry_attempts': 3,
            'retry_delay': 1.0,
            'enable_metrics': True,
            'log_level': 'INFO',
            'analysis_types': [
                'syntactic',
                'semantic', 
                'pragmatic',
                'logical',
                'entity_extraction',
                'relation_extraction',
                'consistency_validation',
                'coherence_validation',
                'unified_analysis'
            ]
        }
    
    async def initialize(self) -> bool:
        """
        Initialise tous les composants de l'orchestrateur.
        
        Returns:
            bool: True si l'initialisation réussit
        """
        try:
            self.logger.info("Initialisation des composants d'analyse...")
            
            # Initialiser les analyseurs
            self.syntactic_analyzer = SyntacticAnalyzer()
            self.semantic_analyzer = SemanticAnalyzer()
            self.pragmatic_analyzer = PragmaticAnalyzer()
            self.logical_analyzer = LogicalAnalyzer()
            
            # Initialiser les extracteurs
            self.entity_extractor = EntityExtractor()
            self.relation_extractor = RelationExtractor()
            
            # Initialiser les validateurs
            self.consistency_validator = ConsistencyValidator()
            self.coherence_validator = CoherenceValidator()
            
            # Initialiser l'analyseur unifié
            self.unified_analyzer = UnifiedTextAnalyzer()
            
            # Initialiser le gestionnaire d'erreurs
            self.error_handler = ErrorHandler()
            
            self.is_initialized = True
            self.logger.info("Tous les composants initialisés avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            self.is_initialized = False
            return False
    
    async def analyze_text(self, request: LLMAnalysisRequest) -> LLMAnalysisResult:
        """
        Analyse un texte selon le type d'analyse demandé.
        
        Args:
            request: Requête d'analyse LLM
            
        Returns:
            LLMAnalysisResult: Résultat de l'analyse
        """
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000000)}"
        
        try:
            self.metrics['total_requests'] += 1
            
            # Vérifier le cache si activé
            if self.config['cache_enabled']:
                cached_result = self._get_cached_result(request)
                if cached_result:
                    self.metrics['cache_hits'] += 1
                    self.logger.debug(f"Résultat trouvé en cache pour {request_id}")
                    return cached_result
                
                self.metrics['cache_misses'] += 1
            
            # Effectuer l'analyse selon le type
            result = await self._perform_analysis(request)
            
            # Calculer le temps de traitement
            processing_time = time.time() - start_time
            
            # Créer le résultat
            analysis_result = LLMAnalysisResult(
                request_id=request_id,
                analysis_type=request.analysis_type,
                result=result,
                confidence=result.get('confidence', 0.8),
                processing_time=processing_time,
                timestamp=datetime.now(),
                metadata={
                    'request_params': request.parameters,
                    'context': request.context
                }
            )
            
            # Mettre en cache si activé
            if self.config['cache_enabled']:
                self._cache_result(request, analysis_result)
            
            # Mettre à jour les métriques
            self.metrics['successful_analyses'] += 1
            self._update_average_processing_time(processing_time)
            
            self.logger.info(f"Analyse {request_id} terminée en {processing_time:.2f}s")
            return analysis_result
            
        except Exception as e:
            self.metrics['failed_analyses'] += 1
            self.logger.error(f"Erreur lors de l'analyse {request_id}: {e}")
            
            # Retourner un résultat d'erreur
            return LLMAnalysisResult(
                request_id=request_id,
                analysis_type=request.analysis_type,
                result={'error': str(e), 'success': False},
                confidence=0.0,
                processing_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={'error': True}
            )
    
    async def _perform_analysis(self, request: LLMAnalysisRequest) -> Dict[str, Any]:
        """
        Effectue l'analyse selon le type demandé.
        
        Args:
            request: Requête d'analyse
            
        Returns:
            Dict: Résultat de l'analyse
        """
        analysis_type = request.analysis_type.lower()
        text = request.text
        context = request.context or {}
        parameters = request.parameters or {}
        
        if analysis_type == 'syntactic':
            return await self._analyze_syntactic(text, context, parameters)
        elif analysis_type == 'semantic':
            return await self._analyze_semantic(text, context, parameters)
        elif analysis_type == 'pragmatic':
            return await self._analyze_pragmatic(text, context, parameters)
        elif analysis_type == 'logical':
            return await self._analyze_logical(text, context, parameters)
        elif analysis_type == 'entity_extraction':
            return await self._extract_entities(text, context, parameters)
        elif analysis_type == 'relation_extraction':
            return await self._extract_relations(text, context, parameters)
        elif analysis_type == 'consistency_validation':
            return await self._validate_consistency(text, context, parameters)
        elif analysis_type == 'coherence_validation':
            return await self._validate_coherence(text, context, parameters)
        elif analysis_type == 'unified_analysis':
            return await self._unified_analysis(text, context, parameters)
        else:
            raise ValueError(f"Type d'analyse non supporté: {analysis_type}")
    
    async def _analyze_syntactic(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Analyse syntaxique du texte."""
        try:
            result = self.syntactic_analyzer.analyze(text)
            return {
                'success': True,
                'analysis_type': 'syntactic',
                'result': result,
                'confidence': 0.9,
                'metadata': {'method': 'syntactic_analyzer'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _analyze_semantic(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Analyse sémantique du texte."""
        try:
            result = self.semantic_analyzer.analyze(text)
            return {
                'success': True,
                'analysis_type': 'semantic',
                'result': result,
                'confidence': 0.85,
                'metadata': {'method': 'semantic_analyzer'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _analyze_pragmatic(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Analyse pragmatique du texte."""
        try:
            result = self.pragmatic_analyzer.analyze(text, context)
            return {
                'success': True,
                'analysis_type': 'pragmatic',
                'result': result,
                'confidence': 0.8,
                'metadata': {'method': 'pragmatic_analyzer'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _analyze_logical(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Analyse logique du texte."""
        try:
            result = self.logical_analyzer.analyze(text)
            return {
                'success': True,
                'analysis_type': 'logical',
                'result': result,
                'confidence': 0.9,
                'metadata': {'method': 'logical_analyzer'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _extract_entities(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Extraction d'entités du texte."""
        try:
            entities = self.entity_extractor.extract(text)
            return {
                'success': True,
                'analysis_type': 'entity_extraction',
                'entities': entities,
                'count': len(entities),
                'confidence': 0.85,
                'metadata': {'method': 'entity_extractor'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _extract_relations(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Extraction de relations du texte."""
        try:
            relations = self.relation_extractor.extract(text)
            return {
                'success': True,
                'analysis_type': 'relation_extraction',
                'relations': relations,
                'count': len(relations),
                'confidence': 0.8,
                'metadata': {'method': 'relation_extractor'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _validate_consistency(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Validation de cohérence du texte."""
        try:
            result = self.consistency_validator.validate(text)
            return {
                'success': True,
                'analysis_type': 'consistency_validation',
                'is_consistent': result.get('is_consistent', False),
                'issues': result.get('issues', []),
                'confidence': result.get('confidence', 0.8),
                'metadata': {'method': 'consistency_validator'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _validate_coherence(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Validation de cohérence du texte."""
        try:
            result = self.coherence_validator.validate(text)
            return {
                'success': True,
                'analysis_type': 'coherence_validation',
                'is_coherent': result.get('is_coherent', False),
                'score': result.get('score', 0.0),
                'confidence': result.get('confidence', 0.8),
                'metadata': {'method': 'coherence_validator'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _unified_analysis(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Analyse unifiée complète du texte."""
        try:
            result = self.unified_analyzer.analyze_text(text)
            return {
                'success': True,
                'analysis_type': 'unified_analysis',
                'result': result,
                'confidence': result.get('metadata', {}).get('confidence', 0.8),
                'metadata': {'method': 'unified_analyzer'}
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_cached_result(self, request: LLMAnalysisRequest) -> Optional[LLMAnalysisResult]:
        """Récupère un résultat du cache."""
        cache_key = self._generate_cache_key(request)
        return self.analysis_cache.get(cache_key)
    
    def _cache_result(self, request: LLMAnalysisRequest, result: LLMAnalysisResult):
        """Met en cache un résultat."""
        cache_key = self._generate_cache_key(request)
        self.analysis_cache[cache_key] = result
    
    def _generate_cache_key(self, request: LLMAnalysisRequest) -> str:
        """Génère une clé de cache pour la requête."""
        import hashlib
        content = f"{request.text}:{request.analysis_type}:{json.dumps(request.parameters, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _update_average_processing_time(self, new_time: float):
        """Met à jour le temps de traitement moyen."""
        total_successful = self.metrics['successful_analyses']
        current_avg = self.metrics['average_processing_time']
        
        if total_successful == 1:
            self.metrics['average_processing_time'] = new_time
        else:
            self.metrics['average_processing_time'] = (
                (current_avg * (total_successful - 1) + new_time) / total_successful
            )
    
    async def batch_analyze(self, requests: List[LLMAnalysisRequest]) -> List[LLMAnalysisResult]:
        """
        Effectue des analyses en lot.
        
        Args:
            requests: Liste de requêtes d'analyse
            
        Returns:
            List[LLMAnalysisResult]: Résultats des analyses
        """
        if not self.is_initialized:
            await self.initialize()
        
        # Limiter la concurrence
        max_concurrent = self.config['max_concurrent_analyses']
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(request):
            async with semaphore:
                return await self.analyze_text(request)
        
        # Lancer les analyses en parallèle
        tasks = [analyze_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Erreur dans l'analyse batch {i}: {result}")
                processed_results.append(LLMAnalysisResult(
                    request_id=f"batch_error_{i}",
                    analysis_type=requests[i].analysis_type,
                    result={'error': str(result), 'success': False},
                    confidence=0.0,
                    processing_time=0.0,
                    timestamp=datetime.now(),
                    metadata={'error': True, 'batch_index': i}
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de l'orchestrateur."""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Remet à zéro les métriques."""
        self.metrics = {
            'total_requests': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def clear_cache(self):
        """Vide le cache d'analyse."""
        self.analysis_cache.clear()
        self.logger.info("Cache d'analyse vidé")
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état de l'orchestrateur."""
        return {
            'is_initialized': self.is_initialized,
            'active_sessions': len(self.active_sessions),
            'cache_size': len(self.analysis_cache),
            'config': self.config,
            'metrics': self.metrics
        }


# Point d'entrée pour les tests
async def main():
    """Fonction principale pour tester l'orchestrateur."""
    orchestrator = RealLLMOrchestrator()
    await orchestrator.initialize()
    
    # Test simple
    request = LLMAnalysisRequest(
        text="Ce texte est un exemple d'argumentation logique.",
        analysis_type="unified_analysis"
    )
    
    result = await orchestrator.analyze_text(request)
    print(f"Résultat: {result}")
    
    # Afficher les métriques
    print(f"Métriques: {orchestrator.get_metrics()}")


if __name__ == "__main__":
    asyncio.run(main())


# Logger du module  
logger = logging.getLogger(__name__)
logger.debug("Module real_llm_orchestrator chargé.")
